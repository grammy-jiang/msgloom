"""Bounded chronological protection shared by Teams component handoff facts."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from message_ingest.acquisition.handoff import FactSpec, StorageRelation
from message_ingest.catalog.models.handoff import AcquisitionFact
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore

from ._common import compare_observed


def capture_ordered_relation(
    writer: Session,
    handoff: AcquisitionHandoffStore,
    fact: FactSpec,
    relation: StorageRelation,
) -> StorageRelation:
    """Never let a delayed component capture replace a later accepted capture.

    The mutable effective pointer may identify an early advanced observation
    even after a later equivalent observation has been staged. Compare the
    complete bounded set of accepted captures at the same effective key.
    Stale observations stay in history, without becoming releasable state.
    """
    if relation != StorageRelation.ADVANCED:
        return relation
    if handoff.current_effective_state(writer, fact.effective_key) is None:
        return relation
    accepted = writer.scalars(
        select(AcquisitionFact.payload)
        .where(
            AcquisitionFact.effective_key == fact.effective_key.digest,
            AcquisitionFact.storage_relation.in_(
                (StorageRelation.ADVANCED, StorageRelation.CURRENT_EQUIVALENT)
            ),
        )
        .limit(10_001)
    )
    for index, payload in enumerate(accepted, 1):
        if index > 10_000:
            raise ValueError("Teams component chronology exceeds safe history bound")
        prior = FactSpec.from_json(payload)
        if compare_observed(fact.provider_observed_at, prior.provider_observed_at) <= 0:
            return StorageRelation.STALE
    return relation


__all__ = ["capture_ordered_relation"]
