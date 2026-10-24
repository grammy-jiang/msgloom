"""I0-01 scheduler status policy: closed states, total table, strict input."""

from __future__ import annotations

import ast
import inspect
from typing import Any

import pytest

from msgloom.a2_kedro.activation import status_policy
from msgloom.a2_kedro.activation.status_policy import (
    TERMINAL_STATES,
    TRANSITIONS,
    SchedulerEvent,
    SchedulerState,
    StatusPolicyError,
    TerminalStateError,
    TransitionRejectedError,
    UnknownEventError,
    UnknownStateError,
    allowed_events,
    is_terminal,
    parse_event,
    parse_state,
    transition,
)

STATES = ("pending", "busy", "held", "blocked", "failed", "cancelled")
EVENTS = ("claim", "release", "hold", "resume", "block", "fail", "cancel")
X = "REJECT"

#: Hand-written expectation. Row = state, column = event in EVENTS order.
EXPECTED: dict[str, tuple[str, ...]] = {
    #            claim   release    hold    resume     block      fail      cancel
    "pending": ("busy", X, "held", X, "blocked", X, "cancelled"),
    "busy": (X, "pending", "held", X, "blocked", "failed", "cancelled"),
    "held": (X, X, X, "pending", "blocked", X, "cancelled"),
    "blocked": (X, X, X, X, X, X, X),
    "failed": (X, X, X, X, X, X, X),
    "cancelled": (X, X, X, X, X, X, X),
}

CELLS = [
    (state, event, EXPECTED[state][column])
    for state in STATES
    for column, event in enumerate(EVENTS)
]

#: Text that must never appear in an error.
SECRET = "alice@example.com /home/alice/secret"


class StrChild(str):
    """A str subclass with a valid wire value."""


def any_value(value: object) -> Any:
    return value


def test_members_are_literal() -> None:
    if tuple(s.value for s in SchedulerState) != STATES:
        pytest.fail("state names changed")
    if tuple(e.value for e in SchedulerEvent) != EVENTS:
        pytest.fail("event names changed")
    if set(STATES) & set(EVENTS):
        pytest.fail("a state name equals an event name")


def test_literal_table_is_complete() -> None:
    if len(CELLS) != 42:
        pytest.fail("expected 6 states x 7 events")
    if len(TRANSITIONS) != 42:
        pytest.fail("table must hold exactly 42 pairs")


@pytest.mark.parametrize(("state", "event", "expected"), CELLS)
def test_full_matrix(state: str, event: str, expected: str) -> None:
    source, trigger = SchedulerState(state), SchedulerEvent(event)
    table_value = TRANSITIONS[source, trigger]
    if expected == X:
        if table_value is not None:
            pytest.fail("table must reject this pair")
        with pytest.raises(TransitionRejectedError):
            transition(source, trigger)
        return
    result = transition(source, trigger)
    if result.value != expected or type(result) is not SchedulerState:
        pytest.fail("wrong next state")
    if table_value is not result:
        pytest.fail("table and function disagree")


@pytest.mark.parametrize("state", ["blocked", "failed", "cancelled"])
@pytest.mark.parametrize("event", EVENTS)
def test_terminal_states_never_transition(state: str, event: str) -> None:
    source = SchedulerState(state)
    if not is_terminal(source) or allowed_events(source):
        pytest.fail("state must be terminal with no events")
    with pytest.raises(TerminalStateError):
        transition(source, SchedulerEvent(event))


def test_terminal_set_is_literal() -> None:
    if {s.value for s in TERMINAL_STATES} != {"blocked", "failed", "cancelled"}:
        pytest.fail("terminal set changed")
    for name in ("pending", "busy", "held"):
        if is_terminal(SchedulerState(name)):
            pytest.fail("non-terminal state flagged terminal")


def test_allowed_events_literal() -> None:
    expected = {
        "pending": {"claim", "hold", "block", "cancel"},
        "busy": {"release", "hold", "block", "fail", "cancel"},
        "held": {"resume", "block", "cancel"},
    }
    for name, events in expected.items():
        got = {e.value for e in allowed_events(SchedulerState(name))}
        if got != events:
            pytest.fail("allowed events changed")


def test_self_transition_is_rejected() -> None:
    with pytest.raises(TransitionRejectedError):
        transition(SchedulerState.HELD, SchedulerEvent.HOLD)
    with pytest.raises(TransitionRejectedError):
        transition(SchedulerState.BUSY, SchedulerEvent.CLAIM)


def test_distinct_paths_never_collapse() -> None:
    held = transition(SchedulerState.PENDING, SchedulerEvent.HOLD)
    busy = transition(SchedulerState.PENDING, SchedulerEvent.CLAIM)
    blocked = transition(SchedulerState.PENDING, SchedulerEvent.BLOCK)
    failed = transition(SchedulerState.BUSY, SchedulerEvent.FAIL)
    cancelled = transition(SchedulerState.BUSY, SchedulerEvent.CANCEL)
    results = [held, busy, blocked, failed, cancelled, SchedulerState.PENDING]
    if len(set(results)) != 6:
        pytest.fail("two different states collapsed")


