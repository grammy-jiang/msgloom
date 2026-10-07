"""Evidence-bound deterministic grouping for prepared Phase 1 records."""

from __future__ import annotations

import json
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from msgloom.contracts import VersionRef
from msgloom.preparation.filtering import FilterOutcome, FilterResult
from msgloom.preparation.grouping_graph import (
    analyze_direct_relationships,
    evidence_is_connected,
    source_scope,
)
from msgloom.preparation.grouping_graph import (
    evidence_key as _evidence_key,
)
from msgloom.preparation.grouping_graph import (
    version_key as _version_key,
)
from msgloom.preparation.records import (
    NativeRelationship,
    PreparedRecord,
    PreparedSourceType,
)

GROUP_RESULT_KIND = "group_result"
GROUP_RESULT_SCHEMA_VERSION = "1"
MAX_GROUP_RESULT_BYTES = 4 * 1024 * 1024
MAX_RELATIONSHIP_KIND_CHARS = 128
MAX_REASON_CHARS = 2048

OUTLOOK_CONVERSATION = "outlook_conversation"
OUTLOOK_REPLY = "in_reply_to"
TEAMS_CHANNEL_REPLY = "teams_channel_reply_to"
TEAMS_CHAT_REPLY = "teams_chat_reply_to"


class _FrozenModel(BaseModel):
    """Reject coercion, unknown fields, and mutation at the semantics boundary."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


class GroupStatus(StrEnum):
    """Confidence state based only on supported source-native evidence."""

    CONFIRMED = "confirmed"
    UNCERTAIN = "uncertain"
    NONE = "none"


class GroupMethod(StrEnum):
    """Source-native method used to derive a group result."""

    OUTLOOK_REPLY = "outlook_reply"
    OUTLOOK_CONVERSATION = "outlook_conversation"
    TEAMS_CHANNEL_REPLY = "teams_channel_reply"
    TEAMS_CHAT_REPLY = "teams_chat_reply"
    NONE = "none"


class GroupEvidence(_FrozenModel):
    """Exact source relationship retained as grouping evidence."""

    source: VersionRef
    relationship_kind: str
    target: VersionRef

    @field_validator("relationship_kind")
    @classmethod
    def _bounded_kind(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("group evidence relationship kind must be non-empty")
        if len(value) > MAX_RELATIONSHIP_KIND_CHARS:
            raise ValueError("group evidence relationship kind exceeds bound")
        return value


class GroupResult(_FrozenModel):
    """One exact grouping decision with member filters and source evidence."""

    status: GroupStatus
    members: tuple[VersionRef, ...]
    method: GroupMethod
    evidence: tuple[GroupEvidence, ...]
    reason: str
    filters: tuple[FilterResult, ...]

    @model_validator(mode="after")
    def _integrity(self) -> GroupResult:
        if not self.members:
            raise ValueError("group result must contain at least one member")
        if self.members != tuple(sorted(self.members, key=_version_key)):
            raise ValueError("group members must use canonical order")
        if len(self.members) != len(set(self.members)):
            raise ValueError("group members must be unique")
        if not self.reason.strip():
            raise ValueError("group result reason must be non-empty")
        if len(self.reason) > MAX_REASON_CHARS:
            raise ValueError("group result reason exceeds configured bound")
        if self.evidence != tuple(sorted(self.evidence, key=_evidence_key)):
            raise ValueError("group evidence must use canonical order")
        if len(self.evidence) != len(set(self.evidence)):
            raise ValueError("group evidence must be unique")
        if any(item.source not in self.members for item in self.evidence):
            raise ValueError("group evidence source must be a group member")
        if self.status is GroupStatus.CONFIRMED and any(
            item.target not in self.members for item in self.evidence
        ):
            raise ValueError("confirmed group evidence target must be a member")
        filter_inputs = tuple(item.input for item in self.filters)
        if filter_inputs != self.members:
            raise ValueError("group filters must exactly match canonical members")
        held = any(
            item.outcome in (FilterOutcome.EXCLUDED, FilterOutcome.CONFLICT)
            for item in self.filters
        )
        if self.status is GroupStatus.NONE:
            if len(self.members) != 1:
                raise ValueError("ungrouped results must contain exactly one member")
            if self.method is not GroupMethod.NONE or self.evidence:
                raise ValueError("ungrouped results cannot claim grouping evidence")
        else:
            if self.method is GroupMethod.NONE:
                raise ValueError("grouped results require a source-native method")
            if held:
                raise ValueError("held filter outcomes cannot enter a grouped result")
            expected_kind = {
                GroupMethod.OUTLOOK_REPLY: OUTLOOK_REPLY,
                GroupMethod.OUTLOOK_CONVERSATION: OUTLOOK_CONVERSATION,
                GroupMethod.TEAMS_CHANNEL_REPLY: TEAMS_CHANNEL_REPLY,
                GroupMethod.TEAMS_CHAT_REPLY: TEAMS_CHAT_REPLY,
            }[self.method]
            if any(item.relationship_kind != expected_kind for item in self.evidence):
                raise ValueError("group evidence must match the claimed method")
        if self.status is GroupStatus.CONFIRMED:
            if len(self.members) < 2:
                raise ValueError("confirmed groups require at least two members")
            if self.method is GroupMethod.OUTLOOK_CONVERSATION:
                raise ValueError("conversation candidates cannot be confirmed")
            if len(self.evidence) != len(self.members) - 1:
                raise ValueError("confirmed groups require a spanning parent edge set")
            sources = tuple(item.source for item in self.evidence)
            if len(sources) != len(set(sources)):
                raise ValueError(
                    "confirmed members may claim at most one native parent"
                )
            edges = tuple((item.source, item.target) for item in self.evidence)
            if not evidence_is_connected(self.members, edges):
                raise ValueError("confirmed group evidence must connect every member")
        elif self.status is GroupStatus.UNCERTAIN:
            if self.method is not GroupMethod.OUTLOOK_CONVERSATION:
                if len(self.members) != 1:
                    raise ValueError(
                        "uncertain direct-parent results must be single-member"
                    )
            elif not self.evidence:
                raise ValueError("conversation uncertainty requires candidate evidence")
            elif len(self.members) > 1:
                sources = {item.source for item in self.evidence}
                targets = {item.target for item in self.evidence}
                if (
                    len(self.evidence) != len(self.members)
                    or sources != set(self.members)
                    or len(targets) != 1
                ):
                    raise ValueError(
                        "conversation candidates require one shared target per member"
                    )
        return self


def _direct_kind(source_type: PreparedSourceType) -> tuple[str, GroupMethod] | None:
    if source_type is PreparedSourceType.OUTLOOK_EMAIL:
        return (OUTLOOK_REPLY, GroupMethod.OUTLOOK_REPLY)
    if source_type is PreparedSourceType.TEAMS_CHANNEL_MESSAGE:
        return (TEAMS_CHANNEL_REPLY, GroupMethod.TEAMS_CHANNEL_REPLY)
    if source_type is PreparedSourceType.TEAMS_CHAT_MESSAGE:
        return (TEAMS_CHAT_REPLY, GroupMethod.TEAMS_CHAT_REPLY)
    return None


def _relationship_evidence(
    record: PreparedRecord, relationship: NativeRelationship
) -> GroupEvidence:
    return GroupEvidence(
        source=record.source,
        relationship_kind=relationship.kind,
        target=relationship.target,
    )


def _result(
    records: tuple[PreparedRecord, ...],
    filters: dict[VersionRef, FilterResult],
    status: GroupStatus,
    method: GroupMethod,
    evidence: tuple[GroupEvidence, ...],
    reason: str,
) -> GroupResult:
    members = tuple(sorted((record.source for record in records), key=_version_key))
    return GroupResult(
        status=status,
        members=members,
        method=method,
        evidence=tuple(sorted(evidence, key=_evidence_key)),
        reason=reason,
        filters=tuple(filters[member] for member in members),
    )


def _context_results(
    records: tuple[PreparedRecord, ...],
    filters: dict[VersionRef, FilterResult],
) -> tuple[GroupResult, ...]:
    return tuple(
        _result(
            (record,),
            filters,
            GroupStatus.NONE,
            GroupMethod.NONE,
            (),
            "Contextual source does not automatically form a communication group.",
        )
        for record in records
    )


def _partition_direct(
    records: tuple[PreparedRecord, ...],
    filters: dict[VersionRef, FilterResult],
    relation_kind: str,
    method: GroupMethod,
) -> tuple[tuple[GroupResult, ...], tuple[PreparedRecord, ...]]:
    by_ref = {record.source: record for record in records}
    relations, blocked = analyze_direct_relationships(records, relation_kind)

    parent = {record.source: record.source for record in records}

    def find(item: VersionRef) -> VersionRef:
        while parent[item] != item:
            item = parent[item]
        return item

    def union(left: VersionRef, right: VersionRef) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root == right_root:
            return
        if _version_key(left_root) <= _version_key(right_root):
            parent[right_root] = left_root
        else:
            parent[left_root] = right_root

    for record in records:
        direct = relations[record.source]
        if len(direct) != 1 or record.source in blocked:
            continue
        union(record.source, direct[0].target)

    components: dict[VersionRef, list[PreparedRecord]] = {}
    for record in records:
        if record.source in blocked:
            continue
        components.setdefault(find(record.source), []).append(record)

    results: list[GroupResult] = []
    consumed: set[VersionRef] = set()
    for members in components.values():
        if len(members) < 2:
            continue
        member_refs = {record.source for record in members}
        evidence = tuple(
            _relationship_evidence(record, relation)
            for record in members
            for relation in relations[record.source]
            if relation.target in member_refs
        )
        results.append(
            _result(
                tuple(members),
                filters,
                GroupStatus.CONFIRMED,
                method,
                evidence,
                "Exact scoped source-native parent relationship confirms membership.",
            )
        )
        consumed.update(member_refs)

    for source, reason in sorted(
        blocked.items(), key=lambda item: _version_key(item[0])
    ):
        record = by_ref[source]
        evidence = tuple(
            _relationship_evidence(record, item) for item in relations[source]
        )
        results.append(
            _result(
                (record,),
                filters,
                GroupStatus.UNCERTAIN,
                method,
                evidence,
                reason,
            )
        )
        consumed.add(source)

    remaining = tuple(record for record in records if record.source not in consumed)
    return (tuple(results), remaining)


def _outlook_candidates(
    records: tuple[PreparedRecord, ...],
    filters: dict[VersionRef, FilterResult],
) -> tuple[GroupResult, ...]:
    candidates: dict[tuple[VersionRef, VersionRef], list[PreparedRecord]] = {}
    ambiguous: list[tuple[PreparedRecord, str]] = []
    no_candidate: list[PreparedRecord] = []
    for record in records:
        relations = tuple(
            item
            for item in record.relationships
            if item.kind == OUTLOOK_CONVERSATION
            and item.target.kind == OUTLOOK_CONVERSATION
        )
        scope, scope_reason = source_scope(record)
        if relations and scope_reason is not None:
            ambiguous.append((record, scope_reason))
        elif len(relations) == 1 and scope is not None:
            candidates.setdefault((scope, relations[0].target), []).append(record)
        elif len(relations) > 1:
            ambiguous.append(
                (record, "Multiple Outlook conversation memberships are ambiguous.")
            )
        else:
            no_candidate.append(record)

    results: list[GroupResult] = []
    for (_, target), members in candidates.items():
        evidence = tuple(
            _relationship_evidence(record, relationship)
            for record in members
            for relationship in record.relationships
            if relationship.kind == OUTLOOK_CONVERSATION
            and relationship.target == target
        )
        results.append(
            _result(
                tuple(members),
                filters,
                GroupStatus.UNCERTAIN,
                GroupMethod.OUTLOOK_CONVERSATION,
                evidence,
                "Outlook conversation membership is supporting evidence only.",
            )
        )
    for record, reason in ambiguous:
        evidence = tuple(
            _relationship_evidence(record, relationship)
            for relationship in record.relationships
            if relationship.kind == OUTLOOK_CONVERSATION
        )
        results.append(
            _result(
                (record,),
                filters,
                GroupStatus.UNCERTAIN,
                GroupMethod.OUTLOOK_CONVERSATION,
                evidence,
                reason,
            )
        )
    for record in no_candidate:
        results.append(
            _result(
                (record,),
                filters,
                GroupStatus.NONE,
                GroupMethod.NONE,
                (),
                "No supported source-native grouping relationship is present.",
            )
        )
    return tuple(results)


def _communication_results(
    records: tuple[PreparedRecord, ...],
    filters: dict[VersionRef, FilterResult],
) -> tuple[GroupResult, ...]:
    direct = _direct_kind(records[0].source_type)
    if direct is None:
        return _context_results(records, filters)
    direct_results, remaining = _partition_direct(
        records, filters, direct[0], direct[1]
    )
    if records[0].source_type is PreparedSourceType.OUTLOOK_EMAIL:
        rest = _outlook_candidates(remaining, filters)
    else:
        rest = tuple(
            _result(
                (record,),
                filters,
                GroupStatus.NONE,
                GroupMethod.NONE,
                (),
                "No supported source-native grouping relationship is present.",
            )
            for record in remaining
        )
    return direct_results + rest


def group_records(
    records: tuple[PreparedRecord, ...],
    filter_results: tuple[FilterResult, ...],
) -> tuple[GroupResult, ...]:
    """Group exact prepared versions without subject or cross-source inference."""
    if not isinstance(records, tuple) or not isinstance(filter_results, tuple):
        raise TypeError("grouping inputs must be tuples")
    refs = tuple(record.source for record in records)
    if len(refs) != len(set(refs)):
        raise ValueError("prepared grouping inputs must have unique source versions")
    filters = {result.input: result for result in filter_results}
    if len(filters) != len(filter_results) or set(filters) != set(refs):
        raise ValueError("filter results must exactly cover grouping inputs")

    by_type: dict[PreparedSourceType, list[PreparedRecord]] = {}
    held: list[GroupResult] = []
    for record in sorted(records, key=lambda item: _version_key(item.source)):
        outcome = filters[record.source].outcome
        if outcome in (FilterOutcome.EXCLUDED, FilterOutcome.CONFLICT):
            held.append(
                _result(
                    (record,),
                    filters,
                    GroupStatus.NONE,
                    GroupMethod.NONE,
                    (),
                    "Filter exclusion or conflict blocks semantic grouping.",
                )
            )
            continue
        by_type.setdefault(record.source_type, []).append(record)

    results = tuple(held) + tuple(
        result
        for source_type in sorted(by_type, key=lambda item: item.value)
        for result in _communication_results(tuple(by_type[source_type]), filters)
    )
    return tuple(
        sorted(results, key=lambda item: tuple(map(_version_key, item.members)))
    )


class GroupResultCodec:
    """Canonical bounded codec compatible with the semantic-data registry."""

    kind = GROUP_RESULT_KIND
    schema_version = GROUP_RESULT_SCHEMA_VERSION
    python_type = GroupResult
    max_bytes = MAX_GROUP_RESULT_BYTES

    def encode(self, value: object) -> bytes:
        """Revalidate a group result and encode deterministic UTF-8 JSON."""
        if not isinstance(value, GroupResult):
            raise TypeError("group_result@1 data must be a GroupResult")
        try:
            payload = json.dumps(
                value.model_dump(mode="json", round_trip=True, warnings="error"),
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            GroupResult.model_validate_json(payload, strict=True)
        except (TypeError, ValueError):
            raise TypeError("group_result@1 data failed validation") from None
        return payload

    def decode(self, payload: bytes) -> GroupResult:
        """Decode canonical bytes and reject bypassed or noncanonical data."""
        if len(payload) > self.max_bytes:
            raise ValueError("stored group_result@1 data exceeds size bound")
        try:
            result = GroupResult.model_validate_json(payload, strict=True)
        except ValueError:
            raise ValueError("stored group_result@1 data failed validation") from None
        if self.encode(result) != payload:
            raise ValueError("stored group_result@1 data is not canonical")
        return result
