"""C0-01: ``FrozenSourceSelection`` strict structure and forged inputs."""

from __future__ import annotations

from dataclasses import asdict, replace
from typing import Any

import pytest

from msgloom.a2_kedro.contracts.codec import A2ContractError, sha256_hex
from msgloom.a2_kedro.contracts.source import (
    FrozenRoot,
    FrozenSourceSelection,
    baseline_root,
    verify_baseline_selection,
    verify_exact_occurrence,
)
from msgloom.contracts import ResultRef, VersionRef
from msgloom.preparation_pipeline.intake import _identity
from msgloom.preparation_pipeline.intake_models import (
    IntakeAnchor,
    PreparationIntakeWorkset,
)
from msgloom.sources._snapshot import CollectedSelectionCodec
from tests.a2_kedro.a1_typed import collected
from tests.a2_kedro.helpers import (
    CODE,
    CONFIG,
    SCOPE,
    WORKSET_REF,
    check,
    entry,
    evidence_for,
    mutate,
    root_for,
    selection_for,
    workset,
)
from tests.a2_kedro.test_source import SHA, baseline_workset

BAD = (ValueError, A2ContractError)


def incremental() -> FrozenSourceSelection:
    ws = workset(2)
    roots = (root_for(ws, 0), root_for(ws, 1))
    return FrozenSourceSelection.build(WORKSET_REF, SCOPE, incremental_roots=roots)


def baseline() -> FrozenSourceSelection:
    root = baseline_root(baseline_workset(), 0, selection_sha256=SHA)
    return FrozenSourceSelection.build(WORKSET_REF, SCOPE, baseline_roots=(root,))


def dump(model: FrozenSourceSelection) -> dict[str, Any]:
    return model.model_dump(mode="json")


def reject(data: dict[str, Any]) -> None:
    with pytest.raises(BAD):
        FrozenSourceSelection.model_validate(data, strict=False)


def test_incremental_selection_round_trips_with_recomputed_digest() -> None:
    selection = incremental()
    check(selection.header.kind == "frozen_source_selection", "header kind")
    check(selection.baseline_roots is None, "no baseline set")
    check(len(selection.roots()) == 2, "two roots")
    check(selection.selection_set_sha256 == selection.content_sha256(), "digest")
    again = FrozenSourceSelection.decode(selection.encode())
    check(again == selection, "canonical round trip")


def test_baseline_selection_round_trips() -> None:
    selection = baseline()
    check(selection.incremental_roots is None, "no incremental set")
    check(selection.roots()[0].role == "baseline", "baseline root")
    check(FrozenSourceSelection.decode(selection.encode()) == selection, "trip")


def test_selection_matches_its_frozen_workset() -> None:
    ws = workset(2)
    incremental().verify_against(ws)
    baseline().verify_against(baseline_workset())


def test_verify_against_rejects_another_workset_shape() -> None:
    with pytest.raises(ValueError, match="mode differs"):
        incremental().verify_against(baseline_workset())
    with pytest.raises(ValueError, match="mode differs"):
        baseline().verify_against(workset(2))
    shifted = workset(2, selections=(selection_for(1), selection_for(2, 1)))
    with pytest.raises(ValueError, match="differs from the frozen"):
        incremental().verify_against(shifted)
    with pytest.raises(ValueError, match="differs from the frozen"):
        incremental().verify_against(workset(1))


def test_both_root_sets_rejected() -> None:
    data = dump(incremental())
    data["baseline_roots"] = dump(baseline())["baseline_roots"]
    reject(data)
    ws = workset(1)
    with pytest.raises(BAD):
        FrozenSourceSelection.build(
            WORKSET_REF,
            SCOPE,
            incremental_roots=(root_for(ws),),
            baseline_roots=baseline().baseline_roots,
        )


def test_neither_or_empty_root_set_rejected() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        FrozenSourceSelection.build(WORKSET_REF, SCOPE)
    with pytest.raises(ValueError, match="exactly one"):
        FrozenSourceSelection.build(WORKSET_REF, SCOPE, incremental_roots=())
    with pytest.raises(ValueError, match="exactly one"):
        FrozenSourceSelection.build(WORKSET_REF, SCOPE, baseline_roots=())


def test_forged_digest_rejected() -> None:
    data = dump(incremental())
    data["selection_set_sha256"] = "2" * 64
    reject(data)
    with pytest.raises(ValueError, match="digest"):
        mutate(incremental(), selection_set_sha256="2" * 64)


