"""Acquire paginated events from the signed-in user's default calendar."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any
from urllib.parse import urlencode

from scrapy.http import TextResponse
from scrapy.settings import BaseSettings

from message_ingest.items import OutlookCalendarEventItem
from message_ingest.providers.microsoft_graph.spider import MicrosoftGraphSpider


class OutlookCalendarSpider(MicrosoftGraphSpider):
    """Read default-calendar events through native Scrapy pagination."""

    name = "outlook_calendar"
    page_size = 50

    @classmethod
    def update_settings(cls, settings: BaseSettings) -> None:
        """Declare Calendar permissions and resource-specific components."""
        settings.set(
            "MS_GRAPH_SCOPES",
            ["Calendars.ReadBasic"],
            priority="spider",
        )
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

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """Reject JOBDIR until Calendar resume semantics are explicitly tested."""
        if crawler.settings.get("JOBDIR"):
            raise ValueError(
                "Outlook Calendar acquisition does not support JOBDIR yet"
            )
        return super().from_crawler(crawler, *args, **kwargs)

    async def start(self) -> AsyncIterator[Any]:
        """Schedule the first default-calendar event page."""
        self.crawler.stats.set_value("msgloom/crawl/mode", "calendar")
        self.crawler.stats.set_value(
            "msgloom/crawl/calendar/pagination_exhausted",
            False,
        )
        query = urlencode(
            {
                "$select": "id,subject,start,end,type",
                "$top": self.page_size,
            }
        )
        yield self._request(
            f"{self.graph_root}/me/calendar/events?{query}",
            callback=self.parse_events,
            purpose="calendar-event-page",
            cb_kwargs={},
            prefer='IdType="ImmutableId"',
        )

    def parse_events(
        self,
        response: TextResponse,
        *,
        purpose: str,
    ) -> Iterator[Any]:
        """Yield evidence, event observations, and an opaque continuation."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence

        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Calendar response must be a JSON object")
        values = payload.get("value")
        if not isinstance(values, list):
            raise ValueError("Calendar response must contain a value list")

        self.crawler.stats.inc_value("msgloom/crawl/calendar/page_count")
        for event in values:
            if not isinstance(event, dict):
                raise ValueError("Calendar event must be a JSON object")
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

        self.crawler.stats.inc_value(
            "msgloom/crawl/calendar/continuation_count"
        )
        yield self._request(
            next_link,
            callback=self.parse_events,
            purpose="calendar-event-page",
            cb_kwargs={},
            verbatim_url=True,
            prefer='IdType="ImmutableId"',
        )
