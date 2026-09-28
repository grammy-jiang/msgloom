"""Incrementally synchronize one fixed primary-calendar view."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from datetime import datetime
from typing import Any, ClassVar
from urllib.parse import urlencode

import scrapy
from scrapy.http import TextResponse
from scrapy.settings import BaseSettings
from twisted.python.failure import Failure

from message_ingest.items.acquisition import AcquisitionFailureItem
from message_ingest.items.microsoft.outlook.calendar import (
    OutlookCalendarDeltaCheckpointCandidateItem,
    OutlookCalendarDeltaObservationItem,
    OutlookCalendarEventItem,
)
from message_ingest.spiders.microsoft._graph import MicrosoftGraphSpider
from message_ingest.sync.microsoft.outlook.calendar.checkpoints import (
    CalendarDeltaCheckpointStore,
)

from ._delta_state import CalendarDeltaExecutionState, execution_payload


class OutlookCalendarDeltaSpider(MicrosoftGraphSpider):
    """Track changes inside one fixed primary-calendar time window."""

    name = "outlook_calendar_delta"
    graph_permissions: ClassVar[tuple[str, ...]] = ("Calendars.Read",)
    failure_context_keys = ("start_datetime", "end_datetime")
    calendar_scope = "default"

    def __init__(
        self,
        *args,
        start_datetime: str = "",
        end_datetime: str = "",
        page_size: str = "100",
        **kwargs,
    ) -> None:
        """Validate one immutable Calendar delta scope."""
        super().__init__(*args, **kwargs)
        self.start_datetime = self._window_datetime(
            start_datetime, name="start_datetime"
        )
        self.end_datetime = self._window_datetime(end_datetime, name="end_datetime")
        if self._parsed_datetime(self.start_datetime) >= self._parsed_datetime(
            self.end_datetime
        ):
            raise ValueError("start_datetime must be earlier than end_datetime")
        self.page_size = self._bounded_int(
            page_size, name="page_size", minimum=1, maximum=1000
        )
        self.state: dict[str, Any] = {}
        self.attempt = 0
        self.base_revision: int | None = None
        self._terminal_delta_seen = False
        self._delta_start_scheduled = False

    @classmethod
    def update_settings(cls, settings: BaseSettings) -> None:
        """Enable least-privilege Calendar delta components."""
        settings.set("MSGLOOM_DELTA_CHECKPOINT_ENABLED", False, priority="spider")
        extensions = settings.getdict("EXTENSIONS")
        extensions["scrapy.extensions.spiderstate.SpiderState"] = None
        extensions[
            "message_ingest.extensions.microsoft.outlook.calendar.checkpoint.CalendarDeltaSpiderState"
        ] = 0
        settings.set("EXTENSIONS", extensions, priority="spider")
        settings.set(
            "REQUEST_FINGERPRINTER_CLASS",
            "message_ingest.fingerprints.CalendarDeltaRequestFingerprinter",
            priority="spider",
        )
        settings.set(
            "MSGLOOM_CALENDAR_DELTA_CHECKPOINT_ENABLED",
            True,
            priority="spider",
        )
        settings.set("MSGLOOM_CRAWL_STATUS_ENABLED", False, priority="spider")
        settings.set(
            "ITEM_PIPELINES",
            {
                "message_ingest.pipelines.evidence.RawEvidencePipeline": 200,
                "message_ingest.acquisition.evidence_link.EvidenceLinkPipeline": 250,
                "message_ingest.pipelines.calendar.CalendarPipeline": 300,
            },
            priority="spider",
        )
        super().update_settings(settings)

    async def start(self) -> AsyncIterator[Any]:
        """
        Load one committed cursor or continue queued JOBDIR execution state.

        Scrapy SpiderState owns only execution facts and queued Requests.
        Provider delta links remain transactional catalog checkpoints.
        """
        self._restore_execution_state()
        self.crawler.stats.set_value("msgloom/crawl/mode", "calendar_delta")
        self.crawler.stats.set_value("msgloom/crawl/run_id", self.run_id)
        self.crawler.stats.set_value(
            "msgloom/crawl/calendar/delta/window_start",
            self.start_datetime,
        )
        self.crawler.stats.set_value(
            "msgloom/crawl/calendar/delta/window_end",
            self.end_datetime,
        )

        if self._delta_start_scheduled:
            self.crawler.stats.set_value(
                "msgloom/crawl/calendar/delta/job_resumed",
                True,
            )
            if self.base_revision is not None:
                self.crawler.stats.set_value(
                    "msgloom/crawl/calendar/delta/checkpoint_revision",
                    self.base_revision,
                )
            return

        store = CalendarDeltaCheckpointStore.from_crawler(
            self.crawler,
            start_datetime=self.start_datetime,
            end_datetime=self.end_datetime,
            calendar_scope=self.calendar_scope,
        )
        checkpoint = await asyncio.to_thread(store.get_checkpoint)
        self._delta_start_scheduled = True
        if checkpoint is None:
            self.base_revision = None
            self.crawler.stats.set_value(
                "msgloom/crawl/calendar/delta/checkpoint_loaded",
                False,
            )
            self._persist_execution_state()
            yield self._initial_delta_request(reset_count=0)
            return

        self.base_revision = checkpoint.revision
        self.crawler.stats.set_value(
            "msgloom/crawl/calendar/delta/checkpoint_loaded",
            True,
        )
        self.crawler.stats.set_value(
            "msgloom/crawl/calendar/delta/checkpoint_revision",
            checkpoint.revision,
        )
        self._persist_execution_state()
        yield self._delta_request(
            checkpoint.delta_link,
            page_number=1,
            from_checkpoint=True,
            reset_count=0,
        )

    def parse_delta(
        self,
        response: TextResponse,
        *,
        purpose: str,
        page_number: int,
        from_checkpoint: bool,
        reset_count: int,
        start_datetime: str,
        end_datetime: str,
    ) -> Iterator[Any]:
        """Emit ordered changes and stage only a terminal delta cursor."""
        if start_datetime != self.start_datetime or end_datetime != self.end_datetime:
            raise ValueError("Calendar delta callback scope changed in flight")
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence

        payload = response.json()
        if not isinstance(payload, dict):
            raise TypeError("Calendar delta response must be a JSON object")
        values = payload.get("value")
        if not isinstance(values, list):
            raise TypeError("Calendar delta response must contain a value list")
        # Graph may repeat an event in one page. Keep every delta entry, but
        # project only its last upsert into the source-wide event record.
        last_upserts = {
            event["id"]: index
            for index, event in enumerate(values)
            if isinstance(event, dict)
            and isinstance(event.get("id"), str)
            and event.get("@removed") is None
        }

        self.crawler.stats.inc_value("msgloom/crawl/calendar/delta/page_count")
        self.crawler.stats.inc_value(
            "msgloom/crawl/calendar/delta/entry_count",
            count=len(values),
        )

        for entry_index, event in enumerate(values):
            if not isinstance(event, dict):
                raise TypeError("Calendar delta event must be a JSON object")
            event_id = event.get("id")
            if not isinstance(event_id, str) or not event_id:
                raise ValueError("Calendar delta event must contain a non-empty id")

            removed = event.get("@removed")
            if removed is not None and not isinstance(removed, dict):
                raise ValueError("Calendar @removed value must be an object")
            kind = "removed" if isinstance(removed, dict) else "upsert"
            removed_reason = None
            if isinstance(removed, dict):
                reason = removed.get("reason")
                removed_reason = reason if isinstance(reason, str) else None
                self.crawler.stats.inc_value(
                    "msgloom/crawl/calendar/delta/removed_count"
                )
            else:
                self.crawler.stats.inc_value(
                    "msgloom/crawl/calendar/delta/upsert_count"
                )

            yield OutlookCalendarDeltaObservationItem(
                event_id=event_id,
                kind=kind,
                raw=event,
                observed_at=evidence.observed_at,
                evidence_id=evidence.evidence_id,
                run_id=self.run_id,
                attempt=self.attempt,
                page_number=page_number,
                entry_index=entry_index,
                start_datetime=self.start_datetime,
                end_datetime=self.end_datetime,
                removed_reason=removed_reason,
                calendar_scope=self.calendar_scope,
            )

            if kind == "upsert" and last_upserts[event_id] == entry_index:
                yield OutlookCalendarEventItem(
                    event_id=event_id,
                    raw=event,
                    observed_at=evidence.observed_at,
                    evidence_id=evidence.evidence_id,
                    run_id=self.run_id,
                    calendar_id=self.calendar_scope,
                    observation_kind="delta",
                )

        next_link = payload.get("@odata.nextLink")
        delta_link = payload.get("@odata.deltaLink")
        if next_link is not None and delta_link is not None:
            self.mark_run_failed("calendar_delta_conflicting_state")
            yield self._state_failure(
                response,
                evidence,
                "Calendar delta response contained both @odata.nextLink "
                "and @odata.deltaLink",
                "DeltaStateConflict",
            )
            return

        if next_link is not None:
            if not isinstance(next_link, str) or not next_link:
                raise ValueError("Calendar @odata.nextLink must be a non-empty string")
            self.crawler.stats.inc_value(
                "msgloom/crawl/calendar/delta/continuation_count"
            )
            yield self._delta_request(
                next_link,
                page_number=page_number + 1,
                from_checkpoint=from_checkpoint,
                reset_count=reset_count,
            )
            return

        if delta_link is not None:
            if not isinstance(delta_link, str) or not delta_link:
                raise ValueError("Calendar @odata.deltaLink must be a non-empty string")
            self._terminal_delta_seen = True
            self.crawler.stats.set_value(
                "msgloom/crawl/calendar/delta/terminal_seen", True
            )
            self._persist_execution_state()
            yield OutlookCalendarDeltaCheckpointCandidateItem(
                run_id=self.run_id,
                attempt=self.attempt,
                base_revision=self.base_revision,
                delta_link=delta_link,
                observed_at=evidence.observed_at,
                evidence_id=evidence.evidence_id,
                start_datetime=self.start_datetime,
                end_datetime=self.end_datetime,
                calendar_scope=self.calendar_scope,
            )
            return

        self.mark_run_failed("calendar_delta_state_missing")
        yield self._state_failure(
            response,
            evidence,
            "Microsoft Graph Calendar delta response contained neither "
            "@odata.nextLink nor @odata.deltaLink",
            "DeltaStateMissing",
        )

    def errback(self, failure: Failure) -> Iterator[Any]:
        """Restart one expired cursor once; persist other exhausted failures."""
        request = self._failure_request(failure)
        callback_data = request.cb_kwargs
        purpose = callback_data.get("purpose", "unknown")
        evidence = self._failure_evidence_item(failure)
        yield evidence

        if purpose == "calendar-delta-page" and evidence.response_status == 410:
            reset_count = int(callback_data.get("reset_count", 0))
            if reset_count < 1:
                self.attempt += 1
                self._terminal_delta_seen = False
                self.crawler.stats.inc_value(
                    "msgloom/crawl/calendar/delta/checkpoint_reset_count"
                )
                self._persist_execution_state()
                self.logger.warning(
                    "Calendar delta checkpoint expired; restarting the fixed "
                    "window once"
                )
                yield self._initial_delta_request(reset_count=reset_count + 1)
                return

        yield self._request_failure_item(failure, evidence)

    def mark_run_failed(self, reason: str) -> None:
        """Persist failure integrity facts for a graceful JOBDIR resume."""
        super().mark_run_failed(reason)
        self._persist_execution_state()

    def delta_execution_snapshot(self) -> dict[str, Any]:
        """Return facts that the idle extension uses for safe promotion."""
        return {
            "run_id": self.run_id,
            "attempt": self.attempt,
            "base_revision": self.base_revision,
            "terminal_delta_seen": self._terminal_delta_seen,
            "run_failed": self.run_failed,
            "failure_reasons": set(self.failure_reasons),
        }

    def _restore_execution_state(self) -> None:
        """Restore one exact Calendar delta execution scope from SpiderState."""
        saved = self.state.get("msgloom_calendar_delta")
        if saved is None and not self.state:
            self._persist_execution_state()
            return
        if not isinstance(saved, dict):
            raise TypeError("JOBDIR has no valid Calendar delta state")
        restored = CalendarDeltaExecutionState.restore(
            saved,
            start_datetime=self.start_datetime,
            end_datetime=self.end_datetime,
            calendar_scope=self.calendar_scope,
            default_run_id=self.run_id,
        )
        self.run_id = restored.run_id
        self.attempt = restored.attempt
        self.base_revision = restored.base_revision
        self._terminal_delta_seen = restored.terminal_delta_seen
        self._run_failed = self._run_failed or restored.run_failed
        self._failure_reasons.update(restored.failure_reasons)
        self._delta_start_scheduled = restored.delta_start_scheduled

    def _persist_execution_state(self) -> None:
        """Store execution facts while keeping provider cursors in the catalog."""
        self.state["msgloom_calendar_delta"] = execution_payload(
            run_id=self.run_id,
            start_datetime=self.start_datetime,
            end_datetime=self.end_datetime,
            calendar_scope=self.calendar_scope,
            attempt=self.attempt,
            base_revision=self.base_revision,
            terminal_delta_seen=self._terminal_delta_seen,
            run_failed=self._run_failed,
            failure_reasons=self._failure_reasons,
            delta_start_scheduled=self._delta_start_scheduled,
        )

    def _initial_delta_request(self, *, reset_count: int) -> scrapy.Request:
        """Build the first request for the exact configured window."""
        query = urlencode(
            {
                "startDateTime": self.start_datetime,
                "endDateTime": self.end_datetime,
            }
        )
        return self._delta_request(
            f"{self.graph_root}/me/calendarView/delta?{query}",
            page_number=1,
            from_checkpoint=False,
            reset_count=reset_count,
        )

    def _delta_request(
        self,
        url: str,
        *,
        page_number: int,
        from_checkpoint: bool,
        reset_count: int,
    ) -> scrapy.Request:
        """Follow opaque state URLs without cache replay or query rebuilding."""
        return self._request(
            url,
            callback=self.parse_delta,
            purpose="calendar-delta-page",
            cb_kwargs={
                "page_number": page_number,
                "from_checkpoint": from_checkpoint,
                "reset_count": reset_count,
                "start_datetime": self.start_datetime,
                "end_datetime": self.end_datetime,
            },
            dont_cache=True,
            verbatim_url=page_number > 1 or from_checkpoint,
            prefer=(f'IdType="ImmutableId", odata.maxpagesize={self.page_size}'),
        )

    def _state_failure(
        self,
        response: TextResponse,
        evidence,
        message: str,
        error_type: str,
    ) -> AcquisitionFailureItem:
        """Create one linked semantic failure for malformed delta state."""
        self.crawler.stats.inc_value("msgloom/crawl/failure_count")
        self.crawler.stats.inc_value(
            "msgloom/crawl/failure_purpose_count/calendar-delta-page"
        )
        self.crawler.stats.inc_value(f"msgloom/crawl/failure_type_count/{error_type}")
        return AcquisitionFailureItem(
            url=response.url,
            purpose="calendar-delta-page",
            error_type=error_type,
            error_message=message,
            observed_at=evidence.observed_at,
            context={
                "start_datetime": self.start_datetime,
                "end_datetime": self.end_datetime,
            },
            evidence_id=evidence.evidence_id,
            run_id=self.run_id,
        )

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
        """Parse a Calendar window boundary, accepting a Z suffix."""
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(
                "Calendar delta values must be valid ISO-8601 datetimes"
            ) from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("Calendar delta datetimes must include a timezone offset")
        return parsed
