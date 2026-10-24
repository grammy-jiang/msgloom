"""C0-18: read-only scoped status types, exit codes and text line."""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from msgloom.a2_kedro.contracts.held import HeldReason, InputDisposition
from msgloom.a2_kedro.contracts.receipt import (
    CompletionReceipt,
    TerminalRoot,
    TransitionBatch,
)
from msgloom.cli import a2_scope_status as module
from msgloom.cli.a2_scope_status import (
    EXIT_CODES,
    BlockedCatalogError,
    BlockedReferenceError,
    BlockedSourceError,
    BusyScopeError,
    ClaimLostError,
    HeldTerminalError,
    ScopeInputError,
    ScopeProgress,
    ScopeState,
    ScopeStatus,
    ScopeStatusError,
    exit_code,
    status_from_error,
    status_from_held,
    status_from_receipt,
    status_line,
)
from msgloom.contracts import Limitation, TerminalStatus
from tests.a2_kedro.helpers import (
    CODE,
    CONFIG,
    WORKSET_REF,
    accepted_ref,
    check,
    root_for,
    workset,
)
from tests.a2_kedro.test_held_receipt import (
    held_ref,
    prepared_ref,
    receipt,
    terminal,
)

COMPLETE, INCOMPLETE = TerminalStatus.COMPLETE, TerminalStatus.INCOMPLETE
MODULE_PATH = Path(module.__file__ or "")
SECRET = "sentinel-private-detail-text"
SCOPE = "scope-visible-in-status-only"


STATE_CODES = [
    ("complete", 0),
    ("claim_lost", 4),
    ("incomplete", 20),
    ("busy", 21),
    ("held", 22),
    ("blocked_source", 30),
    ("blocked_reference", 31),
    ("blocked_catalog", 32),
]


class SubStr(str):
    """A str subclass that strict models must refuse."""


def progress(occurrences: int = 2, **changes: Any) -> ScopeProgress:
    return ScopeProgress(scope_id=SCOPE, expected_occurrences=occurrences, **changes)


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
    roots: tuple[TerminalRoot, ...], status: TerminalStatus
) -> CompletionReceipt:
    """Build a receipt that skips validation, as a hostile caller could."""
    return CompletionReceipt.model_construct(
        workset=WORKSET_REF,
        status=status,
        policy_version="policy-1",
        roots=roots,
        transition_batch=None,
        intake_held_count=0,
        acceptance_index_sha256="0" * 64,
        claim_proofs=(),
    )


def batch_for(ws: Any, status: TerminalStatus) -> TransitionBatch:
    return TransitionBatch(
        transitions=ws.transitions,
        result=accepted_ref("3", "prepared_transitions", "2"),
        status=status,
    )


def test_complete_receipt_is_the_only_complete_state() -> None:
    status = status_from_receipt(progress(), complete_receipt())
    check(status.state is ScopeState.COMPLETE, "complete state")
    check(status.terminal_status is COMPLETE, "contract status")
    check((status.occurrences, status.complete) == (2, 2), "counts")
    check(status.limitation_codes == (), "no limitation")
    check(exit_code(status) == 0, "exit zero")
    check(
        status_line(status)
        == "a2 scope complete: occurrences=2 complete=2 incomplete=0 held=0"
        " missing=0 intake_held=0 batches=0 batches_complete=0 limitations=none",
        "line",
    )


def test_complete_with_complete_batch() -> None:
    ws = workset(1, transitions=1)
    good = receipt(
        (terminal(ws, 0, prepared_ref("1")),), transition_batch=batch_for(ws, COMPLETE)
    )
    status = status_from_receipt(progress(1, expects_batch=True), good)
    check(status.state is ScopeState.COMPLETE, "complete with batch")


def test_incomplete_root_gives_incomplete_with_codes() -> None:
    ws = workset(2)
    partial = receipt(
        (
            terminal(ws, 0, prepared_ref("1")),
            terminal(ws, 1, prepared_ref("2"), INCOMPLETE),
        ),
        status=INCOMPLETE,
    )
    status = status_from_receipt(progress(), partial)
    check((status.complete, status.incomplete) == (1, 1), "counts")
    codes = ("partial", "receipt_incomplete")
    check(
        (status.state, status.limitation_codes) == (ScopeState.INCOMPLETE, codes),
        "codes",
    )
    check(exit_code(status) == 20, "exit twenty")


def test_receipt_with_missing_occurrence_is_never_complete() -> None:
    ws = workset(2)
    one = receipt((terminal(ws, 0, prepared_ref("1")),))
    status = status_from_receipt(progress(2), one)
    check(status.missing == 1 and status.complete == 1, "missing count")
    check(status.state is ScopeState.INCOMPLETE, "state")
    check(status.limitation_codes == ("occurrence_missing",), "code")


