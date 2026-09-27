"""Persist Microsoft Calendar event observations in the shared catalog."""

from __future__ import annotations

import asyncio
from uuid import uuid4

from scrapy.exceptions import NotConfigured
from sqlalchemy import select

from message_ingest.catalog import CalendarEventObservation
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items import OutlookCalendarEventItem


class CalendarPipeline:
    """Persist Calendar observations after provider-independent evidence linking."""

    def __init__(
        self,
        *,
        service: CatalogService,
        source_id: str,
        stats=None,
    ) -> None:
        """Borrow the crawler-owned catalog, write lock, and stats collector."""
        self.service = service
        self.catalog = service.catalog
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
        """Close the crawler-shared catalog after all item processing completes."""
        self.service.close()

    async def process_item(self, item):
        """Persist Calendar items and pass every other resource item through."""
        if not isinstance(item, OutlookCalendarEventItem):
            return item

        async with self._write_lock:
            created = await asyncio.to_thread(self._persist_sync, item)
        self._inc("msgloom/calendar/event_item_processed_count")
        outcome = "created" if created else "replay"
        self._inc(f"msgloom/calendar/event_observation_{outcome}_count")
        return item

    def _persist_sync(self, item: OutlookCalendarEventItem) -> bool:
        """Insert one observation, deduplicating replay of the same evidence."""
        with self.catalog.Session() as session, session.begin():
            if item.evidence_id is not None:
                existing = session.scalar(
                    select(CalendarEventObservation.observation_id).filter_by(
                        source_id=self.source_id,
                        event_id=item.event_id,
                        evidence_id=item.evidence_id,
                    )
                )
                if existing is not None:
                    return False

            raw = item.raw
            start = raw.get("start")
            end = raw.get("end")
            session.add(
                CalendarEventObservation(
                    observation_id=uuid4().hex,
                    source_id=self.source_id,
                    event_id=item.event_id,
                    run_id=item.run_id,
                    evidence_id=item.evidence_id,
                    observed_at=item.observed_at,
                    subject=raw.get("subject")
                    if isinstance(raw.get("subject"), str)
                    else None,
                    start=start if isinstance(start, dict) else None,
                    end=end if isinstance(end, dict) else None,
                    event_type=raw.get("type")
                    if isinstance(raw.get("type"), str)
                    else None,
                    raw=raw,
                )
            )
        return True

    def _inc(self, key: str) -> None:
        """Publish bounded Calendar persistence counters when stats are present."""
        if self.stats is not None:
            self.stats.inc_value(key)
