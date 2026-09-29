"""Discover calendars visible to the signed-in Microsoft account."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any

from scrapy.http import TextResponse
from scrapy.settings import BaseSettings

from message_ingest.items.microsoft.outlook.calendar import OutlookCalendarItem
from microsoft_graph.protocol import GraphCollectionPage

from ._base import OutlookCalendarSpider


class OutlookCalendarDiscoverSpider(OutlookCalendarSpider):
    """Inventory visible calendars without inferring deletion from absence."""

    name = "outlook_calendar_discover"

    def __init__(
        self,
        *args,
        page_size: str = "100",
        **kwargs,
    ) -> None:
        """Validate Calendar inventory arguments."""
        super().__init__(*args, **kwargs)
        self.page_size = self._bounded_int(
            page_size, name="page_size", minimum=1, maximum=1000
        )

    @classmethod
    def update_settings(cls, settings: BaseSettings) -> None:
        """Declare Calendar permissions and its persistence pipeline."""
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
                "message_ingest.pipelines.microsoft.outlook.calendar.OutlookCalendarPipeline": 300,
            },
            priority="spider",
        )
        super().update_settings(settings)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """Reject JOBDIR until Calendar resume semantics are tested."""
        if crawler.settings.get("JOBDIR"):
            raise ValueError("Calendar discovery does not support JOBDIR yet")
        return super().from_crawler(crawler, *args, **kwargs)

    async def start(self) -> AsyncIterator[Any]:
        """Schedule the first visible-calendar inventory page."""
        self.crawler.stats.set_value("msgloom/crawl/mode", "calendar_discover")
        self.crawler.stats.set_value(
            "msgloom/crawl/calendar/inventory_exhausted",
            False,
        )
        yield self._request(
            f"{self.graph_root}{self.calendars_path(page_size=self.page_size)}",
            callback=self.parse_calendars,
            purpose="calendar-inventory-page",
            cb_kwargs={},
        )

    def parse_calendars(
        self,
        response: TextResponse,
        *,
        purpose: str,
    ) -> Iterator[Any]:
        """Yield page evidence, calendar inventory items, and continuation."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        page = GraphCollectionPage.from_payload(
            response.json(),
            context="Calendar inventory",
            validate_links=False,
        )
        values = page.values

        self.crawler.stats.inc_value("msgloom/crawl/calendar/inventory_page_count")
        for calendar in values:
            item = OutlookCalendarItem.from_graph(
                calendar,
                observed_at=evidence.observed_at,
                evidence_id=evidence.evidence_id,
                run_id=self.run_id,
            )
            self.crawler.stats.inc_value("msgloom/crawl/calendar/calendar_count")
            yield item

        next_link = page.next_link
        if next_link is None:
            self.crawler.stats.set_value(
                "msgloom/crawl/calendar/inventory_exhausted",
                True,
            )
            return
        self.crawler.stats.inc_value(
            "msgloom/crawl/calendar/inventory_continuation_count"
        )
        yield self._request(
            next_link,
            callback=self.parse_calendars,
            purpose="calendar-inventory-page",
            cb_kwargs={},
            verbatim_url=True,
        )
