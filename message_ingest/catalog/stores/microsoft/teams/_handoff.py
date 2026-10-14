"""Stage exact Teams facts inside the existing provider-owned transactions."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from sqlalchemy.orm import Session

from message_ingest.acquisition.handoff import (
    AcquisitionFactKind,
    AcquisitionStream,
    FactSpec,
    SourceVersionLocator,
    StorageRelation,
    canonical_json,
)
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore

from ._common import Outcome


def _digest(value: object) -> str:
    """Hash unbounded provider projections while keeping ledger payloads bounded."""
    return hashlib.sha256(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def observation_locator(family: str, observation_id: int) -> str:
    """Name one immutable Teams observation family and row without table leakage."""
    return canonical_json([family, observation_id])


def _relation(outcome: Outcome) -> StorageRelation:
    if outcome == "stale":
        return StorageRelation.STALE
    if outcome in {"replay", "tie"}:
        return StorageRelation.CURRENT_EQUIVALENT
    return StorageRelation.ADVANCED


def _message_parts(scope_key: object) -> tuple[str, ...]:
    if (
        not isinstance(scope_key, list)
        or len(scope_key) < 4
        or scope_key[0] != "message"
        or any(not isinstance(value, str) or not value for value in scope_key[1:])
    ):
        raise ValueError("Teams handoff message scope is invalid")
    location = scope_key[1]
    size = {"chat": 4, "channel-root": 5, "channel-reply": 6}.get(location)
    if size is None or len(scope_key) != size:
        raise ValueError("Teams handoff message scope is invalid")
    return tuple(scope_key[1:])


def message_resource_identity(scope_key: object) -> str:
    """Return one opaque, scoped message identity independent of capture version."""
    return canonical_json(_message_parts(scope_key))


def message_stream(scope_key: object) -> AcquisitionStream:
    return (
        AcquisitionStream.TEAMS_CHAT
        if _message_parts(scope_key)[0] == "chat"
        else AcquisitionStream.TEAMS_CHANNEL
    )


def message_scope_identity(scope_key: object) -> tuple[str, str]:
    parts = _message_parts(scope_key)
    if parts[0] == "chat":
        return "teams_chat", canonical_json([parts[1]])
    return "teams_channel", canonical_json([parts[1], parts[2]])


def message_state(row: Any) -> dict[str, object]:
    return {
        "scope_key": row.scope_key,
        "provider_etag": row.provider_etag,
        "deleted_date_time": row.deleted_date_time,
        "raw": row.raw,
    }


def topology_state(row: Any) -> dict[str, object]:
    return {
        "resource_kind": row.resource_kind,
        "scope_key": row.scope_key,
        "raw": row.raw,
        "context": row.context,
    }


def coverage_state(row: Any) -> dict[str, object]:
    return {
        "scope_kind": row.scope_kind,
        "scope_key": row.scope_key,
        "fact_kind": row.fact_kind,
        "status": row.status,
        "history_incomplete": row.history_incomplete,
        "visible_scope": row.visible_scope,
        "retention_limitations": row.retention_limitations,
        "subscription_id": row.subscription_id,
        "subscription_valid_from": row.subscription_valid_from,
        "subscription_valid_until": row.subscription_valid_until,
        "gap_kind": row.gap_kind,
        "details": row.details,
    }


def reference_state(row: Any) -> dict[str, object]:
    return {
        "attachment_ordinal": row.attachment_ordinal,
        "state": row.state,
        "details": row.details,
    }


def hosted_state(row: Any) -> dict[str, object]:
    return {
        "hosted_content_id": row.hosted_content_id,
        "observation_kind": row.observation_kind,
        "provider_version_bound": row.provider_version_bound,
        "content_type": row.content_type,
        "content_sha256": row.content_sha256,
        "content_bytes": row.content_bytes,
        "failure_kind": row.failure_kind,
        "status_code": row.status_code,
        "raw": row.raw,
        "details": row.details,
    }


def deletion_state(row: Any) -> dict[str, object]:
    return {
        "scope_key": row.scope_key,
        "deletion_kind": row.deletion_kind,
        "declared_deleted_at": row.declared_deleted_at,
        "readback_state": row.readback_state,
        "readback_observed_at": row.readback_observed_at,
        "readback_evidence_id": row.readback_evidence_id,
    }


def _locator(
    row: Any,
    *,
    family: str,
    resource_identity: str,
    component_kind: str | None = None,
    state_key: str,
) -> SourceVersionLocator:
    # Deletions have their own immutable primary key, not observation_id.
    observation_id = row.deletion_id if family == "deletion" else row.observation_id
    return SourceVersionLocator(
        kind="observation",
        evidence_id=row.evidence_id,
        resource_identity=resource_identity,
        observation_id=observation_locator(family, observation_id),
        component_kind=component_kind,
        resource_version=state_key,
    )


def stage_message(
    writer: Session,
    handoff: AcquisitionHandoffStore,
    *,
    spider_name: str,
    row: Any,
    run_id: str,
    outcome: Outcome,
) -> None:
    identity = message_resource_identity(row.scope_key)
    scope_kind, scope_identity = message_scope_identity(row.scope_key)
    key = _digest(message_state(row))
    handoff.stage_state_fact_in_session(
        writer,
        FactSpec(
            source_id=row.source_id,
            stream=message_stream(row.scope_key),
            run_id=run_id,
            spider_name=spider_name,
            fact_kind=AcquisitionFactKind.RESOURCE_OBSERVATION,
            resource_kind="teams_message",
            resource_identity=identity,
            scope_kind=scope_kind,
            scope_identity=scope_identity,
            provider_observed_at=row.observed_at,
            evidence_id=row.evidence_id,
            source_state_key=key,
            source_version_locator=_locator(
                row,
                family="message",
                resource_identity=identity,
                state_key=key,
            ),
            storage_relation=_relation(outcome),
        ),
    )


def _topology_stream(row: Any) -> AcquisitionStream:
    if row.resource_kind in {"chat", "chat-member", "pin"}:
        return AcquisitionStream.TEAMS_CHAT
    return AcquisitionStream.TEAMS_CHANNEL


def stage_topology(
    writer: Session,
    handoff: AcquisitionHandoffStore,
    *,
    spider_name: str,
    row: Any,
    run_id: str,
    outcome: Outcome,
) -> None:
    key = _digest(topology_state(row))
    resource_identity = canonical_json(row.scope_key)
    fact_kind = AcquisitionFactKind.CONTROL_CONTEXT
    parent_kind = parent_identity = component_kind = None
    scope_kind, scope_identity = "teams_topology", resource_identity
    if row.resource_kind == "pin":
        chat_id = row.context.get("chat_id")
        message_id = row.context.get("message_id")
        if not isinstance(chat_id, str) or not isinstance(message_id, str):
            raise ValueError("Teams pin handoff lacks message scope")
        parent_scope = ["message", "chat", chat_id, message_id]
        fact_kind = AcquisitionFactKind.COMPONENT_OBSERVATION
        parent_kind = "teams_message"
        parent_identity = message_resource_identity(parent_scope)
        component_kind = "pin_state"
        scope_kind, scope_identity = message_scope_identity(parent_scope)
    handoff.stage_state_fact_in_session(
        writer,
        FactSpec(
            source_id=row.source_id,
            stream=_topology_stream(row),
            run_id=run_id,
            spider_name=spider_name,
            fact_kind=fact_kind,
            resource_kind="teams_pin" if component_kind else "teams_topology",
            resource_identity=resource_identity,
            parent_resource_kind=parent_kind,
            parent_resource_identity=parent_identity,
            scope_kind=scope_kind,
            scope_identity=scope_identity,
            component_kind=component_kind,
            provider_observed_at=row.observed_at,
            evidence_id=row.evidence_id,
            source_state_key=key,
            source_version_locator=_locator(
                row,
                family="topology",
                resource_identity=resource_identity,
                component_kind=component_kind,
                state_key=key,
            ),
            storage_relation=_relation(outcome),
        ),
    )


def _coverage_stream(row: Any) -> AcquisitionStream:
    if row.scope_kind in {"chat", "chat-messages"}:
        return AcquisitionStream.TEAMS_CHAT
    if row.scope_kind == "hosted-content":
        values = row.scope_key
        if isinstance(values, list) and len(values) >= 4 and values[2] == "chat":
            return AcquisitionStream.TEAMS_CHAT
    return AcquisitionStream.TEAMS_CHANNEL


def stage_coverage(
    writer: Session,
    handoff: AcquisitionHandoffStore,
    *,
    spider_name: str,
    row: Any,
    run_id: str,
    outcome: Outcome,
) -> None:
    key = _digest(coverage_state(row))
    # Coverage is an immutable event stream. Keep the row identity so a late
    # history-gap observation cannot be suppressed by a newer benign status.
    identity = canonical_json([*row.scope_key, row.fact_kind, row.observation_id])
    relation = (
        StorageRelation.CURRENT_EQUIVALENT
        if outcome == "replay"
        else StorageRelation.ADVANCED
    )
    handoff.stage_state_fact_in_session(
        writer,
        FactSpec(
            source_id=row.source_id,
            stream=_coverage_stream(row),
            run_id=run_id,
            spider_name=spider_name,
            fact_kind=AcquisitionFactKind.CONTROL_CONTEXT,
            resource_kind="teams_coverage",
            resource_identity=identity,
            scope_kind="teams_coverage",
            scope_identity=canonical_json(row.scope_key),
            provider_observed_at=row.observed_at,
            evidence_id=row.evidence_id,
            source_state_key=key,
            source_version_locator=_locator(
                row,
                family="coverage",
                resource_identity=identity,
                state_key=key,
            ),
            storage_relation=relation,
        ),
    )


def stage_reference(
    writer: Session,
    handoff: AcquisitionHandoffStore,
    *,
    spider_name: str,
    row: Any,
    trigger: Any,
    run_id: str,
    outcome: Outcome,
) -> None:
    parent = message_resource_identity(trigger.scope_key)
    scope_kind, scope_identity = message_scope_identity(trigger.scope_key)
    identity = canonical_json([parent, "reference", row.attachment_ordinal])
    key = _digest(reference_state(row))
    handoff.stage_state_fact_in_session(
        writer,
        FactSpec(
            source_id=row.source_id,
            stream=message_stream(trigger.scope_key),
            run_id=run_id,
            spider_name=spider_name,
            fact_kind=AcquisitionFactKind.COMPONENT_OBSERVATION,
            resource_kind="teams_reference_resolution",
            resource_identity=identity,
            parent_resource_kind="teams_message",
            parent_resource_identity=parent,
            scope_kind=scope_kind,
            scope_identity=scope_identity,
            component_kind="reference_resolution",
            provider_observed_at=row.observed_at,
            evidence_id=row.evidence_id,
            source_state_key=key,
            source_version_locator=_locator(
                row,
                family="reference",
                resource_identity=identity,
                component_kind="reference_resolution",
                state_key=key,
            ),
            storage_relation=_relation(outcome),
        ),
    )


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
    handoff.stage_state_fact_in_session(
        writer,
        FactSpec(
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
            storage_relation=(
                StorageRelation.CURRENT_EQUIVALENT
                if outcome == "replay"
                else StorageRelation.ADVANCED
            ),
        ),
    )


def stage_deletion(
    writer: Session,
    handoff: AcquisitionHandoffStore,
    *,
    spider_name: str,
    row: Any,
    run_id: str,
    outcome: Outcome,
) -> None:
    identity = message_resource_identity(row.scope_key)
    scope_kind, scope_identity = message_scope_identity(row.scope_key)
    key = _digest(deletion_state(row))
    handoff.stage_state_fact_in_session(
        writer,
        FactSpec(
            source_id=row.source_id,
            stream=message_stream(row.scope_key),
            run_id=run_id,
            spider_name=spider_name,
            fact_kind=AcquisitionFactKind.SCOPED_STATE_TRANSITION,
            resource_kind="teams_message_presence",
            resource_identity=identity,
            scope_kind=scope_kind,
            scope_identity=scope_identity,
            provider_observed_at=row.observed_at,
            evidence_id=row.evidence_id,
            source_state_key=key,
            source_version_locator=_locator(
                row,
                family="deletion",
                resource_identity=identity,
                state_key=key,
            ),
            storage_relation=_relation(outcome),
            transition_reason="provider_deleted",
        ),
    )


__all__ = [
    "coverage_state",
    "deletion_state",
    "hosted_state",
    "message_resource_identity",
    "message_scope_identity",
    "message_state",
    "message_stream",
    "observation_locator",
    "reference_state",
    "stage_coverage",
    "stage_deletion",
    "stage_hosted",
    "stage_message",
    "stage_reference",
    "stage_topology",
    "topology_state",
]
