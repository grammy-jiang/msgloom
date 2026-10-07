"""UTF-8-safe serialized-byte splitting and exact coverage validation."""

from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from typing import Literal

from msgloom.contracts import SemanticDataRef, VersionRef

from .build import BuiltUnit
from .canonical import canonical_json, digest
from .models import (
    CoverageFailure,
    FragmentKind,
    InputPart,
    InputPartReference,
    SemanticFragment,
    SplitBudget,
    TrustedInputVersions,
)

PART_KIND = "triage_input_part"
PART_SCHEMA_VERSION = "1"


class TriageInputSplitError(ValueError):
    """Expose a fixed safe splitting/coverage classification."""


def encode_part(part: InputPart) -> bytes:
    """Return exact canonical bytes supplied to a later isolated AI attempt."""
    return canonical_json(part)


def part_id_for(
    unit_id: str,
    unit_hash: str,
    index: int,
    fragments: tuple[SemanticFragment, ...],
) -> str:
    """Derive one part identity from its exact meaning-bearing content."""
    return digest(
        {
            "unit_id": unit_id,
            "unit_hash": unit_hash,
            "part_index": index,
            "fragments": [
                item.model_dump(mode="json", round_trip=True) for item in fragments
            ],
        }
    )


def _part(
    unit: BuiltUnit,
    index: int,
    fragments: tuple[SemanticFragment, ...],
    working_context_ref: VersionRef,
    versions: TrustedInputVersions,
) -> InputPart:
    return InputPart(
        part_id=part_id_for(
            unit.manifest.unit_id,
            unit.manifest.unit_hash,
            index,
            fragments,
        ),
        unit_id=unit.manifest.unit_id,
        unit_hash=unit.manifest.unit_hash,
        part_index=index,
        working_context_ref=working_context_ref,
        versions=versions,
        fragments=fragments,
    )


def _envelope(part: InputPart) -> InputPartReference:
    payload = encode_part(part)
    return InputPartReference(
        reference=SemanticDataRef(
            data_id=part.part_id,
            kind=PART_KIND,
            schema_version=PART_SCHEMA_VERSION,
            sha256=sha256(payload).hexdigest(),
            byte_count=len(payload),
        ),
        part=part,
    )


def _fits(part: InputPart, budget: SplitBudget) -> bool:
    return len(encode_part(part)) <= budget.max_part_bytes


def _text_chunk(
    fragment: SemanticFragment,
    start: int,
    end: int,
) -> SemanticFragment:
    text = fragment.value
    if not isinstance(text, str):
        raise TriageInputSplitError("triage input splitting failed")
    base = fragment.text_start
    if base is None:
        raise TriageInputSplitError("triage input splitting failed")
    return fragment.model_copy(
        update={
            "value": text[start - base : end - base],
            "text_start": start,
            "text_end": end,
        }
    )


def _largest_text_prefix(
    unit: BuiltUnit,
    fragment: SemanticFragment,
    start: int,
    part_index: int,
    working_context_ref: VersionRef,
    versions: TrustedInputVersions,
    budget: SplitBudget,
) -> SemanticFragment | None:
    end = fragment.text_end
    if end is None or end <= start:
        return None
    low = start + 1
    high = end
    best: SemanticFragment | None = None
    while low <= high:
        middle = (low + high) // 2
        candidate = _text_chunk(fragment, start, middle)
        part = _part(
            unit,
            part_index,
            (candidate,),
            working_context_ref,
            versions,
        )
        if _fits(part, budget):
            best = candidate
            low = middle + 1
        else:
            high = middle - 1
    return best


def _remaining_failure(
    unit: BuiltUnit,
    occurrence_index: int,
    reason: Literal["part-count-exceeded", "irreducible-fragment"],
    *,
    first_text_offset: int | None = None,
) -> CoverageFailure:
    remaining = unit.manifest.occurrences[occurrence_index:]
    return CoverageFailure(
        unit_id=unit.manifest.unit_id,
        reason=reason,
        first_occurrence=occurrence_index,
        first_text_offset=first_text_offset,
        remaining_occurrences=len(remaining),
        remaining_digest=digest(
            {
                "first_text_offset": first_text_offset,
                "occurrences": [
                    item.model_dump(mode="json", round_trip=True) for item in remaining
                ],
            }
        ),
    )


