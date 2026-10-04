"""Reconcile To Do presence and publish under caller-owned authority."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from message_ingest.acquisition.handoff import (
    AcquisitionFactKind,
    AcquisitionStream,
    FactRole,
    FactSpec,
    ReleaseEntryKind,
    ReleaseEntrySpec,
    ReleaseGroupSpec,
    ReleaseKind,
    StorageRelation,
    canonical_json,
    source_state_key,
)
from message_ingest.catalog.models.handoff import AcquisitionFact
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore


class SnapshotRelease:
    """
    Collect exact applied impacts inside the snapshot writer transaction.

    Positive candidates come only from this run's immutable facts. The ledger
    checks their pinned effective application again at publication. Each child
    component has a bounded direct impact retaining its task parent; arbitrary
    checklist/link counts cannot overflow a parent's 128-member entry budget.
    Presence transitions have a separate source-scoped effective identity.
    """

    def __init__(
        self,
        session: Session,
        handoff: AcquisitionHandoffStore,
        *,
        source_id: str,
        run_id: str,
        revision: int,
        observed_at: str,
        evidence_id: str,
        committed_at: str,
    ) -> None:
        self.session = session
        self.handoff = handoff
        self.source_id = source_id
        self.run_id = run_id
        self.revision = revision
        self.observed_at = observed_at
        self.evidence_id = evidence_id
        self.committed_at = committed_at
        self.entries: list[ReleaseEntrySpec] = []
        self.winning: list[str] = []
        self.positive: dict[tuple[str, str], FactSpec] = {}
        rows = session.scalars(
            select(AcquisitionFact.payload)
            .where(
                AcquisitionFact.source_id == source_id,
                AcquisitionFact.stream == AcquisitionStream.TODO,
                AcquisitionFact.run_id == run_id,
            )
            .order_by(AcquisitionFact.fact_id)
        )
        for payload in rows:
            fact = FactSpec.from_json(payload)
            if (
                fact.storage_relation
                not in {
                    StorageRelation.ADVANCED,
                    StorageRelation.CURRENT_EQUIVALENT,
                }
                or fact.fact_kind == AcquisitionFactKind.SCOPED_STATE_TRANSITION
            ):
                continue
            current = handoff.current_effective_state(session, fact.effective_key)
            expected = (
                fact.revalidated_fact_id
                if fact.storage_relation == StorageRelation.CURRENT_EQUIVALENT
                else fact.fact_id
            )
            if current is not None and (
                current["fact_id"] == expected
                and current["source_state_key"] == fact.source_state_key
            ):
                self.positive[(fact.resource_kind, fact.resource_identity)] = fact

    def applied(
        self,
        key_names: tuple[str, ...],
        key: tuple[str, ...],
        *,
        desired: bool,
        previous: bool | None,
    ) -> None:
        """Bind only an actually applied presence key, never a skipped one."""
        kind = {
            "list_id": "todo_task_list",
            "task_id": "todo_task",
            "checklist_item_id": "todo_checklist_item",
            "linked_resource_id": "todo_linked_resource",
        }[key_names[-1]]
        identity = canonical_json(key)
        if desired and (fact := self.positive.get((kind, identity))) is not None:
            role: FactRole = (
                "context"
                if fact.fact_kind == AcquisitionFactKind.CONTROL_CONTEXT
                else "component"
                if fact.fact_kind == AcquisitionFactKind.COMPONENT_OBSERVATION
                else "primary"
            )
            entry_kind = {
                "context": ReleaseEntryKind.CONTEXT,
                "component": ReleaseEntryKind.COMPONENT,
                "primary": ReleaseEntryKind.RESOURCE,
            }[role]
            self.entries.append(self._entry(fact, role, entry_kind))
        if previous is not None and previous == desired:
            return
        parent_kind = (
            "todo_task"
            if len(key) == 3
            else "todo_task_list"
            if len(key) == 2
            else None
        )
        fact = self.handoff.stage_authority_fact_in_session(
            self.session,
            FactSpec(
                source_id=self.source_id,
                stream=AcquisitionStream.TODO,
                run_id=self.run_id,
                spider_name="microsoft_todo_sync",
                fact_kind=AcquisitionFactKind.SCOPED_STATE_TRANSITION,
                resource_kind=kind,
                resource_identity=identity,
                parent_resource_kind=parent_kind,
                parent_resource_identity=(
                    canonical_json(key[:-1]) if parent_kind else None
                ),
                scope_kind="todo_source",
                scope_identity=self.source_id,
                component_kind="presence",
                provider_observed_at=self.observed_at,
                evidence_id=self.evidence_id,
                authority_revision=str(self.revision),
                source_state_key=source_state_key({"is_present": desired}),
                transition_reason=(
                    "snapshot_present" if desired else "snapshot_absent"
                ),
            ),
        )
        self.winning.append(fact.fact_id)
        self.entries.append(
            self._entry(fact, "transition", ReleaseEntryKind.TRANSITION)
        )

    @staticmethod
    def _entry(
        fact: FactSpec,
        role: FactRole,
        kind: ReleaseEntryKind,
    ) -> ReleaseEntrySpec:
        """Retain exact direct resource, parent and scope associations."""
        return ReleaseEntrySpec(
            resource_kind=fact.resource_kind,
            resource_identity=fact.resource_identity,
            parent_resource_kind=fact.parent_resource_kind,
            parent_resource_identity=fact.parent_resource_identity,
            scope_kind=fact.scope_kind,
            scope_identity=fact.scope_identity,
            entry_kind=kind,
            facts=((fact.fact_id, role),),
        )

    def publish(self) -> None:
        """Commit one authority decision through the existing ledger API."""
        self.handoff.release_authority_group_in_session(
            self.session,
            ReleaseGroupSpec(
                source_id=self.source_id,
                stream=AcquisitionStream.TODO,
                release_kind=ReleaseKind.AUTHORITY_SCOPE,
                subject_kind="todo_snapshot",
                subject_identity=self.source_id,
                scope_kind="todo_source",
                scope_identity=self.source_id,
                owner_run_id=self.run_id,
                released_at=self.committed_at,
                coverage_kind="complete",
                authority_revision=str(self.revision),
            ),
            self.entries,
            winning_fact_ids=self.winning,
        )


def _capture_time(value: str) -> datetime:
    """Parse an aware timestamp with the snapshot's existing ordering rule."""
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(
            "To Do snapshot observation timestamps must include a timezone"
        )
    return parsed.astimezone(UTC)


