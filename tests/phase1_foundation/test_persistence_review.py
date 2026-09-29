"""Review regressions for Phase 1 persistence ownership and history."""

from __future__ import annotations

import asyncio
import sqlite3
import threading
from dataclasses import replace
from pathlib import Path

import pytest

import msgloom.persistence.async_store as async_store_module
from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    Diagnostic,
    ExecutionIdentity,
    ExternalEffectState,
    Failure,
    Limitation,
    ResultSchemaRegistry,
    StageResult,
    TerminalStatus,
    VersionRef,
)
from msgloom.persistence import (
    ImmutableRecordError,
    Phase1Persistence,
    StaleClaimError,
    UnknownResultSchemaError,
)


def _url(path: Path) -> str:
    return f"sqlite:///{path}"


def _registry() -> ResultSchemaRegistry:
    return ResultSchemaRegistry.phase1().with_schema("fake_result", "1")


def _result(result_id: str, *, kind: str = "prepared") -> StageResult:
    return StageResult(
        result_id=result_id,
        kind=kind,
        schema_version="1",
        execution=ExecutionIdentity(f"execution-{result_id}"),
        attempt=AttemptIdentity(f"attempt-{result_id}"),
        input_refs=(),
        source_versions=(VersionRef("source", "source-1", "v1"),),
        prepared_versions=(VersionRef("prepared", "prepared-1", "v1"),),
        topic_versions=(VersionRef("topic", "topic-1", "v1"),),
        configuration_version="config-v1",
        code_version="build-v1",
        rule_version="rules-v1",
        prompt_version="prompt-v1",
        model_identifier="synthetic-model",
        working_context_version=VersionRef("context", "context-1", "v1"),
        exposed_output_ref=VersionRef("diagnostic", f"output-{result_id}", "v1"),
        exposed_diagnostics=(Diagnostic("synthetic", "Synthetic diagnostic"),),
        limitations=(Limitation("synthetic_gap", "Synthetic limitation"),),
        failures=(Failure("synthetic_failure", "Synthetic failure"),),
        status=TerminalStatus.COMPLETE,
        acceptable=True,
    )


def test_result_schema_is_validated_again_when_read_after_reopen(
    tmp_path: Path,
) -> None:
    path = tmp_path / "phase1.sqlite3"

    async def write_extended_result() -> None:
        persistence = await Phase1Persistence.open(_url(path), registry=_registry())
        try:
            await persistence.append_result(_result("extended", kind="fake_result"))
        finally:
            await persistence.close()

    async def read_with_base_registry() -> None:
        persistence = await Phase1Persistence.open(_url(path))
        try:
            with pytest.raises(UnknownResultSchemaError):
                await persistence.get_result("extended")
        finally:
            await persistence.close()

    asyncio.run(write_extended_result())
    asyncio.run(read_with_base_registry())


def test_terminal_claim_history_is_immutable_and_identical_replay_is_idempotent(
    tmp_path: Path,
) -> None:
    path = tmp_path / "phase1.sqlite3"

    async def exercise() -> None:
        persistence = await Phase1Persistence.open(_url(path))
        try:
            token = await persistence.acquire_claim(
                "submit:immutable-history",
                ClaimKind.REPORT_SUBMIT,
                ExecutionIdentity("execution-history"),
                AttemptIdentity("attempt-history"),
                lease_seconds=60,
            )
            await persistence.finish_claim(
                token,
                TerminalStatus.FAILED,
                ExternalEffectState.UNKNOWN,
            )
            connection = sqlite3.connect(path)
            try:
                first_finished = connection.execute(
                    "SELECT finished_at FROM phase1_claim_attempts "
                    "WHERE claim_token = ?",
                    (token.token,),
                ).fetchone()
            finally:
                connection.close()
            await asyncio.sleep(0.01)
            await persistence.finish_claim(
                token,
                TerminalStatus.FAILED,
                ExternalEffectState.UNKNOWN,
            )
            connection = sqlite3.connect(path)
            try:
                replay_finished = connection.execute(
                    "SELECT finished_at FROM phase1_claim_attempts "
                    "WHERE claim_token = ?",
                    (token.token,),
                ).fetchone()
            finally:
                connection.close()
            if replay_finished != first_finished:
                pytest.fail("Identical finish replay rewrote terminal history")
            with pytest.raises(ImmutableRecordError):
                await persistence.finish_claim(
                    token,
                    TerminalStatus.CANCELLED,
                    ExternalEffectState.UNKNOWN,
                )
            with pytest.raises(ImmutableRecordError):
                await persistence.mark_external_effect(
                    token,
                    ExternalEffectState.CONFIRMED,
                )
        finally:
            await persistence.close()

    asyncio.run(exercise())


