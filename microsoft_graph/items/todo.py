"""Optional To Do projections with unchanged provider JSON and no run state."""

from dataclasses import dataclass, field
from typing import Any, Self

from microsoft_graph.protocol import graph_object


def _resource(resource: dict[str, Any], context: str, **parents: str) -> dict[str, Any]:
    """Validate only object and resource/parent IDs, never optional content."""
    raw = graph_object(resource, context=context)
    for name, value in {"id": raw.get("id"), **parents}.items():
        if not isinstance(value, str) or not value:
            raise ValueError(f"{context} requires a non-empty {name}")
    return raw


@dataclass(slots=True)
class TodoTaskListItem:
    """
    Task-list identity, fields, and the original provider dictionary.

    Optional projections snapshot values at construction. Missing values are
    ``None``; falsey and unknown values remain unchanged. :meth:`from_graph`
    validates identity only. Built-in list kinds receive no special behavior.
    """

    list_id: str
    raw: dict[str, Any]
    display_name: str | None = field(init=False)
    is_owner: bool | None = field(init=False)
    is_shared: bool | None = field(init=False)
    wellknown_list_name: str | None = field(init=False)

    def __post_init__(self) -> None:
        """Project list metadata without truth-value coercion."""
        self.display_name = self.raw.get("displayName")
        self.is_owner = self.raw.get("isOwner")
        self.is_shared = self.raw.get("isShared")
        self.wellknown_list_name = self.raw.get("wellknownListName")

    @classmethod
    def from_graph(cls, resource: dict[str, Any], **kwargs: Any) -> Self:
        """Map a list; keyword arguments supply consumer subclass fields."""
        raw = _resource(resource, "To Do task list")
        return cls(list_id=raw["id"], raw=raw, **kwargs)


@dataclass(slots=True)
class TodoTaskItem:
    """Task fields, parent identity, and unchanged nested provider values."""

    list_id: str
    task_id: str
    raw: dict[str, Any]
    title: str | None = field(init=False)
    body: dict[str, Any] | None = field(init=False)
    status: str | None = field(init=False)
    importance: str | None = field(init=False)
    categories: list[str] | None = field(init=False)
    created_date_time: str | None = field(init=False)
    last_modified_date_time: str | None = field(init=False)
    body_last_modified_date_time: str | None = field(init=False)
    due_date_time: dict[str, Any] | None = field(init=False)
    start_date_time: dict[str, Any] | None = field(init=False)
    completed_date_time: dict[str, Any] | None = field(init=False)
    reminder_date_time: dict[str, Any] | None = field(init=False)
    is_reminder_on: bool | None = field(init=False)
    recurrence: dict[str, Any] | None = field(init=False)

    def __post_init__(self) -> None:
        """Preserve nested object identity for each provider field."""
        self.title = self.raw.get("title")
        self.body = self.raw.get("body")
        self.status = self.raw.get("status")
        self.importance = self.raw.get("importance")
        self.categories = self.raw.get("categories")
        self.created_date_time = self.raw.get("createdDateTime")
        self.last_modified_date_time = self.raw.get("lastModifiedDateTime")
        self.body_last_modified_date_time = self.raw.get("bodyLastModifiedDateTime")
        self.due_date_time = self.raw.get("dueDateTime")
        self.start_date_time = self.raw.get("startDateTime")
        self.completed_date_time = self.raw.get("completedDateTime")
        self.reminder_date_time = self.raw.get("reminderDateTime")
        self.is_reminder_on = self.raw.get("isReminderOn")
        self.recurrence = self.raw.get("recurrence")

    @classmethod
    def from_graph(
        cls, resource: dict[str, Any], *, list_id: str, **kwargs: Any
    ) -> Self:
        """Map a task without interpreting embedded relations."""
        raw = _resource(resource, "To Do task", list_id=list_id)
        return cls(list_id=list_id, task_id=raw["id"], raw=raw, **kwargs)


@dataclass(slots=True)
class TodoChecklistItem:
    """Checklist entry with explicit task/list identity and provider state."""

    list_id: str
    task_id: str
    checklist_item_id: str
    raw: dict[str, Any]
    display_name: str | None = field(init=False)
    is_checked: bool | None = field(init=False)
    created_date_time: str | None = field(init=False)
    checked_date_time: str | None = field(init=False)

    def __post_init__(self) -> None:
        """Project checklist metadata, retaining checked state and dates."""
        self.display_name = self.raw.get("displayName")
        self.is_checked = self.raw.get("isChecked")
        self.created_date_time = self.raw.get("createdDateTime")
        self.checked_date_time = self.raw.get("checkedDateTime")

    @classmethod
    def from_graph(
        cls, resource: dict[str, Any], *, list_id: str, task_id: str, **kwargs: Any
    ) -> Self:
        """Map an explicit checklist entry with consumer parent IDs."""
        raw = _resource(
            resource, "To Do checklist item", list_id=list_id, task_id=task_id
        )
        return cls(
            list_id=list_id,
            task_id=task_id,
            checklist_item_id=raw["id"],
            raw=raw,
            **kwargs,
        )


@dataclass(slots=True)
class TodoLinkedResourceItem:
    """Provider evidence link; a missing web URL is a valid representation."""

    list_id: str
    task_id: str
    linked_resource_id: str
    raw: dict[str, Any]
    web_url: str | None = field(init=False)
    application_name: str | None = field(init=False)
    display_name: str | None = field(init=False)
    external_id: str | None = field(init=False)

    def __post_init__(self) -> None:
        """Preserve link metadata, including missing and empty URLs."""
        self.web_url = self.raw.get("webUrl")
        self.application_name = self.raw.get("applicationName")
        self.display_name = self.raw.get("displayName")
        self.external_id = self.raw.get("externalId")

    @classmethod
    def from_graph(
        cls, resource: dict[str, Any], *, list_id: str, task_id: str, **kwargs: Any
    ) -> Self:
        """Map a resource from its relation collection with parent identity."""
        raw = _resource(
            resource, "To Do linked resource", list_id=list_id, task_id=task_id
        )
        return cls(
            list_id=list_id,
            task_id=task_id,
            linked_resource_id=raw["id"],
            raw=raw,
            **kwargs,
        )


__all__ = [
    "TodoChecklistItem",
    "TodoLinkedResourceItem",
    "TodoTaskItem",
    "TodoTaskListItem",
]
