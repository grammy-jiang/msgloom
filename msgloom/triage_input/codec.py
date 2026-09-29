"""Canonical bounded codec for triage_input@1 semantic data."""

from __future__ import annotations

import json

from pydantic import ValidationError

from .build import occurrence_id_for
from .canonical import digest
from .integrity import selection_binding_digest
from .models import (
    FragmentKind,
    InputPart,
    OccurrenceManifest,
    PartState,
    SemanticFragment,
    TriageInputSnapshot,
)
from .split import encode_part, validate_part_reference

TRIAGE_INPUT_KIND = "triage_input"
TRIAGE_INPUT_SCHEMA_VERSION = "1"
MAX_TRIAGE_INPUT_BYTES = 64 * 1024 * 1024

_REF_KINDS = (
    ("prepared", "1"),
    ("filter_result", "1"),
    ("group_result", "1"),
)


class TriageInputCodec:
    """Canonical validating codec compatible with SemanticDataRegistry."""

    kind = TRIAGE_INPUT_KIND
    schema_version = TRIAGE_INPUT_SCHEMA_VERSION
    python_type = TriageInputSnapshot
    max_bytes = MAX_TRIAGE_INPUT_BYTES

    def encode(self, value: object) -> bytes:
        """Fully revalidate snapshot structure and return canonical UTF-8 JSON."""
        if not isinstance(value, TriageInputSnapshot):
            raise TypeError("triage_input@1 data must be a TriageInputSnapshot")
        try:
            data = value.model_dump(mode="json", round_trip=True, warnings="error")
            payload = json.dumps(
                data,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            checked = TriageInputSnapshot.model_validate_json(payload, strict=True)
            self._validate(checked)
        except (ValidationError, TypeError, ValueError):
            raise TypeError("triage_input@1 data failed validation") from None
        if len(payload) > self.max_bytes:
            raise TypeError("triage_input@1 data exceeds codec size bound")
        if len(payload) > checked.configuration.max_snapshot_bytes:
            raise TypeError("triage_input@1 data exceeds configured size bound")
        return payload

    def decode(self, payload: bytes) -> TriageInputSnapshot:
        """Decode canonical bytes and reject bypassed/noncanonical snapshots."""
        if len(payload) > self.max_bytes:
            raise ValueError("stored triage_input@1 data exceeds size bound")
        try:
            value = TriageInputSnapshot.model_validate_json(payload, strict=True)
            self._validate(value)
        except (ValidationError, TypeError, ValueError):
            raise ValueError("stored triage_input@1 data failed validation") from None
        if len(payload) > value.configuration.max_snapshot_bytes:
            raise ValueError("stored triage_input@1 data exceeds configured bound")
        if self.encode(value) != payload:
            raise ValueError("stored triage_input@1 data is not canonical")
        return value

    def _validate(self, value: TriageInputSnapshot) -> None:
        self._validate_top_level(value)
        units = {item.unit_id: item for item in value.units}
        if len(units) != len(value.units):
            raise ValueError("unit identities must be unique")
        failures = {item.unit_id: item for item in value.failures}
        if len(failures) != len(value.failures) or not set(failures) <= set(units):
            raise ValueError("coverage failures must name unique known units")

        selected_roles = {item.source_ref: item.role for item in value.selected_sources}
        if len(selected_roles) != len(value.selected_sources):
            raise ValueError("selected source bindings must be unique")
        held_refs = {item.source_ref for item in value.held}
        if len(held_refs) != len(value.held) or not held_refs <= set(selected_roles):
            raise ValueError("held source coverage is invalid")
        for held in value.held:
            if held.role is not selected_roles[held.source_ref]:
                raise ValueError("held source role is invalid")

        by_unit: dict[str, list[InputPart]] = {}
        seen_parts = set()
        seen_part_refs = set()
        for envelope in value.parts:
            validate_part_reference(envelope)
            part = envelope.part
            if envelope.state is not PartState.PENDING:
                raise ValueError("saved input parts must remain pending")
            if (
                part.part_id in seen_parts
                or envelope.reference in seen_part_refs
                or part.unit_id not in units
            ):
                raise ValueError("part identity or unit binding is invalid")
            seen_parts.add(part.part_id)
            seen_part_refs.add(envelope.reference)
            if part.unit_hash != units[part.unit_id].unit_hash:
                raise ValueError("part unit hash mismatch")
            if part.working_context_ref != value.working_context_ref:
                raise ValueError("part working context mismatch")
            if part.versions != value.versions:
                raise ValueError("part version binding mismatch")
            if envelope.reference.byte_count > value.configuration.split.max_part_bytes:
                raise ValueError("part exceeds configured byte limit")
            if len(encode_part(part)) > value.configuration.split.max_part_bytes:
                raise ValueError("part exceeds configured byte limit")
            by_unit.setdefault(part.unit_id, []).append(part)

        active_refs = []
        for unit_id, unit in units.items():
            if not set(unit.source_refs) <= set(selected_roles):
                raise ValueError("unit source membership is invalid")
            active_refs.extend(unit.source_refs)
            parts = sorted(by_unit.get(unit_id, []), key=lambda item: item.part_index)
            if len(parts) > value.configuration.split.max_parts_per_unit:
                raise ValueError("unit exceeds configured part limit")
            if tuple(item.part_index for item in parts) != tuple(range(len(parts))):
                raise ValueError("part indexes must be contiguous per unit")
            self._validate_unit(
                unit,
                parts,
                failures.get(unit_id),
                selected_roles,
            )

        if len(active_refs) != len(set(active_refs)):
            raise ValueError("selected source appears in multiple units")
        if set(active_refs) & held_refs:
            raise ValueError("held source cannot also be active")
        if set(active_refs) | held_refs != set(selected_roles):
            raise ValueError("selected source coverage is incomplete")

    def _validate_top_level(self, value: TriageInputSnapshot) -> None:
        expected_binding = selection_binding_digest(
            selection_hash=value.selection_hash,
            selected_sources=value.selected_sources,
            prepared_refs=value.prepared_refs,
            filter_refs=value.filter_refs,
            group_refs=value.group_refs,
            rule_ref=value.rule_ref,
            working_context_ref=value.working_context_ref,
            versions=value.versions,
        )
        if value.selection_binding_hash != expected_binding:
            raise ValueError("selection binding hash mismatch")
        if value.configuration_hash != digest(value.configuration):
            raise ValueError("configuration hash mismatch")
        if value.configuration.version != value.versions.configuration:
            raise ValueError("configuration version binding mismatch")
        refs_and_kinds = (
            (value.prepared_refs, *_REF_KINDS[0]),
            (value.filter_refs, *_REF_KINDS[1]),
            (value.group_refs, *_REF_KINDS[2]),
        )
        for refs, kind, version in refs_and_kinds:
            if len(refs) != len(set(refs)):
                raise ValueError("saved semantic references must be unique")
            if any(ref.kind != kind or ref.schema_version != version for ref in refs):
                raise ValueError("saved semantic reference kind is invalid")
        if (
            value.rule_ref.kind != "triage_rules"
            or value.rule_ref.schema_version != "1"
        ):
            raise ValueError("saved rule reference kind is invalid")
        data = value.model_dump(mode="json", round_trip=True, warnings="error")
        data["snapshot_hash"] = ""
        if value.snapshot_hash != digest(data):
            raise ValueError("snapshot hash mismatch")
        if value.complete != (not value.failures):
            raise ValueError("snapshot completion state mismatch")

    def _validate_unit(
        self,
        unit,
        parts: list[InputPart],
        failure,
        selected_roles,
    ) -> None:
        fragments = [fragment for part in parts for fragment in part.fragments]
        expected_list = unit.occurrences
        expected = {item.occurrence_id: item for item in expected_list}
        if len(expected) != len(expected_list):
            raise ValueError("unit occurrence identities must be unique")

        actual: dict[str, list[SemanticFragment]] = {}
        for fragment in fragments:
            manifest = expected.get(fragment.occurrence_id)
            if manifest is None:
                raise ValueError("unknown unit occurrence")
            self._validate_fragment_identity(fragment, manifest, unit, selected_roles)
            actual.setdefault(fragment.occurrence_id, []).append(fragment)

        complete_count = len(expected_list)
        partial_offset = None
        if failure is not None:
            self._validate_failure(failure, expected_list)
            complete_count = failure.first_occurrence
            partial_offset = failure.first_text_offset
            if unit.commitment != "retained-prefix":
                raise ValueError("incomplete unit commitment is invalid")
        elif unit.commitment != "complete-content":
            raise ValueError("complete unit commitment is invalid")

        allowed = {item.occurrence_id for item in expected_list[:complete_count]}
        if partial_offset is not None:
            if partial_offset <= 0:
                raise ValueError("partial text offset must retain content")
            allowed.add(expected_list[complete_count].occurrence_id)
        if set(actual) != allowed:
            raise ValueError("unit occurrence coverage mismatch")

        for manifest in expected_list[:complete_count]:
            self._validate_occurrence(actual[manifest.occurrence_id], manifest)
        if partial_offset is not None:
            manifest = expected_list[complete_count]
            if manifest.text_length is None:
                raise ValueError("partial offset requires text occurrence")
            cursor = self._validate_text_prefix(actual[manifest.occurrence_id])
            if cursor != partial_offset or cursor >= manifest.text_length:
                raise ValueError("partial text coverage is invalid")

        if failure is None:
            committed = self._reconstruct_fragments(expected_list, actual)
            basis_key = "fragments"
        else:
            committed = fragments
            basis_key = "retained_fragments"
        expected_hash = digest(
            {
                "unit_id": unit.unit_id,
                basis_key: [
                    item.model_dump(mode="json", round_trip=True) for item in committed
                ],
            }
        )
        if unit.unit_hash != expected_hash:
            raise ValueError("unit content commitment mismatch")

    @staticmethod
    def _reconstruct_fragments(
        manifests: tuple[OccurrenceManifest, ...],
        actual: dict[str, list[SemanticFragment]],
    ) -> tuple[SemanticFragment, ...]:
        reconstructed = []
        for manifest in manifests:
            found = actual[manifest.occurrence_id]
            if manifest.text_length is None:
                reconstructed.append(found[0])
                continue
            ordered = sorted(found, key=lambda item: item.text_start or 0)
            first = ordered[0]
            text = "".join(str(item.value) for item in ordered)
            reconstructed.append(
                first.model_copy(
                    update={
                        "value": text,
                        "text_start": 0,
                        "text_end": len(text),
                    }
                )
            )
        return tuple(reconstructed)

    @staticmethod
    def _validate_fragment_identity(
        fragment: SemanticFragment,
        manifest: OccurrenceManifest,
        unit,
        selected_roles,
    ) -> None:
        if (
            fragment.source_ref != manifest.source_ref
            or fragment.role is not manifest.role
            or fragment.namespace != manifest.namespace
            or fragment.path != manifest.path
            or fragment.kind is not manifest.kind
            or fragment.source_ref not in unit.source_refs
            or selected_roles.get(fragment.source_ref) is not fragment.role
            or fragment.namespace not in {"prepared", "filter", "rule", "group"}
        ):
            raise ValueError("fragment semantic identity mismatch")
        expected_id = occurrence_id_for(
            fragment.source_ref,
            fragment.namespace,
            fragment.path,
            fragment.kind,
        )
        if fragment.occurrence_id != expected_id:
            raise ValueError("fragment occurrence identity mismatch")

    @staticmethod
    def _validate_failure(failure, expected_list) -> None:
        if not 0 <= failure.first_occurrence < len(expected_list):
            raise ValueError("coverage failure index is invalid")
        if failure.remaining_occurrences != (
            len(expected_list) - failure.first_occurrence
        ):
            raise ValueError("coverage failure count is invalid")
        suffix = expected_list[failure.first_occurrence :]
        expected_digest = digest(
            {
                "first_text_offset": failure.first_text_offset,
                "occurrences": [
                    item.model_dump(mode="json", round_trip=True) for item in suffix
                ],
            }
        )
        if failure.remaining_digest != expected_digest:
            raise ValueError("coverage failure digest is invalid")

    @staticmethod
    def _validate_occurrence(
        found: list[SemanticFragment], manifest: OccurrenceManifest
    ) -> None:
        if manifest.text_length is None:
            if len(found) != 1:
                raise ValueError("non-text occurrence repeated")
            return
        cursor = TriageInputCodec._validate_text_prefix(found)
        if cursor != manifest.text_length:
            raise ValueError("text occurrence range is incomplete")

    @staticmethod
    def _validate_text_prefix(found: list[SemanticFragment]) -> int:
        ordered = sorted(
            found,
            key=lambda item: -1 if item.text_start is None else item.text_start,
        )
        cursor = 0
        for fragment in ordered:
            if (
                fragment.kind is not FragmentKind.TEXT
                or fragment.text_start != cursor
                or fragment.text_end is None
            ):
                raise ValueError("text occurrence coverage mismatch")
            cursor = fragment.text_end
        return cursor