def test_missing_batch_and_incomplete_batch_are_never_complete() -> None:
    ws = workset(1, transitions=1)
    roots = (terminal(ws, 0, prepared_ref("1")),)
    status = status_from_receipt(progress(1, expects_batch=True), receipt(roots))
    check(status.state is ScopeState.INCOMPLETE, "state")
    check(status.limitation_codes == ("batch_missing",), "batch code")
    check((status.batches, status.batches_complete) == (1, 0), "batch counts")
    batch = batch_for(ws, INCOMPLETE)
    open_batch = receipt(roots, status=INCOMPLETE, transition_batch=batch)
    status = status_from_receipt(progress(1, expects_batch=True), open_batch)
    check(status.state is ScopeState.INCOMPLETE, "state")
    check("batch_incomplete" in status.limitation_codes, "batch code")


def test_held_only_receipt_is_incomplete_intake_held() -> None:
    held_only = receipt((), status=INCOMPLETE, intake_held_count=2)
    status = status_from_receipt(
        ScopeProgress(scope_id=SCOPE, expected_occurrences=0, expected_intake_held=2),
        held_only,
    )
    check(status.intake_held == 2 and status.occurrences == 0, "counts")
    check(status.state is ScopeState.INCOMPLETE, "state")
    check(status.limitation_codes == ("intake_held", "receipt_incomplete"), "codes")


def test_a2_held_root_is_held_incomplete_never_complete() -> None:
    ws = workset(2)
    held_root = terminal(ws, 1, held_ref("2"), INCOMPLETE)
    mixed = receipt((terminal(ws, 0, prepared_ref("1")), held_root), status=INCOMPLETE)
    status = status_from_receipt(progress(), mixed)
    check(status.state is ScopeState.HELD, "held state")
    check(status.terminal_status is INCOMPLETE, "held reports incomplete")
    check((status.complete, status.held, status.incomplete) == (1, 1, 0), "counts")
    check(exit_code(status) == 22, "exit twenty-two")


def test_forged_held_root_claiming_complete_raises_typed_error() -> None:
    ws = workset(1)
    forged = TerminalRoot.model_construct(
        workset_selection_index=0,
        result=held_ref("2"),
        disposition="held",
        status=COMPLETE,
        limitations=(),
        selection=ws.selections[0],
        baseline_selection=None,
        baseline_source=None,
    )
    fake = forged_receipt((forged,), COMPLETE)
    with pytest.raises(HeldTerminalError, match="never complete"):
        status_from_receipt(progress(1), fake)
    # Held is detected by the result kind too, not only by disposition.
    relabeled = forged.model_copy(update={"disposition": "prepared"})
    with pytest.raises(HeldTerminalError):
        status_from_receipt(
            progress(1), fake.model_copy(update={"roots": (relabeled,)})
        )
    state = status_from_error(SCOPE, HeldTerminalError())
    check(state.state is ScopeState.HELD, "mapped to held")
    check(state.terminal_status is INCOMPLETE, "never complete")


def test_receipt_status_claim_is_not_trusted() -> None:
    ws = workset(1)
    forged = forged_receipt((terminal(ws, 0, prepared_ref("1"), INCOMPLETE),), COMPLETE)
    status = status_from_receipt(progress(1), forged)
    check(status.state is ScopeState.INCOMPLETE, "recomputed from roots")
    flipped = forged_receipt((terminal(ws, 0, prepared_ref("1")),), INCOMPLETE)
    check(
        status_from_receipt(progress(1), flipped).state is ScopeState.INCOMPLETE,
        "an incomplete receipt status blocks complete",
    )


def test_held_record_maps_to_held() -> None:
    held = InputDisposition.from_root(
        root_for(workset(1)),
        HeldReason.PARSER_UNSUPPORTED,
        configuration_version=CONFIG,
        code_version=CODE,
    )
    status = status_from_held(SCOPE, held)
    check(status.state is ScopeState.HELD, "held state")
    check(status.limitation_codes == ("parser_unsupported",), "reason code")
    check((status.occurrences, status.held) == (1, 1), "counts")


BLOCKED, FAILED = TerminalStatus.BLOCKED, TerminalStatus.FAILED
MESSAGES = {
    BlockedSourceError: "scope is blocked: source unavailable",
    BlockedReferenceError: "scope is blocked: reference unresolved",
    BlockedCatalogError: "scope is blocked: catalog unavailable",
    BusyScopeError: "scope is busy: another claim is active",
    ClaimLostError: "scope claim was lost",
    HeldTerminalError: "A2 held terminal root is never complete",
}