def test_held_returns_only_through_resume_to_pending() -> None:
    resumed = transition(SchedulerState.HELD, SchedulerEvent.RESUME)
    if resumed is not SchedulerState.PENDING:
        pytest.fail("resume must give pending")
    with pytest.raises(TransitionRejectedError):
        transition(SchedulerState.HELD, SchedulerEvent.CLAIM)


@pytest.mark.parametrize(
    "bad",
    [
        True,
        False,
        0,
        1,
        None,
        1.0,
        b"pending",
        ("pending",),
        "PENDING",
        "",
        "unknown",
        " pending",
        "pending\n",
        "busy ",
        StrChild("pending"),
    ],
)
def test_bad_state_is_rejected(bad: object) -> None:
    value = any_value(bad)
    with pytest.raises(UnknownStateError):
        transition(value, SchedulerEvent.CLAIM)
    with pytest.raises(UnknownStateError):
        parse_state(value)
    with pytest.raises(UnknownStateError):
        is_terminal(value)
    with pytest.raises(UnknownStateError):
        allowed_events(value)


@pytest.mark.parametrize(
    "bad",
    [
        True,
        False,
        0,
        1,
        None,
        1.0,
        b"claim",
        ("claim",),
        "CLAIM",
        "",
        "unknown",
        "claim ",
        "complete",
        "pending",
        StrChild("claim"),
    ],
)
def test_bad_event_is_rejected(bad: object) -> None:
    value = any_value(bad)
    with pytest.raises(UnknownEventError):
        transition(SchedulerState.PENDING, value)
    with pytest.raises(UnknownEventError):
        parse_event(value)


def test_plain_string_is_not_accepted_by_transition() -> None:
    with pytest.raises(UnknownStateError):
        transition(any_value("pending"), SchedulerEvent.CLAIM)
    with pytest.raises(UnknownEventError):
        transition(SchedulerState.PENDING, any_value("claim"))


def test_event_in_state_slot_and_state_in_event_slot() -> None:
    with pytest.raises(UnknownStateError):
        transition(any_value(SchedulerEvent.CLAIM), SchedulerEvent.CLAIM)
    with pytest.raises(UnknownEventError):
        transition(SchedulerState.PENDING, any_value(SchedulerState.BUSY))


def test_state_check_runs_before_event_check() -> None:
    with pytest.raises(UnknownStateError):
        transition(any_value("x"), any_value("y"))
    with pytest.raises(TerminalStateError):
        transition(SchedulerState.FAILED, SchedulerEvent.CLAIM)


def test_parse_accepts_exact_wire_names_only() -> None:
    for name in STATES:
        if parse_state(name).value != name:
            pytest.fail("state parse failed")
        if parse_state(SchedulerState(name)) is not SchedulerState(name):
            pytest.fail("member parse failed")
    for name in EVENTS:
        if parse_event(name).value != name:
            pytest.fail("event parse failed")


def test_errors_are_fixed_and_pii_free() -> None:
    errors: list[StatusPolicyError] = []
    for call in (
        lambda: transition(any_value(SECRET), SchedulerEvent.CLAIM),
        lambda: transition(SchedulerState.PENDING, any_value(SECRET)),
        lambda: parse_state(SECRET),
        lambda: parse_event(SECRET),
        lambda: parse_state(StrChild(SECRET)),
        lambda: transition(SchedulerState.PENDING, SchedulerEvent.RESUME),
        lambda: transition(SchedulerState.FAILED, SchedulerEvent.CLAIM),
    ):
        with pytest.raises(StatusPolicyError) as caught:
            call()
        errors.append(caught.value)
    for error in errors:
        text = f"{error!s}|{error!r}|{error.args!r}"
        for part in ("alice", "example.com", "/home", "secret"):
            if part in text:
                pytest.fail("error text leaks input")
        if error.args != (type(error).message,):
            pytest.fail("error message is not fixed")
    codes = {type(e).code for e in errors}
    expected = {
        "unknown_state",
        "unknown_event",
        "transition_rejected",
        "terminal_state",
    }
    if codes != expected:
        pytest.fail("error codes changed")


def test_error_classes_take_no_argument() -> None:
    for cls in (UnknownStateError, UnknownEventError, TransitionRejectedError):
        with pytest.raises(TypeError):
            cls(SECRET)  # type: ignore[call-arg]
    if not issubclass(TerminalStateError, TransitionRejectedError):
        pytest.fail("terminal error must be a rejection")


def test_table_is_read_only() -> None:
    key = (SchedulerState.PENDING, SchedulerEvent.CLAIM)
    with pytest.raises(TypeError):
        any_value(TRANSITIONS)[key] = SchedulerState.FAILED
    if transition(*key) is not SchedulerState.BUSY:
        pytest.fail("table changed")


def test_module_is_pure() -> None:
    tree = ast.parse(inspect.getsource(status_policy))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    allowed = {"__future__", "collections", "enum", "types", "typing"}
    if imported - allowed:
        pytest.fail("status policy imports a non-pure module")
    if "assert" in {type(n).__name__.lower() for n in ast.walk(tree)}:
        pytest.fail("assert statement in source")
