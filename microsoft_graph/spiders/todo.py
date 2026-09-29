"""Microsoft To Do read scopes and v1.0 collection paths."""

from typing import ClassVar
from urllib.parse import quote, urlencode

from .graph import MicrosoftGraphSpider


class MicrosoftTodoSpider(MicrosoftGraphSpider):
    """Supply provider paths; consumers own task traversal and persistence."""

    graph_permissions: ClassVar[tuple[str, ...]] = ("Tasks.Read",)

    def task_lists_path(self, *, page_size: int | None = None) -> str:
        """List the account's task lists with an optional page size."""
        path = "/me/todo/lists"
        if page_size is None:
            return path
        return f"{path}?{urlencode({'$top': page_size})}"

    def tasks_path(self, list_id: str, *, page_size: int | None = None) -> str:
        """Encode the raw list ID once and add only a new page-size query."""
        path = f"{self.task_lists_path()}/{quote(list_id, safe='')}/tasks"
        if page_size is None:
            return path
        return f"{path}?{urlencode({'$top': page_size})}"

    def checklist_items_path(self, list_id: str, task_id: str) -> str:
        """Build the explicit checklist collection path from raw parent IDs."""
        return f"{self.tasks_path(list_id)}/{quote(task_id, safe='')}/checklistItems"

    def linked_resources_path(self, list_id: str, task_id: str) -> str:
        """Build the explicit linked-resource collection path from raw IDs."""
        return f"{self.tasks_path(list_id)}/{quote(task_id, safe='')}/linkedResources"


__all__ = ["MicrosoftTodoSpider"]
