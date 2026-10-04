"""Current-state To Do persistence with capture-time conflict handling."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal

from message_ingest.catalog.models.microsoft.todo import (
    TodoChecklistItemRecord,
    TodoLinkedResourceRecord,
    TodoRecord,
    TodoTaskListRecord,
    TodoTaskRecord,
)
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.items.microsoft.todo import (
    TodoChecklistItem,
    TodoLinkedResourceItem,
    TodoTaskItem,
    TodoTaskListItem,
)

from ._todo_handoff import stage_todo_fact

if TYPE_CHECKING:
    from message_ingest.catalog import Catalog

type TodoItem = (
    TodoTaskListItem | TodoTaskItem | TodoChecklistItem | TodoLinkedResourceItem
)
type Outcome = Literal["created", "changed", "unchanged", "stale"]


class TodoStore:
    """Persist To Do state for one source without inferring removal."""

    def __init__(
        self,
        catalog: Catalog,
        *,
        source_id: str,
        spider_name: str = "microsoft_todo_discover",
    ) -> None:
        self.catalog = catalog
        self.source_id = source_id
        self.spider_name = spider_name
        self.handoff = AcquisitionHandoffStore(catalog)

    def persist_task_list(self, item: TodoTaskListItem) -> Outcome:
        """Upsert a list observation without interpreting its built-in kind."""
        return self._upsert(TodoTaskListRecord, item)

    def persist_task(self, item: TodoTaskItem) -> Outcome:
        """Upsert task state; retain embedded relations only in raw JSON."""
        return self._upsert(TodoTaskRecord, item)

    def persist_checklist_item(self, item: TodoChecklistItem) -> Outcome:
        """Upsert one explicitly observed checklist entry."""
        return self._upsert(TodoChecklistItemRecord, item)

    def persist_linked_resource(self, item: TodoLinkedResourceItem) -> Outcome:
        """Upsert one explicit evidence link, with or without a URL."""
        return self._upsert(TodoLinkedResourceRecord, item)

    def _upsert(self, model: type[TodoRecord], item: TodoItem) -> Outcome:
        """
        Commit a complete projection if its capture is not older than current.

        Model column names match provider item attributes. Only source and
        capture provenance differ, so no second Graph field mapper is needed.
        Optional values, including empty containers and false booleans, are
        copied directly. Equal capture times use processing order. Reserve
        SQLite writer intent
        before freshness reads and commit state plus its exact fact together.
        Snapshot sightings remain a separate authority proof write.
        """
        observed = self._capture_time(item.observed_at)
        identity = {
            column.name: getattr(item, column.name)
            for column in model.__mapper__.primary_key
            if column.name != "source_id"
        }
        identity["source_id"] = self.source_id
        with self.catalog.writer_session() as session:
            record = session.get(model, identity)
            if record is not None and observed < self._capture_time(
                record.latest_observed_at
            ):
                stage_todo_fact(
                    session,
                    self.handoff,
                    source_id=self.source_id,
                    spider_name=self.spider_name,
                    item=item,
                    outcome="stale",
                )
                return "stale"
            provenance = {
                "source_id": self.source_id,
                "latest_observed_at": item.observed_at,
                "latest_evidence_id": item.evidence_id,
            }
            values = {
                column.name: getattr(item, column.name)
                for column in model.__table__.columns
                if column.name not in provenance
            }
            values.update(provenance)
            if record is None:
                session.add(model(**values))
                outcome: Outcome = "created"
            else:
                outcome = "unchanged" if record.raw == item.raw else "changed"
                for name, value in values.items():
                    setattr(record, name, value)
            stage_todo_fact(
                session,
                self.handoff,
                source_id=self.source_id,
                spider_name=self.spider_name,
                item=item,
                outcome=outcome,
            )
            return outcome

    @staticmethod
    def _capture_time(value: str) -> datetime:
        """Parse capture time as a timezone-aware instant."""
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("To Do observed_at must include a timezone offset")
        return parsed


__all__ = ["TodoStore"]
