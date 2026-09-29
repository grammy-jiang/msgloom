"""Durability, claim, lineage, and cancellation tests for Phase 1 persistence."""

from __future__ import annotations

import asyncio
import multiprocessing
import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest

from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    Diagnostic,
    ExecutionIdentity,
    ExternalEffectState,
    Failure,
    Limitation,
    ResultRef,
    ResultSchemaRegistry,
    StageResult,
    TerminalStatus,
    VersionRef,
)
from msgloom.persistence import (
    ClaimUnavailableError,
    DependencyNotReadyError,
    ExternalEffectReconciliationRequired,
    ImmutableRecordError,
    Phase1Persistence,
    StaleClaimError,
    UnknownResultSchemaError,
)


def _url(path: Path) -> str:
    return f"sqlite:///{path}"


def _registry() -> ResultSchemaRegistry:
    return ResultSchemaRegistry.phase1().with_schema("fake_result", "1")


def _result(
    result_id: str,
    *,
    kind: str = "prepared",
    schema_version: str = "1",
    status: TerminalStatus = TerminalStatus.COMPLETE,
    acceptable: bool = True,
    inputs: tuple[ResultRef, ...] = (),
) -> StageResult:
    return StageResult(
        result_id=result_id,
        kind=kind,
        schema_version=schema_version,
        execution=ExecutionIdentity(f"execution-{result_id}"),
        attempt=AttemptIdentity(f"attempt-{result_id}"),
        input_refs=inputs,
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
        failures=(Failure("synthetic_failure", "Synthetic failure", retryable=False),),
        status=status,
        acceptable=acceptable,
    )


def test_unknown_result_schema_is_rejected_visibly(tmp_path: Path) -> None:
    async def exercise() -> None:
        persistence = await Phase1Persistence.open(_url(tmp_path / "phase1.sqlite3"))
        try:
            with pytest.raises(UnknownResultSchemaError):
                await persistence.append_result(
                    _result("unknown-kind", kind="unknown", schema_version="9")
                )
            with pytest.raises(UnknownResultSchemaError):
                await persistence.append_result(
                    _result("unknown-version", schema_version="999")
                )
            with pytest.raises(UnknownResultSchemaError):
                await persistence.acquire_claim(
                    "triage:unknown-schema",
                    ClaimKind.TRIAGE,
                    ExecutionIdentity("execution-unknown-schema"),
                    AttemptIdentity("attempt-unknown-schema"),
                    required_inputs=(ResultRef("missing", "unknown", "1"),),
                )
        finally:
            await persistence.close()

    asyncio.run(exercise())


def test_append_only_rerun_lineage_retains_accepted_history(tmp_path: Path) -> None:
    async def exercise() -> None:
        persistence = await Phase1Persistence.open(
            _url(tmp_path / "phase1.sqlite3"), registry=_registry()
        )
        try:
            first = _result("first", kind="fake_result")
            second = _result(
                "second",
                kind="fake_result",
                inputs=(ResultRef(first.result_id, first.kind, first.schema_version),),
            )
            await persistence.append_result(first)
            await persistence.append_result(second)

            loaded_first = await persistence.get_result("first")
            loaded_second = await persistence.get_result("second")
            if loaded_first != first:
                pytest.fail("Accepted historical result changed after rerun")
            if loaded_second != second:
                pytest.fail("Rerun result or lineage was not retained")
            with pytest.raises(ImmutableRecordError):
                await persistence.append_result(
                    replace(first, code_version="different-build")
                )

            fake = _result("fake", kind="fake_result")
            await persistence.append_result(fake)
            if await persistence.get_result("fake") != fake:
                pytest.fail("Registered fake result producer is incompatible")
        finally:
            await persistence.close()

    asyncio.run(exercise())


def test_dependent_claim_requires_durable_acceptable_input(tmp_path: Path) -> None:
    async def exercise() -> None:
        persistence = await Phase1Persistence.open(
            _url(tmp_path / "phase1.sqlite3"), registry=_registry()
        )
        try:
            missing = ResultRef("missing", "prepared", "1")
            with pytest.raises(DependencyNotReadyError):
                await persistence.acquire_claim(
                    "triage:topic-1",
                    ClaimKind.TRIAGE,
                    ExecutionIdentity("execution-triage"),
                    AttemptIdentity("attempt-triage"),
                    required_inputs=(missing,),
                )

            incomplete = _result(
                "incomplete",
                status=TerminalStatus.INCOMPLETE,
                acceptable=False,
            )
            await persistence.append_result(incomplete)
            ref = ResultRef(
                incomplete.result_id, incomplete.kind, incomplete.schema_version
            )
            with pytest.raises(DependencyNotReadyError):
                await persistence.acquire_claim(
                    "triage:topic-1",
                    ClaimKind.TRIAGE,
                    ExecutionIdentity("execution-triage"),
                    AttemptIdentity("attempt-triage"),
                    required_inputs=(ref,),
                )

            acceptable = replace(
                incomplete,
                result_id="acceptable",
                kind="fake_result",
                acceptable=True,
            )
            await persistence.append_result(acceptable)
            acceptable_ref = ResultRef(
                acceptable.result_id, acceptable.kind, acceptable.schema_version
            )
            token = await persistence.acquire_claim(
                "triage:topic-1",
                ClaimKind.TRIAGE,
                ExecutionIdentity("execution-triage"),
                AttemptIdentity("attempt-triage"),
                required_inputs=(acceptable_ref,),
            )
            await persistence.finish_claim(
                token,
                TerminalStatus.COMPLETE,
                ExternalEffectState.NONE,
            )
        finally:
            await persistence.close()

    asyncio.run(exercise())


