"""Held records and the completion receipt (terminal INCOMPLETE rules)."""

from __future__ import annotations

from typing import Any

import pytest

from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.a2_kedro.contracts.held import HeldReason, InputDisposition
from msgloom.a2_kedro.contracts.receipt import (
    CompletionReceipt,
    TerminalRoot,
    TransitionBatch,
)
from msgloom.contracts import Limitation, ResultRef, TerminalStatus, VersionRef
from tests.a2_kedro.helpers import (
    CODE,
    CONFIG,
    WORKSET_REF,
    accepted_ref,
    check,
    mutate,
    root_for,
    transition_for,
    workset,
)
from tests.a2_kedro.test_source import SHA, baseline_root, baseline_workset

COMPLETE, INCOMPLETE = TerminalStatus.COMPLETE, TerminalStatus.INCOMPLETE


def prepared_ref(char: str) -> ResultRef:
    return accepted_ref(char, "prepared", "2")


def held_ref(char: str) -> ResultRef:
    return accepted_ref(char, "a2_input_disposition", "1")


def terminal(ws: Any, index: int, ref: ResultRef, status: TerminalStatus = COMPLETE):
    disposition = "held" if ref.kind == "a2_input_disposition" else "prepared"
    return TerminalRoot(
        workset_selection_index=index,
        result=ref,
        disposition=disposition,
        status=status,
        limitations=() if status is COMPLETE else (Limitation("partial", "d"),),
        selection=ws.selections[index],
    )


def receipt(roots: tuple[TerminalRoot, ...] = (), **changes: Any) -> CompletionReceipt:
    values: dict[str, Any] = {
        "workset": WORKSET_REF,
        "status": COMPLETE,
        "policy_version": "policy-1",
        "roots": roots,
    }
    values.update(changes)
    return CompletionReceipt.model_validate(values)


def test_held_record_is_built_from_the_verified_root() -> None:
    ws = workset(1)
    held = InputDisposition.from_root(
        root_for(ws),
        HeldReason.PARSER_UNSUPPORTED,
        configuration_version=CONFIG,
        code_version=CODE,
    )
    check(held.repair_class == "operator_repair", "explicit repair class")
    check(held.entry == ws.selections[0].entry, "entry copied from root")
    check(held.selection_sha256 == SHA, "selection digest copied from root")


def test_baseline_held_has_source_and_no_entry() -> None:
    root = baseline_root(baseline_workset(), 0, selection_sha256=SHA)
    held = InputDisposition.from_root(
        root, HeldReason.INPUT_LIMIT, configuration_version=CONFIG, code_version=CODE
    )
    check(held.entry is None and held.baseline_source is not None, "baseline shape")


def test_held_negative_cases() -> None:
    ws = workset(1)
    held = InputDisposition.from_root(
        root_for(ws),
        HeldReason.PROOF_MISSING,
        configuration_version=CONFIG,
        code_version=CODE,
    )
    with pytest.raises(ValueError, match="collected_selection"):
        mutate(held, selected=ResultRef("x", "prepared", "2"))
    with pytest.raises(ValueError, match="cannot be baseline"):
        mutate(held, baseline_approval="a", baseline_source=VersionRef("m", "i", "v"))
    with pytest.raises(ValueError, match="approved source"):
        mutate(held, entry=None)
    with pytest.raises(ValueError):
        mutate(held, repair_class="auto_repair")
    with pytest.raises(ValueError):
        mutate(held, reason="free text reason")


def test_complete_receipt_covers_every_occurrence_in_order() -> None:
    ws = workset(2, transitions=1)
    batch = TransitionBatch(
        transitions=ws.transitions,
        result=accepted_ref("3", "prepared_transitions", "2"),
        status=COMPLETE,
    )
    good = receipt(
        (terminal(ws, 0, prepared_ref("1")), terminal(ws, 1, prepared_ref("2"))),
        transition_batch=batch,
    )
    good.validate_against(ws, WORKSET_REF)
    check(len(good.digest()) == 64, "digest present")
    check(
        good.digest()
        != receipt(good.roots, transition_batch=batch, policy_version="p2").digest(),
        "policy",
    )


def test_held_only_workset_is_terminal_incomplete_never_complete() -> None:
    ws = workset(0, held=2)
    receipt((), status=INCOMPLETE, intake_held_count=2).validate_against(
        ws, WORKSET_REF
    )
    with pytest.raises(ValueError, match="conflicts with coverage"):
        receipt((), status=COMPLETE, intake_held_count=2)
    with pytest.raises(ValueError, match="without any frozen work"):
        receipt((), status=INCOMPLETE)
    with pytest.raises(A2ContractError, match="intake-held count"):
        receipt((), status=INCOMPLETE, intake_held_count=1).validate_against(
            ws, WORKSET_REF
        )


