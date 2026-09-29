"""Closed native-reply graph analysis for deterministic grouping."""

from __future__ import annotations

from typing import Protocol

from msgloom.contracts import VersionRef
from msgloom.preparation.filtering import SOURCE_SCOPE_RELATIONSHIP
from msgloom.preparation.records import NativeRelationship, PreparedRecord


def version_key(reference: VersionRef) -> tuple[str, str, str]:
    """Return the canonical ordering key for an exact version reference."""
    return (reference.kind, reference.identity, reference.version)


class EvidenceLike(Protocol):
    """Structural evidence fields needed for canonical ordering."""

    source: VersionRef
    relationship_kind: str
    target: VersionRef


def evidence_key(
    evidence: EvidenceLike,
) -> tuple[str, str, str, str, str, str, str]:
    """Return the canonical ordering key for grouping evidence."""
    return (
        *version_key(evidence.source),
        evidence.relationship_kind,
        *version_key(evidence.target),
    )


def source_scope(record: PreparedRecord) -> tuple[VersionRef | None, str | None]:
    """Return one valid declared scope or a privacy-safe uncertainty reason."""
    scopes = tuple(
        item.target
        for item in record.relationships
        if item.kind == SOURCE_SCOPE_RELATIONSHIP
    )
    if not scopes:
        return (None, "Source scope evidence is missing.")
    if len(scopes) != 1:
        return (None, "Multiple source scope relationships are ambiguous.")
    if scopes[0].kind != SOURCE_SCOPE_RELATIONSHIP:
        return (None, "Source scope relationship has an invalid target kind.")
    return (scopes[0], None)


def analyze_direct_relationships(
    records: tuple[PreparedRecord, ...],
    relation_kind: str,
) -> tuple[
    dict[VersionRef, tuple[NativeRelationship, ...]],
    dict[VersionRef, str],
]:
    """Close invalid ancestry before any native-reply edge can be unioned."""
    ordered = tuple(sorted(records, key=lambda item: version_key(item.source)))
    by_ref = {record.source: record for record in ordered}
    relations = {
        record.source: tuple(
            item for item in record.relationships if item.kind == relation_kind
        )
        for record in ordered
    }
    blocked: dict[VersionRef, str] = {}

    participants = {record.source for record in ordered if relations[record.source]}
    participants.update(
        relation.target
        for record in ordered
        for relation in relations[record.source]
        if relation.target in by_ref
    )
    scopes: dict[VersionRef, VersionRef] = {}
    for source in sorted(participants, key=version_key):
        scope, reason = source_scope(by_ref[source])
        if reason is not None:
            blocked[source] = reason
        elif scope is not None:
            scopes[source] = scope

    for record in ordered:
        direct = relations[record.source]
        if len(direct) > 1:
            blocked[record.source] = "Multiple native parent links are ambiguous."
            continue
        if not direct or record.source in blocked:
            continue
        target = direct[0].target
        target_record = by_ref.get(target)
        if target == record.source:
            blocked[record.source] = "A native parent self-link is invalid."
        elif target.kind != record.source.kind or target_record is None:
            blocked[record.source] = (
                "Native parent is missing from this exact source scope."
            )
        elif target_record.source_type is not record.source_type:
            blocked[record.source] = "Cross-source relationship cannot form a group."
        elif target in blocked:
            continue
        elif scopes[record.source] != scopes[target]:
            blocked[record.source] = (
                "Native parent belongs to a different declared source scope."
            )

    _block_cycles(ordered, relations, blocked, by_ref)
    _close_blocked_ancestry(ordered, relations, blocked)
    return (relations, blocked)


def _block_cycles(
    records: tuple[PreparedRecord, ...],
    relations: dict[VersionRef, tuple[NativeRelationship, ...]],
    blocked: dict[VersionRef, str],
    by_ref: dict[VersionRef, PreparedRecord],
) -> None:
    """Mark every member of a valid-looking parent cycle as uncertain."""
    for record in records:
        start = record.source
        if start in blocked:
            continue
        path: list[VersionRef] = []
        positions: dict[VersionRef, int] = {}
        current = start
        while current not in blocked and current in by_ref:
            if current in positions:
                for member in path[positions[current] :]:
                    blocked[member] = "Native parent relationships form a cycle."
                break
            positions[current] = len(path)
            path.append(current)
            direct = relations[current]
            if len(direct) != 1:
                break
            current = direct[0].target


def _close_blocked_ancestry(
    records: tuple[PreparedRecord, ...],
    relations: dict[VersionRef, tuple[NativeRelationship, ...]],
    blocked: dict[VersionRef, str],
) -> None:
    """Propagate invalid ancestry to every descendant before component union."""
    changed = True
    while changed:
        changed = False
        for record in records:
            source = record.source
            if source in blocked:
                continue
            direct = relations[source]
            if len(direct) == 1 and direct[0].target in blocked:
                blocked[source] = (
                    "Native parent ancestry contains uncertain relationship evidence."
                )
                changed = True


def evidence_is_connected(
    members: tuple[VersionRef, ...],
    edges: tuple[tuple[VersionRef, VersionRef], ...],
) -> bool:
    """Return whether undirected evidence edges connect every exact member."""
    if not members:
        return False
    adjacency = {member: set() for member in members}
    for source, target in edges:
        if source not in adjacency or target not in adjacency:
            return False
        adjacency[source].add(target)
        adjacency[target].add(source)
    seen: set[VersionRef] = set()
    pending = [members[0]]
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        pending.extend(adjacency[current] - seen)
    return len(seen) == len(members)
