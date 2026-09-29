"""Add To Do current-state tables scoped by source and provider parents."""

from sqlalchemy import JSON, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class TodoRecord(Base):
    """Share capture provenance; resource tables define provider keys."""

    __abstract__ = True

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True, sort_order=-1)
    latest_observed_at: Mapped[str] = mapped_column(String(40), index=True)
    latest_evidence_id: Mapped[str | None] = mapped_column(String(32), index=True)
    raw: Mapped[dict[str, object]] = mapped_column(JSON)


class TodoTaskListRecord(TodoRecord):
    """Latest observed task-list metadata, including built-in list kind."""

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
    """Latest explicitly fetched checklist state for one task/list pair."""

    __tablename__ = "todo_checklist_items"

    list_id: Mapped[str] = mapped_column(Text, primary_key=True)
    task_id: Mapped[str] = mapped_column(Text, primary_key=True)
    checklist_item_id: Mapped[str] = mapped_column(Text, primary_key=True)
    display_name: Mapped[str | None] = mapped_column(Text)
    is_checked: Mapped[bool | None] = mapped_column(Boolean)
    created_date_time: Mapped[str | None] = mapped_column(Text)
    checked_date_time: Mapped[str | None] = mapped_column(Text)


class TodoLinkedResourceRecord(TodoRecord):
    """Latest explicit provider evidence link; web_url may be absent."""

    __tablename__ = "todo_linked_resources"

    list_id: Mapped[str] = mapped_column(Text, primary_key=True)
    task_id: Mapped[str] = mapped_column(Text, primary_key=True)
    linked_resource_id: Mapped[str] = mapped_column(Text, primary_key=True)
    web_url: Mapped[str | None] = mapped_column(Text)
    application_name: Mapped[str | None] = mapped_column(Text)
    display_name: Mapped[str | None] = mapped_column(Text)
    external_id: Mapped[str | None] = mapped_column(Text)


__all__ = [
    "TodoChecklistItemRecord",
    "TodoLinkedResourceRecord",
    "TodoTaskListRecord",
    "TodoTaskRecord",
]
