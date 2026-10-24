"""C0-17c review minors: boundary and fail-closed pins. Synthetic data only."""

from __future__ import annotations

import asyncio

from msgloom.contracts import Limitation, TerminalStatus
from msgloom.triage_input import adapter_v2 as adapter
from msgloom.triage_input.adapter_v2 import (
    LimitationOverflowError,
    UnsupportedVersionError,
    admit_upstream,
    classify_upstream,
)
from tests.a2_kedro.helpers import check
from tests.a2_kedro.test_c0_17c import (
    SECRET,
    family,
    refuses,
    stage,
    v2_handler,
)


def test_v1_style_family_with_unknown_version_fails_closed() -> None:
    # Behavior pin: prepared@3 beside v1 refs is refused at preflight, not
    # treated as v1. Before C0-17c the handler ignored the version.
    versions = ("3", "1", "1")
    refuses(
        lambda: classify_upstream(
            (*family("1")[1:], family("3")[0]),
        ),
        UnsupportedVersionError,
    )
    case = v2_handler(versions=versions)
    outcome = asyncio.run(case.triage.run(case.request))
    check(outcome.status is TerminalStatus.FAILED, "failed, fail closed")
    check(outcome.failures[0].code == "triage_input_invalid", "typed failure")
    check(outcome.failures[0].detail == "UnsupportedVersionError", "class name only")
    check(outcome.result_refs == (), "no result refs")
    check(case.runner.calls == 0, "no provider call")
    check(SECRET not in repr(outcome), "no input value in outcome")


def test_limitation_carry_boundary() -> None:
    prepared = family("2")[0]
    just_fits = tuple(Limitation(f"code_{i:03d}", "x") for i in range(63))
    saved = stage(prepared, status=TerminalStatus.INCOMPLETE, limitations=just_fits)
    hold = admit_upstream([(prepared, saved)])
    check(hold is not None, "63 carried plus the hold marker is allowed")
    check(
        hold is not None and len(hold.limitations) == adapter.MAX_CARRIED_LIMITATIONS,
        "hold has exactly 64 limitations",
    )
    check(
        hold is not None and hold.limitations[-1].code == adapter.HOLD_CODE,
        "hold marker last",
    )
    check(
        hold is not None and set(just_fits) <= set(hold.limitations),
        "all 63 carried",
    )
    too_many = tuple(Limitation(f"code_{i:03d}", "x") for i in range(64))
    heavy = stage(prepared, status=TerminalStatus.INCOMPLETE, limitations=too_many)
    refuses(lambda: admit_upstream([(prepared, heavy)]), LimitationOverflowError)


def test_handler_holds_when_every_v2_upstream_is_complete() -> None:
    case = v2_handler()
    check(
        all(s.status is TerminalStatus.COMPLETE for s in case.saved.values()),
        "all upstream results complete",
    )
    outcome = asyncio.run(case.triage.run(case.request))
    check(outcome.status is TerminalStatus.INCOMPLETE, "held, not complete")
    check(
        outcome.limitations == (Limitation(adapter.HOLD_CODE, adapter.HOLD_DETAIL),),
        "only the hold marker",
    )
    check(outcome.result_refs == () and outcome.failures == (), "no result, no failure")
    check(case.runner.calls == 0, "no provider call")