@pytest.mark.parametrize("field", ["kind", "execution", "attempt"])
def test_claim_token_metadata_must_match_current_owner(
    tmp_path: Path,
    field: str,
) -> None:
    async def exercise() -> None:
        persistence = await Phase1Persistence.open(_url(tmp_path / "phase1.sqlite3"))
        try:
            token = await persistence.acquire_claim(
                "submit:token-metadata",
                ClaimKind.REPORT_SUBMIT,
                ExecutionIdentity("execution-owner"),
                AttemptIdentity("attempt-owner"),
            )
            replacements = {
                "kind": {"kind": ClaimKind.PREPARE},
                "execution": {"execution": ExecutionIdentity("execution-forged")},
                "attempt": {"attempt": AttemptIdentity("attempt-forged")},
            }
            forged = replace(token, **replacements[field])
            with pytest.raises(StaleClaimError):
                await persistence.mark_external_effect(
                    forged,
                    ExternalEffectState.PENDING,
                )
            with pytest.raises(StaleClaimError):
                await persistence.finish_claim(
                    forged,
                    TerminalStatus.FAILED,
                    ExternalEffectState.UNKNOWN,
                )
            await persistence.finish_claim(
                token,
                TerminalStatus.FAILED,
                ExternalEffectState.UNKNOWN,
            )
        finally:
            await persistence.close()

    asyncio.run(exercise())


def test_cancelled_open_disposes_constructed_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started = threading.Event()
    release = threading.Event()
    stores: list[object] = []

    class SlowStore:
        def __init__(
            self,
            database_url: str,
            registry: ResultSchemaRegistry,
        ) -> None:
            del database_url, registry
            self.closed = False
            stores.append(self)
            started.set()
            release.wait(timeout=2)

        def close(self) -> None:
            self.closed = True

    monkeypatch.setattr(async_store_module, "Phase1Store", SlowStore)

    async def exercise() -> None:
        task = asyncio.create_task(
            Phase1Persistence.open(_url(tmp_path / "phase1.sqlite3"))
        )
        await asyncio.to_thread(started.wait, 2)
        task.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        if len(stores) != 1:
            pytest.fail("Slow constructor did not create exactly one store")
        store = stores[0]
        if not getattr(store, "closed", False):
            pytest.fail("Cancelled open discarded a live constructed store")

    asyncio.run(exercise())


def test_close_rejects_new_calls_and_drains_all_accepted_work(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        persistence = await Phase1Persistence.open(
            _url(tmp_path / "phase1.sqlite3"),
            max_concurrent_threads=2,
        )
        started = threading.Event()
        release = threading.Event()
        active = 0
        active_lock = threading.Lock()
        disposed_while_active = False
        original_close = persistence._store.close

        def slow_get(result_id: str) -> None:
            del result_id
            nonlocal active
            with active_lock:
                active += 1
            started.set()
            release.wait(timeout=2)
            with active_lock:
                active -= 1

        def recording_close() -> None:
            nonlocal disposed_while_active
            with active_lock:
                disposed_while_active = active > 0
            original_close()

        persistence._store.get_result = slow_get  # type: ignore[method-assign]
        persistence._store.close = recording_close  # type: ignore[method-assign]
        accepted = asyncio.create_task(persistence.get_result("accepted"))
        await asyncio.to_thread(started.wait, 2)
        closing = asyncio.create_task(persistence.close())
        await asyncio.sleep(0)
        with pytest.raises(RuntimeError, match="clos"):
            await persistence.get_result("rejected")
        if closing.done():
            pytest.fail("Close completed while accepted work was still active")
        release.set()
        await accepted
        await closing
        if disposed_while_active:
            pytest.fail("Engine was disposed while accepted work was active")

    asyncio.run(exercise())


def test_queued_call_accepted_before_close_drains_but_later_call_is_rejected(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        persistence = await Phase1Persistence.open(
            _url(tmp_path / "phase1.sqlite3"),
            max_concurrent_threads=1,
        )
        first_started = threading.Event()
        release_first = threading.Event()
        calls: list[str] = []

        def queued_get(result_id: str) -> None:
            calls.append(result_id)
            if result_id == "first":
                first_started.set()
                release_first.wait(timeout=2)

        persistence._store.get_result = queued_get  # type: ignore[method-assign]
        first = asyncio.create_task(persistence.get_result("first"))
        await asyncio.to_thread(first_started.wait, 2)
        second = asyncio.create_task(persistence.get_result("second"))
        await asyncio.sleep(0)
        closing = asyncio.create_task(persistence.close())
        await asyncio.sleep(0)
        with pytest.raises(RuntimeError, match="clos"):
            await persistence.get_result("late")
        release_first.set()
        await first
        await second
        await closing
        if calls != ["first", "second"]:
            pytest.fail(f"Accepted/late call boundary was wrong: {calls!r}")

    asyncio.run(exercise())


def test_repeated_cancellation_of_close_still_disposes_once(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        persistence = await Phase1Persistence.open(_url(tmp_path / "phase1.sqlite3"))
        started = threading.Event()
        release = threading.Event()
        close_count = 0
        original_close = persistence._store.close

        def slow_close() -> None:
            nonlocal close_count
            close_count += 1
            started.set()
            release.wait(timeout=2)
            original_close()

        persistence._store.close = slow_close  # type: ignore[method-assign]
        task = asyncio.create_task(persistence.close())
        await asyncio.to_thread(started.wait, 2)
        task.cancel()
        task.cancel()
        await asyncio.sleep(0)
        if task.done():
            pytest.fail("Cancelled close returned before engine disposal drained")
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        await persistence.close()
        if close_count != 1:
            pytest.fail(f"Persistence disposed {close_count} times")

    asyncio.run(exercise())