def test_tampered_content_with_old_digest_rejected() -> None:
    data = dump(incremental())
    data["incremental_roots"][0]["selection_sha256"] = "3" * 64
    reject(data)


def test_forged_role_with_stale_digest_rejected() -> None:
    for kind, role in (
        ("incremental_roots", "component"),
        ("incremental_roots", "baseline"),
        ("incremental_roots", "owner"),
        ("baseline_roots", "component"),
    ):
        data = dump(baseline() if kind == "baseline_roots" else incremental())
        data[kind][0]["role"] = role
        reject(data)


def test_forged_role_with_valid_digest_hits_the_role_rules() -> None:
    root = root_for(workset(1))
    for changes, message in (
        ({"role": "baseline"}, "baseline cannot carry release proof"),
        ({"role": "owner"}, "Input should be"),
        ({"role": "primary", "ordinal": 1}, "primary role needs"),
    ):
        with pytest.raises(BAD, match=message):
            forged = mutate(root, **changes)
            FrozenSourceSelection.build(WORKSET_REF, SCOPE, incremental_roots=(forged,))
    with pytest.raises(BAD, match="incremental root needs release"):
        mutate(baseline().roots()[0], role="component")


def test_primary_role_needs_ordinal_zero_and_is_unique_per_entry() -> None:
    ws = workset(1)
    root = root_for(ws)
    late = mutate(root, ordinal=1)
    with pytest.raises(ValueError, match="ordinal 0"):
        FrozenSourceSelection.build(WORKSET_REF, SCOPE, incremental_roots=(late,))
    second = mutate(root, workset_index=1, ordinal=0)
    with pytest.raises(ValueError, match="duplicate entry"):
        FrozenSourceSelection.build(
            WORKSET_REF, SCOPE, incremental_roots=(root, second)
        )


def test_forged_ordinal_proof_rejected() -> None:
    root = mutate(root_for(workset(1)), a1_ordinal_proof="4" * 64)
    with pytest.raises(ValueError, match="ordinal proof"):
        FrozenSourceSelection.build(WORKSET_REF, SCOPE, incremental_roots=(root,))


def test_duplicate_or_descending_index_rejected() -> None:
    ws = workset(2)
    first, second = root_for(ws, 0), root_for(ws, 1)
    for roots in ((first, first), (second, first)):
        with pytest.raises(ValueError, match="ascending"):
            FrozenSourceSelection.build(WORKSET_REF, SCOPE, incremental_roots=roots)
    other = baseline_root(baseline_workset(), 0, selection_sha256=SHA)
    with pytest.raises(ValueError, match="ascending"):
        FrozenSourceSelection.build(WORKSET_REF, SCOPE, baseline_roots=(other, other))


def test_duplicate_entry_ordinal_rejected() -> None:
    root = root_for(workset(1))
    clash = mutate(root, workset_index=1)
    with pytest.raises(ValueError, match="duplicate entry ordinal"):
        FrozenSourceSelection.build(WORKSET_REF, SCOPE, incremental_roots=(root, clash))


def test_mixed_baseline_approvals_rejected() -> None:
    root = baseline_root(baseline_workset(), 0, selection_sha256=SHA)
    other = mutate(root, workset_index=1, baseline_approval="approval-2")
    with pytest.raises(ValueError, match="one approval"):
        FrozenSourceSelection.build(WORKSET_REF, SCOPE, baseline_roots=(root, other))


def test_wrong_header_or_workset_schema_rejected() -> None:
    data = dump(incremental())
    data["header"] = {
        "kind": "zones",
        "version": "1",
        "profile": data["header"]["profile"],
    }
    reject(data)
    wrong = ResultRef("intake-workset:" + "9" * 64, "prepared", "2")
    with pytest.raises(ValueError, match="workset schema"):
        FrozenSourceSelection.build(
            wrong, SCOPE, incremental_roots=incremental().incremental_roots
        )


def test_extra_field_rejected() -> None:
    data = dump(incremental())
    data["note"] = "x"
    reject(data)
    nested = dump(incremental())
    nested["incremental_roots"][0]["extra"] = 1
    reject(nested)


def test_wrong_types_rejected() -> None:
    with pytest.raises(BAD):
        FrozenSourceSelection(
            workset=WORKSET_REF,
            scope=SCOPE,
            incremental_roots=[root_for(workset(1))],  # type: ignore[arg-type]
            selection_set_sha256="1" * 64,
        )
    text = incremental().model_dump_json()
    forged = text.replace('"workset_index":0', '"workset_index":"0"', 1)
    check(forged != text, "fixture holds an integer index")
    with pytest.raises(BAD):
        FrozenSourceSelection.model_validate_json(forged, strict=True)
    data = dump(incremental())
    data["selection_set_sha256"] = "ABC"
    reject(data)


