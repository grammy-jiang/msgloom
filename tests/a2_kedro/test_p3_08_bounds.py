"""P3-08 bounds: record count and transition count, at and above the limit."""

from __future__ import annotations

import pytest

from msgloom.a2_kedro.contracts.header import LIMITS
from msgloom.a2_kedro.semantics import transitions as module
from msgloom.a2_kedro.semantics.transitions import (
    ObservedRecord,
    ScopeObservation,
    ScopeRef,
    StateRecord,
    TransitionSemanticsError,
    derive_transitions,
)
from tests.a2_kedro.helpers import SCOPE, check, entry

STREAM = ScopeRef(intake=SCOPE, scope_kind="stream", scope_id="mail")
LIMIT = 3


def scope() -> ScopeObservation:
    return ScopeObservation(
        scope=STREAM,
        role="content",
        enumeration="complete",
        authority="content-src",
        entry=entry(9),
    )


def digest(number: int) -> str:
    return f"{number:064x}"


def prev(count: int, offset: int = 0) -> tuple[StateRecord, ...]:
    return tuple(
        StateRecord(
            scope=STREAM,
            resource_kind="mail",
            resource_id=f"m{offset + n}",
            fact_id=digest(offset + n + 1),
            content_sha256=digest(0),
        )
        for n in range(count)
    )


def now(count: int, offset: int = 0) -> tuple[ObservedRecord, ...]:
    return tuple(
        ObservedRecord(
            scope=STREAM,
            resource_kind="mail",
            resource_id=f"m{offset + n}",
            fact_id=digest(offset + n + 1),
            content_sha256=digest(0),
            entry=entry(3),
        )
        for n in range(count)
    )


def test_record_bound_accepts_exactly_the_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module, "MAX_RECORDS", LIMIT)
    out = derive_transitions(scope(), (), now(LIMIT))
    check(len(out.transitions) == LIMIT, "observed at the limit")
    out2 = derive_transitions(scope(), prev(LIMIT), now(LIMIT))
    check(out2.transitions == (), "previous and observed at the limit")


def test_record_bound_refuses_observed_above_the_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module, "MAX_RECORDS", LIMIT)
    with pytest.raises(TransitionSemanticsError) as err:
        derive_transitions(scope(), (), now(LIMIT + 1))
    check(err.value.code == "too_many", "observed above the limit")


def test_record_bound_refuses_previous_above_the_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module, "MAX_RECORDS", LIMIT)
    with pytest.raises(TransitionSemanticsError) as err:
        derive_transitions(scope(), prev(LIMIT + 1), ())
    check(err.value.code == "too_many", "previous above the limit")


def test_transition_bound_accepts_exactly_the_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(LIMITS, "max_transitions", LIMIT)
    out = derive_transitions(scope(), (), now(LIMIT))
    check(len(out.transitions) == LIMIT, "presence at the limit")
    gone = derive_transitions(scope(), prev(LIMIT), ())
    check(len(gone.transitions) == LIMIT, "absence at the limit")


def test_transition_bound_refuses_above_the_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(LIMITS, "max_transitions", LIMIT)
    with pytest.raises(TransitionSemanticsError) as err:
        derive_transitions(scope(), (), now(LIMIT + 1))
    check(err.value.code == "too_many", "presence above the limit")
    with pytest.raises(TransitionSemanticsError) as err2:
        derive_transitions(scope(), prev(LIMIT + 1), ())
    check(err2.value.code == "too_many", "absence above the limit")
    # Mixed kinds count together: 2 absences plus 2 presences.
    with pytest.raises(TransitionSemanticsError) as err3:
        derive_transitions(scope(), prev(2), now(2, offset=10))
    check(err3.value.code == "too_many", "mixed kinds above the limit")


def test_production_limits_are_unchanged() -> None:
    check(module.MAX_RECORDS == 65536, "record bound")
    check(LIMITS["max_transitions"] == 1024, "transition bound")