def _reconcile_presence(
    session: Session,
    *,
    source_id: str,
    release: SnapshotRelease,
    content_model,
    sighting_model,
    presence_model,
    key_names: tuple[str, ...],
    run_id: str,
    observed_at: str,
    evidence_id: str,
) -> tuple[int, int]:
    """
    Apply presence and stage exact transitions under the caller's writer lock.

    Newer content blocks inferred absence. Newer presence blocks replacement.
    Neither skip emits an impact. Positive content is selected from run facts,
    never reconstructed from mutable rows after this transaction.
    """
    candidate_time = _capture_time(observed_at)
    content_rows = session.scalars(
        select(content_model)
        .filter_by(source_id=source_id)
        .order_by(*(getattr(content_model, name) for name in key_names))
    ).all()
    sighting_rows = session.scalars(
        select(sighting_model).filter_by(source_id=source_id, run_id=run_id)
    ).all()
    seen = {tuple(getattr(row, name) for name in key_names) for row in sighting_rows}
    present = 0
    absent = 0
    for content in content_rows:
        key = tuple(getattr(content, name) for name in key_names)
        desired = key in seen
        if not desired and _capture_time(content.latest_observed_at) > candidate_time:
            continue
        current = session.get(presence_model, (source_id, *key))
        if (
            current is not None
            and _capture_time(current.latest_observed_at) > candidate_time
        ):
            continue
        previous = None if current is None else current.is_present
        values = {
            "is_present": desired,
            "latest_run_id": run_id,
            "latest_observed_at": observed_at,
            "latest_evidence_id": evidence_id,
        }
        if current is None:
            session.add(
                presence_model(
                    source_id=source_id,
                    **dict(zip(key_names, key, strict=True)),
                    **values,
                )
            )
        else:
            for name, value in values.items():
                setattr(current, name, value)
        release.applied(key_names, key, desired=desired, previous=previous)
        if desired:
            present += 1
        else:
            absent += 1
    return present, absent
