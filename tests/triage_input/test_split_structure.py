"""Structured splitting, Unicode, tables, and coverage tests."""

from __future__ import annotations

import pytest

from msgloom.triage_input import (
    FragmentKind,
    PartExecution,
    PartState,
    TriageInputCodec,
    build_triage_input,
    initial_part_states,
    saved_part_payloads,
    validate_parent_part_states,
)

from .helpers import config, record, selection, with_large_cell, with_link_and_mime


def _text_for_path(snapshot, source_ref, suffix: tuple[object, ...]) -> str:
    fragments = [
        fragment
        for envelope in snapshot.parts
        for fragment in envelope.part.fragments
        if fragment.source_ref == source_ref
        and fragment.kind is FragmentKind.TEXT
        and tuple(fragment.path[-len(suffix) :]) == suffix
    ]
    fragments.sort(key=lambda item: item.text_start or 0)
    return "".join(str(item.value) for item in fragments)


def test_long_unicode_body_splits_without_loss_or_utf8_overrun() -> None:
    body = "付款🙂Δ" * 2400
    source = record("unicode", body=body)
    snapshot = build_triage_input(
        selection((source,)),
        config(max_part_bytes=1800, max_parts=512),
    )
    if not snapshot.complete:
        pytest.fail("bounded Unicode body should split completely")
    if _text_for_path(snapshot, source.source, ("body",)) != body:
        pytest.fail("Unicode body changed across chunk boundaries")
    if any(item.reference.byte_count > 1800 for item in snapshot.parts):
        pytest.fail("serialized part exceeded explicit byte budget")


def test_large_table_cell_formula_cached_value_and_coordinates_survive() -> None:
    cell_text = "synthetic-cell🙂" * 1200
    source = with_large_cell(record("table"), cell_text)
    snapshot = build_triage_input(
        selection((source,)),
        config(max_part_bytes=1900, max_parts=512),
    )
    if (
        _text_for_path(snapshot, source.source, ("cells", 0, "text")).count(cell_text)
        != 1
    ):
        pytest.fail("large parsed cell text was lost or duplicated")
    paths = {
        tuple(fragment.path)
        for envelope in snapshot.parts
        for fragment in envelope.part.fragments
        if fragment.source_ref == source.source
    }
    required = {"row_index", "column_index", "formula", "cached_value", "coordinate"}
    tails = {path[-1] for path in paths if path}
    if not required <= tails:
        pytest.fail("table coordinates/formula/cached semantics were flattened")


def test_parser_limitations_and_source_mappings_remain_structured() -> None:
    source = record("mapped")
    snapshot = build_triage_input(selection((source,)), config())
    paths = [
        tuple(fragment.path)
        for envelope in snapshot.parts
        for fragment in envelope.part.fragments
        if fragment.source_ref == source.source
    ]
    if not any("source_mappings" in path for path in paths):
        pytest.fail("source mappings were dropped")
    if not any("limitations" in path for path in paths):
        pytest.fail("missing/partial limitations were dropped")
    if not any("location" in path for path in paths):
        pytest.fail("parser/source locations were dropped")


def test_part_count_exhaustion_is_explicit_incomplete_coverage() -> None:
    source = record("too-large", body="x🙂" * 5000)
    snapshot = build_triage_input(
        selection((source,)),
        config(max_part_bytes=900, max_parts=1),
    )
    if snapshot.complete or len(snapshot.failures) != 1:
        pytest.fail("part budget exhaustion must be explicit incomplete coverage")
    failure = snapshot.failures[0]
    if failure.remaining_occurrences < 1 or not failure.remaining_digest:
        pytest.fail("remaining coverage must be bounded and identified")