def test_empty_scope_rejected() -> None:
    data = dump(incremental())
    data["scope"]["source_id"] = ""
    reject(data)
    data = dump(incremental())
    data["scope"]["catalog"]["catalog_identity"] = ""
    reject(data)
    data = dump(incremental())
    del data["scope"]
    reject(data)


def test_root_outside_scope_catalog_rejected() -> None:
    other = mutate(SCOPE, catalog={"catalog_identity": "cat-2", "schema_version": 1})
    roots = incremental().incremental_roots
    with pytest.raises(ValueError, match="outside the selection scope"):
        FrozenSourceSelection.build(WORKSET_REF, other, incremental_roots=roots)


def test_non_canonical_bytes_rejected() -> None:
    raw = incremental().encode()
    with pytest.raises(A2ContractError):
        FrozenSourceSelection.decode(raw + b" ")
    with pytest.raises(A2ContractError):
        FrozenSourceSelection.decode(raw.replace(b'"outlook_mail"', b'"nope"'))


def test_frozen_root_type_is_still_the_occurrence_unit() -> None:
    first = incremental().roots()[0]
    check(isinstance(first, FrozenRoot), "occurrence root")
    check(first.entry == entry(1), "entry bound")


def only_baseline() -> FrozenRoot:
    return baseline().roots()[0]


def test_baseline_root_inside_incremental_roots_rejected() -> None:
    first = root_for(workset(1))
    stray = mutate(only_baseline(), workset_index=1)
    with pytest.raises(ValueError, match="mixes a baseline root"):
        FrozenSourceSelection.build(
            WORKSET_REF, SCOPE, incremental_roots=(first, stray)
        )
    with pytest.raises(ValueError, match="mixes a baseline root"):
        FrozenSourceSelection.build(
            WORKSET_REF, SCOPE, incremental_roots=(only_baseline(),)
        )


def test_incremental_root_inside_baseline_roots_rejected() -> None:
    stray = mutate(root_for(workset(1)), workset_index=1)
    with pytest.raises(ValueError, match="mixes an incremental root"):
        FrozenSourceSelection.build(
            WORKSET_REF, SCOPE, baseline_roots=(only_baseline(), stray)
        )
    with pytest.raises(ValueError, match="mixes an incremental root"):
        FrozenSourceSelection.build(
            WORKSET_REF, SCOPE, baseline_roots=(root_for(workset(1)),)
        )


def test_baseline_source_or_selection_repeat_rejected() -> None:
    first = only_baseline()
    same_source = mutate(
        first, workset_index=1, selected=ResultRef("sel-2", "collected_selection", "1")
    )
    with pytest.raises(ValueError, match="source repeats"):
        FrozenSourceSelection.build(
            WORKSET_REF, SCOPE, baseline_roots=(first, same_source)
        )
    other = VersionRef("mail", "m2", "v1")
    same_selected = mutate(first, workset_index=1, baseline_source=other)
    with pytest.raises(ValueError, match="selection repeats"):
        FrozenSourceSelection.build(
            WORKSET_REF, SCOPE, baseline_roots=(first, same_selected)
        )


def test_same_selected_ref_under_two_entries_is_not_rejected() -> None:
    # The plan treats this as a legal defensive case (CR-03), not an error.
    ws = workset(2)
    first = root_for(ws, 0)
    twin = mutate(
        root_for(ws, 1),
        selected=first.selected,
        a1_ordinal_proof=(first.a1_ordinal_proof),
    )
    built = FrozenSourceSelection.build(
        WORKSET_REF, SCOPE, incremental_roots=(first, twin)
    )
    check(len(built.roots()) == 2, "both occurrences kept")


def forged(index: int = 0, **changes: Any) -> FrozenSourceSelection:
    """Build a valid-digest selection whose root ``index`` is forged."""
    ws = workset(2)
    roots = [root_for(ws, 0), root_for(ws, 1)]
    roots[index] = mutate(roots[index], **changes)
    return FrozenSourceSelection.build(
        WORKSET_REF, SCOPE, incremental_roots=tuple(roots)
    )


def proofs() -> list[Any]:
    return [evidence_for(1), evidence_for(2)]


