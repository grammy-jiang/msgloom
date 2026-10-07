"""Real Phase1Persistence lifecycle tests for AI evidence sessions."""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path

import pytest

from msgloom.ai import AnalysisResponse, AttemptStatus, TraceEvent, TraceKind
from msgloom.ai_evidence import (
    DuplicateAttemptError,
    EvidenceSession,
    EvidenceStateError,
    TerminalEvidence,
    TraceEvidence,
)
from msgloom.contracts import AttemptIdentity, ExecutionIdentity, ResultRef
from msgloom.persistence import Phase1Persistence

from .helpers import analysis_attempt, open_store, save_seed, trusted_policy


def _event(attempt: AttemptIdentity, sequence: int) -> TraceEvent:
    return TraceEvent(
        attempt=attempt,
        sequence=sequence,
        kind=TraceKind.DIAGNOSTIC,
        name="synthetic-event",
        text=f"event-{sequence}",
        data={"sequence": sequence},
    )


async def _begin(
    path: Path,
) -> tuple[Phase1Persistence, EvidenceSession, ResultRef]:
    store = await open_store(path)
    seed = await save_seed(store)
    request = analysis_attempt()
    session = await EvidenceSession.begin(
        store,
        ExecutionIdentity("exec-ai-1"),
        request,
        trusted_policy=trusted_policy(request),
        required_inputs=(seed,),
        configuration_version="config-ai-v1",
        code_version="code-ai-v1",
    )
    return store, session, seed