@pytest.mark.parametrize(
    ("error", "state", "terminal", "code"),
    [
        (BlockedSourceError, ScopeState.BLOCKED_SOURCE, BLOCKED, 30),
        (BlockedReferenceError, ScopeState.BLOCKED_REFERENCE, BLOCKED, 31),
        (BlockedCatalogError, ScopeState.BLOCKED_CATALOG, BLOCKED, 32),
        (BusyScopeError, ScopeState.BUSY, INCOMPLETE, 21),
        (ClaimLostError, ScopeState.CLAIM_LOST, FAILED, 4),
        (HeldTerminalError, ScopeState.HELD, INCOMPLETE, 22),
    ],
)
def test_typed_errors_map_to_state_exit_and_fixed_message(
    error: type[ScopeStatusError],
    state: ScopeState,
    terminal: TerminalStatus,
    code: int,
) -> None:
    check(str(error()) == MESSAGES[error], "fixed message")
    check(issubclass(error, ScopeStatusError), "single base")
    with pytest.raises(TypeError):
        error("extra detail")  # type: ignore[call-arg]
    status = status_from_error(SCOPE, error())
    check(status.state is state, "state")
    check(status.terminal_status is terminal, "contract status")
    check(exit_code(status) == code, "exit code")
    check(status.occurrences == 0, "no counts")
    check(len(status.limitation_codes) == 1, "one code")


def test_exit_code_table_is_pinned() -> None:
    table = {state.value: code for state, code in EXIT_CODES.items()}
    check(table == dict(STATE_CODES), "exit code table")
    check(set(EXIT_CODES) == set(ScopeState), "every state has a code")
    check(len(set(EXIT_CODES.values())) == len(EXIT_CODES), "codes are distinct")
    # Codes 2 and 3 belong to runner.py (invalid input, untrusted authority).
    check(not {2, 3} & set(EXIT_CODES.values()), "no clash with runner codes")


def test_text_never_carries_input_values() -> None:
    ws = workset(2)
    secret_root = open_root(ws, 1, (Limitation("partial", SECRET),))
    partial = receipt(
        (terminal(ws, 0, prepared_ref("1")), secret_root), status=INCOMPLETE
    )
    status = status_from_receipt(progress(), partial)
    shown = status_line(status)
    for value in (SECRET, SCOPE, WORKSET_REF.result_id, prepared_ref("1").result_id):
        check(value not in shown, "value leaked into the line")
        check(value not in repr(status.limitation_codes), "value leaked in codes")
    check(SECRET not in status.model_dump_json(), "detail not in status")
    check(shown.isascii() and "\n" not in shown, "single ascii line")
    check("/" not in shown, "no path separator")


def test_unsafe_limitation_code_is_replaced() -> None:
    ws = workset(1)
    root = open_root(ws, 0, (Limitation(SECRET + "/x", "d"),))
    status = status_from_receipt(progress(1), receipt((root,), status=INCOMPLETE))
    check(
        status.limitation_codes == ("limitation_code_unsafe", "receipt_incomplete"),
        "unsafe code replaced",
    )
    check(SECRET not in status_line(status), "no leak")


def test_many_distinct_codes_are_truncated_not_dropped_silently() -> None:
    ws = workset(1)
    root = open_root(ws, 0, tuple(Limitation(f"c{n:03d}", "d") for n in range(64)))
    status = status_from_receipt(progress(1), receipt((root,), status=INCOMPLETE))
    check(len(status.limitation_codes) == 64, "bounded")
    check("limitation_codes_truncated" in status.limitation_codes, "marker")


def test_negative_inputs_raise_typed_errors() -> None:
    good = complete_receipt()
    bad: Any = "text"
    calls = [
        lambda: status_from_receipt(bad, good),
        lambda: status_from_receipt(progress(), bad),
        lambda: status_from_receipt(progress(1), good),  # extra occurrence
        lambda: status_from_receipt(progress(2, expected_intake_held=1), good),
        lambda: status_from_error(SCOPE, ScopeInputError()),
        lambda: status_from_error(SCOPE, ScopeStatusError()),
        lambda: status_from_error(SCOPE, bad),
        lambda: status_from_error("", BusyScopeError()),
        lambda: status_from_error(SubStr(SCOPE), BusyScopeError()),
        lambda: status_from_held(SCOPE, bad),
        lambda: exit_code(bad),
        lambda: status_line(None),  # type: ignore[arg-type]
    ]
    for call in calls:
        with pytest.raises(ScopeInputError, match="invalid"):
            call()


