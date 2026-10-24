"""Shared builders for the C0-18 scope status tests."""

from __future__ import annotations

from typing import Any

from msgloom.a2_kedro.contracts.receipt import (
    CompletionReceipt,
    TerminalRoot,
    TransitionBatch,
)
from msgloom.cli.a2_scope_status import ScopeProgress
from msgloom.contracts import Limitation, ResultRef, TerminalStatus
from tests.a2_kedro.helpers import WORKSET_REF, accepted_ref, hexd, workset

COMPLETE, INCOMPLETE = TerminalStatus.COMPLETE, TerminalStatus.INCOMPLETE
SCOPE = hexd("7")
#: A workset reference that differs from ``WORKSET_REF``.
FOREIGN_WORKSET = ResultRef(
    "intake-workset:" + hexd("8"), "preparation_intake_workset", "1"
)


def prepared_ref(char: str) -> ResultRef:
    return accepted_ref(char, "prepared", "2")


def held_ref(char: str) -> ResultRef:
    return accepted_ref(char, "a2_input_disposition", "1")


def terminal(
    ws: Any, index: int, ref: ResultRef, status: TerminalStatus = COMPLETE
) -> TerminalRoot:
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
    return CompletionReceipt.build(**values)


def progress(occurrences: int = 2, **changes: Any) -> ScopeProgress:
    values: dict[str, Any] = {"scope_id": SCOPE, "workset": WORKSET_REF}
    values.update(changes)
    return ScopeProgress(expected_occurrences=occurrences, **values)


def open_root(ws: Any, index: int, limitations: tuple[Limitation, ...]) -> TerminalRoot:
    """Return an INCOMPLETE prepared root with explicit ``limitations``."""
    return TerminalRoot(
        workset_selection_index=index,
        result=prepared_ref(str(index + 1)),
        disposition="prepared",
        status=INCOMPLETE,
        limitations=limitations,
        selection=ws.selections[index],
    )


def complete_receipt() -> CompletionReceipt:
    ws = workset(2)
    return receipt(
        (terminal(ws, 0, prepared_ref("1")), terminal(ws, 1, prepared_ref("2")))
    )


def forged_receipt(
    roots: tuple[TerminalRoot, ...], status: TerminalStatus, **changes: Any
) -> CompletionReceipt:
    """Build a receipt that skips validation, as a hostile caller could."""
    values: dict[str, Any] = {
        "workset": WORKSET_REF,
        "status": status,
        "policy_version": "policy-1",
        "roots": roots,
        "transition_batch": None,
        "intake_held_count": 0,
        "acceptance_index_sha256": "0" * 64,
        "claim_proofs": (),
    }
    values.update(changes)
    return CompletionReceipt.model_construct(**values)


def batch_for(ws: Any, status: TerminalStatus) -> TransitionBatch:
    return TransitionBatch(
        transitions=ws.transitions,
        result=accepted_ref("3", "prepared_transitions", "2"),
        status=status,
    )
