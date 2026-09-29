"""To Do provider projections with msgloom observation and evidence context."""

from dataclasses import dataclass

from microsoft_graph.items.todo import TodoChecklistItem as GraphTodoChecklistItem
from microsoft_graph.items.todo import (
    TodoLinkedResourceItem as GraphTodoLinkedResourceItem,
)
from microsoft_graph.items.todo import TodoTaskItem as GraphTodoTaskItem
from microsoft_graph.items.todo import TodoTaskListItem as GraphTodoTaskListItem


@dataclass(slots=True)
class TodoTaskListItem(GraphTodoTaskListItem):
    """One list observation linked to its committed response evidence."""

    observed_at: str
    evidence_id: str | None
    run_id: str | None


@dataclass(slots=True)
class TodoTaskItem(GraphTodoTaskItem):
    """One task observation, retaining provider action state and deadlines."""

    observed_at: str
    evidence_id: str | None
    run_id: str | None


@dataclass(slots=True)
class TodoChecklistItem(GraphTodoChecklistItem):
    """One explicitly fetched checklist entry with response provenance."""

    observed_at: str
    evidence_id: str | None
    run_id: str | None


@dataclass(slots=True)
class TodoLinkedResourceItem(GraphTodoLinkedResourceItem):
    """One explicitly fetched evidence link with response provenance."""

    observed_at: str
    evidence_id: str | None
    run_id: str | None


@dataclass(slots=True)
class TodoTraversalCompleteItem:
    """Terminal-page proof for one authoritative collection traversal."""

    collection_kind: str
    list_id: str | None
    task_id: str | None
    observed_at: str
    evidence_id: str | None
    run_id: str | None


__all__ = [
    "TodoChecklistItem",
    "TodoLinkedResourceItem",
    "TodoTaskItem",
    "TodoTaskListItem",
    "TodoTraversalCompleteItem",
]
