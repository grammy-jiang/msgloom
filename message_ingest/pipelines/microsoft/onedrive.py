"""Persist OneDrive observations after raw evidence capture and linking."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from scrapy.exceptions import NotConfigured

from message_ingest.catalog.stores.microsoft.onedrive import OneDriveStore, Outcome
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.microsoft.onedrive import (
    OneDriveContentItem,
    OneDriveDeltaCheckpointCandidateItem,
    OneDriveDeltaResyncAttemptItem,
    OneDriveDeltaResyncObservationItem,
    OneDriveDriveItem,
    OneDriveItem,
)


class OneDrivePipeline:
    """Await source-scoped writes under the crawler's shared catalog lock."""

    def __init__(
        self,
        *,
        service: CatalogService,
        source_id: str,
        stats=None,
        spider_name: str = "onedrive_store",
    ) -> None:
        self.service = service
        self.catalog = service.catalog
        self.store = OneDriveStore(
            self.catalog, source_id=source_id, spider_name=spider_name
        )
        self.stats = stats

    @classmethod
    def from_crawler(cls, crawler):
        """Enable only when the shared SQL catalog is available."""
        if not crawler.settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            raise NotConfigured("OneDrive persistence requires the SQL catalog")
        return cls(
            service=CatalogService.from_crawler(crawler),
            source_id=crawler.settings["MSGLOOM_SOURCE_ID"],
            stats=crawler.stats,
            spider_name=crawler.spidercls.name,
        )

    async def process_item(self, item: Any) -> Any:
        """Persist OneDrive items and propagate failures to run integrity."""
        if isinstance(item, OneDriveDriveItem):
            return await self._persist(item, "drive", self.store.persist_drive)
        if isinstance(item, OneDriveDeltaResyncAttemptItem):
            return await self._persist(
                item, "resync_attempt", self.store.persist_resync_attempt
            )
        if isinstance(item, OneDriveDeltaResyncObservationItem):
            return await self._persist(
                item, "resync_observation", self.store.persist_resync_observation
            )
        if isinstance(item, OneDriveItem):
            return await self._persist(item, "item", self.store.persist_item)
        if isinstance(item, OneDriveContentItem):
            return await self._persist(item, "content", self.store.persist_content)
        if isinstance(item, OneDriveDeltaCheckpointCandidateItem):
            return await self._persist(item, "candidate", self.store.persist_candidate)
        return item

    async def _persist[Item](
        self, item: Item, kind: str, operation: Callable[[Item], Outcome]
    ) -> Item:
        """Await serialized writes before publishing bounded stats."""
        async with self.service.write_lock:
            outcome = await asyncio.to_thread(operation, item)
        if self.stats is not None:
            self.stats.inc_value(f"msgloom/catalog/onedrive/{kind}_processed_count")
            self.stats.inc_value(f"msgloom/catalog/onedrive/{kind}_{outcome}_count")
        return item

    def close_spider(self) -> None:
        """Close shared resources after Scrapy drains item pipeline work."""
        self.service.close()


__all__ = ["OneDrivePipeline"]
