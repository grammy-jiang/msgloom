"""Persist Microsoft To Do state and durable traversal completion proof."""

from __future__ import annotations

import asyncio

from scrapy.exceptions import NotConfigured

from message_ingest.catalog.stores.microsoft.todo import TodoStore
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.microsoft.todo import (
    TodoChecklistItem,
    TodoLinkedResourceItem,
    TodoTaskItem,
    TodoTaskListItem,
    TodoTraversalCompleteItem,
)
from message_ingest.sync.microsoft.todo.snapshots import TodoSnapshotStore


class TodoPipeline:
    """Persist To Do items under the crawler-shared catalog write lock."""

    def __init__(self, crawler, service: CatalogService, source_id: str) -> None:
        """Bind source-scoped content and snapshot stores to shared resources."""
        self.crawler = crawler
        self.service = service
        self.catalog = service.catalog
        self.store = TodoStore(
            self.catalog, source_id=source_id, spider_name=crawler.spidercls.name
        )
        self.snapshot_store = TodoSnapshotStore(self.catalog, source_id=source_id)

    @classmethod
    def from_crawler(cls, crawler):
        """Enable persistence only with the shared SQL catalog."""
        if not crawler.settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            raise NotConfigured("To Do persistence requires the SQLAlchemy catalog")
        source_id = crawler.settings.get("MSGLOOM_SOURCE_ID")
        if not source_id:
            raise NotConfigured("MSGLOOM_SOURCE_ID is required")
        return cls(crawler, CatalogService.from_crawler(crawler), source_id)

    async def process_item(self, item):
        """Await content and snapshot proof writes before item completion."""
        if not isinstance(
            item,
            (
                TodoTaskListItem,
                TodoTaskItem,
                TodoChecklistItem,
                TodoLinkedResourceItem,
                TodoTraversalCompleteItem,
            ),
        ):
            return item
        async with self.service.write_lock:
            outcome, kind = await asyncio.to_thread(self._persist, item)
        if kind != "traversal_completion":
            self.crawler.stats.inc_value(
                f"msgloom/catalog/todo/{kind}_item_processed_count"
            )
        self.crawler.stats.inc_value(f"msgloom/catalog/todo/{kind}_{outcome}_count")
        return item

    def close_spider(self, _spider=None) -> None:
        """Release the crawler-shared catalog after all pipeline work."""
        self.service.close()

    def _persist(self, item) -> tuple[str, str]:
        """Run one serialized content/proof write in the worker thread."""
        if isinstance(item, TodoTraversalCompleteItem):
            self.snapshot_store.record_completion(item)
            return "recorded", "traversal_completion"
        if isinstance(item, TodoTaskListItem):
            outcome = self.store.persist_task_list(item)
            kind = "task_list"
        elif isinstance(item, TodoTaskItem):
            outcome = self.store.persist_task(item)
            kind = "task"
        elif isinstance(item, TodoChecklistItem):
            outcome = self.store.persist_checklist_item(item)
            kind = "checklist_item"
        else:
            outcome = self.store.persist_linked_resource(item)
            kind = "linked_resource"
        # Both modes need the exact discovered child scopes for completion.
        # Sightings alone never promote authoritative presence.
        self.snapshot_store.record_sighting(item)
        return outcome, kind


__all__ = ["TodoPipeline"]
