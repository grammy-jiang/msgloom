"""C0-09 a2_input_disposition@1: explicit repair class, no forced body."""

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
from msgloom.a2_kedro.contracts.source import FrozenRoot
from msgloom.contracts import Limitation, ResultRef, TerminalStatus, VersionRef
from tests.a2_kedro.helpers import (
    CODE,
    CONFIG,
    WORKSET_REF,
    accepted_ref,
    check,
    hexd,
    mutate,
    root_for,
    workset,
)
from tests.a2_kedro.test_source import SHA, baseline_root, baseline_workset

COMPLETE, INCOMPLETE = TerminalStatus.COMPLETE, TerminalStatus.INCOMPLETE
SENTINEL = "alice.private@example.invalid"


def held_from(root: FrozenRoot, reason: HeldReason = HeldReason.PROOF_MISSING):
    return InputDisposition.from_root(
        root, reason, configuration_version=CONFIG, code_version=CODE
    )


def held_ref(char: str) -> ResultRef:
    return accepted_ref(char, "a2_input_disposition", "1")


def receipt(roots: tuple[TerminalRoot, ...] = (), **changes: Any) -> CompletionReceipt:
    values: dict[str, Any] = {
        "workset": WORKSET_REF,
        "status": INCOMPLETE,
        "policy_version": "policy-1",
        "roots": roots,
    }
    values.update(changes)
    return CompletionReceipt.model_validate(values)


def test_every_reason_carries_the_explicit_repair_class() -> None:
    root = root_for(workset(1))
    for reason in HeldReason:
        held = held_from(root, reason)
        check(held.repair_class == "operator_repair", "repair class")
        check(held.model_dump(mode="json")["repair_class"] == "operator_repair", "wire")
        held.validate_against(root)


def test_repair_class_is_required_on_the_wire() -> None:
    data = held_from(root_for(workset(1))).model_dump(mode="json")
    del data["repair_class"]
    with pytest.raises(ValueError, match="repair_class"):
        InputDisposition.model_validate(data)


@pytest.mark.parametrize("value", ["auto_repair", "retry", "", "OPERATOR_REPAIR", None])
def test_other_repair_classes_are_rejected(value: Any) -> None:
    held = held_from(root_for(workset(1)))
    with pytest.raises(ValueError):
        mutate(held, repair_class=value)


@pytest.mark.parametrize("reason", ["", "free text", "PROOF_MISSING", "body_missing"])
def test_reasons_are_a_closed_content_free_enum(reason: str) -> None:
    held = held_from(root_for(workset(1)))
    with pytest.raises(ValueError):
        mutate(held, reason=reason)
    check(
        {r.value for r in HeldReason}
        == {
            "role_unverifiable",
            "source_evidence_unavailable",
            "parser_unsupported",
            "input_limit",
            "proof_missing",
        },
        "reason vocabulary changed",
    )


def test_held_only_workset_needs_no_body_and_no_prepared_result() -> None:
    ws = workset(0, held=2)
    done = receipt((), intake_held_count=2)
    done.validate_against(ws, WORKSET_REF)
    check(done.roots == () and done.transition_batch is None, "no body forced")
    check(done.status is INCOMPLETE, "held-only is INCOMPLETE")


def test_a2_held_roots_alone_are_a_legal_terminal() -> None:
    ws = workset(2)
    roots = tuple(
        TerminalRoot(
            workset_selection_index=i,
            result=held_ref(str(i + 1)),
            disposition="held",
            status=INCOMPLETE,
            limitations=(Limitation("held", "operator_repair"),),
            selection=ws.selections[i],
        )
        for i in range(2)
    )
    receipt(roots).validate_against(ws, WORKSET_REF)
    held = held_from(root_for(ws, 1), HeldReason.PARSER_UNSUPPORTED)
    held.validate_against(root_for(ws, 1))
    check(held.workset_index == 1 and held.entry == ws.selections[1].entry, "copy")


def test_context_only_workset_needs_a_batch_but_no_root_or_held_record() -> None:
    ws = workset(0, transitions=2)
    batch = TransitionBatch(
        transitions=ws.transitions,
        result=accepted_ref("3", "prepared_transitions", "2"),
        status=COMPLETE,
    )
    done = receipt((), status=COMPLETE, transition_batch=batch)
    done.validate_against(ws, WORKSET_REF)
    check(done.roots == (), "no body root")


def test_approved_baseline_held_has_source_and_no_release_entry() -> None:
    bws = baseline_workset()
    root = baseline_root(bws, 0, selection_sha256=SHA)
    held = held_from(root, HeldReason.SOURCE_EVIDENCE_UNAVAILABLE)
    held.validate_against(root)
    check(held.entry is None, "baseline never fabricates a release entry")
    check(held.baseline_source == bws.baseline_sources[0], "approved source")
    check(held.baseline_approval == "approval-1", "approval copied")
    terminal = TerminalRoot(
        workset_selection_index=0,
        result=held_ref("1"),
        disposition="held",
        status=INCOMPLETE,
        limitations=(Limitation("held", "operator_repair"),),
        baseline_selection=bws.baseline_selections[0],
        baseline_source=bws.baseline_sources[0],
    )
    receipt((terminal,)).validate_against(bws, WORKSET_REF)