def test_unexpected_batch_and_foreign_status_are_rejected() -> None:
    ws = workset(1, transitions=1)
    batch = batch_for(ws, COMPLETE)
    with_batch = receipt((terminal(ws, 0, prepared_ref("1")),), transition_batch=batch)
    with pytest.raises(ScopeInputError):
        status_from_receipt(progress(1), with_batch)
    failed = terminal(ws, 0, prepared_ref("1")).model_copy(
        update={"status": TerminalStatus.FAILED}
    )
    fake = forged_receipt((failed,), INCOMPLETE)
    with pytest.raises(ScopeInputError):
        status_from_receipt(progress(1), fake)


def test_models_reject_bad_shapes() -> None:
    with pytest.raises(ValidationError):
        ScopeProgress(scope_id="", expected_occurrences=1)  # empty scope id
    with pytest.raises(ValueError, match="no frozen work"):
        ScopeProgress(scope_id=SCOPE, expected_occurrences=0)  # empty scope
    with pytest.raises(ValidationError):
        ScopeProgress(scope_id=SubStr(SCOPE), expected_occurrences=1)
    with pytest.raises(ValidationError):
        ScopeProgress(scope_id=SCOPE, expected_occurrences=True)  # bool is not int
    with pytest.raises(ValidationError):
        ScopeProgress(scope_id=SCOPE, expected_occurrences=1, extra_field=1)  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        ScopeStatus(scope_id=SCOPE, state="unknown")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        ScopeStatus(scope_id=SCOPE, state="complete")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        ScopeStatus(scope_id=SCOPE, state=ScopeState.BUSY, surprise=1)  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        ScopeStatus(
            scope_id=SCOPE, state=ScopeState.BUSY, limitation_codes=(SubStr("busy"),)
        )
    with pytest.raises(ValidationError):
        ScopeStatus(
            scope_id=SCOPE, state=ScopeState.BUSY, limitation_codes=("Has Space",)
        )
    with pytest.raises(ValidationError):
        ScopeStatus(scope_id=SCOPE, state=ScopeState.BUSY, limitation_codes=("b", "a"))


def test_complete_status_cannot_be_built_with_open_work() -> None:
    base: dict[str, Any] = {
        "scope_id": SCOPE,
        "state": ScopeState.COMPLETE,
        "occurrences": 1,
        "complete": 1,
    }
    ScopeStatus(**base)  # the valid shape builds
    for change in (
        {"complete": 0, "incomplete": 1},
        {"complete": 0, "held": 1},
        {"complete": 0, "missing": 1},
        {"intake_held": 1},
        {"limitation_codes": ("partial",)},
        {"batches": 1},
        {"occurrences": 0, "complete": 0},
        {"occurrences": 2},
    ):
        with pytest.raises(ValidationError):
            ScopeStatus(**{**base, **change})
    with pytest.raises(ValidationError):
        ScopeStatus(**{**base, "batches_complete": 1})


def test_status_is_frozen_and_deterministic() -> None:
    first = status_from_receipt(progress(), complete_receipt())
    second = status_from_receipt(progress(), complete_receipt())
    check(first == second, "equal status")
    check(first.model_dump_json() == second.model_dump_json(), "equal json")
    check(status_line(first) == status_line(second), "equal line")
    with pytest.raises(ValidationError):
        first.state = ScopeState.INCOMPLETE  # type: ignore[misc]


def test_module_never_touches_persistence_environment_or_files() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            names.add(f"{node.value.id}.{node.attr}")
    forbidden = ("persistence", "sqlite3", "os", "pathlib", "sys.environ", "open")
    for name in names:
        check(
            not any(part in forbidden for part in name.split(".")),
            "forbidden dependency in scope status module",
        )
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    check("open" not in calls, "no file open")


def run_module(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", "-m", "msgloom.cli.a2_scope_status", *args],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize(("state", "code"), STATE_CODES)
def test_process_exit_code_for_each_state(state: str, code: int) -> None:
    done = run_module(state)
    check(done.returncode == code, "real process exit code")
    check(done.stdout == f"a2 scope {state}: exit={code}\n", "stdout line")
    check(done.stderr == "", "stderr is empty")


@pytest.mark.parametrize("args", [(), ("nonsense",), ("complete", "busy"), ("",)])
def test_process_rejects_bad_command_lines_with_two(args: tuple[str, ...]) -> None:
    done = run_module(*args)
    check(done.returncode == 2, "invalid input exit code")
    check(done.stdout == "a2 scope status: invalid state\n", "fixed text")
