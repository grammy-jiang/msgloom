"""Source-scoped Microsoft To Do observations, sightings, and presence."""

from sqlalchemy import JSON, Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class TodoRecord(Base):
    """Share source identity and latest-capture provenance for To Do state."""

    __abstract__ = True

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True, sort_order=-1)
    latest_observed_at: Mapped[str] = mapped_column(String(40), index=True)
    latest_evidence_id: Mapped[str | None] = mapped_column(String(32), index=True)
    raw: Mapped[dict[str, object]] = mapped_column(JSON)


class TodoTaskListRecord(TodoRecord):
    """Latest provider fields for one task list within one logical source."""

    __tablename__ = "todo_task_lists"

    list_id: Mapped[str] = mapped_column(Text, primary_key=True)
    display_name: Mapped[str | None] = mapped_column(Text)
    is_owner: Mapped[bool | None] = mapped_column(Boolean)
    is_shared: Mapped[bool | None] = mapped_column(Boolean)
    wellknown_list_name: Mapped[str | None] = mapped_column(Text)


class TodoTaskRecord(TodoRecord):
    """
    Latest task action state and deadlines within its observed list.

    Scalar provider timestamps retain their original text. Zoned date/time,
    body, categories, and recurrence projections retain their JSON shape.
    Absence from a later inventory never removes this record.
    """

    __tablename__ = "todo_tasks"

    list_id: Mapped[str] = mapped_column(Text, primary_key=True)
    task_id: Mapped[str] = mapped_column(Text, primary_key=True)
    title: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(Text)
    importance: Mapped[str | None] = mapped_column(Text)
    body: Mapped[dict[str, object] | None] = mapped_column(JSON)
    categories: Mapped[list[str] | None] = mapped_column(JSON)
    created_date_time: Mapped[str | None] = mapped_column(Text)
    last_modified_date_time: Mapped[str | None] = mapped_column(Text)
    body_last_modified_date_time: Mapped[str | None] = mapped_column(Text)
    due_date_time: Mapped[dict[str, object] | None] = mapped_column(JSON)
    start_date_time: Mapped[dict[str, object] | None] = mapped_column(JSON)
    completed_date_time: Mapped[dict[str, object] | None] = mapped_column(JSON)
    reminder_date_time: Mapped[dict[str, object] | None] = mapped_column(JSON)
    is_reminder_on: Mapped[bool | None] = mapped_column(Boolean)
    recurrence: Mapped[dict[str, object] | None] = mapped_column(JSON)


class TodoChecklistItemRecord(TodoRecord):
    """Latest checklist item state scoped through list and task identity."""

    __tablename__ = "todo_checklist_items"

    list_id: Mapped[str] = mapped_column(Text, primary_key=True)
    task_id: Mapped[str] = mapped_column(Text, primary_key=True)
    checklist_item_id: Mapped[str] = mapped_column(Text, primary_key=True)
    display_name: Mapped[str | None] = mapped_column(Text)
    is_checked: Mapped[bool | None] = mapped_column(Boolean)
    created_date_time: Mapped[str | None] = mapped_column(Text)
    checked_date_time: Mapped[str | None] = mapped_column(Text)


class TodoLinkedResourceRecord(TodoRecord):
    """Latest linked-resource state without dereferencing provider URLs."""

    __tablename__ = "todo_linked_resources"

    list_id: Mapped[str] = mapped_column(Text, primary_key=True)
    task_id: Mapped[str] = mapped_column(Text, primary_key=True)
    linked_resource_id: Mapped[str] = mapped_column(Text, primary_key=True)
    web_url: Mapped[str | None] = mapped_column(Text)
    application_name: Mapped[str | None] = mapped_column(Text)
    display_name: Mapped[str | None] = mapped_column(Text)
    external_id: Mapped[str | None] = mapped_column(Text)


class TodoSighting(Base):
    """Durable proof that one provider key appeared in one snapshot run."""

    __abstract__ = True

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True, sort_order=-2)
    run_id: Mapped[str] = mapped_column(String(32), primary_key=True, sort_order=-1)
    observed_at: Mapped[str] = mapped_column(String(40), index=True)
    evidence_id: Mapped[str] = mapped_column(String(32), index=True)


class TodoTaskListSighting(TodoSighting):
    """One list observed by one authoritative snapshot run."""

    __tablename__ = "todo_task_list_sightings"

    list_id: Mapped[str] = mapped_column(Text, primary_key=True)


class TodoTaskSighting(TodoSighting):
    """One list-scoped task observed by one authoritative snapshot run."""

    __tablename__ = "todo_task_sightings"

    list_id: Mapped[str] = mapped_column(Text, primary_key=True)
    task_id: Mapped[str] = mapped_column(Text, primary_key=True)


