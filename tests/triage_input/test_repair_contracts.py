"""Regression coverage for reviewed R1 triage-input boundary gaps."""

from __future__ import annotations

import pytest

from msgloom.contracts import SemanticDataRef, VersionRef
from msgloom.triage_input import (
    PartExecution,
    PartState,
    TriageInputBuildError,
    TriageInputCodec,
    build_triage_input,
    saved_part_payloads,
    validate_parent_part_states,
)
from msgloom.triage_input.build import build_units
from msgloom.triage_input.canonical import canonical_json, digest
from msgloom.triage_input.selection import validate_selection
from msgloom.triage_input.split import (
    _envelope,
    _part,
    encode_part,
    part_id_for,
    split_unit,
)

from .helpers import config, exclusion_filter, record, selection


def _rehash(snapshot):
    data = snapshot.model_dump(mode="json", round_trip=True)
    data["snapshot_hash"] = ""
    return snapshot.model_copy(update={"snapshot_hash": digest(data)})


def _replace_first_part(snapshot, part):
    envelope = _envelope(part)
    return _rehash(
        snapshot.model_copy(update={"parts": (envelope, *snapshot.parts[1:])})
    )


def test_exact_serialized_part_boundary_is_accepted_without_overrun() -> None:
    selected = validate_selection(selection((record("boundary"),)))
    unit = build_units(selected, config())[0]
    candidate = _part(
        unit,
        0,
        (unit.fragments[0],),
        selected.working_context_ref,
        selected.versions,
    )
    exact_bytes = len(encode_part(candidate))
    if exact_bytes < 512:
        pytest.fail("synthetic part must exercise the configured byte boundary")
    budget = config(max_part_bytes=exact_bytes, max_parts=1).split
    _, parts, failure = split_unit(
        unit,
        budget,
        selected.working_context_ref,
        selected.versions,
    )
    if not parts or parts[0].reference.byte_count != exact_bytes:
        pytest.fail("a part exactly at the serialized limit must be retained")
    if failure is None:
        pytest.fail("one-part fixture should retain explicit remaining coverage")
    if any(item.reference.byte_count > exact_bytes for item in parts):
        pytest.fail("exact-boundary split emitted an oversized part")


def test_codec_rejects_rehashed_fragment_from_unselected_source() -> None:
    snapshot = build_triage_input(selection((record("selected"),)), config())
    part = snapshot.parts[0].part
    fragment = part.fragments[0].model_copy(
        update={"source_ref": VersionRef("outlook_email", "other", "v1")}
    )
    bad = _replace_first_part(
        snapshot,
        part.model_copy(update={"fragments": (fragment, *part.fragments[1:])}),
    )
    with pytest.raises(TypeError):
        TriageInputCodec().encode(bad)


@pytest.mark.parametrize(
    ("field", "value"),
    (("namespace", "invented"), ("path", ("invented",))),
)
def test_codec_rejects_rehashed_fragment_identity_metadata(field, value) -> None:
    snapshot = build_triage_input(selection((record("selected"),)), config())
    part = snapshot.parts[0].part
    fragment = part.fragments[0].model_copy(update={field: value})
    changed = (fragment, *part.fragments[1:])
    part = part.model_copy(
        update={
            "part_id": part_id_for(
                part.unit_id,
                part.unit_hash,
                part.part_index,
                changed,
            ),
            "fragments": changed,
        }
    )
    with pytest.raises(TypeError):
        TriageInputCodec().encode(_replace_first_part(snapshot, part))


def test_codec_rejects_changed_content_with_recomputed_part_identity() -> None:
    snapshot = build_triage_input(selection((record("selected"),)), config())
    envelope = next(
        item
        for item in snapshot.parts
        if any(
            fragment.namespace == "prepared" and fragment.path == ("body",)
            for fragment in item.part.fragments
        )
    )
    part = envelope.part
    changed = []
    for fragment in part.fragments:
        if fragment.namespace == "prepared" and fragment.path == ("body",):
            changed.append(
                fragment.model_copy(
                    update={
                        "value": "X" * len(str(fragment.value)),
                    }
                )
            )
        else:
            changed.append(fragment)
    fragments = tuple(changed)
    changed_part = part.model_copy(
        update={
            "part_id": part_id_for(
                part.unit_id,
                part.unit_hash,
                part.part_index,
                fragments,
            ),
            "fragments": fragments,
        }
    )
    parts = tuple(
        _envelope(changed_part) if item is envelope else item for item in snapshot.parts
    )
    with pytest.raises(TypeError):
        TriageInputCodec().encode(_rehash(snapshot.model_copy(update={"parts": parts})))


def test_codec_enforces_rehashed_configured_part_limits_on_encode_and_decode() -> None:
    snapshot = build_triage_input(selection((record("selected"),)), config())
    split = snapshot.configuration.split.model_copy(
        update={"max_part_bytes": 512, "max_parts_per_unit": 1}
    )
    changed_config = snapshot.configuration.model_copy(update={"split": split})
    bad = _rehash(
        snapshot.model_copy(
            update={
                "configuration": changed_config,
                "configuration_hash": digest(changed_config),
            }
        )
    )
    codec = TriageInputCodec()
    with pytest.raises(TypeError):
        codec.encode(bad)
    with pytest.raises(ValueError):
        codec.decode(canonical_json(bad))


