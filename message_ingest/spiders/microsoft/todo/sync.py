"""Authoritative read-only Microsoft To Do snapshot spider."""

from typing import ClassVar

from message_ingest.spiders.microsoft.todo.discover import MicrosoftTodoDiscoverSpider


class MicrosoftTodoSyncSpider(MicrosoftTodoDiscoverSpider):
    """Reuse discovery traversal while requiring uncached snapshot proof."""

    name = "microsoft_todo_sync"
    authoritative_snapshot: ClassVar[bool] = True


__all__ = ["MicrosoftTodoSyncSpider"]