def test_begin_persists_request_before_trace_and_rejects_missing_input(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        store = await open_store(tmp_path / "phase1.sqlite3")
        request = analysis_attempt()
        try:
            with pytest.raises(EvidenceStateError):
                await EvidenceSession.begin(
                    store,
                    ExecutionIdentity("exec-ai-1"),
                    request,
                    trusted_policy=trusted_policy(request),
                    required_inputs=(ResultRef("missing", "seed", "1"),),
                    configuration_version="config-ai-v1",
                    code_version="code-ai-v1",
                )
            seed = await save_seed(store)
            session = await EvidenceSession.begin(
                store,
                ExecutionIdentity("exec-ai-1"),
                request,
                trusted_policy=trusted_policy(request),
                required_inputs=(seed,),
                configuration_version="config-ai-v1",
                code_version="code-ai-v1",
            )
            saved = await store.get_result(session.request_ref.result_id)
            if saved is None or saved.semantic_data_ref is None:
                pytest.fail("begin returned before request evidence was durable")
            await session.trace_sink.write(_event(request.attempt, 0))
            trace = await store.get_result(session.trace_refs[0].result_id)
            if trace is None or trace.input_refs != (session.request_ref,):
                pytest.fail("first trace does not bind exact request lineage")
        finally:
            await store.close()

    asyncio.run(exercise())


def test_order_identity_count_and_duplicate_attempt_are_rejected(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        store, session, seed = await _begin(tmp_path / "phase1.sqlite3")
        request = session.request.request
        try:
            with pytest.raises(EvidenceStateError):
                await session.write({"invalid": "trace"})  # type: ignore[arg-type]
            with pytest.raises(EvidenceStateError):
                await session.finish(object())  # type: ignore[arg-type]
            with pytest.raises(EvidenceStateError):
                await session.write(_event(request.attempt, 1))
            with pytest.raises(EvidenceStateError):
                await session.write(_event(AttemptIdentity("wrong-attempt"), 0))
            await session.write(_event(request.attempt, 0))
            await session.write(_event(request.attempt, 1))
            second = await store.get_result(session.trace_refs[1].result_id)
            expected = (session.request_ref, session.trace_refs[0])
            if second is None or second.input_refs != expected:
                pytest.fail("trace lineage did not retain durable ordered prefix")
            with pytest.raises(EvidenceStateError):
                await session.finish(
                    AnalysisResponse(
                        attempt=request.attempt,
                        status=AttemptStatus.COMPLETE,
                        structured_output={"result": "synthetic"},
                        trace_count=1,
                    )
                )
            with pytest.raises(DuplicateAttemptError):
                await EvidenceSession.begin(
                    store,
                    ExecutionIdentity("exec-ai-1"),
                    request,
                    trusted_policy=trusted_policy(request),
                    required_inputs=(seed,),
                    configuration_version="config-ai-v1",
                    code_version="code-ai-v1",
                )
        finally:
            await store.close()

    asyncio.run(exercise())


def test_exact_request_trace_terminal_replay_after_reopen(tmp_path: Path) -> None:
    async def exercise() -> None:
        path = tmp_path / "phase1.sqlite3"
        store, session, _seed = await _begin(path)
        request = session.request.request
        await session.write(_event(request.attempt, 0))
        response = AnalysisResponse(
            attempt=request.attempt,
            status=AttemptStatus.COMPLETE,
            structured_output={"result": "synthetic"},
            trace_count=1,
        )
        terminal_ref = await session.finish(response)
        request_ref = session.request_ref
        trace_ref = session.trace_refs[0]
        await store.close()

        reopened = await open_store(path)
        try:
            request_result = await reopened.get_result(request_ref.result_id)
            trace_result = await reopened.get_result(trace_ref.result_id)
            terminal_result = await reopened.get_result(terminal_ref.result_id)
            if (
                request_result is None
                or trace_result is None
                or terminal_result is None
                or request_result.semantic_data_ref is None
                or trace_result.semantic_data_ref is None
                or terminal_result.semantic_data_ref is None
            ):
                pytest.fail("durable evidence references were not replayable")
            request_data = await reopened.load_semantic_data(
                request_result.semantic_data_ref
            )
            trace_data = await reopened.load_semantic_data(
                trace_result.semantic_data_ref
            )
            terminal_data = await reopened.load_semantic_data(
                terminal_result.semantic_data_ref
            )
            if request_data != session.request:
                pytest.fail("request evidence changed after reopen")
            if not isinstance(trace_data, TraceEvidence):
                pytest.fail("trace evidence decoded to the wrong type")
            if not isinstance(terminal_data, TerminalEvidence):
                pytest.fail("terminal evidence decoded to the wrong type")
            if terminal_data.trace_refs != (trace_ref,):
                pytest.fail("terminal evidence lost exact ordered trace references")
            if terminal_result.input_refs != (request_ref, trace_ref):
                pytest.fail("terminal stage lineage is not exact")
            with pytest.raises(DuplicateAttemptError):
                await EvidenceSession.begin(
                    reopened,
                    ExecutionIdentity("exec-ai-1"),
                    request,
                    trusted_policy=trusted_policy(request),
                    required_inputs=(ResultRef("seed-result", "seed", "1"),),
                    configuration_version="config-ai-v1",
                    code_version="code-ai-v1",
                )
        finally:
            await reopened.close()

    asyncio.run(exercise())


def test_failed_trace_write_never_advances_evidence_prefix(tmp_path: Path) -> None:
    async def exercise() -> None:
        store, session, _seed = await _begin(tmp_path / "phase1.sqlite3")
        original = store._store.append_result_with_data

        def fail_trace(result: object, value: object) -> None:
            if getattr(result, "kind", None) == "ai_trace":
                raise RuntimeError("synthetic persistence failure")
            original(result, value)  # type: ignore[arg-type]

        store._store.append_result_with_data = fail_trace  # type: ignore[method-assign]
        try:
            with pytest.raises(RuntimeError, match="synthetic persistence failure"):
                await session.write(_event(session.request.request.attempt, 0))
            if session.trace_refs:
                pytest.fail("failed persistence advanced the durable trace prefix")
            if session.terminal_ref is not None:
                pytest.fail("failed persistence reported evidence complete")
        finally:
            store._store.append_result_with_data = original  # type: ignore[method-assign]
            await store.close()

    asyncio.run(exercise())


def test_repeated_cancellation_drains_accepted_trace_write(tmp_path: Path) -> None:
    async def exercise() -> None:
        store, session, _seed = await _begin(tmp_path / "phase1.sqlite3")
        original = store._store.append_result_with_data
        started = threading.Event()
        release = threading.Event()

        def slow_write(result: object, value: object) -> None:
            if getattr(result, "kind", None) == "ai_trace":
                started.set()
                if not release.wait(2):
                    raise RuntimeError("synthetic write barrier timed out")
            original(result, value)  # type: ignore[arg-type]

        store._store.append_result_with_data = slow_write  # type: ignore[method-assign]
        try:
            task = asyncio.create_task(
                session.write(_event(session.request.request.attempt, 0))
            )
            ready = await asyncio.to_thread(started.wait, 2)
            if not ready:
                pytest.fail("trace write did not reach controlled barrier")
            task.cancel()
            await asyncio.sleep(0)
            task.cancel()
            await asyncio.sleep(0)
            if task.done():
                pytest.fail("cancelled trace returned before accepted write drained")
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            if len(session.trace_refs) != 1:
                pytest.fail(
                    "durable cancelled write was not reflected in session state"
                )
            saved = await store.get_result(session.trace_refs[0].result_id)
            if saved is None:
                pytest.fail("accepted trace write was lost under cancellation")
        finally:
            release.set()
            store._store.append_result_with_data = original  # type: ignore[method-assign]
            await store.close()

    asyncio.run(exercise())


def test_failed_and_malformed_transport_remain_non_triage(tmp_path: Path) -> None:
    async def exercise() -> None:
        path = tmp_path / "phase1.sqlite3"
        store, session, _seed = await _begin(path)
        request = session.request.request
        malformed = AnalysisResponse(
            attempt=request.attempt,
            status=AttemptStatus.COMPLETE,
            structured_output=["not", "an", "object"],
            trace_count=0,
        )
        terminal = await session.finish(malformed)
        saved = await store.get_result(terminal.result_id)
        if saved is None or saved.acceptable:
            pytest.fail("malformed transport evidence became dependency-eligible")
        if saved.semantic_data_ref is None:
            pytest.fail("malformed transport evidence was not retained")
        evidence = await store.load_semantic_data(saved.semantic_data_ref)
        if not isinstance(evidence, TerminalEvidence):
            pytest.fail("malformed terminal evidence decoded to the wrong type")
        if evidence.transport_eligible or evidence.triage_semantics_accepted:
            pytest.fail("malformed transport was converted to triage acceptance")
        await store.close()

        store2, session2, _seed2 = await _begin(tmp_path / "phase1-2.sqlite3")
        try:
            diagnostic = await session2.finish_diagnostic(
                cancelled=True,
                failure_code="runner_cancelled",
                failure_detail="synthetic cancellation",
            )
            saved2 = await store2.get_result(diagnostic.result_id)
            if saved2 is None or saved2.acceptable:
                pytest.fail("cancelled runner diagnostic became eligible")
        finally:
            await store2.close()

    asyncio.run(exercise())
