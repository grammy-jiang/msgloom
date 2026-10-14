"""Read exact Teams release messages using the existing saved-source adapter.

The release fact binds its immutable Teams observation. The adapter then
retains the existing captured-component selection semantics, including
explicit limitations for additive evidence that is not provider-version-bound.
No traversal, token, Spider or mutable current projection is admitted here.
"""

from __future__ import annotations

import json

from msgloom.contracts import VersionRef
from msgloom.preparation.records import PreparedSourceType
from msgloom.sources._catalog import encode_parts
from msgloom.sources._release_evidence import ReleaseEvidence, digest
from msgloom.sources._release_observations import row as immutable_row
from msgloom.sources._teams import TeamsSavedSourceAdapter
from msgloom.sources.handoff_models import ReleasedFact
from msgloom.sources.models import CollectedRecord, SourceReferenceError


def _json(value: object) -> object:
    if value is None:
        return None
    if not isinstance(value, str):
        raise SourceReferenceError("Invalid immutable Teams observation encoding")
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        raise SourceReferenceError(
            "Invalid immutable Teams observation encoding"
        ) from None


def _message_parts(fact: ReleasedFact) -> tuple[str, ...]:
    parts = _json(fact.resource_identity)
    if not isinstance(parts, list) or any(
        not isinstance(item, str) or not item for item in parts
    ):
        raise SourceReferenceError("Invalid Teams message release identity")
    expected = {"chat": 3, "channel-root": 4, "channel-reply": 5}
    if not parts or len(parts) != expected.get(parts[0]):
        raise SourceReferenceError("Invalid Teams message release scope")
    if (parts[0] == "chat") != (fact.stream == "teams_chat"):
        raise SourceReferenceError("Teams release crosses message stream")
    return tuple(parts)


def message(fact: ReleasedFact, evidence: ReleaseEvidence) -> CollectedRecord:
    """Pin one Teams message to the exact immutable observation and its bytes."""
    locator = evidence.validate_locator(fact)
    identity = _json(locator.observation_id)
    if (
        locator.kind != "observation"
        or not isinstance(identity, list)
        or len(identity) != 2
        or identity[0] != "message"
        or type(identity[1]) is not int
        or not 1 <= identity[1] < 2**63
    ):
        raise SourceReferenceError("Invalid Teams release observation locator")
    parts = _message_parts(fact)
    found = immutable_row(
        evidence.catalog,
        "SELECT * FROM teams_message_observations "
        "WHERE observation_id=? AND source_id=? AND evidence_id=?",
        (identity[1], fact.source_id, locator.evidence_id),
    )
    raw = _json(found["raw"])
    scope = _json(found["scope_key"])
    state = {
        "scope_key": scope,
        "provider_etag": _json(found["provider_etag"]),
        "deleted_date_time": _json(found["deleted_date_time"]),
        "raw": raw,
    }
    if (
        scope != ["message", *parts]
        or not isinstance(raw, dict)
        or raw.get("id") != parts[-1]
        or not fact.source_state_key
        or locator.resource_version != fact.source_state_key
        or digest(state) != fact.source_state_key
        or found["observed_at"] != fact.provider_observed_at
    ):
        raise SourceReferenceError(
            "Teams release fact disagrees with saved observation"
        )
    source_type = (
        PreparedSourceType.TEAMS_CHAT_MESSAGE
        if fact.stream == "teams_chat"
        else PreparedSourceType.TEAMS_CHANNEL_MESSAGE
    )
    reference = VersionRef(
        source_type.value,
        encode_parts(fact.source_id, *parts),
        encode_parts(str(identity[1]), locator.evidence_id),
    )
    return TeamsSavedSourceAdapter(evidence.catalog, evidence.files).read(
        reference, release_facts_only=True
    )


_SIDE_FAMILIES = {
    "topology": ("teams_topology_observations", "observation_id"),
    "coverage": ("teams_coverage_observations", "observation_id"),
    "reference": ("teams_reference_resolution_observations", "observation_id"),
    "hosted": ("teams_hosted_content_observations", "observation_id"),
    "deletion": ("teams_message_deletions", "deletion_id"),
}


