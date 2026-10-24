"""C0-18: receipt binding to the scope, scope id safety and shape checks."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from msgloom.cli.a2_scope_status import (
    BusyScopeError,
    HeldTerminalError,
    ScopeInputError,
    ScopeProgress,
    ScopeState,
    ScopeStatus,
    ScopeStatusError,
    status_from_error,
    status_from_held,
    status_from_receipt,
    status_line,
)
from msgloom.contracts import TerminalStatus
from tests.a2_kedro.helpers import WORKSET_REF, check, workset
from tests.a2_kedro.helpers_c0_18 import (
    FOREIGN_WORKSET,
    SCOPE,
    complete_receipt,
    forged_receipt,
    held_ref,
    prepared_ref,
    progress,
    receipt,
    terminal,
)

COMPLETE, INCOMPLETE = TerminalStatus.COMPLETE, TerminalStatus.INCOMPLETE
CANARY = "alice.canary@example.com"


def test_matching_workset_is_complete_and_foreign_workset_is_refused() -> None:
    status = status_from_receipt(progress(), complete_receipt())
    check(status.state is ScopeState.COMPLETE, "matching workset is complete")
    foreign = complete_receipt().model_copy(update={"workset": FOREIGN_WORKSET})
    with pytest.raises(ScopeInputError, match="invalid"):
        status_from_receipt(progress(), foreign)
    # The same receipt is complete for the scope that names its workset.
    other = progress(workset=FOREIGN_WORKSET)
    check(
        status_from_receipt(other, foreign).state is ScopeState.COMPLETE,
        "binding follows the scope workset",
    )
    with pytest.raises(ScopeInputError):
        status_from_receipt(other, complete_receipt())


def test_workset_binding_checks_kind_and_version_too() -> None:
    receipt_ref = complete_receipt().workset
    for ref in (
        type(receipt_ref)(receipt_ref.result_id, "other_kind", "1"),
        type(receipt_ref)(receipt_ref.result_id, receipt_ref.kind, "2"),
    ):
        with pytest.raises(ScopeInputError):
            status_from_receipt(progress(workset=ref), complete_receipt())


def test_foreign_receipt_cannot_make_a_non_complete_state_complete() -> None:
    ws = workset(2)
    roots = (terminal(ws, 0, prepared_ref("1")), terminal(ws, 1, prepared_ref("2")))
    for fake in (
        forged_receipt(roots, COMPLETE, workset=FOREIGN_WORKSET),
        forged_receipt(roots, INCOMPLETE, workset=FOREIGN_WORKSET),
        forged_receipt(roots[:1], COMPLETE, workset=FOREIGN_WORKSET),
    ):
        with pytest.raises(ScopeInputError):
            status_from_receipt(progress(), fake)
    # A foreign receipt with a held root claiming COMPLETE fails closed on
    # the binding. It does not reach the held check.
    held_root = terminal(ws, 1, held_ref("2"), INCOMPLETE).model_copy(
        update={"status": COMPLETE, "limitations": ()}
    )
    fake = forged_receipt((roots[0], held_root), COMPLETE, workset=FOREIGN_WORKSET)
    with pytest.raises(ScopeInputError) as caught:
        status_from_receipt(progress(), fake)
    check(not isinstance(caught.value, HeldTerminalError), "binding comes first")
    # The same receipt for the right workset still raises the held error.
    with pytest.raises(HeldTerminalError):
        status_from_receipt(
            progress(), fake.model_copy(update={"workset": WORKSET_REF})
        )
    # Held, blocked and busy states come only from their own inputs.
    for error in (HeldTerminalError(), BusyScopeError()):
        check(
            status_from_error(SCOPE, error).state is not ScopeState.COMPLETE,
            "error state is never complete",
        )


def test_scope_id_is_a_digest_and_cannot_carry_an_address() -> None:
    for bad in (CANARY, "", "scope-visible", "A" * 64, "7" * 63, "7" * 65):
        with pytest.raises(ValidationError):
            ScopeProgress(scope_id=bad, workset=WORKSET_REF, expected_occurrences=1)
        with pytest.raises(ValidationError):
            ScopeStatus(scope_id=bad, state=ScopeState.BUSY)
        with pytest.raises(ScopeInputError):
            status_from_error(bad, BusyScopeError())
    held_status = status_from_error(SCOPE, BusyScopeError())
    shown = [
        repr(held_status),
        held_status.model_dump_json(),
        status_line(held_status),
        repr(progress()),
        progress().model_dump_json(),
    ]
    for text in shown:
        check(CANARY not in text and "example.com" not in text, "canary leaked")
    check(SCOPE in repr(held_status), "the scope digest is the only scope output")


def test_forged_intake_held_count_must_be_an_exact_int() -> None:
    for forged in (True, False, 1.0, "0", None):
        count = 1 if forged is True else 0
        expected = progress(2, expected_intake_held=count)
        fake: Any = forged_receipt(complete_receipt().roots, COMPLETE)
        fake = fake.model_copy(update={"intake_held_count": forged})
        with pytest.raises(ScopeInputError):
            status_from_receipt(expected, fake)


def test_batch_check_runs_for_zero_count_statuses() -> None:
    base: dict[str, Any] = {"scope_id": SCOPE, "state": ScopeState.BLOCKED_SOURCE}
    ScopeStatus(**base, intake_held=5)  # zero counts with intake-held entries
    with pytest.raises(ValidationError):
        ScopeStatus(**base, intake_held=5, batches=0, batches_complete=1)
    with pytest.raises(ValidationError):
        ScopeStatus(**base, batches_complete=1)
    ScopeStatus(**base, batches=1, batches_complete=1)


def test_held_status_and_line_use_the_digest_scope() -> None:
    ws = workset(1)
    one = receipt((terminal(ws, 0, prepared_ref("1")),))
    status = status_from_receipt(progress(1), one)
    check(status.scope_id == SCOPE, "scope digest kept")
    with pytest.raises(ScopeInputError):
        status_from_held(CANARY, None)  # type: ignore[arg-type]
    with pytest.raises(ScopeInputError):
        status_from_error(SCOPE, ScopeStatusError())
