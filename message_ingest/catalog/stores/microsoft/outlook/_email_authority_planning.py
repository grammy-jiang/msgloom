"""Read provisional observations without granting them publication rights."""

import json

from sqlalchemy import select

from message_ingest.acquisition.handoff import StorageRelation
from message_ingest.catalog.models.microsoft.outlook._email_authority import (
    MailAuthorityObservation as Observation,
)

from ._email_handoff import is_stale
from ._email_observations import load_fact


def pending_message_ids(session, source, runs, kinds):
    """Expose run-local discoveries to deferred Full target planning."""
    if kinds and "delta" not in kinds:
        return set()
    rows = session.scalars(
        select(Observation).where(
            Observation.source_id == source,
            Observation.run_id.in_(runs),
            Observation.authority_kind == "message_delta",
            Observation.resource_kind == "message",
        )
    )
    return {
        row.resource_id
        for row in rows
        if (fact := load_fact(session, row)).component_kind is None
        and fact.storage_relation != StorageRelation.STALE
    }


def newer_pending_folder(session, source, folder, observed_at):
    """
    Conservatively protect snapshot absence using pending positive heads.

    Snapshot inventory and folder delta have independent cursor lineages.
    This guard does not make speculative metadata globally authoritative.
    """
    rows = session.scalars(
        select(Observation)
        .where(
            Observation.source_id == source,
            Observation.resource_kind == "mail_folder",
            Observation.resource_id == folder,
        )
        .order_by(Observation.sequence)
    ).all()
    heads = {}
    for row in rows:
        fact = load_fact(session, row)
        if (
            fact.component_kind is None
            and fact.storage_relation != StorageRelation.STALE
        ):
            heads[row.run_id] = (fact, json.loads(row.payload))
    return any(
        data["present"] and is_stale(observed_at, fact.provider_observed_at)
        for fact, data in heads.values()
    )