def test_codec_rejects_missing_or_duplicate_occurrence_coverage() -> None:
    snapshot = build_triage_input(selection((record("selected"),)), config())
    missing = _rehash(snapshot.model_copy(update={"parts": snapshot.parts[1:]}))
    with pytest.raises(TypeError):
        TriageInputCodec().encode(missing)

    part = snapshot.parts[0].part
    fragments = (*part.fragments, part.fragments[0])
    duplicate = part.model_copy(
        update={
            "part_id": part_id_for(
                part.unit_id,
                part.unit_hash,
                part.part_index,
                fragments,
            ),
            "fragments": fragments,
        }
    )
    with pytest.raises(TypeError):
        TriageInputCodec().encode(_replace_first_part(snapshot, duplicate))


def test_incomplete_unit_uses_verifiable_retained_prefix_commitment() -> None:
    snapshot = build_triage_input(
        selection((record("partial", body="🙂x" * 10_000),)),
        config(max_part_bytes=1200, max_parts=20),
    )
    if snapshot.complete:
        pytest.fail("synthetic input should exhaust its finite part budget")
    if snapshot.failures[0].first_text_offset is None:
        pytest.fail("synthetic input should retain an exact partial text prefix")
    unit = snapshot.units[0]
    if unit.commitment != "retained-prefix":
        pytest.fail("incomplete unit must not claim a complete-content hash")
    retained = [
        fragment
        for envelope in snapshot.parts
        for fragment in envelope.part.fragments
        if envelope.part.unit_id == unit.unit_id
    ]
    expected = digest(
        {
            "unit_id": unit.unit_id,
            "retained_fragments": [
                item.model_dump(mode="json", round_trip=True) for item in retained
            ],
        }
    )
    if unit.unit_hash != expected:
        pytest.fail("partial unit hash must commit only to retained material")
    TriageInputCodec().encode(snapshot)


@pytest.mark.parametrize("budget", (2048, 4096, 8192))
def test_exhaustion_before_first_large_body_chunk_is_storable(budget: int) -> None:
    snapshot = build_triage_input(
        selection((record("large", body="x" * 50_000),)),
        config(max_part_bytes=budget, max_parts=1),
    )
    if snapshot.complete or len(snapshot.failures) != 1:
        pytest.fail("finite exhaustion must be represented as incomplete coverage")
    TriageInputCodec().encode(snapshot)


def test_handoff_revalidates_constructed_state_and_blocks_incomplete_parent() -> None:
    snapshot = build_triage_input(
        selection((record("large", body="x" * 50_000),)),
        config(max_part_bytes=8192, max_parts=1),
    )
    states = tuple(
        PartExecution(reference=item.reference, state=PartState.COMPLETE)
        for item in snapshot.parts
    )
    if validate_parent_part_states(snapshot, states):
        pytest.fail("incomplete input cannot authorize parent completion")

    if states:
        invalid = PartExecution.model_construct(
            reference=states[0].reference,
            state="complete",
            failure_code="contradictory",
        )
        with pytest.raises(ValueError):
            validate_parent_part_states(snapshot, (invalid, *states[1:]))


def test_held_only_snapshot_never_authorizes_empty_parent_completion() -> None:
    source = record("held")
    snapshot = build_triage_input(
        selection((source,), filter_config=exclusion_filter("held")),
        config(),
    )
    if snapshot.parts:
        pytest.fail("held-only input should not emit ordinary AI parts")
    if validate_parent_part_states(snapshot, ()):
        pytest.fail("empty held-only input cannot authorize semantic completion")


def test_public_build_wraps_snapshot_limit_and_structural_limit_failures(
    monkeypatch,
) -> None:
    source = record("bounded")
    with pytest.raises(TriageInputBuildError) as size_error:
        build_triage_input(
            selection((source,)),
            config(max_snapshot_bytes=4096),
        )
    if "bounded" in str(size_error.value):
        pytest.fail("public size failure leaked source identity")

    monkeypatch.setattr("msgloom.triage_input.build.MAX_TOTAL_OCCURRENCES", 4)
    with pytest.raises(TriageInputBuildError) as structural_error:
        build_triage_input(selection((source,)), config())
    if "bounded" in str(structural_error.value):
        pytest.fail("public structural failure leaked source identity")


def test_handoff_revalidates_snapshot_before_emitting_payloads() -> None:
    snapshot = build_triage_input(selection((record("selected"),)), config())
    bad_ref = SemanticDataRef(
        data_id=snapshot.parts[0].reference.data_id,
        kind="wrong",
        schema_version="1",
        sha256=snapshot.parts[0].reference.sha256,
        byte_count=snapshot.parts[0].reference.byte_count,
    )
    bad_envelope = snapshot.parts[0].model_copy(update={"reference": bad_ref})
    bad = snapshot.model_copy(update={"parts": (bad_envelope, *snapshot.parts[1:])})
    with pytest.raises(ValueError):
        saved_part_payloads(bad)


def test_outer_rehash_cannot_replace_original_saved_selection_binding() -> None:
    snapshot = build_triage_input(selection((record("selected"),)), config())
    ref = snapshot.prepared_refs[0]
    changed_ref = SemanticDataRef(
        data_id="different-prepared-data",
        kind=ref.kind,
        schema_version=ref.schema_version,
        sha256=ref.sha256,
        byte_count=ref.byte_count,
    )
    bad = _rehash(snapshot.model_copy(update={"prepared_refs": (changed_ref,)}))
    with pytest.raises(TypeError):
        TriageInputCodec().encode(bad)
