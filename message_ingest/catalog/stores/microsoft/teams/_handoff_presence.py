"""Revalidate pending restored Teams presence with exact immutable observations."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from message_ingest.acquisition.handoff import EffectiveStateKey, FactSpec
from message_ingest.catalog.models.handoff import AcquisitionFact
from message_ingest.catalog.models.microsoft.teams.message import (
    TeamsMessageCurrent,
    TeamsMessageObservation,
)
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore

from ._handoff import (
    message_resource_identity,
    message_scope_identity,
    message_stream,
    stage_live_presence,
)


def revalidate_live_presence(
    writer: Session,
    handoff: AcquisitionHandoffStore,
    *,
    spider_name: str,
    current_message: TeamsMessageObservation,
    run_id: str,
) -> None:
    """Restage only a still-effective positive transition in a fresh run.

    A failed release may leave the restored presence fact unpublished. Reuse
    its immutable observation and its effective state key; a newer live message
    is not itself a second restoration. The handoff store owns equivalence and
    ensures an already released positive state cannot be emitted again.
    """
    source = current_message.source_id
    scope = current_message.scope_key
    identity = message_resource_identity(scope)
    scope_kind, scope_identity = message_scope_identity(scope)
    latest = writer.get(
        TeamsMessageCurrent,
        (source, current_message.scope_key_sha256),
    )
    if (
        latest is None
        or latest.is_deleted
        or latest.message_observation_id != current_message.observation_id
    ):
        return
    key = EffectiveStateKey(
        source_id=source,
        stream=message_stream(scope),
        resource_kind="teams_message_presence",
        resource_identity=identity,
        scope_kind=scope_kind,
        scope_identity=scope_identity,
    )
    pointer = handoff.current_effective_state(writer, key)
    if pointer is None:
        return
    payload = writer.scalar(
        select(AcquisitionFact.payload).where(
            AcquisitionFact.fact_id == pointer["fact_id"]
        )
    )
    if payload is None:
        raise ValueError("Teams presence state references a missing fact")
    fact = FactSpec.from_json(payload)
    if fact.transition_reason != "observed_present":
        return
    locator = fact.source_version_locator
    if locator is None or locator.observation_id is None:
        raise ValueError("Teams positive presence lacks an immutable locator")
    try:
        family, observation_id = json.loads(locator.observation_id)
    except (ValueError, TypeError):
        raise ValueError("Teams positive presence locator is invalid") from None
    if family != "message" or type(observation_id) is not int:
        raise ValueError("Teams positive presence locator is invalid")
    prior = writer.get(TeamsMessageObservation, observation_id)
    if (
        prior is None
        or prior.source_id != source
        or prior.scope_key_sha256 != current_message.scope_key_sha256
        or prior.evidence_id != fact.evidence_id
        or prior.deleted_date_time is not None
    ):
        raise ValueError("Teams positive presence no longer has exact provenance")
    stage_live_presence(
        writer, handoff, spider_name=spider_name, row=prior, run_id=run_id
    )


__all__ = ["revalidate_live_presence"]
