"""Chronological Teams hosted-component release staging and replay."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Literal

from sqlalchemy.orm import Session

from message_ingest.acquisition.handoff import (
    AcquisitionFactKind,
    FactSpec,
    StorageRelation,
    canonical_json,
)
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore

from ._handoff import (
    _digest,
    _locator,
    hosted_state,
    message_resource_identity,
    message_scope_identity,
    message_stream,
)
from ._handoff_chronology import capture_ordered_relation


def stage_hosted(
    writer: Session,
    handoff: AcquisitionHandoffStore,
    *,
    spider_name: str,
    row: Any,
    trigger: Any,
    run_id: str,
    outcome: Literal["created", "replay"],
) -> None:
    parent = message_resource_identity(trigger.scope_key)
    scope_kind, scope_identity = message_scope_identity(trigger.scope_key)
    component = f"hosted_{row.observation_kind}"
    identity = canonical_json([parent, row.hosted_content_id, row.observation_kind])
    key = _digest(hosted_state(row))
    fact = FactSpec(
        source_id=row.source_id,
        stream=message_stream(trigger.scope_key),
        run_id=run_id,
        spider_name=spider_name,
        fact_kind=AcquisitionFactKind.COMPONENT_OBSERVATION,
        resource_kind="teams_hosted_content",
        resource_identity=identity,
        parent_resource_kind="teams_message",
        parent_resource_identity=parent,
        scope_kind=scope_kind,
        scope_identity=scope_identity,
        component_kind=component,
        provider_observed_at=row.observed_at,
        evidence_id=row.evidence_id,
        source_state_key=key,
        source_version_locator=_locator(
            row,
            family="hosted",
            resource_identity=identity,
            component_kind=component,
            state_key=key,
        ),
        storage_relation=StorageRelation.ADVANCED,
    )
    handoff.stage_state_fact_in_session(
        writer,
        replace(
            fact,
            storage_relation=capture_ordered_relation(
                writer,
                handoff,
                fact,
                StorageRelation.CURRENT_EQUIVALENT
                if outcome == "replay"
                else StorageRelation.ADVANCED,
            ),
        ),
    )


__all__ = ["stage_hosted"]
