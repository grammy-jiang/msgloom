"""Map committed Teams catalog observations into saved-source records."""

from __future__ import annotations

import json
from typing import Any

from msgloom.contracts import Limitation, VersionRef
from msgloom.preparation.contracts import DocumentLocation, SavedByteReference
from msgloom.preparation.records import (
    NativeRelationship,
    PreparedParty,
    PreparedSourceType,
)
from msgloom.sources._catalog import EvidenceRow, ReadOnlyCatalog
from msgloom.sources._io import EvidenceFiles
from msgloom.sources._mapping import body_descriptor, content_kind, graph_object
from msgloom.sources._mapping import source_time as parse_source_time
from msgloom.sources._teams_catalog import (
    TeamsCatalogQueries,
    TeamsComponentRows,
    TeamsMessageSelection,
    decode_json,
    scope_digest,
)
from msgloom.sources.models import (
    CollectedAttachment,
    CollectedRecord,
    ContentKind,
    SourceEvidenceError,
    SourceReferenceError,
)

_JSON_LOCATION = DocumentLocation(part="graph-json")
_BINARY_LOCATION = DocumentLocation(part="saved-bytes")
_RELATIONS = {
    "deletion": "teams_message_deletion",
    "reference": "teams_reference_resolution",
    "hosted": "teams_hosted_content",
    "topology": "teams_topology",
    "coverage": "teams_coverage",
}


def _reject_constant(_value: str) -> object:
    raise ValueError("non-finite JSON number")


def _json_value(value: object, label: str) -> object:
    if value is None or not isinstance(value, str):
        return value
    try:
        return json.loads(value, parse_constant=_reject_constant)
    except (json.JSONDecodeError, ValueError):
        raise SourceReferenceError(f"Teams {label} JSON is invalid") from None


def _optional_dict(value: object, label: str) -> dict[str, Any] | None:
    parsed = _json_value(value, label)
    if parsed is not None and not isinstance(parsed, dict):
        raise SourceReferenceError(f"Teams {label} JSON is invalid")
    return parsed


def _canonical(value: object) -> str:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError):
        raise SourceReferenceError("Teams saved component is invalid") from None