def _claim_process(database_url: str, gate, results) -> None:
    async def exercise() -> None:
        persistence = await Phase1Persistence.open(database_url)
        try:
            gate.wait()
            try:
                await persistence.acquire_claim(
                    "prepare:source-1",
                    ClaimKind.PREPARE,
                    ExecutionIdentity(
                        f"execution-{multiprocessing.current_process().pid}"
                    ),
                    AttemptIdentity(f"attempt-{multiprocessing.current_process().pid}"),
                    lease_seconds=60,
                )
            except ClaimUnavailableError:
                results.put("blocked")
            else:
                results.put("acquired")
        finally:
            await persistence.close()

    asyncio.run(exercise())


def test_duplicate_claim_is_excluded_across_processes(tmp_path: Path) -> None:
    database_url = _url(tmp_path / "phase1.sqlite3")

    async def initialize() -> None:
        persistence = await Phase1Persistence.open(database_url)
        await persistence.close()

    asyncio.run(initialize())
    context = multiprocessing.get_context("spawn")
    gate = context.Event()
    results = context.Queue()
    processes = [
        context.Process(target=_claim_process, args=(database_url, gate, results))
        for _ in range(2)
    ]
    for process in processes:
        process.start()
    gate.set()
    observed = sorted(results.get(timeout=10) for _ in processes)
    for process in processes:
        process.join(timeout=10)
        if process.exitcode != 0:
            pytest.fail(f"Claim worker exited with {process.exitcode}")
    if observed != ["acquired", "blocked"]:
        pytest.fail(f"Expected one durable claim winner, got {observed!r}")


def test_stale_attempt_cannot_release_newer_claim(tmp_path: Path) -> None:
    async def exercise() -> None:
        persistence = await Phase1Persistence.open(_url(tmp_path / "phase1.sqlite3"))
        try:
            old = await persistence.acquire_claim(
                "prepare:source-1",
                ClaimKind.PREPARE,
                ExecutionIdentity("execution-old"),
                AttemptIdentity("attempt-old"),
                lease_seconds=0,
            )
            new = await persistence.acquire_claim(
                "prepare:source-1",
                ClaimKind.PREPARE,
                ExecutionIdentity("execution-new"),
                AttemptIdentity("attempt-new"),
                lease_seconds=60,
            )
            with pytest.raises(StaleClaimError):
                await persistence.finish_claim(
                    old,
                    TerminalStatus.CANCELLED,
                    ExternalEffectState.NONE,
                )
            with pytest.raises(ClaimUnavailableError):
                await persistence.acquire_claim(
                    "prepare:source-1",
                    ClaimKind.PREPARE,
                    ExecutionIdentity("execution-third"),
                    AttemptIdentity("attempt-third"),
                )
            await persistence.finish_claim(
                new,
                TerminalStatus.COMPLETE,
                ExternalEffectState.NONE,
            )
        finally:
            await persistence.close()

    asyncio.run(exercise())


def test_unknown_external_effect_blocks_blind_retry(tmp_path: Path) -> None:
    async def exercise() -> None:
        persistence = await Phase1Persistence.open(_url(tmp_path / "phase1.sqlite3"))
        try:
            token = await persistence.acquire_claim(
                "submit:report-1",
                ClaimKind.REPORT_SUBMIT,
                ExecutionIdentity("execution-submit"),
                AttemptIdentity("attempt-submit"),
                lease_seconds=60,
            )
            with pytest.raises(ValueError, match="classify"):
                await persistence.finish_claim(
                    token,
                    TerminalStatus.FAILED,
                    ExternalEffectState.NONE,
                )
            await persistence.finish_claim(
                token,
                TerminalStatus.FAILED,
                ExternalEffectState.UNKNOWN,
            )
            with pytest.raises(ExternalEffectReconciliationRequired):
                await persistence.acquire_claim(
                    "submit:report-1",
                    ClaimKind.REPORT_SUBMIT,
                    ExecutionIdentity("execution-retry"),
                    AttemptIdentity("attempt-retry"),
                )
        finally:
            await persistence.close()

    asyncio.run(exercise())


def test_cancellation_waits_for_inflight_write_to_finish(tmp_path: Path) -> None:
    async def exercise() -> None:
        persistence = await Phase1Persistence.open(
            _url(tmp_path / "phase1.sqlite3"), registry=_registry()
        )
        started = threading.Event()
        original = persistence._store.append_result

        def slow_append(result: StageResult) -> None:
            started.set()
            time.sleep(0.15)
            original(result)

        persistence._store.append_result = slow_append  # type: ignore[method-assign]
        result = _result("cancelled-write", kind="fake_result")
        task = asyncio.create_task(persistence.append_result(result))
        await asyncio.to_thread(started.wait, 2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        loaded = await persistence.get_result(result.result_id)
        if loaded != result:
            pytest.fail("Cancellation returned before the durable write drained")
        await persistence.close()

    asyncio.run(exercise())
