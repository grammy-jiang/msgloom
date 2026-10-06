"""Keep integrated preparation proofs on the fixture's controlled clock."""

from __future__ import annotations

import asyncio
import sqlite3
from collections.abc import Coroutine
from pathlib import Path
from typing import Any

import pytest

from msgloom.contracts import OperationOutcome, TerminalStatus
from msgloom.persistence import Phase1Persistence, preparation_proof, store
from msgloom.persistence.records import PREPARATION_PLAN_PROOFS
from msgloom.reporting import ReportBuildHandler
from msgloom.reporting import handler as reporting_handler
from tests.triage_pipeline import test_default_composition as composition
from tests.triage_pipeline.test_deadline_boundaries import (
    DeadlineClock,
    deadline_clock,
    saved_result_kinds,
)


@pytest.mark.parametrize("fault", ["normal", "exception", "cancellation"])
def test_integrated_clock_restores_after_real_composition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    """
    Publish and accept real preparation before reporting and unwinding.

    Missing proof-clock binding rejects the first selection as expired. Each
    exit must restore both wall bindings and the loop clock, including nested
    report-clock scopes. Injected failures retain their identity and cause.
    """
    error = (
        asyncio.CancelledError("integrated cancellation")
        if fault == "cancellation"
        else OSError("integrated exception")
    )
    _compose(tmp_path, monkeypatch, error=None if fault == "normal" else error)
    _accepted_preparation(tmp_path / "composed.db")


@pytest.mark.parametrize("advance_active", [False, True])
def test_integrated_report_timeout_remains_active(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, advance_active: bool
) -> None:
    """
    Keep the real five-second timeout after integrated preparation succeeds.

    Moving the outer clock cannot expire the nested report clock. Moving the
    active report clock six seconds must reject the report while its original
    ten-second lease remains live.
    """
    outcomes = _compose(tmp_path, monkeypatch, advance_active=advance_active)
    _accepted_preparation(tmp_path / "composed.db")
    if len(outcomes) != 1:
        pytest.fail("Actual reporting was not reached exactly once")
    outcome = outcomes[0]
    expected = TerminalStatus.FAILED if advance_active else TerminalStatus.COMPLETE
    failures = ("report_build_timeout",) if advance_active else ()
    if (
        outcome.status is not expected
        or tuple(item.code for item in outcome.failures) != failures
    ):
        pytest.fail(f"Report deadline control changed: {outcome}")
    kinds = saved_result_kinds(tmp_path / "composed.db", "report-execution")
    if ("report" in kinds) == advance_active:
        pytest.fail(f"Report publication crossed the active deadline: {kinds}")


def _accepted_preparation(path: Path) -> None:
    """Require the producer receipt and matching frozen claim history."""
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as connection:
        receipts = connection.execute(
            f"SELECT accepted_status FROM {PREPARATION_PLAN_PROOFS.name}"
        ).fetchall()
        history = connection.execute(
            "SELECT started_at, finished_at, terminal_status "
            "FROM phase1_claim_attempts WHERE execution_id = 'composed-prepare'"
        ).fetchall()
    if receipts != [("complete",)]:
        pytest.fail(f"Preparation has no exact accepted receipt: {receipts}")
    if len(history) != 1 or history[0][2] != "complete":
        pytest.fail(f"Preparation history was not accepted: {history}")
    if any(
        value is None or not value.startswith("2026-10-04T00:00:00")
        for value in history[0][:2]
    ):
        pytest.fail(f"Publication and acceptance clocks diverged: {history}")


def _compose(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    error: BaseException | None = None,
    advance_active: bool | None = None,
) -> list[OperationOutcome]:
    """Run the existing complete producer chain with scoped clock controls."""
    original_run = asyncio.run
    original_report = ReportBuildHandler.run
    original_append = Phase1Persistence.append_result_with_data
    original_wall = store.datetime
    original_proof = preparation_proof.datetime
    original_monotonic = reporting_handler.monotonic
    restored: list[bool] = []
    outcomes: list[OperationOutcome] = []
    cause = RuntimeError("integrated original cause")

    async def report_observed(self, request):
        if self._config.timeout_seconds != 5 or self._config.claim_lease_seconds != 10:
            pytest.fail("The original reporting bounds changed")
        outcome = await original_report(self, request)
        outcomes.append(outcome)
        return outcome

    async def controlled(coroutine: Coroutine[Any, Any, None]) -> None:
        loop = asyncio.get_running_loop()
        original_time = loop.time
        try:
            with monkeypatch.context() as scoped, deadline_clock(scoped) as clock:
                scoped.setattr(reporting_handler, "monotonic", clock.time)

                async def append_observed(self, result, value, **kwargs):
                    await original_append(self, result, value, **kwargs)
                    if result.kind == "report_selection" and advance_active is not None:
                        active = getattr(loop.time, "__self__", None)
                        if not isinstance(active, DeadlineClock):
                            pytest.fail("Active report clock is missing")
                        (active if advance_active else clock).advance(6.0)

                scoped.setattr(
                    Phase1Persistence, "append_result_with_data", append_observed
                )
                await coroutine
                # The inner report scope has exited; its bindings must return
                # to this still-active outer preparation clock.
                if (
                    store.datetime is not clock
                    or preparation_proof.datetime is not clock
                    or loop.time != clock.time
                ):
                    pytest.fail("Nested report scope did not restore the outer clock")
                if error is not None:
                    raise error from cause
        finally:
            restored.append(
                loop.time == original_time
                and store.datetime is original_wall
                and preparation_proof.datetime is original_proof
                and reporting_handler.monotonic is original_monotonic
            )

    with monkeypatch.context() as scoped:
        scoped.setattr(
            asyncio, "run", lambda coroutine: original_run(controlled(coroutine))
        )
        scoped.setattr(ReportBuildHandler, "run", report_observed)
        target = composition.test_default_prepare_triage_report_chain_survives_restart
        if error is not None:
            with pytest.raises(type(error)) as caught:
                target(tmp_path, scoped)
            if caught.value is not error or caught.value.__cause__ is not cause:
                pytest.fail("Clock cleanup replaced the injected failure")
        elif advance_active:
            with pytest.raises(pytest.fail.Exception) as caught:
                target(tmp_path, scoped)
            if len(outcomes) != 1 or str(caught.value) != (
                "Default reporting did not consume actual A3 output: "
                + str(outcomes[0])
            ):
                pytest.fail("An unrelated fixture failure hid the timeout control")
        else:
            target(tmp_path, scoped)
    if restored != [True]:
        pytest.fail(f"Clock bindings leaked after the composition: {restored}")
    if (
        asyncio.run is not original_run
        or ReportBuildHandler.run is not original_report
        or Phase1Persistence.append_result_with_data is not original_append
    ):
        pytest.fail("Composition observers leaked after the test")
    return outcomes