class TeamsSavedSourceAdapter:
    """Read exact Teams observations using shared catalog and evidence guards."""

    def __init__(self, catalog: ReadOnlyCatalog, files: EvidenceFiles) -> None:
        self._catalog = catalog
        self._files = files
        self._queries = TeamsCatalogQueries(catalog)

    def list_versions(
        self,
        source_type: PreparedSourceType,
        source_id: str,
        limit: int,
    ) -> tuple[VersionRef, ...]:
        """List exact scoped Teams message observations."""
        return self._queries.list_versions(source_type, source_id, limit)

    def read(self, source: VersionRef) -> CollectedRecord:
        """Map one exact message and its currently captured additive facts."""
        selected = self._queries.select(source)
        raw, source_bytes = self._primary_evidence(selected)
        rows = self._queries.components(selected)
        scope = self._catalog.source_scope(selected.source_id)
        relationships = [NativeRelationship(kind="source_scope", target=scope)]
        limitations: list[Limitation] = []
        reference_limits, hosted = self._components(
            selected, rows, relationships, limitations
        )
        self._reply_relation(selected, rows, relationships, limitations)
        attachments = (
            self._message_attachments(selected, raw, rows, reference_limits) + hosted
        )
        body = body_descriptor(raw.get("body"), source_bytes)
        if body is None:
            limitations.append(
                Limitation(
                    "teams-body-unavailable",
                    "Selected Teams evidence contains no readable message body.",
                )
            )
        return CollectedRecord(
            source=selected.source,
            source_scope=scope,
            source_type=selected.source_type,
            semantic_identity="teams:" + selected.source.identity,
            observed_at=parse_source_time(selected.observed_at, selected.observed_at),
            source_time=parse_source_time(
                raw.get("lastModifiedDateTime") or raw.get("createdDateTime"),
                selected.observed_at,
            ),
            subject=raw.get("subject") if isinstance(raw.get("subject"), str) else None,
            sender=None,
            author=self._party(raw.get("from")),
            recipients=(),
            source_content_kind=ContentKind.JSON,
            source_bytes=source_bytes,
            body=body,
            alternate_bodies=(),
            attachments=attachments,
            relationships=tuple(relationships),
            metadata=(),
            source_locations=(_JSON_LOCATION,),
            limitations=tuple(limitations),
        )

    def _primary_evidence(
        self, selected: TeamsMessageSelection
    ) -> tuple[dict[str, Any], SavedByteReference]:
        row, data = self._evidence(
            selected.source_id, selected.evidence_id, selected.observed_at
        )
        try:
            payload = json.loads(data, parse_constant=_reject_constant)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            raise SourceEvidenceError(
                "saved Teams evidence is not valid JSON"
            ) from None
        raw = graph_object(payload, selected.message_id)
        if raw != selected.raw:
            raise SourceEvidenceError(
                "saved Teams evidence differs from immutable message observation"
            )
        return raw, self._files.reference(row)

    def _evidence(
        self, source_id: str, evidence_id: str, observed_at: str
    ) -> tuple[EvidenceRow, bytes]:
        row = self._catalog.evidence(evidence_id)
        if row.source_id != source_id:
            raise SourceEvidenceError("saved Teams evidence belongs to another source")
        if row.observed_at != observed_at:
            raise SourceEvidenceError("saved Teams evidence capture time changed")
        return row, self._files.read(row)

    def _components(
        self,
        selected: TeamsMessageSelection,
        rows: TeamsComponentRows,
        relationships: list[NativeRelationship],
        limitations: list[Limitation],
    ) -> tuple[dict[int, tuple[Limitation, ...]], tuple[CollectedAttachment, ...]]:
        per_attachment: dict[int, list[Limitation]] = {}
        hosted: list[CollectedAttachment] = []
        groups = (
            ("deletion", rows.deletions),
            ("reference", rows.references),
            ("hosted", rows.hosted),
            ("topology", rows.topology),
            ("coverage", rows.coverage),
        )
        for category, values in groups:
            for row in values:
                evidence, _data = self._evidence(
                    selected.source_id, row["evidence_id"], row["observed_at"]
                )
                facts = self._normalized_component(category, selected, row)
                observation_id = (
                    row["deletion_id"]
                    if category == "deletion"
                    else row["observation_id"]
                )
                relation_kind = _RELATIONS[category]
                relationships.append(
                    NativeRelationship(
                        kind=relation_kind,
                        target=VersionRef(
                            relation_kind + "_observation",
                            _canonical([selected.source_id, category, observation_id]),
                            _canonical(facts),
                        ),
                    )
                )
                self._component_effect(
                    category,
                    facts,
                    evidence,
                    limitations,
                    per_attachment,
                    hosted,
                )
        return (
            {key: tuple(value) for key, value in per_attachment.items()},
            tuple(hosted),
        )

    def _normalized_component(
        self,
        category: str,
        selected: TeamsMessageSelection,
        row: dict[str, Any],
    ) -> dict[str, Any]:
        facts = dict(row)
        json_fields: dict[str, tuple[type[list | dict] | None, str]] = {
            "deletion": (None, "declared_deleted_at"),
            "reference": (dict, "details"),
            "hosted": (None, "content_type"),
            "topology": (list, "scope_key"),
            "coverage": (list, "scope_key"),
        }
        expected, field = json_fields[category]
        if field in facts:
            facts[field] = (
                _json_value(facts[field], field)
                if expected is None
                else decode_json(facts[field], expected, field)
            )
        if category == "deletion":
            readback = row["readback_evidence_id"]
            if readback is not None:
                readback_at = row["readback_observed_at"]
                if not isinstance(readback_at, str):
                    raise SourceReferenceError(
                        "Teams deletion readback capture time is missing"
                    )
                self._evidence(selected.source_id, readback, readback_at)
        elif category == "hosted":
            if bool(row["provider_version_bound"]):
                raise SourceReferenceError(
                    "Teams hosted content falsely claims provider-version binding"
                )
            facts["raw"] = _optional_dict(row["raw"], "hosted raw")
            facts["details"] = decode_json(row["details"], dict, "hosted details")
        elif category == "topology":
            self._validate_scope(facts, "topology")
            facts["raw"] = _optional_dict(row["raw"], "topology raw")
            facts["context"] = decode_json(row["context"], dict, "topology context")
        elif category == "coverage":
            self._validate_scope(facts, "coverage")
            facts["visible_scope"] = _optional_dict(
                row["visible_scope"], "coverage visible scope"
            )
            facts["retention_limitations"] = decode_json(
                row["retention_limitations"], list, "coverage retention limitations"
            )
            facts["details"] = decode_json(row["details"], dict, "coverage details")
        return facts

    @staticmethod
    def _validate_scope(facts: dict[str, Any], label: str) -> None:
        scope = facts["scope_key"]
        if not isinstance(scope, list) or facts["scope_key_sha256"] != scope_digest(
            scope
        ):
            raise SourceReferenceError(f"Teams {label} scope digest is invalid")

    def _component_effect(
        self,
        category: str,
        facts: dict[str, Any],
        evidence: EvidenceRow,
        limitations: list[Limitation],
        per_attachment: dict[int, list[Limitation]],
        hosted: list[CollectedAttachment],
    ) -> None:
        if category == "deletion":
            limitations.append(
                Limitation(
                    "teams-explicit-deletion-observed",
                    "An explicit deletion fact exists; earlier captured content "
                    "remains historical evidence.",
                )
            )
            return
        if category == "reference":
            if facts["state"] != "resolved":
                per_attachment.setdefault(facts["attachment_ordinal"], []).append(
                    Limitation(
                        f"teams-reference-{facts['state']}",
                        "The captured Teams file reference is not a resolved "
                        "broad-file acquisition.",
                    )
                )
            return
        if category == "hosted":
            self._hosted_effect(facts, evidence, limitations, hosted)
            return
        if category == "topology":
            context = facts["context"]
            if isinstance(context, dict) and context.get("detail_complete") is False:
                detail = context.get("detail_limitation")
                limitations.append(
                    Limitation(
                        "teams-topology-detail-incomplete",
                        detail
                        if isinstance(detail, str) and detail
                        else "A Teams topology detail representation is incomplete.",
                    )
                )
            return
        if bool(facts["history_incomplete"]):
            limitations.append(
                Limitation(
                    "teams-history-incomplete",
                    "Teams coverage records an irreversible history gap.",
                )
            )
        retention = facts["retention_limitations"]
        if isinstance(retention, list):
            limitations.extend(
                Limitation("teams-retention-limitation", value)
                for value in retention
                if isinstance(value, str) and value
            )

    def _hosted_effect(
        self,
        facts: dict[str, Any],
        evidence: EvidenceRow,
        limitations: list[Limitation],
        hosted: list[CollectedAttachment],
    ) -> None:
        if facts["observation_kind"] == "failure":
            limitations.append(
                Limitation(
                    "teams-hosted-content-failure",
                    "A hosted-content retrieval for this captured message failed.",
                )
            )
            return
        if facts["observation_kind"] != "bytes":
            return
        saved = self._files.reference(evidence)
        if (
            facts["content_sha256"] != saved.sha256
            or facts["content_bytes"] != saved.byte_count
        ):
            raise SourceEvidenceError(
                "Teams hosted-content bytes differ from linked raw evidence"
            )
        declared = facts["content_type"]
        content_type = declared if isinstance(declared, str) else None
        hosted.append(
            CollectedAttachment(
                reference=VersionRef(
                    "teams_hosted_content",
                    _canonical(
                        [
                            evidence.source_id,
                            facts["hosted_content_id"],
                            facts["observation_id"],
                        ]
                    ),
                    _canonical(facts),
                ),
                name=None,
                content_type=content_type,
                content_kind=content_kind(content_type),
                byte_count=saved.byte_count,
                inline=True,
                saved_bytes=saved,
                location=_BINARY_LOCATION,
                limitations=(
                    Limitation(
                        "teams-hosted-not-provider-version-bound",
                        "Hosted bytes link to the triggering observation, not an "
                        "exact provider message version.",
                    ),
                ),
            )
        )

    def _message_attachments(
        self,
        selected: TeamsMessageSelection,
        raw: dict[str, Any],
        rows: TeamsComponentRows,
        reference_limits: dict[int, tuple[Limitation, ...]],
    ) -> tuple[CollectedAttachment, ...]:
        raw_values = raw.get("attachments", [])
        if raw_values is None:
            raw_values = []
        if not isinstance(raw_values, list) or len(raw_values) != len(rows.attachments):
            raise SourceReferenceError(
                "Teams attachment observations differ from message evidence"
            )
        if any(key < 0 or key >= len(raw_values) for key in reference_limits):
            raise SourceReferenceError("Teams reference attachment ordinal is invalid")
        values: list[CollectedAttachment] = []
        for ordinal, (row, raw_value) in enumerate(
            zip(rows.attachments, raw_values, strict=True)
        ):
            attachment_raw = decode_json(row["raw"], dict, "attachment raw")
            if (
                row["ordinal"] != ordinal
                or not isinstance(raw_value, dict)
                or attachment_raw != raw_value
            ):
                raise SourceReferenceError(
                    "Teams attachment observation differs from message evidence"
                )
            declared = _json_value(row["content_type"], "attachment content type")
            content_type = declared if isinstance(declared, str) else None
            name, inline = attachment_raw.get("name"), attachment_raw.get("isInline")
            values.append(
                CollectedAttachment(
                    reference=VersionRef(
                        "teams_message_attachment",
                        f"{selected.source.identity}/{ordinal}",
                        _canonical(
                            {
                                "evidence_id": selected.evidence_id,
                                "kind": row["kind"],
                                "raw": attachment_raw,
                            }
                        ),
                    ),
                    name=name if isinstance(name, str) else None,
                    content_type=content_type,
                    content_kind=ContentKind.JSON,
                    byte_count=None,
                    inline=inline if isinstance(inline, bool) else None,
                    saved_bytes=None,
                    location=_JSON_LOCATION,
                    limitations=reference_limits.get(ordinal, ()),
                )
            )
        return tuple(values)

    def _reply_relation(
        self,
        selected: TeamsMessageSelection,
        rows: TeamsComponentRows,
        relationships: list[NativeRelationship],
        limitations: list[Limitation],
    ) -> None:
        if selected.location != "channel-reply":
            return
        if rows.reply_target is None:
            limitations.append(
                Limitation(
                    "teams-reply-root-unavailable",
                    "No saved root observation predating this reply was found.",
                )
            )
            return
        target = self._queries.select(rows.reply_target)
        self._primary_evidence(target)
        relationships.append(
            NativeRelationship(kind="teams_channel_reply_to", target=rows.reply_target)
        )

    @staticmethod
    def _party(value: object) -> PreparedParty | None:
        if not isinstance(value, dict):
            return None
        for kind in ("user", "application", "device"):
            candidate = value.get(kind)
            if not isinstance(candidate, dict):
                continue
            identity = candidate.get("id")
            if isinstance(identity, str) and identity:
                name = candidate.get("displayName")
                return PreparedParty(
                    identity=f"{kind}:{identity}",
                    display_name=name if isinstance(name, str) and name else None,
                )
        return None
