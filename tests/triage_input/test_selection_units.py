"""Selection, grouping authority, held disposition, and replay tests."""

from __future__ import annotations

import pytest

from msgloom.contracts import VersionRef
from msgloom.persistence.semantic import SemanticDataRegistry
from msgloom.preparation import NativeRelationship, PreparedSourceType
from msgloom.triage_input import (
    FragmentKind,
    HeldReason,
    TriageInputBuildError,
    TriageInputCodec,
    build_triage_input,
)

from .helpers import config, exclusion_filter, record, selection


def test_confirmed_native_group_shares_one_unit() -> None:
    parent = record("parent")
    child = record(
        "child",
        relationships=(NativeRelationship(kind="in_reply_to", target=parent.source),),
    )
    snapshot = build_triage_input(selection((child, parent)), config())
    if len(snapshot.units) != 1:
        pytest.fail("confirmed native relationship must authorize one unit")
    if set(snapshot.units[0].source_refs) != {parent.source, child.source}:
        pytest.fail("confirmed unit lost exact source membership")


def test_same_subject_without_relationship_stays_separate() -> None:
    first = record("first")
    second = record("second")
    snapshot = build_triage_input(selection((first, second)), config())
    if len(snapshot.units) != 2:
        pytest.fail("shared subject must not merge independent records")
    if any(len(unit.source_refs) != 1 for unit in snapshot.units):
        pytest.fail("uncertain/none grouping must remain single-source")


def test_contextual_sources_remain_separate() -> None:
    todo = record("todo", source_type=PreparedSourceType.TODO)
    drive = record("drive", source_type=PreparedSourceType.ONEDRIVE)
    snapshot = build_triage_input(selection((todo, drive)), config())
    if len(snapshot.units) != 2:
        pytest.fail("contextual sources must not form communication units")


def test_filter_exclusion_is_held_and_not_sent_as_unit() -> None:
    source = record("held")
    snapshot = build_triage_input(
        selection((source,), filter_config=exclusion_filter("held")),
        config(),
    )
    if snapshot.units:
        pytest.fail("excluded source must not be ordinary semantic input")
    if len(snapshot.held) != 1:
        pytest.fail("excluded source must remain explicitly held")
    if HeldReason.FILTER_EXCLUDED not in snapshot.held[0].reasons:
        pytest.fail("held source must retain filter exclusion reason")


def test_selection_permutations_replay_identically() -> None:
    first = record("a")
    second = record("b")
    one = build_triage_input(selection((first, second)), config())
    two = build_triage_input(selection((second, first)), config())
    if one != two:
        pytest.fail("input permutation changed canonical triage snapshot")


def test_exact_dedup_is_opt_in_and_retains_occurrence_mapping() -> None:
    parent = record("a", body="identical synthetic body")
    child = record(
        "b",
        body="identical synthetic body",
        relationships=(NativeRelationship(kind="in_reply_to", target=parent.source),),
    )
    plain = build_triage_input(selection((parent, child)), config(dedup=False))
    deduped = build_triage_input(selection((parent, child)), config(dedup=True))
    plain_repetitions = [
        fragment
        for envelope in plain.parts
        for fragment in envelope.part.fragments
        if fragment.kind is FragmentKind.REPETITION
    ]
    dedup_repetitions = [
        fragment
        for envelope in deduped.parts
        for fragment in envelope.part.fragments
        if fragment.kind is FragmentKind.REPETITION
    ]
    if plain_repetitions:
        pytest.fail("repetition removal must be disabled by default")
    if not dedup_repetitions:
        pytest.fail("explicit exact repetition removal must retain mappings")
    if any(item.repetition_of is None for item in dedup_repetitions):
        pytest.fail("removed occurrences must identify the retained occurrence")


def test_codec_is_registry_compatible_without_global_registration() -> None:
    snapshot = build_triage_input(selection((record("one"),)), config())
    registry = SemanticDataRegistry((TriageInputCodec(),))
    encoded = registry.encode("input-1", "triage_input", "1", snapshot)
    decoded = registry.decode(encoded.reference, encoded.payload)
    if decoded != snapshot:
        pytest.fail("registry round trip changed triage input")


def test_mismatched_saved_prepared_reference_fails_opaque() -> None:
    selected = selection((record("one"),))
    bad_ref = selected.prepared[0].data_ref
    bad_ref = type(bad_ref)(
        data_id=bad_ref.data_id,
        kind=bad_ref.kind,
        schema_version=bad_ref.schema_version,
        sha256="00" * 32,
        byte_count=bad_ref.byte_count,
    )
    prepared = selected.prepared[0].model_copy(update={"data_ref": bad_ref})
    selected = selected.model_copy(update={"prepared": (prepared,)})
    with pytest.raises(TriageInputBuildError) as error:
        build_triage_input(selected, config())
    if "one" in str(error.value):
        pytest.fail("public validation error leaked source identity")


def test_trusted_configuration_version_must_match() -> None:
    selected = selection((record("one"),))
    bad = config().model_copy(
        update={"version": VersionRef("triage_input_config", "other", "v1")}
    )
    with pytest.raises(TriageInputBuildError):
        build_triage_input(selected, bad)


def test_earlier_and_new_roles_are_preserved_inside_confirmed_unit() -> None:
    parent = record("earlier")
    child = record(
        "new",
        relationships=(NativeRelationship(kind="in_reply_to", target=parent.source),),
    )
    from msgloom.triage_input import SourceRole

    snapshot = build_triage_input(
        selection(
            (parent, child),
            roles=(SourceRole.EARLIER_CONTEXT, SourceRole.NEW_SOURCE),
        ),
        config(),
    )
    roles = {
        fragment.source_ref: fragment.role
        for envelope in snapshot.parts
        for fragment in envelope.part.fragments
    }
    if roles[parent.source] is not SourceRole.EARLIER_CONTEXT:
        pytest.fail("earlier context role was not retained")
    if roles[child.source] is not SourceRole.NEW_SOURCE:
        pytest.fail("new-source role was not retained")


def test_different_source_scopes_never_share_confirmed_unit() -> None:
    parent = record("scope-a")
    child = record(
        "scope-b",
        relationships=(NativeRelationship(kind="in_reply_to", target=parent.source),),
    )
    different_scope = NativeRelationship(
        kind="source_scope",
        target=VersionRef("source_scope", "different", "v1"),
    )
    child = child.model_copy(
        update={
            "relationships": (
                different_scope,
                NativeRelationship(kind="in_reply_to", target=parent.source),
            )
        }
    )
    snapshot = build_triage_input(selection((parent, child)), config())
    if any(len(unit.source_refs) > 1 for unit in snapshot.units):
        pytest.fail("different source scopes must not gain combination authority")