class TodoChecklistItemSighting(TodoSighting):
    """One checklist key observed by one authoritative snapshot run."""

    __tablename__ = "todo_checklist_item_sightings"

    list_id: Mapped[str] = mapped_column(Text, primary_key=True)
    task_id: Mapped[str] = mapped_column(Text, primary_key=True)
    checklist_item_id: Mapped[str] = mapped_column(Text, primary_key=True)


class TodoLinkedResourceSighting(TodoSighting):
    """One linked-resource key observed by one authoritative snapshot run."""

    __tablename__ = "todo_linked_resource_sightings"

    list_id: Mapped[str] = mapped_column(Text, primary_key=True)
    task_id: Mapped[str] = mapped_column(Text, primary_key=True)
    linked_resource_id: Mapped[str] = mapped_column(Text, primary_key=True)


class TodoTraversalCompletion(Base):
    """Durable terminal-page proof for one collection traversal."""

    __tablename__ = "todo_traversal_completions"

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    scope_key: Mapped[str] = mapped_column(Text, primary_key=True)
    collection_kind: Mapped[str] = mapped_column(String(32), index=True)
    list_id: Mapped[str | None] = mapped_column(Text)
    task_id: Mapped[str | None] = mapped_column(Text)
    observed_at: Mapped[str] = mapped_column(String(40), index=True)
    evidence_id: Mapped[str] = mapped_column(String(32), index=True)


class TodoSnapshotCandidate(Base):
    """Validated terminal snapshot awaiting compare-and-swap promotion."""

    __tablename__ = "todo_snapshot_candidates"

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    base_revision: Mapped[int | None] = mapped_column(Integer)
    observed_at: Mapped[str] = mapped_column(String(40))
    evidence_id: Mapped[str] = mapped_column(String(32))
    committed_at: Mapped[str | None] = mapped_column(String(40))


class TodoSnapshotState(Base):
    """Latest authoritative snapshot revision for one logical source."""

    __tablename__ = "todo_snapshot_state"

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer)
    run_id: Mapped[str] = mapped_column(String(32))
    observed_at: Mapped[str] = mapped_column(String(40))
    evidence_id: Mapped[str] = mapped_column(String(32))
    committed_at: Mapped[str] = mapped_column(String(40))


class TodoPresence(Base):
    """Current authoritative presence separate from historical provider content."""

    __abstract__ = True

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True, sort_order=-1)
    is_present: Mapped[bool] = mapped_column(Boolean)
    latest_run_id: Mapped[str] = mapped_column(String(32), index=True)
    latest_observed_at: Mapped[str] = mapped_column(String(40), index=True)
    latest_evidence_id: Mapped[str] = mapped_column(String(32), index=True)


class TodoTaskListPresence(TodoPresence):
    """Current presence for one task-list key."""

    __tablename__ = "todo_task_list_presence"

    list_id: Mapped[str] = mapped_column(Text, primary_key=True)


class TodoTaskPresence(TodoPresence):
    """Current presence for one list-scoped task key."""

    __tablename__ = "todo_task_presence"

    list_id: Mapped[str] = mapped_column(Text, primary_key=True)
    task_id: Mapped[str] = mapped_column(Text, primary_key=True)


class TodoChecklistItemPresence(TodoPresence):
    """Current presence for one list/task/checklist key."""

    __tablename__ = "todo_checklist_item_presence"

    list_id: Mapped[str] = mapped_column(Text, primary_key=True)
    task_id: Mapped[str] = mapped_column(Text, primary_key=True)
    checklist_item_id: Mapped[str] = mapped_column(Text, primary_key=True)


class TodoLinkedResourcePresence(TodoPresence):
    """Current presence for one list/task/linked-resource key."""

    __tablename__ = "todo_linked_resource_presence"

    list_id: Mapped[str] = mapped_column(Text, primary_key=True)
    task_id: Mapped[str] = mapped_column(Text, primary_key=True)
    linked_resource_id: Mapped[str] = mapped_column(Text, primary_key=True)


__all__ = [
    "TodoChecklistItemPresence",
    "TodoChecklistItemRecord",
    "TodoChecklistItemSighting",
    "TodoLinkedResourcePresence",
    "TodoLinkedResourceRecord",
    "TodoLinkedResourceSighting",
    "TodoSnapshotCandidate",
    "TodoSnapshotState",
    "TodoTaskListPresence",
    "TodoTaskListRecord",
    "TodoTaskListSighting",
    "TodoTaskPresence",
    "TodoTaskRecord",
    "TodoTaskSighting",
    "TodoTraversalCompletion",
]