def test_intake_held_forces_incomplete_even_with_complete_roots() -> None:
    ws = workset(1, held=1)
    root = terminal(ws, 0, prepared_ref("1"))
    with pytest.raises(ValueError, match="conflicts with coverage"):
        receipt((root,), status=COMPLETE, intake_held_count=1)
    receipt((root,), status=INCOMPLETE, intake_held_count=1).validate_against(
        ws, WORKSET_REF
    )


def test_a2_held_root_is_incomplete_only() -> None:
    ws = workset(1)
    with pytest.raises(ValueError, match="held cannot be COMPLETE"):
        terminal(ws, 0, held_ref("1"), COMPLETE)
    root = terminal(ws, 0, held_ref("1"), INCOMPLETE)
    with pytest.raises(ValueError, match="conflicts with coverage"):
        receipt((root,), status=COMPLETE)
    receipt((root,), status=INCOMPLETE).validate_against(ws, WORKSET_REF)


def test_incomplete_prepared_root_forces_incomplete_receipt() -> None:
    ws = workset(1)
    root = terminal(ws, 0, prepared_ref("1"), INCOMPLETE)
    with pytest.raises(ValueError, match="conflicts with coverage"):
        receipt((root,), status=COMPLETE)


def test_coverage_negative_cases() -> None:
    ws = workset(2)
    one = terminal(ws, 0, prepared_ref("1"))
    two = terminal(ws, 1, prepared_ref("2"))
    with pytest.raises(A2ContractError, match="differ from frozen"):
        receipt((one,)).validate_against(ws, WORKSET_REF)
    with pytest.raises(ValueError, match="frozen indexes in order"):
        receipt((two, one))
    with pytest.raises(ValueError, match="several occurrences"):
        receipt((one, terminal(ws, 1, prepared_ref("1"))))
    with pytest.raises(A2ContractError, match="different workset"):
        receipt((one, two)).validate_against(
            ws, ResultRef("other", "preparation_intake_workset", "1")
        )
    with pytest.raises(A2ContractError, match="missing or unexpected"):
        receipt((one, two)).validate_against(workset(2, transitions=1), WORKSET_REF)
    with pytest.raises(ValueError, match="foreign workset"):
        receipt((one, two), workset=ResultRef("w", "other", "1"))
    other_ws = workset(3)
    with pytest.raises(A2ContractError, match="differ from frozen"):
        receipt((one, two)).validate_against(other_ws, WORKSET_REF)


def test_transition_batch_negative_cases() -> None:
    ws = workset(1, transitions=2)
    ref = accepted_ref("3", "prepared_transitions", "2")
    altered = TransitionBatch(
        transitions=ws.transitions[:1], result=ref, status=COMPLETE
    )
    root = terminal(ws, 0, prepared_ref("1"))
    with pytest.raises(A2ContractError, match="differs from frozen"):
        receipt((root,), transition_batch=altered).validate_against(ws, WORKSET_REF)
    with pytest.raises(ValueError, match="distinct exact"):
        TransitionBatch(transitions=(), result=ref, status=COMPLETE)
    with pytest.raises(ValueError, match="distinct exact"):
        TransitionBatch(
            transitions=(transition_for(1), transition_for(1)),
            result=ref,
            status=COMPLETE,
        )
    with pytest.raises(ValueError, match="wrong kind"):
        TransitionBatch(
            transitions=ws.transitions, result=prepared_ref("3"), status=COMPLETE
        )


def test_terminal_root_result_must_be_accepted_v2_kind() -> None:
    ws = workset(1)
    for ref in (
        ResultRef("plain", "prepared", "2"),
        accepted_ref("1", "prepared", "1"),
        accepted_ref("1", "parsed_parts", "1"),
    ):
        with pytest.raises(ValueError):
            terminal(ws, 0, ref)
    with pytest.raises(ValueError):
        TerminalRoot(
            workset_selection_index=0,
            result=prepared_ref("1"),
            disposition="prepared",
            status=TerminalStatus.FAILED,
            selection=ws.selections[0],
        )


def test_baseline_receipt_uses_ordered_source_and_selection() -> None:
    bws = baseline_workset()
    root = TerminalRoot(
        workset_selection_index=0,
        result=prepared_ref("1"),
        disposition="prepared",
        status=COMPLETE,
        baseline_selection=bws.baseline_selections[0],
        baseline_source=bws.baseline_sources[0],
    )
    receipt((root,)).validate_against(bws, WORKSET_REF)
    with pytest.raises(ValueError, match="source and selection"):
        TerminalRoot(
            workset_selection_index=0,
            result=prepared_ref("1"),
            disposition="prepared",
            status=COMPLETE,
            baseline_selection=bws.baseline_selections[0],
        )
    with pytest.raises(A2ContractError, match="differ from frozen"):
        receipt((terminal(workset(1), 0, prepared_ref("1")),)).validate_against(
            bws, WORKSET_REF
        )
