"""Structured fragment construction for deterministic triage input."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from msgloom.contracts import SemanticDataRef, VersionRef
from msgloom.preparation.grouping import GroupStatus
from msgloom.preparation.records import PreparedSourceType

from .canonical import canonical_json, digest
from .models import (
    MAX_OCCURRENCES_PER_UNIT,
    MAX_TOTAL_OCCURRENCES,
    ContainerKind,
    FragmentKind,
    OccurrenceManifest,
    RepetitionTarget,
    SemanticFragment,
    SourceRole,
    TriageInputConfig,
    TriageSelection,
    UnitManifest,
)
from .selection import TriageInputValidationError, held_sources

_CONTEXTUAL = {
    PreparedSourceType.TODO,
    PreparedSourceType.ONEDRIVE,
    PreparedSourceType.CONTACT,
}


@dataclass(frozen=True, slots=True)
class BuiltUnit:
    """Internal complete unit before serialized-byte splitting."""

    manifest: UnitManifest
    fragments: tuple[SemanticFragment, ...]


def _ref_key(ref: VersionRef) -> tuple[str, str, str]:
    return (ref.kind, ref.identity, ref.version)


@dataclass(slots=True)
class _OccurrenceBudget:
    """Bound fragment expansion before constructing a large fragment graph."""

    remaining: int

    def take(self) -> None:
        if self.remaining <= 0:
            raise TriageInputValidationError("triage input structural limit exceeded")
        self.remaining -= 1


def occurrence_id_for(
    source: VersionRef,
    namespace: str,
    path: tuple[str | int, ...],
    kind: FragmentKind,
) -> str:
    value = {
        "source": {
            "kind": source.kind,
            "identity": source.identity,
            "version": source.version,
        },
        "namespace": namespace,
        "path": path,
        "kind": kind.value,
    }
    return sha256(canonical_json(value)).hexdigest()


def _leaf_fragments(
    value: Any,
    source: VersionRef,
    role: SourceRole,
    namespace: str,
    path: tuple[str | int, ...] = (),
    *,
    total_budget: _OccurrenceBudget,
    unit_budget: _OccurrenceBudget,
) -> list[SemanticFragment]:
    fragments: list[SemanticFragment] = []
    total_budget.take()
    unit_budget.take()
    if isinstance(value, dict):
        fragments.append(
            SemanticFragment(
                occurrence_id=occurrence_id_for(
                    source, namespace, path, FragmentKind.CONTAINER
                ),
                source_ref=source,
                role=role,
                namespace=namespace,
                path=path,
                kind=FragmentKind.CONTAINER,
                container_kind=ContainerKind.OBJECT,
                container_length=len(value),
            )
        )
        for key in sorted(value):
            fragments.extend(
                _leaf_fragments(
                    value[key],
                    source,
                    role,
                    namespace,
                    (*path, str(key)),
                    total_budget=total_budget,
                    unit_budget=unit_budget,
                )
            )
        return fragments
    if isinstance(value, (list, tuple)):
        fragments.append(
            SemanticFragment(
                occurrence_id=occurrence_id_for(
                    source, namespace, path, FragmentKind.CONTAINER
                ),
                source_ref=source,
                role=role,
                namespace=namespace,
                path=path,
                kind=FragmentKind.CONTAINER,
                container_kind=ContainerKind.ARRAY,
                container_length=len(value),
            )
        )
        for index, item in enumerate(value):
            fragments.extend(
                _leaf_fragments(
                    item,
                    source,
                    role,
                    namespace,
                    (*path, index),
                    total_budget=total_budget,
                    unit_budget=unit_budget,
                )
            )
        return fragments
    if isinstance(value, str):
        return [
            SemanticFragment(
                occurrence_id=occurrence_id_for(
                    source, namespace, path, FragmentKind.TEXT
                ),
                source_ref=source,
                role=role,
                namespace=namespace,
                path=path,
                kind=FragmentKind.TEXT,
                value=value,
                text_start=0,
                text_end=len(value),
            )
        ]
    if value is not None and not isinstance(value, (int, float, bool)):
        raise TriageInputValidationError("triage input selection failed validation")
    return [
        SemanticFragment(
            occurrence_id=occurrence_id_for(
                source, namespace, path, FragmentKind.SCALAR
            ),
            source_ref=source,
            role=role,
            namespace=namespace,
            path=path,
            kind=FragmentKind.SCALAR,
            value=value,
        )
    ]


def _deduplicate(
    fragments: tuple[SemanticFragment, ...], config: TriageInputConfig
) -> tuple[SemanticFragment, ...]:
    if not config.repetition.remove_exact_text_repetitions:
        return fragments
    seen: dict[str, SemanticFragment] = {}
    result: list[SemanticFragment] = []
    for fragment in fragments:
        eligible = (
            fragment.kind is FragmentKind.TEXT
            and fragment.namespace == "prepared"
            and bool(fragment.path)
            and fragment.path[-1] in {"body", "text"}
        )
        if not eligible:
            result.append(fragment)
            continue
        text = fragment.value
        if not isinstance(text, str):
            raise TriageInputValidationError("triage input selection failed validation")
        retained = seen.get(text)
        if retained is None:
            seen[text] = fragment
            result.append(fragment)
            continue
        result.append(
            SemanticFragment(
                occurrence_id=occurrence_id_for(
                    fragment.source_ref,
                    fragment.namespace,
                    fragment.path,
                    FragmentKind.REPETITION,
                ),
                source_ref=fragment.source_ref,
                role=fragment.role,
                namespace=fragment.namespace,
                path=fragment.path,
                kind=FragmentKind.REPETITION,
                repetition_of=RepetitionTarget(
                    source_ref=retained.source_ref,
                    namespace=retained.namespace,
                    path=retained.path,
                ),
            )
        )
    return tuple(result)


def _unit_members(
    selection: TriageSelection,
) -> tuple[tuple[tuple[VersionRef, ...], SemanticDataRef | None], ...]:
    held = {item.source_ref for item in held_sources(selection)}
    source_types = {
        item.record.source: item.record.source_type for item in selection.prepared
    }
    units: list[tuple[tuple[VersionRef, ...], SemanticDataRef | None]] = []
    for binding in selection.groups:
        group = binding.result
        active = tuple(member for member in group.members if member not in held)
        if not active:
            continue
        if group.status is GroupStatus.CONFIRMED:
            if any(source_types[item] in _CONTEXTUAL for item in active):
                raise TriageInputValidationError(
                    "triage input selection failed validation"
                )
            units.append((active, binding.data_ref))
            continue
        for member in active:
            units.append(((member,), binding.data_ref))
    return tuple(
        sorted(units, key=lambda item: tuple(_ref_key(ref) for ref in item[0]))
    )


def build_units(
    selection: TriageSelection, config: TriageInputConfig
) -> tuple[BuiltUnit, ...]:
    """Build canonical units without semantic joining beyond confirmed groups."""
    prepared = {item.record.source: item.record for item in selection.prepared}
    filters = {item.result.input: item.result for item in selection.filters}
    rules = {item.source_ref: item for item in selection.rules.evaluation.outcomes}
    roles = {item.source_ref: item.role for item in selection.roles}
    groups = {item.data_ref: item.result for item in selection.groups}
    units: list[BuiltUnit] = []
    total_budget = _OccurrenceBudget(MAX_TOTAL_OCCURRENCES)
    for members, group_ref in _unit_members(selection):
        fragments: list[SemanticFragment] = []
        unit_budget = _OccurrenceBudget(MAX_OCCURRENCES_PER_UNIT)
        for source in members:
            role = roles[source]
            documents = (
                ("prepared", prepared[source].model_dump(mode="json", round_trip=True)),
                ("filter", filters[source].model_dump(mode="json", round_trip=True)),
                ("rule", rules[source].model_dump(mode="json", round_trip=True)),
            )
            for namespace, document in documents:
                fragments.extend(
                    _leaf_fragments(
                        document,
                        source,
                        role,
                        namespace,
                        total_budget=total_budget,
                        unit_budget=unit_budget,
                    )
                )
        if group_ref is not None:
            first = members[0]
            fragments.extend(
                _leaf_fragments(
                    groups[group_ref].model_dump(mode="json", round_trip=True),
                    first,
                    roles[first],
                    "group",
                    total_budget=total_budget,
                    unit_budget=unit_budget,
                )
            )
        complete = _deduplicate(tuple(fragments), config)
        unit_basis = {
            "sources": [
                {"kind": x.kind, "identity": x.identity, "version": x.version}
                for x in members
            ],
            "group_ref": (
                {
                    "data_id": group_ref.data_id,
                    "kind": group_ref.kind,
                    "schema_version": group_ref.schema_version,
                    "sha256": group_ref.sha256,
                    "byte_count": group_ref.byte_count,
                }
                if group_ref is not None
                else None
            ),
        }
        unit_id = digest(unit_basis)
        unit_hash = digest(
            {
                "unit_id": unit_id,
                "fragments": [
                    item.model_dump(mode="json", round_trip=True) for item in complete
                ],
            }
        )
        occurrences = tuple(
            OccurrenceManifest(
                occurrence_id=item.occurrence_id,
                source_ref=item.source_ref,
                role=item.role,
                namespace=item.namespace,
                path=item.path,
                kind=item.kind,
                text_length=(item.text_end if item.kind is FragmentKind.TEXT else None),
            )
            for item in complete
        )
        units.append(
            BuiltUnit(
                manifest=UnitManifest(
                    unit_id=unit_id,
                    unit_hash=unit_hash,
                    commitment="complete-content",
                    source_refs=members,
                    group_ref=group_ref,
                    occurrences=occurrences,
                ),
                fragments=complete,
            )
        )
    return tuple(units)
