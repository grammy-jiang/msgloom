"""Publish Contacts authority effects inside the provider's writer scope."""

from __future__ import annotations

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
    source_state_key,
)
from message_ingest.catalog.models.handoff import AcquisitionFact
from message_ingest.catalog.models.microsoft.contacts import ContactDeltaObservation
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore


class ContactsAuthorityRelease:
    """
    Bind exact effects while snapshot/delta state is applied by its owner.

    The caller already holds writer ownership and validates shared generation
    and checkpoint CAS. This helper never commits or rereads mutable contact
    projections as replay truth. Repeated delta IDs replace only the pending
    entry selection; their original ordered facts remain immutable history.
    """

    def __init__(
        self,
        session: Session,
        handoff: AcquisitionHandoffStore,
        *,
        source_id: str,
        run_id: str,
        generation: int,
        folder_id: str | None = None,
    ) -> None:
        self.session = session
        self.handoff = handoff
        self.source_id = source_id
        self.run_id = run_id
        self.generation = str(generation)
        self.folder_id = folder_id
        self.entries: dict[tuple[str, str, str | None, str], ReleaseEntrySpec] = {}
        self.winning: dict[str, str] = {}
        self.facts = [
            FactSpec.from_json(payload)
            for payload in session.scalars(
                select(AcquisitionFact.payload).filter_by(
                    source_id=source_id,
                    stream=AcquisitionStream.CONTACTS,
                    run_id=run_id,
                )
            )
        ]
        self.delta_facts = {
            (fact.scope_identity, fact.provider_order): fact
            for fact in self.facts
            if fact.storage_relation == StorageRelation.AUTHORITY_STAGED
            and fact.fact_kind == AcquisitionFactKind.RESOURCE_OBSERVATION
        }

    def snapshot_sources(self) -> None:
        """
        Select only this run's exact effective observations or recovery pins.
        """
        for fact in self.facts:
            if fact.storage_relation not in {
                StorageRelation.ADVANCED,
                StorageRelation.CURRENT_EQUIVALENT,
            } or fact.fact_kind not in {
                AcquisitionFactKind.RESOURCE_OBSERVATION,
                AcquisitionFactKind.CONTROL_CONTEXT,
            }:
                continue
            current = self.handoff.current_effective_state(
                self.session, fact.effective_key
            )
            expected = (
                fact.revalidated_fact_id
                if fact.storage_relation == StorageRelation.CURRENT_EQUIVALENT
                else fact.fact_id
            )
            if current is None or current["fact_id"] != expected:
                continue
            self._source_entry(fact)

    def presence(
        self,
        *,
        kind: str,
        identity: str,
        scope: str,
        observed_at: str,
        evidence_id: str | None,
        reason: str,
        proof: FactSpec | None = None,
    ) -> None:
        """
        Stage one applied scoped presence state, with bounded reason metadata.

        The effective presence key excludes revision and observation time so
        unchanged authority rounds do not repeat work. Reappearance changes
        that key. Source content and presence remain distinct state families.
        """
        folder = scope.removeprefix("folder:") if scope.startswith("folder:") else None
        fact = self.handoff.stage_authority_fact_in_session(
            self.session,
            FactSpec(
                source_id=self.source_id,
                stream=AcquisitionStream.CONTACTS,
                run_id=self.run_id,
                spider_name=(
                    "microsoft_contacts_delta"
                    if self.folder_id is not None
                    else "microsoft_contacts_sync"
                ),
                fact_kind=AcquisitionFactKind.SCOPED_STATE_TRANSITION,
                resource_kind=kind,
                resource_identity=identity,
                scope_kind=(
                    "contacts_inventory"
                    if kind == "contact_folder"
                    else "contacts_collection"
                ),
                scope_identity=scope,
                parent_resource_kind="contact_folder" if folder else None,
                parent_resource_identity=folder,
                component_kind="presence",
                provider_observed_at=observed_at,
                evidence_id=evidence_id,
                source_state_key=source_state_key({"is_present": reason == "present"}),
                authority_revision=self.generation,
                provider_order=proof.provider_order if proof else None,
                transition_reason=reason,
            ),
        )
        self.winning[fact.effective_key.digest] = fact.fact_id
        pairs: tuple[tuple[str, FactRole], ...] = ((fact.fact_id, "transition"),)
        if proof is not None:
            pairs = ((fact.fact_id, "transition"), (proof.fact_id, "proof"))
        self._entry(fact, ReleaseEntryKind.TRANSITION, pairs)

    def applied_delta(self, observation: ContactDeltaObservation) -> None:
        """
        Select an applied ordinal; skipped observations never call this path.
        """
        scope = f"folder:{observation.folder_id}"
        fact = self.delta_facts.get((scope, observation.ordinal))
        if (
            fact is None
            or fact.resource_identity != observation.contact_id
            or fact.evidence_id != observation.evidence_id
            or fact.provider_observed_at != observation.observed_at
        ):
            raise RuntimeError("Winning Contacts observation has no exact staged fact")
        self.winning[fact.effective_key.digest] = fact.fact_id
        key = (fact.resource_kind, fact.resource_identity, scope, "resource")
        if observation.is_removed:
            self.entries.pop(key, None)
        else:
            self._source_entry(fact)
        self.presence(
            kind="contact",
            identity=observation.contact_id,
            scope=scope,
            observed_at=observation.observed_at,
            evidence_id=observation.evidence_id,
            reason="delta_removed" if observation.is_removed else "present",
            proof=fact,
        )

    def _source_entry(self, fact: FactSpec) -> None:
        context = fact.fact_kind == AcquisitionFactKind.CONTROL_CONTEXT
        self._entry(
            fact,
            ReleaseEntryKind.CONTEXT if context else ReleaseEntryKind.RESOURCE,
            ((fact.fact_id, "context" if context else "primary"),),
        )

    def _entry(
        self,
        fact: FactSpec,
        kind: ReleaseEntryKind,
        pairs: tuple[tuple[str, FactRole], ...],
    ) -> None:
        entry = ReleaseEntrySpec(
            resource_kind=fact.resource_kind,
            resource_identity=fact.resource_identity,
            parent_resource_kind=fact.parent_resource_kind,
            parent_resource_identity=fact.parent_resource_identity,
            scope_kind=fact.scope_kind,
            scope_identity=fact.scope_identity,
            entry_kind=kind,
            facts=pairs,
        )
        self.entries[
            (fact.resource_kind, fact.resource_identity, fact.scope_identity, kind)
        ] = entry

    def publish(self, committed_at: str) -> None:
        """
        Publish all selected effects atomically with the caller's authority.
        """
        scope = (
            f"folder:{self.folder_id}" if self.folder_id is not None else self.source_id
        )
        self.handoff.release_authority_group_in_session(
            self.session,
            ReleaseGroupSpec(
                source_id=self.source_id,
                stream=AcquisitionStream.CONTACTS,
                release_kind=ReleaseKind.AUTHORITY_SCOPE,
                subject_kind=(
                    "contacts_delta"
                    if self.folder_id is not None
                    else "contacts_snapshot"
                ),
                subject_identity=scope,
                scope_kind=(
                    "contacts_collection"
                    if self.folder_id is not None
                    else "contacts_source"
                ),
                scope_identity=scope,
                owner_run_id=self.run_id,
                released_at=committed_at,
                coverage_kind="complete",
                authority_revision=self.generation,
            ),
            [self.entries[key] for key in sorted(self.entries)],
            winning_fact_ids=tuple(self.winning.values()),
        )
