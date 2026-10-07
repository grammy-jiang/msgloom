"""Durable authoritative-snapshot accounting for Microsoft To Do."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.models.microsoft.todo import (
    TodoChecklistItemPresence,
    TodoChecklistItemRecord,
    TodoChecklistItemSighting,
    TodoLinkedResourcePresence,
    TodoLinkedResourceRecord,
    TodoLinkedResourceSighting,
    TodoSnapshotCandidate,
    TodoSnapshotState,
    TodoTaskListPresence,
    TodoTaskListRecord,
    TodoTaskListSighting,
    TodoTaskPresence,
    TodoTaskRecord,
    TodoTaskSighting,
    TodoTraversalCompletion,
)
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.items.microsoft.todo import (
    TodoChecklistItem,
    TodoLinkedResourceItem,
    TodoTaskItem,
    TodoTaskListItem,
    TodoTraversalCompleteItem,
)

from ._snapshot_release import SnapshotRelease, _capture_time, _reconcile_presence

_ALLOWED_COMPLETIONS = frozenset(
    {"task_lists", "tasks", "checklist_items", "linked_resources"}
)


def _scope_key(kind: str, list_id: str | None, task_id: str | None) -> str:
    """Encode an exact collection scope without rebuilding provider URLs."""
    return json.dumps(
        [kind, list_id, task_id], separators=(",", ":"), ensure_ascii=False
    )


class TodoSnapshotStore:
    """Persist sightings, traversal proof, candidates, and current presence."""

    def __init__(self, catalog, *, source_id: str) -> None:
        """Bind all snapshot state to one stable logical source."""
        self.catalog = catalog
        self.source_id = source_id

    def load_revision(self) -> int | None:
        """Return the current promoted authority revision, if any."""
        with self.catalog.Session() as session:
            state = session.get(TodoSnapshotState, self.source_id)
            return None if state is None else state.revision

    def record_sighting(self, item: object) -> None:
        """Persist one run-scoped sighting after its provider-content write."""
        run_id, evidence_id, observed_at = self._provenance(item)
        model, key, values = self._sighting_projection(
            item, run_id, evidence_id, observed_at
        )
        with self.catalog.writer_session() as session:
            current = session.get(model, key)
            if current is not None:
                if _capture_time(observed_at) < _capture_time(current.observed_at):
                    return
                current.observed_at = observed_at
                current.evidence_id = evidence_id
                return
            session.add(model(source_id=self.source_id, **values))

    def record_completion(self, item: TodoTraversalCompleteItem) -> None:
        """Persist proof that one collection chain reached a terminal page."""
        run_id, evidence_id, _observed_at = self._provenance(item)
        self._validate_completion_scope(item)
        scope_key = _scope_key(item.collection_kind, item.list_id, item.task_id)
        key = (self.source_id, run_id, scope_key)
        values = {
            "source_id": self.source_id,
            "run_id": run_id,
            "scope_key": scope_key,
            "collection_kind": item.collection_kind,
            "list_id": item.list_id,
            "task_id": item.task_id,
            "observed_at": item.observed_at,
            "evidence_id": evidence_id,
        }
        with self.catalog.writer_session() as session:
            current = session.get(TodoTraversalCompletion, key)
            if current is not None:
                if _capture_time(item.observed_at) < _capture_time(current.observed_at):
                    return
                current.observed_at = item.observed_at
                current.evidence_id = evidence_id
                return
            session.add(TodoTraversalCompletion(**values))

    def stage_candidate(
        self,
        run_id: str,
        *,
        base_revision: int | None,
    ) -> TodoSnapshotCandidate:
        """Validate traversal proof and persist one terminal candidate."""
        with self.catalog.writer_session() as session:
            existing = session.get(TodoSnapshotCandidate, (self.source_id, run_id))
            if existing is not None:
                if existing.base_revision != base_revision:
                    raise ValueError("To Do snapshot candidate base revision changed")
                return existing

            completions = session.scalars(
                select(TodoTraversalCompletion).filter_by(
                    source_id=self.source_id, run_id=run_id
                )
            ).all()
            self._validate_full_traversal(session, run_id, completions)
            terminal = max(
                completions,
                key=lambda row: (_capture_time(row.observed_at), row.scope_key),
            )
            evidence = session.get(RawHttpEvidence, terminal.evidence_id)
            if (
                evidence is None
                or evidence.source_id != self.source_id
                or evidence.run_id != run_id
            ):
                raise ValueError(
                    "To Do snapshot terminal proof lacks current-run raw evidence"
                )
            candidate = TodoSnapshotCandidate(
                source_id=self.source_id,
                run_id=run_id,
                base_revision=base_revision,
                observed_at=terminal.observed_at,
                evidence_id=terminal.evidence_id,
                committed_at=None,
            )
            session.add(candidate)
            return candidate

    def promote_snapshot(
        self,
        run_id: str,
        *,
        base_revision: int | None,
    ) -> dict[str, int]:
        """Commit revision, presence, exact facts and release atomically."""
        with self.catalog.writer_session() as session:
            candidate = session.get(TodoSnapshotCandidate, (self.source_id, run_id))
            if candidate is None or candidate.base_revision != base_revision:
                raise ValueError(
                    "To Do snapshot terminal candidate is missing or changed"
                )

            state = session.get(TodoSnapshotState, self.source_id)
            if (
                candidate.committed_at is not None
                and state is not None
                and state.run_id == run_id
            ):
                return self._promotion_summary(session, state.revision, run_id)

            committed_at = datetime.now(UTC).isoformat()
            revision = 1 if base_revision is None else base_revision + 1
            self._claim_revision(
                session,
                run_id=run_id,
                base_revision=base_revision,
                revision=revision,
                observed_at=candidate.observed_at,
                evidence_id=candidate.evidence_id,
                committed_at=committed_at,
            )
            release = SnapshotRelease(
                session,
                AcquisitionHandoffStore(self.catalog),
                source_id=self.source_id,
                run_id=run_id,
                revision=revision,
                observed_at=candidate.observed_at,
                evidence_id=candidate.evidence_id,
                committed_at=committed_at,
            )
            present = 0
            absent = 0
            for content_model, sighting_model, presence_model, key_names in (
                (
                    TodoTaskListRecord,
                    TodoTaskListSighting,
                    TodoTaskListPresence,
                    ("list_id",),
                ),
                (
                    TodoTaskRecord,
                    TodoTaskSighting,
                    TodoTaskPresence,
                    ("list_id", "task_id"),
                ),
                (
                    TodoChecklistItemRecord,
                    TodoChecklistItemSighting,
                    TodoChecklistItemPresence,
                    ("list_id", "task_id", "checklist_item_id"),
                ),
                (
                    TodoLinkedResourceRecord,
                    TodoLinkedResourceSighting,
                    TodoLinkedResourcePresence,
                    ("list_id", "task_id", "linked_resource_id"),
                ),
            ):
                counts = _reconcile_presence(
                    session,
                    source_id=self.source_id,
                    release=release,
                    content_model=content_model,
                    sighting_model=sighting_model,
                    presence_model=presence_model,
                    key_names=key_names,
                    run_id=run_id,
                    observed_at=candidate.observed_at,
                    evidence_id=candidate.evidence_id,
                )
                present += counts[0]
                absent += counts[1]
            release.publish()
            candidate.committed_at = committed_at
            return {"revision": revision, "present": present, "absent": absent}

    def _claim_revision(
        self,
        session,
        *,
        run_id: str,
        base_revision: int | None,
        revision: int,
        observed_at: str,
        evidence_id: str,
        committed_at: str,
    ) -> None:
        values = {
            "source_id": self.source_id,
            "revision": revision,
            "run_id": run_id,
            "observed_at": observed_at,
            "evidence_id": evidence_id,
            "committed_at": committed_at,
        }
        if base_revision is None:
            result = session.execute(
                sqlite_insert(TodoSnapshotState)
                .values(**values)
                .on_conflict_do_nothing(index_elements=["source_id"])
            )
        else:
            result = session.execute(
                update(TodoSnapshotState)
                .where(
                    TodoSnapshotState.source_id == self.source_id,
                    TodoSnapshotState.revision == base_revision,
                )
                .values(**values)
            )
        if result.rowcount != 1:
            raise ValueError("To Do snapshot revision changed during this run")

    def _promotion_summary(self, session, revision: int, run_id: str) -> dict[str, int]:
        present = 0
        absent = 0
        for model in (
            TodoTaskListPresence,
            TodoTaskPresence,
            TodoChecklistItemPresence,
            TodoLinkedResourcePresence,
        ):
            rows = session.scalars(
                select(model).filter_by(source_id=self.source_id, latest_run_id=run_id)
            ).all()
            present += sum(1 for row in rows if row.is_present)
            absent += sum(1 for row in rows if not row.is_present)
        return {"revision": revision, "present": present, "absent": absent}

    def _validate_full_traversal(
        self, session, run_id: str, completions: list[Any]
    ) -> None:
        actual = {
            (row.collection_kind, row.list_id, row.task_id) for row in completions
        }
        lists = {
            row.list_id
            for row in session.scalars(
                select(TodoTaskListSighting).filter_by(
                    source_id=self.source_id, run_id=run_id
                )
            ).all()
        }
        tasks = {
            (row.list_id, row.task_id)
            for row in session.scalars(
                select(TodoTaskSighting).filter_by(
                    source_id=self.source_id, run_id=run_id
                )
            ).all()
        }
        expected = {("task_lists", None, None)}
        expected.update(("tasks", list_id, None) for list_id in lists)
        expected.update(("checklist_items", *task) for task in tasks)
        expected.update(("linked_resources", *task) for task in tasks)
        if actual != expected:
            raise ValueError("To Do snapshot traversal is incomplete")
        if any(row.collection_kind not in _ALLOWED_COMPLETIONS for row in completions):
            raise ValueError("To Do snapshot traversal has an unsupported completion")
        for row in completions:
            evidence = session.get(RawHttpEvidence, row.evidence_id)
            if (
                evidence is None
                or evidence.source_id != self.source_id
                or evidence.run_id != run_id
            ):
                raise ValueError(
                    "To Do snapshot traversal proof lacks current-run raw evidence"
                )

    @staticmethod
    def _validate_completion_scope(item: TodoTraversalCompleteItem) -> None:
        kind = item.collection_kind
        if kind not in _ALLOWED_COMPLETIONS:
            raise ValueError("Unsupported To Do snapshot collection kind")
        if kind == "task_lists":
            valid = item.list_id is None and item.task_id is None
        elif kind == "tasks":
            valid = bool(item.list_id) and item.task_id is None
        else:
            valid = bool(item.list_id) and bool(item.task_id)
        if not valid:
            raise ValueError("Invalid To Do snapshot completion scope")

    @staticmethod
    def _provenance(item: object) -> tuple[str, str, str]:
        run_id = getattr(item, "run_id", None)
        evidence_id = getattr(item, "evidence_id", None)
        observed_at = getattr(item, "observed_at", None)
        if not isinstance(run_id, str):
            raise TypeError("To Do snapshot run ID must be text")
        if not run_id:
            raise ValueError("To Do snapshot item requires a run ID")
        if not isinstance(evidence_id, str):
            raise TypeError("To Do snapshot evidence ID must be text")
        if not evidence_id:
            raise ValueError("To Do snapshot item requires raw evidence")
        if not isinstance(observed_at, str):
            raise TypeError("To Do snapshot observation timestamp must be text")
        _capture_time(observed_at)
        return run_id, evidence_id, observed_at

    def _sighting_projection(
        self,
        item: object,
        run_id: str,
        evidence_id: str,
        observed_at: str,
    ) -> tuple[type[Any], tuple[str, ...], dict[str, Any]]:
        common = {
            "run_id": run_id,
            "observed_at": observed_at,
            "evidence_id": evidence_id,
        }
        if isinstance(item, TodoTaskListItem):
            return (
                TodoTaskListSighting,
                (self.source_id, run_id, item.list_id),
                {**common, "list_id": item.list_id},
            )
        if isinstance(item, TodoTaskItem):
            return (
                TodoTaskSighting,
                (self.source_id, run_id, item.list_id, item.task_id),
                {**common, "list_id": item.list_id, "task_id": item.task_id},
            )
        if isinstance(item, TodoChecklistItem):
            return (
                TodoChecklistItemSighting,
                (
                    self.source_id,
                    run_id,
                    item.list_id,
                    item.task_id,
                    item.checklist_item_id,
                ),
                {
                    **common,
                    "list_id": item.list_id,
                    "task_id": item.task_id,
                    "checklist_item_id": item.checklist_item_id,
                },
            )
        if isinstance(item, TodoLinkedResourceItem):
            return (
                TodoLinkedResourceSighting,
                (
                    self.source_id,
                    run_id,
                    item.list_id,
                    item.task_id,
                    item.linked_resource_id,
                ),
                {
                    **common,
                    "list_id": item.list_id,
                    "task_id": item.task_id,
                    "linked_resource_id": item.linked_resource_id,
                },
            )
        raise TypeError(
            f"Unsupported To Do snapshot sighting item: {type(item).__name__}"
        )


__all__ = ["TodoSnapshotStore"]