def test_forged_root_is_detected_against_the_verified_root() -> None:
    ws = workset(2)
    real, other = root_for(ws, 0), root_for(ws, 1)
    held = held_from(real)
    with pytest.raises(A2ContractError, match="differs from its frozen root"):
        held.validate_against(other)
    with pytest.raises(A2ContractError, match="differs from its frozen root"):
        held.validate_against(mutate(real, selection_sha256=hexd("9")))
    with pytest.raises(A2ContractError, match="differs from its frozen root"):
        mutate(held, selection_sha256=hexd("9")).validate_against(real)
    with pytest.raises(A2ContractError, match="differs from its frozen root"):
        mutate(held, workset_index=1).validate_against(real)
    bws = baseline_workset()
    with pytest.raises(A2ContractError, match="differs from its frozen root"):
        held.validate_against(baseline_root(bws, 0, selection_sha256=SHA))


def test_forged_root_shapes_cannot_be_built() -> None:
    real = root_for(workset(1))
    forged: list[dict[str, Any]] = [
        {"a1_ordinal_proof": None},
        {"entry": None},
        {"ordinal": None},
        {"role": "baseline"},
        {"role": "boss"},
        {"baseline_approval": "a", "baseline_source": VersionRef("m", "i", "v")},
        {"selected": ResultRef("x", "prepared", "2")},
        {"selection_sha256": "not-a-digest"},
        {"workset_index": 5000},
    ]
    for changes in forged:
        with pytest.raises(ValueError):
            mutate(real, **changes)


def test_source_exclusivity_is_enforced_on_the_held_record() -> None:
    inc = held_from(root_for(workset(1)))
    base = held_from(baseline_root(baseline_workset(), 0, selection_sha256=SHA))
    with pytest.raises(ValueError, match="cannot be baseline"):
        mutate(inc, baseline_approval="a")
    with pytest.raises(ValueError, match="approved source"):
        mutate(base, baseline_approval=None)
    with pytest.raises(ValueError, match="approved source"):
        mutate(base, baseline_source=None)
    with pytest.raises(ValueError, match="cannot be baseline"):
        mutate(base, entry=inc.entry)
    with pytest.raises(ValueError, match="approved source"):
        mutate(inc, entry=None)
    with pytest.raises(ValueError, match="collected_selection"):
        mutate(inc, selected=ResultRef("x", "prepared", "2"))


@pytest.mark.parametrize(
    "field", ["body", "text", "content", "prepared_result", "summary", "parts"]
)
def test_fabricated_content_fields_are_rejected(field: str) -> None:
    held = held_from(root_for(workset(1)))
    data = {**held.model_dump(mode="json"), field: SENTINEL}
    with pytest.raises(ValueError) as caught:
        InputDisposition.model_validate(data)
    check(field in str(caught.value) or "extra" in str(caught.value), "extra")
    names = set(InputDisposition.model_fields)
    check(
        names.isdisjoint({"body", "text", "content", "parts", "subject", "sender"}),
        "record has a content field",
    )


def test_held_cannot_pose_as_complete_or_as_a_prepared_result() -> None:
    ws = workset(1)
    with pytest.raises(ValueError, match="held cannot be COMPLETE"):
        TerminalRoot(
            workset_selection_index=0,
            result=held_ref("1"),
            disposition="held",
            status=COMPLETE,
            selection=ws.selections[0],
        )
    with pytest.raises(ValueError, match="wrong kind"):
        TerminalRoot(
            workset_selection_index=0,
            result=accepted_ref("1", "prepared", "2"),
            disposition="held",
            status=INCOMPLETE,
            limitations=(Limitation("held", "operator_repair"),),
            selection=ws.selections[0],
        )
    root = TerminalRoot(
        workset_selection_index=0,
        result=held_ref("1"),
        disposition="held",
        status=INCOMPLETE,
        limitations=(Limitation("held", "operator_repair"),),
        selection=ws.selections[0],
    )
    with pytest.raises(ValueError, match="conflicts with coverage"):
        receipt((root,), status=COMPLETE)


def test_text_rules_and_error_text_stay_content_free() -> None:
    held = held_from(root_for(workset(1)))
    for field in ("configuration_version", "code_version"):
        with pytest.raises(ValueError):
            mutate(held, **{field: "v\n1"})
        with pytest.raises(ValueError):
            mutate(held, **{field: ""})
    with pytest.raises(ValueError) as caught:
        mutate(held, reason=SENTINEL, repair_class=SENTINEL)
    check("repair_class" in str(caught.value), "error names the field")
    check(SENTINEL not in str(caught.value), "input value in error text")
