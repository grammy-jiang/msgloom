"""Publish only OneDrive facts justified by a winning checkpoint transaction."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from message_ingest.acquisition.handoff import (
    AcquisitionFactKind,
    AcquisitionStream,
    FactSpec,
    ReleaseEntryKind,
    ReleaseEntrySpec,
    ReleaseGroupSpec,
    ReleaseKind,
    StorageRelation,
    source_state_key,
)
from message_ingest.catalog.models.handoff import AcquisitionFact
from message_ingest.catalog.models.microsoft.onedrive import (
    OneDriveDeltaCheckpointCandidate,
    OneDriveItemRecord,
)
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.sync.microsoft.onedrive.state import OneDriveResyncChanges

if TYPE_CHECKING:
    from message_ingest.catalog import Catalog


def publish_checkpoint(
    catalog: Catalog,
    session: Session,
    *,
    source_id: str,
    candidate: OneDriveDeltaCheckpointCandidate,
    revision: int,
    changes: OneDriveResyncChanges | None,
) -> None:
    """
    Bind exact winners before the caller commits checkpoint and presence.

    Normal delta revalidates run facts against the effective-state index.
    Reset uses only the final applied observation per item, never pre-reset
    run residue. Derived absence is a source-scoped transition without a
    fabricated provider representation. Cursor bytes never enter the ledger.
    """
    ledger = AcquisitionHandoffStore(catalog)
    staged = [
        FactSpec.from_json(payload)
        for payload in session.scalars(
            select(AcquisitionFact.payload).where(
                AcquisitionFact.source_id == source_id,
                AcquisitionFact.stream == AcquisitionStream.ONEDRIVE,
                AcquisitionFact.run_id == candidate.run_id,
            )
        )
    ]
    winners = (
        _normal_winners(ledger, session, staged)
        if changes is None
        else _reset_winners(staged, changes, candidate)
    )
    entries = []
    for fact in sorted(winners, key=lambda fact: fact.resource_identity):
        entries.append(
            ReleaseEntrySpec(
                resource_kind=fact.resource_kind,
                resource_identity=fact.resource_identity,
                facts=((fact.fact_id, "primary"),),
            )
        )
        record = session.get(OneDriveItemRecord, (source_id, fact.resource_identity))
        if record is None:
            raise ValueError("OneDrive winner has no materialized item")
        entries.append(
            _transition(
                ledger,
                session,
                source_id=source_id,
                candidate=candidate,
                revision=revision,
                item_id=fact.resource_identity,
                reason="provider_deleted" if record.is_deleted else "observed_present",
                observed_at=fact.provider_observed_at,
                evidence_id=fact.evidence_id,
            )
        )
    if changes is not None:
        for item_id in sorted(changes.absent_item_ids):
            entries.append(
                _transition(
                    ledger,
                    session,
                    source_id=source_id,
                    candidate=candidate,
                    revision=revision,
                    item_id=item_id,
                    reason="resync_absent",
                    observed_at=candidate.observed_at,
                    evidence_id=candidate.evidence_id,
                )
            )
    group = ReleaseGroupSpec(
        source_id=source_id,
        stream=AcquisitionStream.ONEDRIVE,
        release_kind=ReleaseKind.AUTHORITY_SCOPE,
        subject_kind="onedrive_delta",
        subject_identity=source_id,
        owner_run_id=candidate.run_id,
        released_at=candidate.observed_at,
        coverage_kind="complete",
        scope_kind="onedrive_source",
        scope_identity=source_id,
        authority_revision=str(revision),
    )
    ledger.release_authority_group_in_session(
        session,
        group,
        entries,
        winning_fact_ids=tuple(fact.fact_id for fact in winners),
    )


def _normal_winners(
    ledger: AcquisitionHandoffStore,
    session: Session,
    staged: list[FactSpec],
) -> list[FactSpec]:
    """Choose the exact live application, including pinned equivalent recovery."""
    winners: dict[str, FactSpec] = {}
    for fact in staged:
        if (
            fact.resource_kind != "onedrive_item"
            or fact.fact_kind != AcquisitionFactKind.RESOURCE_OBSERVATION
            or fact.storage_relation
            not in {StorageRelation.ADVANCED, StorageRelation.CURRENT_EQUIVALENT}
        ):
            continue
        current = ledger.current_effective_state(session, fact.effective_key)
        expected = (
            fact.revalidated_fact_id
            if fact.storage_relation == StorageRelation.CURRENT_EQUIVALENT
            else fact.fact_id
        )
        if (
            current is None
            or current["fact_id"] != expected
            or current["source_state_key"] != fact.source_state_key
        ):
            continue
        record = session.get(
            OneDriveItemRecord, (fact.source_id, fact.resource_identity)
        )
        # Inferred absence preserves raw bytes for diagnostics. Those bytes
        # cannot revalidate a delayed positive run after a completed reset.
        if (
            record is None
            or (record.is_deleted and record.deleted is None)
            or source_state_key(record.raw) != fact.source_state_key
        ):
            continue
        winners[fact.resource_identity] = fact
    return list(winners.values())


def _reset_winners(
    staged: list[FactSpec],
    changes: OneDriveResyncChanges,
    candidate: OneDriveDeltaCheckpointCandidate,
) -> list[FactSpec]:
    """Resolve only exact observation IDs emitted during winning application."""
    by_observation = {
        fact.source_version_locator.observation_id: fact
        for fact in staged
        if fact.storage_relation == StorageRelation.AUTHORITY_STAGED
        and fact.resource_kind == "onedrive_item"
        and fact.authority_revision == str(candidate.base_revision)
        and fact.source_version_locator is not None
        and fact.source_version_locator.kind == "observation"
    }
    winners = []
    for observation_id in changes.applied_observation_ids:
        fact = by_observation.get(str(observation_id))
        if fact is None:
            raise ValueError("OneDrive applied reset observation lacks its fact")
        winners.append(fact)
    return winners


def _transition(
    ledger: AcquisitionHandoffStore,
    session: Session,
    *,
    source_id: str,
    candidate: OneDriveDeltaCheckpointCandidate,
    revision: int,
    item_id: str,
    reason: str,
    observed_at: str,
    evidence_id: str | None,
) -> ReleaseEntrySpec:
    """
    Stage exact source presence without repeating unchanged authority rounds.

    Presence meaning excludes checkpoint revision and run provenance. A return
    from absence is a new effective application even if metadata is unchanged.
    """
    fact = ledger.stage_state_fact_in_session(
        session,
        FactSpec(
            source_id=source_id,
            stream=AcquisitionStream.ONEDRIVE,
            run_id=candidate.run_id,
            spider_name="microsoft_onedrive_delta",
            fact_kind=AcquisitionFactKind.SCOPED_STATE_TRANSITION,
            resource_kind="onedrive_item",
            resource_identity=item_id,
            scope_kind="onedrive_source",
            scope_identity=source_id,
            provider_observed_at=observed_at,
            evidence_id=evidence_id,
            source_state_key=source_state_key(
                {"present": reason == "observed_present"}
            ),
            authority_revision=str(revision),
            transition_reason=reason,
        ),
    )
    return ReleaseEntrySpec(
        resource_kind="onedrive_item",
        resource_identity=item_id,
        entry_kind=ReleaseEntryKind.TRANSITION,
        scope_kind=fact.scope_kind,
        scope_identity=fact.scope_identity,
        facts=((fact.fact_id, "transition"),),
    )
