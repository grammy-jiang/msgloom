"""Persist Outlook Calendar semantic items through the domain catalog store."""

from __future__ import annotations

import asyncio

from scrapy.exceptions import NotConfigured

from message_ingest.catalog.stores.microsoft.outlook.calendar import (
    OutlookCalendarStore,
)
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.microsoft.outlook.calendar import (
    OutlookCalendarAttachmentContentItem,
    OutlookCalendarAttachmentItem,
    OutlookCalendarDeltaCheckpointCandidateItem,
    OutlookCalendarDeltaObservationItem,
    OutlookCalendarEventItem,
    OutlookCalendarEventSurfaceItem,
    OutlookCalendarItem,
    OutlookCalendarSeriesTopologyItem,
)
from message_ingest.sync.microsoft.outlook.calendar.checkpoints import (
    CalendarDeltaCheckpointStore,
)


class OutlookCalendarPipeline:
    """Route Calendar items to durable stores after evidence linking."""

    def __init__(
        self,
        *,
        service: CatalogService,
        source_id: str,
        stats=None,
    ) -> None:
        self.service = service
        self.catalog = service.catalog
        self.store = OutlookCalendarStore(self.catalog, source_id=source_id)
        self.source_id = source_id
        self.stats = stats
        self._write_lock = service.write_lock

    @classmethod
    def from_crawler(cls, crawler):
        """Enable Calendar persistence only when the SQL catalog is available."""
        if not crawler.settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            raise NotConfigured("Calendar persistence requires the SQL catalog")
        return cls(
            service=CatalogService.from_crawler(crawler),
            source_id=crawler.settings["MSGLOOM_SOURCE_ID"],
            stats=crawler.stats,
        )

    def close_spider(self) -> None:
        """Close the crawler-shared catalog after item processing completes."""
        self.service.close()

    async def process_item(self, item):
        """Persist supported Calendar items and pass other resources through."""
        if isinstance(item, OutlookCalendarItem):
            outcome = await self._write(self.store.persist_calendar, item)
            self._outcome("calendar", outcome)
            return item
        if isinstance(item, OutlookCalendarEventItem):
            outcome = await self._write(self.store.persist_event, item)
            self._outcome("event", outcome)
            return item
        if isinstance(item, OutlookCalendarAttachmentItem):
            outcome = await self._write(self.store.persist_attachment_metadata, item)
            self._outcome("attachment", outcome)
            return item
        if isinstance(item, OutlookCalendarAttachmentContentItem):
            outcome = await self._write(self.store.persist_attachment_content, item)
            self._outcome("attachment_content", outcome)
            return item
        if isinstance(item, OutlookCalendarSeriesTopologyItem):
            outcome = await self._write(self.store.persist_series_topology, item)
            self._outcome("series_topology", outcome)
            return item
        if isinstance(item, OutlookCalendarEventSurfaceItem):
            async with self._write_lock:
                await asyncio.to_thread(
                    self.store.set_event_surface,
                    event_id=item.event_id,
                    run_id=item.run_id,
                    surface=item.surface,
                    status=item.status,
                    evidence_id=item.evidence_id,
                    observed_at=item.observed_at,
                    profile_version=item.profile_version,
                    resource_version=item.resource_version,
                )
            surface_kind = item.surface.split(":", maxsplit=1)[0]
            self._inc(
                "msgloom/calendar/surface_item_processed_count/"
                f"{surface_kind}/{item.status}"
            )
            return item
        if isinstance(item, OutlookCalendarDeltaObservationItem):
            outcome = await self._write(self.store.persist_delta_observation, item)
            self._outcome("delta_observation", outcome)
            return item
        if isinstance(item, OutlookCalendarDeltaCheckpointCandidateItem):
            async with self._write_lock:
                await asyncio.to_thread(self._persist_delta_candidate, item)
            self._inc("msgloom/calendar/delta_candidate_processed_count")
            return item
        return item

    async def _write(self, operation, item) -> str:
        async with self._write_lock:
            return await asyncio.to_thread(operation, item)

    def _persist_delta_candidate(
        self,
        item: OutlookCalendarDeltaCheckpointCandidateItem,
    ) -> None:
        store = CalendarDeltaCheckpointStore(
            self.catalog,
            source_id=self.source_id,
            start_datetime=item.start_datetime,
            end_datetime=item.end_datetime,
            calendar_scope=item.calendar_scope,
        )
        store.write_candidate(
            run_id=item.run_id,
            attempt=item.attempt,
            base_revision=item.base_revision,
            delta_link=item.delta_link,
            evidence_id=item.evidence_id,
            observed_at=item.observed_at,
        )

    def _outcome(self, kind: str, outcome: str) -> None:
        self._inc(f"msgloom/calendar/{kind}_item_processed_count")
        self._inc(f"msgloom/calendar/{kind}_{outcome}_count")

    def _inc(self, key: str) -> None:
        if self.stats is not None:
            self.stats.inc_value(key)


__all__ = ["OutlookCalendarPipeline"]
