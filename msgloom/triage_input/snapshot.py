"""Public deterministic construction of a bounded triage-input snapshot."""

from __future__ import annotations

from pydantic import ValidationError

from .build import build_units
from .canonical import canonical_json, digest
from .integrity import selection_binding_digest
from .models import TriageInputConfig, TriageInputSnapshot, TriageSelection
from .selection import (
    TriageInputValidationError,
    held_sources,
    selection_digest,
    validate_selection,
)
from .split import TriageInputSplitError, split_unit, validate_complete_coverage

MAX_SELECTION_BYTES = 64 * 1024 * 1024


class TriageInputBuildError(ValueError):
    """Expose a fixed safe snapshot-build classification."""


def _validated_config(config: TriageInputConfig) -> TriageInputConfig:
    try:
        return TriageInputConfig.model_validate_json(
            canonical_json(config), strict=True
        )
    except (ValidationError, TypeError, ValueError):
        raise TriageInputBuildError(
            "triage input configuration failed validation"
        ) from None


def _snapshot_hash(snapshot: TriageInputSnapshot) -> str:
    data = snapshot.model_dump(mode="json", round_trip=True, warnings="error")
    data["snapshot_hash"] = ""
    return digest(data)


def _selection_size(selection: TriageSelection) -> None:
    try:
        size = len(canonical_json(selection))
    except (TypeError, ValueError):
        raise TriageInputBuildError(
            "triage input selection failed validation"
        ) from None
    if size > MAX_SELECTION_BYTES:
        raise TriageInputBuildError("triage input selection exceeds size bound")


def build_triage_input(
    selection: TriageSelection, config: TriageInputConfig
) -> TriageInputSnapshot:
    """Validate, structure, split, and bind one replayable AI-input snapshot."""
    config = _validated_config(config)
    _selection_size(selection)
    try:
        selection = validate_selection(selection)
    except TriageInputValidationError:
        raise TriageInputBuildError(
            "triage input selection failed validation"
        ) from None
    if config.version != selection.versions.configuration:
        raise TriageInputBuildError("triage input configuration version mismatch")

    try:
        built_units = build_units(selection, config)
        units = []
        parts = []
        failures = []
        part_bytes = 0
        for unit in built_units:
            final_unit, unit_parts, failure = split_unit(
                unit,
                config.split,
                selection.working_context_ref,
                selection.versions,
            )
            units.append(final_unit)
            parts.extend(unit_parts)
            part_bytes += sum(item.reference.byte_count for item in unit_parts)
            if part_bytes > config.max_snapshot_bytes:
                raise TriageInputBuildError(
                    "triage input snapshot exceeds configured bound"
                )
            if failure is None:
                validate_complete_coverage(final_unit, unit_parts)
            else:
                failures.append(failure)

        prepared_refs = tuple(item.data_ref for item in selection.prepared)
        filter_refs = tuple(item.data_ref for item in selection.filters)
        group_refs = tuple(item.data_ref for item in selection.groups)
        selection_hash = selection_digest(selection)
        binding_hash = selection_binding_digest(
            selection_hash=selection_hash,
            selected_sources=selection.roles,
            prepared_refs=prepared_refs,
            filter_refs=filter_refs,
            group_refs=group_refs,
            rule_ref=selection.rules.data_ref,
            working_context_ref=selection.working_context_ref,
            versions=selection.versions,
        )
        snapshot = TriageInputSnapshot(
            selection_hash=selection_hash,
            selection_binding_hash=binding_hash,
            configuration_hash=digest(config),
            snapshot_hash="",
            configuration=config,
            working_context_ref=selection.working_context_ref,
            versions=selection.versions,
            prepared_refs=prepared_refs,
            filter_refs=filter_refs,
            group_refs=group_refs,
            rule_ref=selection.rules.data_ref,
            held=held_sources(selection),
            units=tuple(item.manifest for item in units),
            selected_sources=selection.roles,
            parts=tuple(parts),
            complete=not failures,
            failures=tuple(failures),
        )
        snapshot = snapshot.model_copy(
            update={"snapshot_hash": _snapshot_hash(snapshot)}
        )
        from .codec import TriageInputCodec

        payload = TriageInputCodec().encode(snapshot)
    except TriageInputBuildError:
        raise
    except (TriageInputSplitError, ValidationError, TypeError, ValueError):
        raise TriageInputBuildError("triage input build failed validation") from None

    if len(payload) > config.max_snapshot_bytes:
        raise TriageInputBuildError("triage input snapshot exceeds configured bound")
    return snapshot
