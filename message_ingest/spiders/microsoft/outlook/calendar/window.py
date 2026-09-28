"""Acquire one bounded Microsoft Calendar view with recurrence expansion."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from datetime import datetime
from typing import Any
from urllib.parse import quote, urlencode

from scrapy.http import TextResponse
from scrapy.settings import BaseSettings

from message_ingest.items.microsoft.outlook.calendar import OutlookCalendarEventItem

from ._base import OutlookCalendarSpider
from ._resume_state import CalendarScopedExecutionState, execution_payload


class OutlookCalendarWindowSpider(OutlookCalendarSpider):
    """Read one explicit Calendar time window through Graph calendarView."""

    name = "outlook_calendar_window"

    def __init__(
        self,
        *args,
        start_datetime: str = "",
        end_datetime: str = "",
        calendar_id: str = "",
        page_size: str = "100",
        **kwargs,
    ) -> None:
        """Validate the declared Calendar collection scope."""
        super().__init__(*args, **kwargs)
        self.start_datetime = self._window_datetime(
            start_datetime, name="start_datetime"
        )
        self.end_datetime = self._window_datetime(end_datetime, name="end_datetime")
        start = self._parsed_datetime(self.start_datetime)
        end = self._parsed_datetime(self.end_datetime)
        if start >= end:
            raise ValueError("start_datetime must be earlier than end_datetime")
        self.calendar_id = calendar_id.strip()
        if calendar_id != self.calendar_id:
            raise ValueError("calendar_id must not contain surrounding whitespace")
        self.page_size = self._bounded_int(
            page_size, name="page_size", minimum=1, maximum=1000
        )
        self.state: dict[str, Any] = {}
        self._job_resumed = False

    @classmethod
    def update_settings(cls, settings: BaseSettings) -> None:
        """Declare Calendar permissions and resource-specific components."""
        settings.set(
            "MSGLOOM_DELTA_CHECKPOINT_ENABLED",
            False,
            priority="spider",
        )
        settings.set(
            "MSGLOOM_CRAWL_STATUS_ENABLED",
            False,
            priority="spider",
        )
        extensions = settings.getdict("EXTENSIONS")
        extensions["scrapy.extensions.spiderstate.SpiderState"] = None
        extensions[
            "message_ingest.extensions.microsoft.outlook.calendar.resume.CalendarWindowSpiderState"
        ] = 0
        settings.set("EXTENSIONS", extensions, priority="spider")
        settings.set(
            "ITEM_PIPELINES",
            {
                "message_ingest.pipelines.evidence.RawEvidencePipeline": 200,
                "message_ingest.acquisition.evidence_link.EvidenceLinkPipeline": 250,
                "message_ingest.pipelines.microsoft.outlook.calendar.OutlookCalendarPipeline": 300,
            },
            priority="spider",
        )
        super().update_settings(settings)

    async def start(self) -> AsyncIterator[Any]:
        """Regenerate the fixed-window start; JOBDIR dupefilter owns replay."""
        self._persist_execution_state()
        self.crawler.stats.set_value("msgloom/crawl/mode", "calendar_window")
        self.crawler.stats.set_value("msgloom/crawl/run_id", self.run_id)
        self.crawler.stats.set_value(
            "msgloom/crawl/calendar/job_resumed", self._job_resumed
        )
        self.crawler.stats.set_value(
            "msgloom/crawl/calendar/pagination_exhausted",
            False,
        )
        self.crawler.stats.set_value(
            "msgloom/crawl/calendar/window_start",
            self.start_datetime,
        )
        self.crawler.stats.set_value(
            "msgloom/crawl/calendar/window_end",
            self.end_datetime,
        )
        base = self._mailbox_url("/calendar/calendarView")
        calendar_key = "default"
        if self.calendar_id:
            encoded = quote(self.calendar_id, safe="")
            base = self._mailbox_url(f"/calendars/{encoded}/calendarView")
            calendar_key = self.calendar_id
        query = urlencode(
            {
                "startDateTime": self.start_datetime,
                "endDateTime": self.end_datetime,
                "$top": self.page_size,
            }
        )
        yield self._request(
            f"{base}?{query}",
            callback=self.parse_events,
            purpose="calendar-window-page",
            cb_kwargs={"calendar_id": calendar_key},
            prefer='IdType="ImmutableId"',
        )

    def parse_events(
        self,
        response: TextResponse,
        *,
        calendar_id: str,
        purpose: str,
    ) -> Iterator[Any]:
        """Yield page evidence, event versions, and opaque continuation."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence

        payload = response.json()
        if not isinstance(payload, dict):
            raise TypeError("Calendar response must be a JSON object")
        values = payload.get("value")
        if not isinstance(values, list):
            raise TypeError("Calendar response must contain a value list")

        self.crawler.stats.inc_value("msgloom/crawl/calendar/page_count")
        for event in values:
            if not isinstance(event, dict):
                raise TypeError("Calendar event must be a JSON object")
            event_id = event.get("id")
            if not isinstance(event_id, str) or not event_id:
                raise ValueError("Calendar event must contain a non-empty id")
            self.crawler.stats.inc_value("msgloom/crawl/calendar/event_count")
            yield OutlookCalendarEventItem(
                event_id=event_id,
                raw=event,
                observed_at=evidence.observed_at,
                evidence_id=evidence.evidence_id,
                run_id=self.run_id,
                calendar_id=calendar_id,
                observation_kind="window",
            )

        next_link = payload.get("@odata.nextLink")
        if next_link is None:
            self.crawler.stats.set_value(
                "msgloom/crawl/calendar/pagination_exhausted",
                True,
            )
            return
        if not isinstance(next_link, str) or not next_link:
            raise ValueError("Calendar @odata.nextLink must be a non-empty string")

        self.crawler.stats.inc_value("msgloom/crawl/calendar/continuation_count")
        yield self._request(
            next_link,
            callback=self.parse_events,
            purpose="calendar-window-page",
            cb_kwargs={"calendar_id": calendar_id},
            verbatim_url=True,
            prefer='IdType="ImmutableId"',
        )

    def _resume_scope(self) -> dict[str, object]:
        return {
            "start_datetime": self.start_datetime,
            "end_datetime": self.end_datetime,
            "calendar_id": self.calendar_id,
            "page_size": self.page_size,
        }

    def _restore_execution_state(self) -> None:
        restored, resumed = CalendarScopedExecutionState.restore(
            self.state.get("msgloom_calendar_window"),
            expected_scope=self._resume_scope(),
            default_run_id=self.run_id,
            label="window",
        )
        self.run_id = restored.run_id
        self._run_failed = restored.run_failed
        self._failure_reasons = set(restored.failure_reasons)
        self._job_resumed = resumed
        self._persist_execution_state()

    def _persist_execution_state(self) -> None:
        self.state["msgloom_calendar_window"] = execution_payload(
            run_id=self.run_id,
            scope=self._resume_scope(),
            run_failed=self._run_failed,
            failure_reasons=self._failure_reasons,
        )

    def mark_run_failed(self, reason: str) -> None:
        super().mark_run_failed(reason)
        self._persist_execution_state()

    @classmethod
    def _window_datetime(cls, raw: str, *, name: str) -> str:
        """Validate a timezone-aware ISO-8601 window boundary."""
        value = raw.strip()
        if not value:
            raise ValueError(f"{name} is required")
        if raw != value:
            raise ValueError(f"{name} must not contain surrounding whitespace")
        cls._parsed_datetime(value)
        return value

    @staticmethod
    def _parsed_datetime(value: str) -> datetime:
        """Parse one ISO-8601 value while accepting the common Z suffix."""
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(
                "Calendar window values must be valid ISO-8601 datetimes"
            ) from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("Calendar window datetimes must include an offset")
        return parsed