def test_true_selection_passes_the_evidence_check() -> None:
    incremental().verify_against_evidence(workset(2), proofs())


def test_forged_role_with_valid_digest_fails_the_evidence_check() -> None:
    selection = forged(role="component")
    selection.verify_against(workset(2))  # digest and workset alone pass
    with pytest.raises(ValueError, match="root role differs"):
        selection.verify_against_evidence(workset(2), proofs())


def test_forged_ordinal_with_valid_digest_fails_the_evidence_check() -> None:
    selection = forged(role="component", ordinal=5)
    selection.verify_against(workset(2))
    with pytest.raises(ValueError, match="differs from A1 evidence"):
        selection.verify_against_evidence(workset(2), proofs())
    # Ordinal alone: a component-only release proves ordinal 0.
    ws = workset(1)
    lone = replace(evidence_for(1), has_primary=False)
    root = verify_exact_occurrence(
        ws, ws.selections[0], lone, saved_selection_sha256=SHA
    )
    selection = FrozenSourceSelection.build(
        WORKSET_REF, SCOPE, incremental_roots=(mutate(root, ordinal=1),)
    )
    with pytest.raises(ValueError, match="root ordinal differs"):
        selection.verify_against_evidence(ws, [lone])


def test_forged_saved_digest_with_valid_digest_fails_evidence_check() -> None:
    selection = forged(selection_sha256="2" * 64)
    with pytest.raises(ValueError, match="differs from re-read release"):
        selection.verify_against_evidence(workset(2), proofs())


def test_missing_extra_or_swapped_evidence_fails() -> None:
    selection = incremental()
    with pytest.raises(ValueError, match="evidence count"):
        selection.verify_against_evidence(workset(2), proofs()[:1])
    with pytest.raises(ValueError, match="evidence count"):
        selection.verify_against_evidence(workset(2), [*proofs(), evidence_for(3)])
    with pytest.raises(ValueError, match="evidence count"):
        selection.verify_against_evidence(workset(2), [])
    with pytest.raises(ValueError, match="does not match exact release"):
        selection.verify_against_evidence(workset(2), proofs()[::-1])
    with pytest.raises(ValueError, match="needs occurrence evidence"):
        selection.verify_against_evidence(workset(2), [SHA, SHA])  # type: ignore[list-item]


def test_verify_against_rejects_stale_digest_and_dropped_root() -> None:
    stale = incremental().model_construct(
        **{**dict(incremental()), "selection_set_sha256": "2" * 64}
    )
    with pytest.raises(ValueError, match="digest"):
        stale.verify_against(workset(2))
    one = FrozenSourceSelection.build(
        WORKSET_REF, SCOPE, incremental_roots=incremental().roots()[:1]
    )
    with pytest.raises(ValueError, match="root count"):
        one.verify_against(workset(2))


def real_baseline() -> tuple[PreparationIntakeWorkset, Any, FrozenSourceSelection]:
    value = collected("base-1")
    ref = ResultRef(
        _identity(
            "baseline-selection",
            [SCOPE.claim_key(), asdict(value.selection), CONFIG, CODE],
        ),
        "collected_selection",
        "1",
    )
    ws = PreparationIntakeWorkset(
        scope=SCOPE,
        previous=IntakeAnchor(),
        cutoff=IntakeAnchor(),
        entries=(),
        configuration_version=CONFIG,
        code_version=CODE,
        baseline_approval="approval-1",
        baseline_sources=(value.source,),
        baseline_selections=(ref,),
    )
    root = verify_baseline_selection(ws, 0, value)
    built = FrozenSourceSelection.build(WORKSET_REF, SCOPE, baseline_roots=(root,))
    return ws, value, built


def test_baseline_selection_is_proven_by_the_collected_value() -> None:
    ws, value, selection = real_baseline()
    selection.verify_against_evidence(ws, [value])
    check(
        selection.roots()[0].selection_sha256
        == sha256_hex(CollectedSelectionCodec().encode(value)),
        "digest from the A1 codec",
    )
    forged_root = mutate(selection.roots()[0], selection_sha256="2" * 64)
    bad = FrozenSourceSelection.build(WORKSET_REF, SCOPE, baseline_roots=(forged_root,))
    bad.verify_against(ws)
    with pytest.raises(ValueError, match="root selection_sha256 differs"):
        bad.verify_against_evidence(ws, [value])
    with pytest.raises(ValueError, match="needs a CollectedSelection"):
        selection.verify_against_evidence(ws, [evidence_for(1)])
