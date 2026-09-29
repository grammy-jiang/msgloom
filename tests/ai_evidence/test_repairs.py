"""Regression tests for reviewed AI evidence admission and serialization."""

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


def test_atomic_begin_has_one_winner_across_one_and_two_facades(
    tmp_path: Path,
) -> None:
    async def race(path: Path, *, two_facades: bool) -> None:
        first = await open_store(path)
        seed = await save_seed(first)
        second = await open_store(path) if two_facades else first
        request = analysis_attempt()
        stores = (first, second)
        originals = tuple(store.append_result_with_data for store in stores)
        ready = asyncio.Event()
        arrived = 0

        def wrapper(original: object):
            async def gated(
                result: object,
                value: object,
                *,
                require_new: bool = False,
            ) -> None:
                nonlocal arrived
                if getattr(result, "kind", None) == "ai_request":
                    arrived += 1
                    if arrived == 2:
                        ready.set()
                    await ready.wait()
                await original(  # type: ignore[operator]
                    result,
                    value,
                    require_new=require_new,
                )

            return gated

        first.append_result_with_data = wrapper(originals[0])  # type: ignore[method-assign]
        second.append_result_with_data = wrapper(originals[1])  # type: ignore[method-assign]

        async def begin(store: Phase1Persistence) -> EvidenceSession:
            return await EvidenceSession.begin(
                store,
                ExecutionIdentity("exec-ai-race"),
                request,
                trusted_policy=trusted_policy(request),
                required_inputs=(seed,),
                configuration_version="config-ai-v1",
                code_version="code-ai-v1",
            )

        try:
            outcomes = await asyncio.gather(
                begin(first),
                begin(second),
                return_exceptions=True,
            )
            winners = [item for item in outcomes if isinstance(item, EvidenceSession)]
            duplicates = [
                item for item in outcomes if isinstance(item, DuplicateAttemptError)
            ]
            if len(winners) != 1 or len(duplicates) != 1:
                pytest.fail("atomic request admission did not select one winner")
        finally:
            first.append_result_with_data = originals[0]  # type: ignore[method-assign]
            second.append_result_with_data = originals[1]  # type: ignore[method-assign]
            if second is not first:
                await second.close()
            await first.close()

        reopened = await open_store(path)
        try:
            with pytest.raises(DuplicateAttemptError):
                await begin(reopened)
        finally:
            await reopened.close()

    async def exercise() -> None:
        await race(tmp_path / "one-facade.sqlite3", two_facades=False)
        await race(tmp_path / "two-facades.sqlite3", two_facades=True)

    asyncio.run(exercise())


def test_strict_result_with_data_duplicate_rolls_back_new_payload(
    tmp_path: Path,
) -> None:
    from dataclasses import replace

    from msgloom.persistence.errors import (
        DependencyNotReadyError,
        DuplicateResultError,
    )

    async def exercise() -> None:
        store, session, _seed = await _begin(tmp_path / "phase1.sqlite3")
        try:
            saved = await store.get_result(session.request_ref.result_id)
            if saved is None:
                pytest.fail("request result was not saved")
            reference = store.semantic_reference(
                "rolled-back-data",
                "ai_request",
                "1",
                session.request,
            )
            conflicting = replace(saved, semantic_data_ref=reference)
            with pytest.raises(DuplicateResultError):
                await store.append_result_with_data(
                    conflicting,
                    session.request,
                    require_new=True,
                )
            with pytest.raises(DependencyNotReadyError):
                await store.load_semantic_data(reference)
        finally:
            await store.close()

    asyncio.run(exercise())


