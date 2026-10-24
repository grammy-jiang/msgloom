"""
Pure scheduler status policy for A2 v2 activation (I0-01).

This module is a closed state machine. Its input is a
:class:`SchedulerState` and a :class:`SchedulerEvent`. Its output is the
next :class:`SchedulerState` or a typed :exc:`StatusPolicyError`. It does no
I/O, reads no clock, uses no randomness and imports no persistence, CLI or
A1 module. It does not import the C0-18 types either, so it stays
independent. The names follow C0-18 (``ScopeState``) on purpose.

States stay distinct:

* ``PENDING`` is waiting for a claim.
* ``BUSY`` is claimed by one attempt.
* ``HELD`` is paused by an input hold and waits for an explicit resume.
* ``BLOCKED`` cannot run because evidence or a reference is unavailable.
* ``FAILED`` is a lost or failed attempt.
* ``CANCELLED`` was stopped on purpose.

``BLOCKED``, ``FAILED`` and ``CANCELLED`` are terminal. No event leaves a
terminal state. A new attempt needs a new scheduler item. A completed scope
is not a scheduler state. The completion receipt records it (C0-18).

:data:`TRANSITIONS` lists every pair of state and event. A pair that is not
allowed maps to ``None``. A self-transition is not allowed, so a repeated
event is an error and never a silent no-op. The table is checked once at
import time. A bad table raises :exc:`RuntimeError` and the module does not
load.

Input checks are strict. The public functions accept only the exact enum
classes. A plain ``str``, a ``str`` subclass, a ``bool`` or an ``int`` is
rejected, even when its value equals a member value. Every error has a fixed
message. No error holds the rejected input, so no address or path can enter
an error text.

CANDIDATE/RESEARCH, PROVISIONAL: nothing calls this module yet. The wire
names and the terminal rule for ``BLOCKED`` are provisional until the
activation decision confirms them. See
``docs/notes/a2-v2-i0-01-status-policy.md``.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType
from typing import ClassVar


class SchedulerState(StrEnum):
    """Closed states of one scheduler item. The wire names are provisional."""

    PENDING = "pending"
    BUSY = "busy"
    HELD = "held"
    BLOCKED = "blocked"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SchedulerEvent(StrEnum):
    """
    Closed events that can move a scheduler item.

    No event value equals a state value, so a state and an event are never
    confused, even as plain strings.
    """

    CLAIM = "claim"
    RELEASE = "release"
    HOLD = "hold"
    RESUME = "resume"
    BLOCK = "block"
    FAIL = "fail"
    CANCEL = "cancel"


class StatusPolicyError(Exception):
    """
    Base of every status policy error. The message is fixed.

    No subclass takes an argument, so no input value can enter the message.
    """

    code: ClassVar[str] = "status_policy_invalid"
    message: ClassVar[str] = "scheduler status input is invalid"

    def __init__(self) -> None:
        super().__init__(self.message)


class UnknownStateError(StatusPolicyError):
    """The value is not exactly a :class:`SchedulerState` member."""

    code = "unknown_state"
    message = "scheduler state is unknown"


class UnknownEventError(StatusPolicyError):
    """The value is not exactly a :class:`SchedulerEvent` member."""

    code = "unknown_event"
    message = "scheduler event is unknown"


class TransitionRejectedError(StatusPolicyError):
    """The table does not allow the event in the state."""

    code = "transition_rejected"
    message = "scheduler transition is not allowed"


class TerminalStateError(TransitionRejectedError):
    """The state is terminal. No event can leave it."""

    code = "terminal_state"
    message = "scheduler state is terminal"


_S, _E = SchedulerState, SchedulerEvent

#: Terminal states. No event leaves them.
TERMINAL_STATES: frozenset[SchedulerState] = frozenset(
    {_S.BLOCKED, _S.FAILED, _S.CANCELLED}
)

#: Total table of (state, event) to next state. ``None`` means rejected.
_TABLE: dict[tuple[SchedulerState, SchedulerEvent], SchedulerState | None] = {
    (_S.PENDING, _E.CLAIM): _S.BUSY,
    (_S.PENDING, _E.RELEASE): None,
    (_S.PENDING, _E.HOLD): _S.HELD,
    (_S.PENDING, _E.RESUME): None,
    (_S.PENDING, _E.BLOCK): _S.BLOCKED,
    (_S.PENDING, _E.FAIL): None,
    (_S.PENDING, _E.CANCEL): _S.CANCELLED,
    (_S.BUSY, _E.CLAIM): None,
    (_S.BUSY, _E.RELEASE): _S.PENDING,
    (_S.BUSY, _E.HOLD): _S.HELD,
    (_S.BUSY, _E.RESUME): None,
    (_S.BUSY, _E.BLOCK): _S.BLOCKED,
    (_S.BUSY, _E.FAIL): _S.FAILED,
    (_S.BUSY, _E.CANCEL): _S.CANCELLED,
    (_S.HELD, _E.CLAIM): None,
    (_S.HELD, _E.RELEASE): None,
    (_S.HELD, _E.HOLD): None,
    (_S.HELD, _E.RESUME): _S.PENDING,
    (_S.HELD, _E.BLOCK): _S.BLOCKED,
    (_S.HELD, _E.FAIL): None,
    (_S.HELD, _E.CANCEL): _S.CANCELLED,
    (_S.BLOCKED, _E.CLAIM): None,
    (_S.BLOCKED, _E.RELEASE): None,
    (_S.BLOCKED, _E.HOLD): None,
    (_S.BLOCKED, _E.RESUME): None,
    (_S.BLOCKED, _E.BLOCK): None,
    (_S.BLOCKED, _E.FAIL): None,
    (_S.BLOCKED, _E.CANCEL): None,
    (_S.FAILED, _E.CLAIM): None,
    (_S.FAILED, _E.RELEASE): None,
    (_S.FAILED, _E.HOLD): None,
    (_S.FAILED, _E.RESUME): None,
    (_S.FAILED, _E.BLOCK): None,
    (_S.FAILED, _E.FAIL): None,
    (_S.FAILED, _E.CANCEL): None,
    (_S.CANCELLED, _E.CLAIM): None,
    (_S.CANCELLED, _E.RELEASE): None,
    (_S.CANCELLED, _E.HOLD): None,
    (_S.CANCELLED, _E.RESUME): None,
    (_S.CANCELLED, _E.BLOCK): None,
    (_S.CANCELLED, _E.FAIL): None,
    (_S.CANCELLED, _E.CANCEL): None,
}

#: Read-only view of the transition table.
TRANSITIONS: Mapping[tuple[SchedulerState, SchedulerEvent], SchedulerState | None] = (
    MappingProxyType(_TABLE)
)


def _check_table() -> None:
    """Raise :exc:`RuntimeError` unless the table is total and consistent."""
    for state in SchedulerState:
        for event in SchedulerEvent:
            if (state, event) not in _TABLE:
                raise RuntimeError("scheduler table is not total")
        moves = [_TABLE[state, event] for event in SchedulerEvent]
        has_move = any(target is not None for target in moves)
        if has_move == (state in TERMINAL_STATES):
            raise RuntimeError("scheduler terminal states are inconsistent")
    if len(_TABLE) != len(SchedulerState) * len(SchedulerEvent):
        raise RuntimeError("scheduler table has extra keys")
    if {s.value for s in SchedulerState} & {e.value for e in SchedulerEvent}:
        raise RuntimeError("scheduler state and event names overlap")


_check_table()


def parse_state(value: object) -> SchedulerState:
    """
    Return the state for an exact member or an exact wire ``str``.

    A ``bool``, an ``int``, a ``str`` subclass or an unknown name raises
    :exc:`UnknownStateError`.
    """
    if type(value) is SchedulerState:
        return value
    if type(value) is str:
        for state in SchedulerState:
            if state.value == value:
                return state
    raise UnknownStateError


def parse_event(value: object) -> SchedulerEvent:
    """
    Return the event for an exact member or an exact wire ``str``.

    A ``bool``, an ``int``, a ``str`` subclass or an unknown name raises
    :exc:`UnknownEventError`.
    """
    if type(value) is SchedulerEvent:
        return value
    if type(value) is str:
        for event in SchedulerEvent:
            if event.value == value:
                return event
    raise UnknownEventError


def is_terminal(state: SchedulerState) -> bool:
    """Return whether ``state`` is terminal. Reject a non-member state."""
    if type(state) is not SchedulerState:
        raise UnknownStateError
    return state in TERMINAL_STATES


def allowed_events(state: SchedulerState) -> frozenset[SchedulerEvent]:
    """Return the events that move ``state``. Terminal states give none."""
    if type(state) is not SchedulerState:
        raise UnknownStateError
    return frozenset(e for e in SchedulerEvent if _TABLE[state, e] is not None)


def transition(state: SchedulerState, event: SchedulerEvent) -> SchedulerState:
    """
    Return the next state for ``event`` in ``state``.

    Only exact enum members are accepted. Wire strings go through
    :func:`parse_state` and :func:`parse_event` first. The check order is
    state type, event type, terminal state, table entry.

    :raises UnknownStateError: ``state`` is not a member.
    :raises UnknownEventError: ``event`` is not a member.
    :raises TerminalStateError: ``state`` is terminal.
    :raises TransitionRejectedError: the table rejects the pair.
    """
    if type(state) is not SchedulerState:
        raise UnknownStateError
    if type(event) is not SchedulerEvent:
        raise UnknownEventError
    if state in TERMINAL_STATES:
        raise TerminalStateError
    target = _TABLE[state, event]
    if target is None:
        raise TransitionRejectedError
    return target