def test_saved_part_payloads_are_exact_and_initially_pending() -> None:
    snapshot = build_triage_input(selection((record("one"),)), config())
    payloads = saved_part_payloads(snapshot)
    states = initial_part_states(snapshot)
    if len(payloads) != len(snapshot.parts) or len(states) != len(snapshot.parts):
        pytest.fail("handoff must retain every exact part")
    if any(item.state is not PartState.PENDING for item in states):
        pytest.fail("new input parts must start pending")
    if validate_parent_part_states(snapshot, states):
        pytest.fail("pending parts cannot authorize semantic combination")


def test_parent_requires_exact_full_part_state_coverage() -> None:
    snapshot = build_triage_input(selection((record("one"),)), config())
    states = tuple(
        PartExecution(reference=item.reference, state=PartState.COMPLETE)
        for item in snapshot.parts
    )
    if not validate_parent_part_states(snapshot, states):
        pytest.fail("all exact completed parts should satisfy parent coverage")
    with pytest.raises(ValueError):
        validate_parent_part_states(snapshot, states[:-1])


def test_failed_part_is_retained_and_blocks_parent_completion() -> None:
    snapshot = build_triage_input(selection((record("one"),)), config())
    states = list(initial_part_states(snapshot))
    states[0] = PartExecution(
        reference=states[0].reference,
        state=PartState.FAILED,
        failure_code="synthetic-failure",
    )
    if validate_parent_part_states(snapshot, tuple(states)):
        pytest.fail("failed part cannot authorize combined semantic output")


def test_codec_rejects_nested_model_copy_bypass() -> None:
    snapshot = build_triage_input(selection((record("one"),)), config())
    envelope = snapshot.parts[0]
    fragment = envelope.part.fragments[0].model_copy(
        update={"kind": FragmentKind.TEXT, "value": "invented"}
    )
    part = envelope.part.model_copy(update={"fragments": (fragment,)})
    bad_envelope = envelope.model_copy(update={"part": part})
    bad = snapshot.model_copy(update={"parts": (bad_envelope, *snapshot.parts[1:])})
    with pytest.raises(TypeError):
        TriageInputCodec().encode(bad)


def test_missing_body_and_attachment_content_remain_explicit_data() -> None:
    from msgloom.contracts import Limitation

    source = record("missing")
    attachment = source.attachments[0].model_copy(
        update={
            "saved_bytes": None,
            "parsed_content_ref": None,
            "limitations": (
                Limitation("missing-content", "Synthetic attachment unavailable."),
            ),
        }
    )
    source = source.model_copy(
        update={
            "body": None,
            "attachments": (attachment,),
            "parsed_contents": (),
            "source_mappings": (),
        }
    )
    snapshot = build_triage_input(selection((source,)), config())
    body = [
        fragment
        for envelope in snapshot.parts
        for fragment in envelope.part.fragments
        if fragment.source_ref == source.source
        and fragment.namespace == "prepared"
        and tuple(fragment.path) == ("body",)
    ]
    if len(body) != 1 or body[0].value is not None:
        pytest.fail("missing body must remain an explicit null source datum")
    paths = {
        tuple(fragment.path)
        for envelope in snapshot.parts
        for fragment in envelope.part.fragments
    }
    if not any("limitations" in path for path in paths):
        pytest.fail("missing attachment limitation was dropped")


def test_links_and_mime_facts_remain_data_with_locations() -> None:
    source = with_link_and_mime(record("links"))
    snapshot = build_triage_input(selection((source,)), config())
    fragments = [
        fragment
        for envelope in snapshot.parts
        for fragment in envelope.part.fragments
        if fragment.source_ref == source.source
    ]
    targets = [
        fragment.value
        for fragment in fragments
        if fragment.path and fragment.path[-1] == "target"
    ]
    content_types = [
        fragment.value
        for fragment in fragments
        if fragment.path and fragment.path[-1] == "content_type"
    ]
    if "https://example.invalid/synthetic" not in targets:
        pytest.fail("parsed link target was dropped")
    if "text/plain" not in content_types:
        pytest.fail("MIME relationship facts were dropped")
    if not any("location" in fragment.path for fragment in fragments):
        pytest.fail("link/MIME locations were dropped")
