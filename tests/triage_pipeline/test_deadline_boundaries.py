"""Separate semantic deadlines from lease loss with real persistence."""

from __future__ import annotations

import asyncio
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta, tzinfo
from pathlib import Path

import pytest

from msgloom.ai import AnalysisResponse, AttemptStatus
from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ExecutionIdentity,
    OperationRequest,
    PhaseCapability,
    TerminalStatus,
)
from msgloom.persistence import preparation_proof
from msgloom.persistence import store as persistence_store
from msgloom.persistence.records import STAGE_RESULTS
from msgloom.triage_pipeline import TriageHandler
from tests.triage_pipeline.helpers import open_store, save_selection, setup


class DeadlineClock:
    """Advance loop and lease clocks at explicit contract boundaries."""

    def __init__(self, monotonic: float) -> None:
        self.monotonic = monotonic
        self.elapsed = 0.0
        self.epoch = datetime(2026, 10, 4, tzinfo=UTC)

    def time(self) -> float:
        """Return the controlled time used by real asyncio deadlines."""
        return self.monotonic + self.elapsed

    def now(self, zone: tzinfo | None = None) -> datetime:
        """Return the matching wall time used by real claim transactions."""
        value = self.epoch + timedelta(seconds=self.elapsed)
        return value.astimezone(zone)

    def advance(self, seconds: float) -> None:
        """Move both clocks independently of CPU or SQLite scheduling."""
        self.elapsed += seconds


@contextmanager
def deadline_clock(monkeypatch: pytest.MonkeyPatch) -> Iterator[DeadlineClock]:
    """
    Control elapsed time while retaining real timeout and persistence code.

    Host scheduling can exhaust a 40 ms lease while an accepted write drains.
    Freeze only the clocks, then cross the tested boundary explicitly. Restore
    the loop clock before loop shutdown; no timeout or lease value is enlarged.

    The fixture owns both independent wall-clock bindings on the finite
    preparation path: claim writes in ``store`` and publication/acceptance
    fences in ``preparation_proof``. Nested scopes restore the outer bindings;
    exception and cancellation exits restore them before loop shutdown.
    Intake finalization is not exercised here and keeps its own clock.
    """
    loop = asyncio.get_running_loop()
    clock = DeadlineClock(loop.time())
    with monkeypatch.context() as scoped:
        scoped.setattr(loop, "time", clock.time)
        scoped.setattr(persistence_store, "datetime", clock)
        scoped.setattr(preparation_proof, "datetime", clock)
        yield clock


class DeadlineRunner:
    """Return a valid COMPLETE candidate at a selected boundary."""

    def __init__(self, clock: DeadlineClock, candidate, elapsed: float) -> None:
        self.clock = clock
        self.candidate = candidate
        self.elapsed = elapsed
        self.calls = 0

    async def run(self, attempt, trace_sink):
        """Cross the boundary before timeout callbacks can preempt us."""
        self.calls += 1
        self.clock.advance(self.elapsed)
        return AnalysisResponse(
            attempt=attempt.attempt,
            status=AttemptStatus.COMPLETE,
            structured_output=self.candidate.model_dump(mode="json"),
            trace_count=0,
        )


def saved_result_kinds(path: Path, execution: str) -> tuple[str, ...]:
    """Inspect durable publications, including unreturned result refs."""
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            f"SELECT kind FROM {STAGE_RESULTS.name} WHERE execution_id = ?",
            (execution,),
        ).fetchall()
        return tuple(row[0] for row in rows)
    finally:
        connection.close()


@pytest.mark.parametrize(
    ("boundary", "status", "limitation", "calls"),
    [
        ("on_time", TerminalStatus.COMPLETE, None, 1),
        ("attempt", TerminalStatus.INCOMPLETE, "triage_part_incomplete", 1),
        (
            "request_persisted",
            TerminalStatus.INCOMPLETE,
            "triage_operation_deadline",
            0,
        ),
        ("publication_expired", TerminalStatus.FAILED, None, 0),
        ("finish_expired", TerminalStatus.FAILED, None, 1),
        ("finish_superseded", TerminalStatus.FAILED, None, 1),
    ],
)
def test_deadline_boundary(tmp_path, monkeypatch, boundary, status, limitation, calls):
    """Fence late work and preserve exact terminal and durable ownership."""
    asyncio.run(_boundary(tmp_path, monkeypatch, boundary, status, limitation, calls))


