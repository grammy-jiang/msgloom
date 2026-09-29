"""Persist To Do observations after evidence capture and linking."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from scrapy.exceptions import NotConfigured

from message_ingest.catalog.stores.microsoft.todo import Outcome, TodoStore
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.microsoft.todo import (
    TodoChecklistItem,
    TodoLinkedResourceItem,
    TodoTaskItem,
    TodoTaskListItem,
)


class TodoPipeline:
    """Await durable current-state writes under the crawler's shared lock."""

    def __init__(self, *, service: CatalogService, source_id: str, stats=None) -> None:
        self.service = service
        self.catalog = service.catalog
        self.store = TodoStore(self.catalog, source_id=source_id)
        self.stats = stats

    @classmethod
    def from_crawler(cls, crawler):
        """Enable only when the shared SQL catalog is available."""
        if not crawler.settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            raise NotConfigured("To Do persistence requires the SQL catalog")
        return cls(
            service=CatalogService.from_crawler(crawler),
            source_id=crawler.settings["MSGLOOM_SOURCE_ID"],
            stats=crawler.stats,
        )

    async def process_item(self, item: Any) -> Any:
        """Persist To Do items; pass storage errors to run integrity."""
        if isinstance(item, TodoTaskListItem):
            return await self._persist(item, "task_list", self.store.persist_task_list)
        if isinstance(item, TodoTaskItem):
            return await self._persist(item, "task", self.store.persist_task)
        if isinstance(item, TodoChecklistItem):
            return await self._persist(
                item, "checklist_item", self.store.persist_checklist_item
            )
        if isinstance(item, TodoLinkedResourceItem):
            return await self._persist(
                item, "linked_resource", self.store.persist_linked_resource
            )
        return item

    async def _persist[Item](
        self, item: Item, kind: str, operation: Callable[[Item], Outcome]
    ) -> Item:
        """Serialize and await a write before recording a bounded outcome."""
        async with self.service.write_lock:
            outcome = await asyncio.to_thread(operation, item)
        if self.stats is not None:
            self.stats.inc_value(f"msgloom/catalog/todo/{kind}_item_processed_count")
            self.stats.inc_value(f"msgloom/catalog/todo/{kind}_{outcome}_count")
        return item

    def close_spider(self) -> None:
        """Close the shared service after Scrapy drains item work."""
        self.service.close()


__all__ = ["TodoPipeline"]
