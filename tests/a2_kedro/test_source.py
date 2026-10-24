"""Frozen roots and the read-only A1 occurrence adapter."""

from __future__ import annotations

from dataclasses import replace

import pytest

from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.a2_kedro.contracts.source import (
    baseline_root,
    verify_exact_occurrence,
)
from msgloom.contracts import ResultRef, VersionRef
from msgloom.preparation_pipeline.intake_models import (
    IntakeAnchor,
    IntakeSelection,
    PreparationIntakeWorkset,
)
from tests.a2_kedro.helpers import (
    CODE,
    CONFIG,
    SCOPE,
    check,
    entry,
    evidence_for,
    hexd,
    mutate,
    selection_for,
    workset,
)

SHA = "1" * 64


def test_primary_root_from_exact_ordinal_proof() -> None:
    ws = workset(2)
    root = verify_exact_occurrence(
        ws, ws.selections[1], evidence_for(2), saved_selection_sha256=SHA
    )
    check(root.role == "primary" and root.ordinal == 0, "primary ordinal 0")
    check(root.workset_index == 1, "frozen workset index")
    check(root.entry == entry(2), "entry bound")
    check(
        root.a1_ordinal_proof == ws.selections[1].result.result_id.split(":")[1],
        "proof is the identity digest",
    )


def test_component_role_comes_from_the_proven_ordinal() -> None:
    component = selection_for(1, ordinal=1)
    ws = workset(1, selections=(component,))
    evidence = replace(evidence_for(1), occurrence_sha256=("2" * 64, SHA))
    root = verify_exact_occurrence(ws, component, evidence, saved_selection_sha256=SHA)
    check(root.role == "component" and root.ordinal == 1, "component ordinal")


def test_component_only_release_has_no_primary_role() -> None:
    ws = workset(1)
    evidence = replace(evidence_for(1), has_primary=False)
    root = verify_exact_occurrence(
        ws, ws.selections[0], evidence, saved_selection_sha256=SHA
    )
    check(root.role == "component", "no primary selection in release")


def test_forged_saved_hash_rejected() -> None:
    ws = workset(1)
    with pytest.raises(A2ContractError, match="differs from re-read"):
        verify_exact_occurrence(
            ws, ws.selections[0], evidence_for(1), saved_selection_sha256="2" * 64
        )


def test_forged_ordinal_identity_rejected() -> None:
    forged = IntakeSelection(
        entry=entry(1),
        result=ResultRef("intake-selection:" + hexd("e"), "collected_selection", "1"),
    )
    ws = workset(1, selections=(forged,))
    with pytest.raises(A2ContractError, match="one role"):
        verify_exact_occurrence(ws, forged, evidence_for(1), saved_selection_sha256=SHA)


def test_changed_member_list_breaks_the_proof() -> None:
    ws = workset(1)
    other = replace(evidence_for(1), members=(("e" * 64, "primary"),))
    with pytest.raises(A2ContractError, match="one role"):
        verify_exact_occurrence(ws, ws.selections[0], other, saved_selection_sha256=SHA)


def test_wrong_entry_or_foreign_selection_rejected() -> None:
    ws = workset(2)
    with pytest.raises(A2ContractError, match="does not match exact release"):
        verify_exact_occurrence(
            ws, ws.selections[0], evidence_for(2), saved_selection_sha256=SHA
        )
    with pytest.raises(A2ContractError, match="not part of the frozen"):
        verify_exact_occurrence(
            ws, selection_for(9), evidence_for(9), saved_selection_sha256=SHA
        )


def baseline_workset() -> PreparationIntakeWorkset:
    return PreparationIntakeWorkset(
        scope=SCOPE,
        previous=IntakeAnchor(),
        cutoff=IntakeAnchor(),
        entries=(),
        configuration_version=CONFIG,
        code_version=CODE,
        baseline_approval="approval-1",
        baseline_sources=(VersionRef("mail", "m1", "v1"),),
        baseline_selections=(ResultRef("sel-1", "collected_selection", "1"),),
    )


def test_baseline_cannot_impersonate_release_entry() -> None:
    ws = baseline_workset()
    with pytest.raises(A2ContractError, match="baseline cannot impersonate"):
        verify_exact_occurrence(
            ws, selection_for(1), evidence_for(1), saved_selection_sha256=SHA
        )


def test_baseline_root_has_source_and_no_release_proof() -> None:
    root = baseline_root(baseline_workset(), 0, selection_sha256=SHA)
    check(root.role == "baseline" and root.entry is None, "baseline shape")
    check(root.ordinal is None and root.a1_ordinal_proof is None, "no proof")
    with pytest.raises(A2ContractError):
        baseline_root(baseline_workset(), 3, selection_sha256=SHA)
    with pytest.raises(A2ContractError):
        baseline_root(workset(1), 0, selection_sha256=SHA)


def test_root_shape_negative_cases() -> None:
    good = baseline_root(baseline_workset(), 0, selection_sha256=SHA)
    with pytest.raises(ValueError, match="release proof"):
        mutate(good, ordinal=0)
    with pytest.raises(ValueError, match="approval and source"):
        mutate(good, baseline_approval=None)
    with pytest.raises(ValueError, match="collected_selection"):
        mutate(good, selected=ResultRef("x", "prepared", "2"))
    ws = workset(1)
    root = verify_exact_occurrence(
        ws, ws.selections[0], evidence_for(1), saved_selection_sha256=SHA
    )
    with pytest.raises(ValueError, match="release and ordinal"):
        mutate(root, ordinal=None)
    with pytest.raises(ValueError, match="carry baseline"):
        mutate(root, baseline_approval="a", baseline_source=VersionRef("m", "i", "v"))
    with pytest.raises(ValueError):
        mutate(root, workset_index=2000)
