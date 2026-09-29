"""Persist Contacts observations after evidence capture and canonical linking."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from scrapy.exceptions import NotConfigured

from message_ingest.catalog.stores.microsoft.contacts import ContactsStore, Outcome
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.microsoft.contacts import (
    ContactCollectionCompleteItem,
    ContactDeltaCheckpointCandidateItem,
    ContactFolderItem,
    ContactItem,
)


class ContactsPipeline:
    """Await every Contacts catalog write under the crawler's shared lock."""

    def __init__(self, *, service: CatalogService, source_id: str, stats=None) -> None:
        self.service = service
        self.catalog = service.catalog
        self.store = ContactsStore(self.catalog, source_id=source_id)
        self.stats = stats

    @classmethod
    def from_crawler(cls, crawler):
        """Enable only when SQL persistence is available."""
        if not crawler.settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            raise NotConfigured("Contacts persistence requires the SQL catalog")
        return cls(
            service=CatalogService.from_crawler(crawler),
            source_id=crawler.settings["MSGLOOM_SOURCE_ID"],
            stats=crawler.stats,
        )

    async def process_item(self, item: Any) -> Any:
        """Persist resource/completion work; propagate failures to Scrapy integrity."""
        if isinstance(item, ContactFolderItem):
            return await self._persist_outcome(
                item, "folder", self.store.persist_folder
            )
        if isinstance(item, ContactItem):
            if item.observation_kind == "delta":
                return await self._persist(
                    item, "delta_observation", self.store.persist_delta_observation
                )
            return await self._persist_outcome(
                item, "contact", self.store.persist_contact
            )
        if isinstance(item, ContactCollectionCompleteItem):
            return await self._persist(
                item, "collection_complete", self.store.persist_completion
            )
        if isinstance(item, ContactDeltaCheckpointCandidateItem):
            return await self._persist(
                item, "delta_candidate", self.store.stage_delta_candidate
            )
        return item

    async def _persist_outcome[Item](
        self, item: Item, kind: str, operation: Callable[[Item], Outcome]
    ) -> Item:
        async with self.service.write_lock:
            outcome = await asyncio.to_thread(operation, item)
        if self.stats is not None:
            self.stats.inc_value(f"msgloom/catalog/contacts/{kind}_processed_count")
            self.stats.inc_value(f"msgloom/catalog/contacts/{kind}_{outcome}_count")
        return item

    async def _persist[Item](
        self, item: Item, kind: str, operation: Callable[[Item], None]
    ) -> Item:
        async with self.service.write_lock:
            await asyncio.to_thread(operation, item)
        if self.stats is not None:
            self.stats.inc_value(f"msgloom/catalog/contacts/{kind}_processed_count")
        return item

    def close_spider(self) -> None:
        """Close the shared service after Scrapy has drained item work."""
        self.service.close()


__all__ = ["ContactsPipeline"]