def test_concurrent_trace_and_finish_serialize_on_durable_prefix(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        store, session, _seed = await _begin(tmp_path / "phase1.sqlite3")
        original = store.append_result_with_data
        trace_entered = asyncio.Event()
        release_trace = asyncio.Event()

        async def gated(
            result: object,
            value: object,
            *,
            require_new: bool = False,
        ) -> None:
            if getattr(result, "kind", None) == "ai_trace":
                trace_entered.set()
                await release_trace.wait()
            await original(result, value, require_new=require_new)  # type: ignore[arg-type]

        store.append_result_with_data = gated  # type: ignore[method-assign]
        request = session.request.request
        second_started = asyncio.Event()
        finish_started = asyncio.Event()

        async def duplicate_write() -> None:
            second_started.set()
            await session.write(_event(request.attempt, 0))

        async def finish() -> ResultRef:
            finish_started.set()
            return await session.finish(
                AnalysisResponse(
                    attempt=request.attempt,
                    status=AttemptStatus.COMPLETE,
                    structured_output={"result": "synthetic"},
                    trace_count=1,
                )
            )

        try:
            first = asyncio.create_task(session.write(_event(request.attempt, 0)))
            await trace_entered.wait()
            second = asyncio.create_task(duplicate_write())
            terminal = asyncio.create_task(finish())
            await second_started.wait()
            await finish_started.wait()
            release_trace.set()
            await first
            with pytest.raises(EvidenceStateError):
                await second
            terminal_ref = await terminal
            if session.trace_refs != (
                ResultRef("ai-trace:attempt-ai-1:0", "ai_trace", "1"),
            ):
                pytest.fail("serialized trace prefix is not exact and unique")
            saved = await store.get_result(terminal_ref.result_id)
            if saved is None or saved.input_refs != (
                session.request_ref,
                session.trace_refs[0],
            ):
                pytest.fail("terminal transition overtook accepted trace persistence")
        finally:
            release_trace.set()
            store.append_result_with_data = original  # type: ignore[method-assign]
            await store.close()

    asyncio.run(exercise())


def test_cancelled_trace_drains_before_waiting_finish_transition(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        store, session, _seed = await _begin(tmp_path / "phase1.sqlite3")
        original = store._store.append_result_with_data
        started = threading.Event()
        release = threading.Event()

        def slow_write(result: object, value: object, **kwargs: object) -> None:
            if getattr(result, "kind", None) == "ai_trace":
                started.set()
                if not release.wait(2):
                    raise RuntimeError("synthetic write barrier timed out")
            original(result, value, **kwargs)  # type: ignore[arg-type]

        store._store.append_result_with_data = slow_write  # type: ignore[method-assign]
        request = session.request.request
        try:
            trace_task = asyncio.create_task(session.write(_event(request.attempt, 0)))
            if not await asyncio.to_thread(started.wait, 2):
                pytest.fail("trace write did not reach controlled barrier")
            trace_task.cancel()
            trace_task.cancel()
            finish_started = asyncio.Event()

            async def finish() -> ResultRef:
                finish_started.set()
                return await session.finish(
                    AnalysisResponse(
                        attempt=request.attempt,
                        status=AttemptStatus.COMPLETE,
                        structured_output={"result": "synthetic"},
                        trace_count=1,
                    )
                )

            terminal_task = asyncio.create_task(finish())
            await finish_started.wait()
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await trace_task
            terminal_ref = await terminal_task
            if len(session.trace_refs) != 1 or session.terminal_ref != terminal_ref:
                pytest.fail("waiting finish did not observe drained cancelled trace")
        finally:
            release.set()
            store._store.append_result_with_data = original  # type: ignore[method-assign]
            await store.close()

    asyncio.run(exercise())


def test_terminal_response_and_diagnostic_cannot_race_overwrite(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        store, session, _seed = await _begin(tmp_path / "phase1.sqlite3")
        original = store.append_result_with_data
        terminal_entered = asyncio.Event()
        release_terminal = asyncio.Event()

        async def gated(
            result: object,
            value: object,
            *,
            require_new: bool = False,
        ) -> None:
            if getattr(result, "kind", None) == "ai_response":
                terminal_entered.set()
                await release_terminal.wait()
            await original(result, value, require_new=require_new)  # type: ignore[arg-type]

        store.append_result_with_data = gated  # type: ignore[method-assign]
        request = session.request.request
        try:
            response_task = asyncio.create_task(
                session.finish(
                    AnalysisResponse(
                        attempt=request.attempt,
                        status=AttemptStatus.COMPLETE,
                        structured_output={"result": "synthetic"},
                        trace_count=0,
                    )
                )
            )
            await terminal_entered.wait()
            diagnostic_task = asyncio.create_task(
                session.finish_diagnostic(
                    cancelled=False,
                    failure_code="synthetic",
                    failure_detail="synthetic",
                )
            )
            release_terminal.set()
            terminal_ref = await response_task
            with pytest.raises(EvidenceStateError):
                await diagnostic_task
            if session.terminal_ref != terminal_ref:
                pytest.fail("diagnostic transition overwrote terminal response")
        finally:
            release_terminal.set()
            store.append_result_with_data = original  # type: ignore[method-assign]
            await store.close()

    asyncio.run(exercise())


def test_session_enforces_declared_trace_and_terminal_byte_budgets(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        store = await open_store(tmp_path / "phase1.sqlite3")
        seed = await save_seed(store)
        request = analysis_attempt(
            max_trace_event_bytes=128,
            max_output_bytes=192,
        )
        session = await EvidenceSession.begin(
            store,
            ExecutionIdentity("exec-ai-budget"),
            request,
            trusted_policy=trusted_policy(request),
            required_inputs=(seed,),
            configuration_version="config-ai-v1",
            code_version="code-ai-v1",
        )
        try:
            oversized_event = TraceEvent(
                attempt=request.attempt,
                sequence=0,
                kind=TraceKind.DIAGNOSTIC,
                name="synthetic",
                text="x" * 512,
                data={},
            )
            with pytest.raises(EvidenceStateError):
                await session.write(oversized_event)
            if session.trace_refs:
                pytest.fail("oversized trace advanced session state")

            oversized_response = AnalysisResponse(
                attempt=request.attempt,
                status=AttemptStatus.COMPLETE,
                structured_output={"result": "x" * 512},
                trace_count=0,
            )
            with pytest.raises(EvidenceStateError):
                await session.finish(oversized_response)
            if session.terminal_ref is not None:
                pytest.fail("oversized terminal response advanced session state")
        finally:
            await store.close()

    asyncio.run(exercise())


def test_persistence_semantic_then_ai_codec_import_composes_in_isolation() -> None:
    import subprocess
    import sys

    root = Path(__file__).parents[2]
    script = (
        "from msgloom.persistence.semantic import SemanticDataRegistry;"
        "from msgloom.ai_evidence.codecs import AI_EVIDENCE_CODECS;"
        "SemanticDataRegistry(AI_EVIDENCE_CODECS)"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if completed.returncode != 0:
        pytest.fail("isolated semantic/evidence registry composition failed")


def test_session_enforces_fixed_trace_and_terminal_codec_ceilings(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        store = await open_store(tmp_path / "phase1.sqlite3")
        seed = await save_seed(store)
        request = analysis_attempt(
            max_trace_event_bytes=2 * 1024 * 1024,
            max_output_bytes=5 * 1024 * 1024,
        )
        session = await EvidenceSession.begin(
            store,
            ExecutionIdentity("exec-ai-fixed-budget"),
            request,
            trusted_policy=trusted_policy(request),
            required_inputs=(seed,),
            configuration_version="config-ai-v1",
            code_version="code-ai-v1",
        )
        try:
            event = TraceEvent(
                attempt=request.attempt,
                sequence=0,
                kind=TraceKind.DIAGNOSTIC,
                name="synthetic",
                text="x" * (1024 * 1024),
                data={},
            )
            with pytest.raises(EvidenceStateError):
                await session.write(event)
            if session.trace_refs:
                pytest.fail("fixed trace ceiling advanced session state")

            response = AnalysisResponse(
                attempt=request.attempt,
                status=AttemptStatus.COMPLETE,
                structured_output={"result": "x" * (4 * 1024 * 1024)},
                trace_count=0,
            )
            with pytest.raises(EvidenceStateError):
                await session.finish(response)
            if session.terminal_ref is not None:
                pytest.fail("fixed terminal ceiling advanced session state")
        finally:
            await store.close()

    asyncio.run(exercise())