def _split_once(
    unit: BuiltUnit,
    budget: SplitBudget,
    working_context_ref: VersionRef,
    versions: TrustedInputVersions,
) -> tuple[tuple[InputPartReference, ...], CoverageFailure | None]:
    parts: list[InputPartReference] = []
    pending: list[SemanticFragment] = []

    def flush() -> bool:
        if not pending:
            return True
        if len(parts) >= budget.max_parts_per_unit:
            return False
        part = _part(
            unit,
            len(parts),
            tuple(pending),
            working_context_ref,
            versions,
        )
        if not _fits(part, budget):
            raise TriageInputSplitError("triage input splitting failed")
        parts.append(_envelope(part))
        pending.clear()
        return True

    for occurrence_index, fragment in enumerate(unit.fragments):
        candidate = _part(
            unit,
            len(parts),
            (*pending, fragment),
            working_context_ref,
            versions,
        )
        if _fits(candidate, budget):
            pending.append(fragment)
            continue
        if pending:
            if not flush():
                first = occurrence_index - len(pending)
                return tuple(parts), _remaining_failure(
                    unit, first, "part-count-exceeded"
                )
            if len(parts) >= budget.max_parts_per_unit:
                return tuple(parts), _remaining_failure(
                    unit, occurrence_index, "part-count-exceeded"
                )

        single = _part(
            unit,
            len(parts),
            (fragment,),
            working_context_ref,
            versions,
        )
        if _fits(single, budget):
            pending.append(fragment)
            continue
        if fragment.kind is not FragmentKind.TEXT:
            return tuple(parts), _remaining_failure(
                unit, occurrence_index, "irreducible-fragment"
            )

        start = fragment.text_start
        end = fragment.text_end
        if start is None or end is None:
            raise TriageInputSplitError("triage input splitting failed")
        original_start = start
        while start < end:
            if len(parts) >= budget.max_parts_per_unit:
                offset = start if start > original_start else None
                return tuple(parts), _remaining_failure(
                    unit,
                    occurrence_index,
                    "part-count-exceeded",
                    first_text_offset=offset,
                )
            chunk = _largest_text_prefix(
                unit,
                fragment,
                start,
                len(parts),
                working_context_ref,
                versions,
                budget,
            )
            if chunk is None:
                return tuple(parts), _remaining_failure(
                    unit, occurrence_index, "irreducible-fragment"
                )
            part = _part(
                unit,
                len(parts),
                (chunk,),
                working_context_ref,
                versions,
            )
            parts.append(_envelope(part))
            if chunk.text_end is None:
                raise TriageInputSplitError("triage input splitting failed")
            start = chunk.text_end

    if pending and not flush():
        index = max(0, len(unit.fragments) - len(pending))
        return tuple(parts), _remaining_failure(unit, index, "part-count-exceeded")
    return tuple(parts), None


def _retained_fragments(
    parts: tuple[InputPartReference, ...],
) -> tuple[SemanticFragment, ...]:
    return tuple(fragment for envelope in parts for fragment in envelope.part.fragments)


def _partial_unit(
    unit: BuiltUnit,
    parts: tuple[InputPartReference, ...],
) -> BuiltUnit:
    retained = _retained_fragments(parts)
    unit_hash = digest(
        {
            "unit_id": unit.manifest.unit_id,
            "retained_fragments": [
                item.model_dump(mode="json", round_trip=True) for item in retained
            ],
        }
    )
    manifest = unit.manifest.model_copy(
        update={"unit_hash": unit_hash, "commitment": "retained-prefix"}
    )
    return replace(unit, manifest=manifest)


def split_unit(
    unit: BuiltUnit,
    budget: SplitBudget,
    working_context_ref: VersionRef,
    versions: TrustedInputVersions,
) -> tuple[BuiltUnit, tuple[InputPartReference, ...], CoverageFailure | None]:
    """Split one unit and return its verifiable final content commitment."""
    parts, failure = _split_once(unit, budget, working_context_ref, versions)
    if failure is None:
        return unit, parts, None

    partial = _partial_unit(unit, parts)
    rebound, rebound_failure = _split_once(
        partial, budget, working_context_ref, versions
    )
    if rebound_failure is None:
        raise TriageInputSplitError("triage input splitting failed")
    if (
        rebound_failure.first_occurrence != failure.first_occurrence
        or rebound_failure.first_text_offset != failure.first_text_offset
        or rebound_failure.reason != failure.reason
    ):
        raise TriageInputSplitError("triage input splitting failed")
    return partial, rebound, rebound_failure


def validate_complete_coverage(
    unit: BuiltUnit, parts: tuple[InputPartReference, ...]
) -> None:
    """Prove every complete-unit occurrence appears exactly once after splitting."""
    by_id: dict[str, list[SemanticFragment]] = {}
    for envelope in parts:
        for fragment in envelope.part.fragments:
            by_id.setdefault(fragment.occurrence_id, []).append(fragment)
    expected = {item.occurrence_id: item for item in unit.manifest.occurrences}
    if set(by_id) != set(expected):
        raise TriageInputSplitError("triage input coverage failed")
    for occurrence_id, manifest in expected.items():
        fragments = by_id[occurrence_id]
        if manifest.text_length is None:
            if len(fragments) != 1:
                raise TriageInputSplitError("triage input coverage failed")
            continue
        ordered = sorted(
            fragments,
            key=lambda item: -1 if item.text_start is None else item.text_start,
        )
        cursor = 0
        for fragment in ordered:
            if fragment.text_start != cursor or fragment.text_end is None:
                raise TriageInputSplitError("triage input coverage failed")
            cursor = fragment.text_end
        if cursor != manifest.text_length:
            raise TriageInputSplitError("triage input coverage failed")


def validate_part_reference(envelope: InputPartReference) -> None:
    """Validate exact saved part bytes and content-derived part identity."""
    payload = encode_part(envelope.part)
    ref = envelope.reference
    part = envelope.part
    expected_id = part_id_for(
        part.unit_id,
        part.unit_hash,
        part.part_index,
        part.fragments,
    )
    if (
        part.part_id != expected_id
        or ref.kind != PART_KIND
        or ref.schema_version != PART_SCHEMA_VERSION
        or ref.data_id != expected_id
        or ref.byte_count != len(payload)
        or ref.sha256 != sha256(payload).hexdigest()
    ):
        raise TriageInputSplitError("triage input part reference failed validation")