async def _boundary(tmp_path, monkeypatch, boundary, status, limitation, calls):
    path = tmp_path / "boundary.sqlite"
    store = await open_store(path)
    try:
        selected, producer, candidate = setup()
        await save_selection(store, selected)
        producer = replace(
            producer,
            attempt_limits=replace(producer.attempt_limits, timeout_seconds=0.01),
            lease_seconds=0.04,
            operation_timeout_seconds=0.03,
            cleanup_margin_seconds=0.005,
        )
        execution = ExecutionIdentity(f"boundary-{boundary}")
        request = OperationRequest(
            execution=execution,
            caller="synthetic-app",
            capability=PhaseCapability.TRIAGE,
            target_inputs=producer.plan.expected_targets,
            authority_ref="synthetic-authority",
            parameters=producer.expected_parameters,
        )
        replacement = None
        with deadline_clock(monkeypatch) as clock:
            elapsed = {"on_time": 0.005, "attempt": 0.011}.get(boundary, 0.026)
            runner = DeadlineRunner(clock, candidate, elapsed)
            append = store.append_result_with_data
            finish = store.finish_claim

            async def append_at_boundary(result, value, **kwargs):
                if boundary == "publication_expired" and result.kind == "triage_rules":
                    clock.advance(0.04)
                await append(result, value, **kwargs)
                if boundary == "request_persisted" and result.kind == "ai_request":
                    clock.advance(0.026)

            async def finish_at_boundary(claim, terminal, effect):
                nonlocal replacement
                if boundary in {"finish_expired", "finish_superseded"}:
                    clock.advance(0.04)
                if boundary == "finish_superseded":
                    replacement = await store.acquire_claim(
                        claim.claim_key,
                        ClaimKind.TRIAGE,
                        ExecutionIdentity("replacement-exec"),
                        AttemptIdentity("replacement-attempt"),
                        lease_seconds=0.04,
                    )
                await finish(claim, terminal, effect)

            with monkeypatch.context() as scoped:
                scoped.setattr(store, "append_result_with_data", append_at_boundary)
                scoped.setattr(store, "finish_claim", finish_at_boundary)
                outcome = await TriageHandler(store, producer, runner).run(request)
            inspection = await store.inspect_claim(producer.claim_key)

        if outcome.status is not status or runner.calls != calls:
            pytest.fail(
                f"{boundary}: unexpected outcome/calls: {outcome}, {runner.calls}"
            )
        if tuple(item.code for item in outcome.limitations) != (
            () if limitation is None else (limitation,)
        ):
            pytest.fail(f"{boundary}: unexpected deadline limitations: {outcome}")
        expected_failures = (
            ("stale_triage_claim",) if status is TerminalStatus.FAILED else ()
        )
        if tuple(item.code for item in outcome.failures) != expected_failures:
            pytest.fail(f"{boundary}: unexpected failures: {outcome}")
        kinds = saved_result_kinds(path, execution.value)
        if ("triage" in kinds) != (status is TerminalStatus.COMPLETE):
            pytest.fail(f"{boundary}: unexpected durable triage publication: {kinds}")
        if boundary == "publication_expired" and kinds:
            pytest.fail(f"expired publication committed result data: {kinds}")
        if boundary == "request_persisted" and "ai_request" not in kinds:
            pytest.fail("post-persistence deadline was not reached after a real write")
        own_attempts = tuple(
            item for item in inspection.attempts if item.token.execution == execution
        )
        if len(own_attempts) != 1:
            pytest.fail(f"missing exact durable claim history: {inspection}")
        own = own_attempts[0]
        if boundary == "finish_superseded":
            if replacement is None or inspection.current_token != replacement:
                pytest.fail("stale finisher replaced or released the new owner")
            if own.terminal_status is not TerminalStatus.INCOMPLETE:
                pytest.fail("supersession did not retain incomplete prior history")
        elif status is TerminalStatus.FAILED:
            if inspection.current_token != own.token or own.finished_at is not None:
                pytest.fail("expired owner was incorrectly terminalized or released")
            if inspection.expires_at is None or inspection.expires_at > clock.now(UTC):
                pytest.fail("stale rejection did not exercise an expired durable claim")
        elif (
            inspection.current_token is not None
            or own.terminal_status is not status
            or own.finished_at is None
        ):
            pytest.fail(f"live owner did not finish durably: {inspection}")
    finally:
        await store.close()