def _side_state(family: str, row: dict) -> dict[str, object]:
    """Recompute the exact immutable A1 projection, never mutable current rows."""
    if family == "topology":
        return {
            "resource_kind": row["resource_kind"],
            "scope_key": _json(row["scope_key"]),
            "raw": _json(row["raw"]),
            "context": _json(row["context"]),
        }
    if family == "coverage":
        values = (
            "scope_kind",
            "scope_key",
            "fact_kind",
            "status",
            "history_incomplete",
            "visible_scope",
            "retention_limitations",
            "subscription_id",
            "subscription_valid_from",
            "subscription_valid_until",
            "gap_kind",
            "details",
        )
        state = {key: row[key] for key in values}
        for key in ("scope_key", "visible_scope", "retention_limitations", "details"):
            state[key] = _json(row[key])
        state["history_incomplete"] = bool(row["history_incomplete"])
        return state
    if family == "reference":
        return {
            "attachment_ordinal": row["attachment_ordinal"],
            "state": row["state"],
            "details": _json(row["details"]),
        }
    if family == "hosted":
        values = (
            "hosted_content_id",
            "observation_kind",
            "provider_version_bound",
            "content_type",
            "content_sha256",
            "content_bytes",
            "failure_kind",
            "status_code",
            "raw",
            "details",
        )
        state = {key: row[key] for key in values}
        for key in ("content_type", "raw", "details"):
            state[key] = _json(row[key])
        state["provider_version_bound"] = bool(row["provider_version_bound"])
        return state
    if family == "deletion":
        return {
            "scope_key": _json(row["scope_key"]),
            "deletion_kind": row["deletion_kind"],
            "declared_deleted_at": _json(row["declared_deleted_at"]),
            "readback_state": row["readback_state"],
            "readback_observed_at": row["readback_observed_at"],
            "readback_evidence_id": row["readback_evidence_id"],
        }
    raise SourceReferenceError("Unknown Teams release observation family")


def _trigger_parts(fact: ReleasedFact, row: dict, evidence: ReleaseEvidence):
    """Verify exact origin message for one released reference or hosted item."""
    found = immutable_row(
        evidence.catalog,
        "SELECT scope_key FROM teams_message_observations "
        "WHERE source_id=? AND scope_key_sha256=? AND evidence_id=?",
        (fact.source_id, row["trigger_scope_sha256"], row["trigger_evidence_id"]),
    )
    scope = _json(found["scope_key"])
    if not isinstance(scope, list) or not scope or scope[0] != "message":
        raise SourceReferenceError("Released Teams component origin is invalid")
    return scope[1:]


def _side_identity(
    family: str, fact: ReleasedFact, row: dict, evidence: ReleaseEvidence
) -> str:
    if family == "topology":
        return json.dumps(
            _json(row["scope_key"]),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    if family == "coverage":
        scope = _json(row["scope_key"])
        if not isinstance(scope, list):
            raise SourceReferenceError("Released Teams coverage scope is invalid")
        return json.dumps(
            [*scope, row["fact_kind"], row["observation_id"]],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    if family in {"reference", "hosted"}:
        parent = json.dumps(
            _trigger_parts(fact, row, evidence),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        if (
            parent != fact.parent_resource_identity
            or fact.parent_resource_kind != "teams_message"
        ):
            raise SourceReferenceError("Teams component crosses parent message")
        item = (
            [parent, "reference", row["attachment_ordinal"]]
            if family == "reference"
            else [parent, row["hosted_content_id"], row["observation_kind"]]
        )
        return json.dumps(
            item, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
    if family == "deletion":
        scope = _json(row["scope_key"])
        if not isinstance(scope, list) or not scope or scope[0] != "message":
            raise SourceReferenceError("Teams deletion lacks exact message scope")
        return json.dumps(
            scope[1:], sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
    raise SourceReferenceError("Unsupported Teams side fact")


def side_fact(fact: ReleasedFact, evidence: ReleaseEvidence) -> None:
    """Verify immutable context/component/deletion before admitting its impact."""
    locator = evidence.validate_locator(fact)
    identity = _json(locator.observation_id)
    if (
        locator.kind != "observation"
        or not isinstance(identity, list)
        or len(identity) != 2
        or identity[0] not in _SIDE_FAMILIES
        or type(identity[1]) is not int
        or not 1 <= identity[1] < 2**63
    ):
        raise SourceReferenceError("Invalid Teams side-fact locator")
    family = identity[0]
    table, key = _SIDE_FAMILIES[family]
    allowed = {
        "topology": {"teams_topology", "teams_pin"},
        "coverage": {"teams_coverage"},
        "reference": {"teams_reference_resolution"},
        "hosted": {"teams_hosted_content"},
        "deletion": {"teams_message_presence"},
    }
    if fact.resource_kind not in allowed[family]:
        raise SourceReferenceError("Teams fact and locator families disagree")
    found = immutable_row(
        evidence.catalog,
        f"SELECT * FROM {table} WHERE {key}=? AND source_id=? AND evidence_id=?",
        (identity[1], fact.source_id, locator.evidence_id),
    )
    if (
        fact.provider_observed_at != found["observed_at"]
        or not fact.source_state_key
        or locator.resource_version != fact.source_state_key
        or digest(_side_state(family, found)) != fact.source_state_key
        or fact.resource_identity != _side_identity(family, fact, found, evidence)
    ):
        raise SourceReferenceError("Teams release side fact differs from saved state")
    # The exact evidence bytes must still be present and hash/length verified.
    evidence.load(locator.evidence_id, fact.source_id)


__all__ = ["message", "side_fact"]
