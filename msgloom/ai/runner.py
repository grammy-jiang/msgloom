"""Awaited Phase 1 AI execution boundary."""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any

from msgloom.ai.ipc import (
    IPCFailure,
    TracePersistenceFailure,
    consume_stdout,
    count_stderr,
)
from msgloom.ai.lifecycle import (
    await_accepted,
    await_until,
    cleanup_owned,
    remaining,
)
from msgloom.ai.models import (
    AnalysisAttempt,
    AnalysisResponse,
    AttemptStatus,
    TraceEvent,
    TraceKind,
    TraceSink,
)
from msgloom.ai.policy import RuntimeIsolation, TrustedPolicy
from msgloom.ai.request import build_worker_payload
from msgloom.ai.sandbox import build_sandbox_command, finish_uncancellable


class AIRunner:
    """Run one isolated AI attempt from trusted application policy."""

    def __init__(self, policy: TrustedPolicy, runtime: RuntimeIsolation) -> None:
        self._policy = policy
        self._runtime = runtime

    async def run(
        self,
        attempt: AnalysisAttempt,
        trace_sink: TraceSink,
    ) -> AnalysisResponse:
        """Run one fresh attempt under one elapsed ownership deadline."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + attempt.limits.timeout_seconds
        schema = self._policy.schema_for(attempt.schema_ref)
        model = self._policy.models.get(attempt.model_ref)
        if schema is None or model is None:
            raise ValueError("attempt references untrusted schema or model")
        payload = build_worker_payload(attempt, schema, model, self._runtime.cli_path)
        encoded = json.dumps(
            payload,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
        worker = Path(__file__).with_name("sdk_worker.py")

        storage_task = asyncio.create_task(
            asyncio.to_thread(self._prepare_storage, attempt)
        )
        timed_out, cancelled = await await_accepted(
            storage_task,
            deadline,
        )
        if cancelled:
            raise asyncio.CancelledError
        if timed_out:
            return self._timed_out(attempt, 0)
        state_dir, work_dir = storage_task.result()

        command = build_sandbox_command(
            self._runtime,
            worker,
            state_dir,
            work_dir,
        )
        if remaining(deadline) <= 0:
            return self._timed_out(attempt, 0)
        environment = {
            "HOME": "/state",
            "CLAUDE_CONFIG_DIR": "/state/claude",
            "XDG_CONFIG_HOME": "/state/config",
            "XDG_CACHE_HOME": "/state/cache",
            "TMPDIR": "/tmp",
            "PATH": "/usr/bin:/bin",
            "PYTHONNOUSERSITE": "1",
            **self._runtime.credentials,
        }
        line_limit = (
            max(
                attempt.limits.max_output_bytes,
                attempt.limits.max_trace_event_bytes,
            )
            + 1
        )
        spawn_task = asyncio.create_task(
            asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=environment,
                start_new_session=True,
                limit=line_limit,
            )
        )
        timed_out, cancelled = await await_accepted(spawn_task, deadline)
        if cancelled and spawn_task.exception() is not None:
            raise asyncio.CancelledError
        process = spawn_task.result()
        if cancelled or timed_out:
            cleanup_cancelled = await cleanup_owned(
                process,
                self._runtime.termination_grace_seconds,
                drain_unclaimed_pipes=True,
            )
            if cancelled or cleanup_cancelled:
                raise asyncio.CancelledError
            return self._timed_out(attempt, 0)
        if process.stdin is None or process.stdout is None or process.stderr is None:
            await cleanup_owned(
                process,
                self._runtime.termination_grace_seconds,
                drain_unclaimed_pipes=True,
            )
            raise RuntimeError("AI child pipes were not created")

        stdout_task = asyncio.create_task(
            consume_stdout(process.stdout, attempt, trace_sink, self._persist)
        )
        stderr_task = asyncio.create_task(
            count_stderr(
                process.stderr,
                attempt.limits.max_trace_event_bytes,
            )
        )
        wait_task = asyncio.create_task(process.wait())
        send_task = asyncio.create_task(self._send_input(process.stdin, encoded))
        owned = (send_task, stdout_task, stderr_task, wait_task)

        timed_out, cancelled = await await_until(send_task, deadline)
        if timed_out or cancelled or send_task.exception() is not None:
            cleanup_cancelled = await cleanup_owned(
                process,
                self._runtime.termination_grace_seconds,
                *owned,
                cancel_tasks=(send_task,),
            )
            if cancelled or cleanup_cancelled:
                raise asyncio.CancelledError
            if timed_out:
                count = self._durable_count(stdout_task)
                return await self._timeout_response(attempt, trace_sink, count)
            return await self._failure_with_diagnostic(
                attempt,
                trace_sink,
                self._durable_count(stdout_task),
                "stdin-failure",
                "isolated AI worker input channel failed",
            )

        timed_out, cancelled = await self._await_process_tasks(
            process,
            deadline,
            stdout_task,
            stderr_task,
            wait_task,
        )
        cleanup_cancelled = await cleanup_owned(
            process,
            self._runtime.termination_grace_seconds,
            *owned,
            cancel_tasks=(send_task,),
        )
        timed_out = timed_out or remaining(deadline) <= 0
        if cancelled or cleanup_cancelled:
            raise asyncio.CancelledError

        failure = stdout_task.exception()
        if isinstance(failure, TracePersistenceFailure):
            return self._failed(
                attempt,
                failure.trace_count,
                "trace-persistence-failure",
                "durable AI trace persistence failed",
            )
        if isinstance(failure, IPCFailure):
            return await self._failure_with_diagnostic(
                attempt,
                trace_sink,
                failure.trace_count,
                "ipc-failure",
                "isolated AI worker output was invalid or exceeded bounds",
            )
        if failure is not None:
            return await self._failure_with_diagnostic(
                attempt,
                trace_sink,
                0,
                "worker-stream-failure",
                "isolated AI worker stream failed",
            )

        trace_count, final = stdout_task.result()
        if timed_out:
            return await self._timeout_response(
                attempt,
                trace_sink,
                trace_count,
            )
        if stderr_task.exception() is not None:
            return await self._failure_with_diagnostic(
                attempt,
                trace_sink,
                trace_count,
                "stderr-overflow",
                "isolated AI worker stderr exceeded its bound",
            )
        stderr_bytes = stderr_task.result()
        if stderr_bytes:
            response = await self._diagnostic(
                attempt,
                trace_sink,
                trace_count,
                "child-stderr",
                f"isolated child emitted {stderr_bytes} stderr bytes",
            )
            if isinstance(response, AnalysisResponse):
                return response
            trace_count += int(response)
        if process.returncode != 0 and (final is None or final["ok"] is True):
            return await self._failure_with_diagnostic(
                attempt,
                trace_sink,
                trace_count,
                "worker-exit",
                "isolated AI worker exited unsuccessfully",
            )
        if remaining(deadline) <= 0:
            return await self._timeout_response(attempt, trace_sink, trace_count)
        return self._response(attempt, trace_count, final)

    async def _await_process_tasks(
        self,
        process: asyncio.subprocess.Process,
        deadline: float,
        stdout_task: asyncio.Task[Any],
        stderr_task: asyncio.Task[Any],
        wait_task: asyncio.Task[Any],
    ) -> tuple[bool, bool]:
        pending: set[asyncio.Task[Any]] = {
            stdout_task,
            stderr_task,
            wait_task,
        }
        cancelled = False
        while pending:
            seconds = remaining(deadline)
            if seconds <= 0:
                return True, cancelled
            try:
                done, pending = await asyncio.wait(
                    pending,
                    timeout=min(seconds, 0.05),
                    return_when=asyncio.FIRST_COMPLETED,
                )
            except asyncio.CancelledError:
                return False, True
            if process.returncode is not None:
                return False, cancelled
            if not done:
                continue
            if wait_task in done:
                return False, cancelled
            if stdout_task in done and stdout_task.exception() is not None:
                return False, cancelled
            if stderr_task in done and stderr_task.exception() is not None:
                return False, cancelled
        return False, cancelled

    @staticmethod
    async def _send_input(stream: Any, encoded: bytes) -> None:
        stream.write(encoded)
        await stream.drain()
        stream.close()
        await stream.wait_closed()

    def _prepare_storage(
        self,
        attempt: AnalysisAttempt,
    ) -> tuple[Path, Path]:
        if not self._runtime.storage_root.is_dir():
            raise RuntimeError("AI storage root is unavailable")
        digest = hashlib.sha256(attempt.attempt.value.encode()).hexdigest()
        attempt_dir = self._runtime.storage_root / digest
        attempt_dir.mkdir(mode=0o700)
        state_dir = attempt_dir / "state"
        work_dir = attempt_dir / "work"
        state_dir.mkdir(mode=0o700)
        work_dir.mkdir(mode=0o700)
        return state_dir, work_dir

    async def _persist(self, sink: TraceSink, event: TraceEvent) -> None:
        task = asyncio.create_task(sink.write(event))
        cancelled = await finish_uncancellable(task)
        if cancelled:
            raise asyncio.CancelledError

    async def _diagnostic(
        self,
        attempt: AnalysisAttempt,
        sink: TraceSink,
        count: int,
        code: str,
        detail: str,
    ) -> AnalysisResponse | bool:
        if count >= attempt.limits.max_trace_events:
            return False
        event = TraceEvent(
            attempt.attempt,
            count,
            TraceKind.DIAGNOSTIC,
            code,
            detail,
            {"code": code},
        )
        encoded = json.dumps(
            {
                "kind": event.kind,
                "name": event.name,
                "text": event.text,
                "data": {"code": code},
            },
            separators=(",", ":"),
        ).encode()
        if len(encoded) > attempt.limits.max_trace_event_bytes:
            return False
        try:
            await self._persist(sink, event)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - sink implementation boundary
            return self._failed(
                attempt,
                count,
                "trace-persistence-failure",
                "durable AI trace persistence failed",
            )
        return True

    async def _failure_with_diagnostic(
        self,
        attempt: AnalysisAttempt,
        sink: TraceSink,
        count: int,
        code: str,
        detail: str,
    ) -> AnalysisResponse:
        sink_failure = await self._diagnostic(
            attempt,
            sink,
            count,
            code,
            detail,
        )
        if isinstance(sink_failure, AnalysisResponse):
            return sink_failure
        return self._failed(attempt, count + int(sink_failure), code, detail)

    async def _timeout_response(
        self,
        attempt: AnalysisAttempt,
        sink: TraceSink,
        count: int,
    ) -> AnalysisResponse:
        sink_failure = await self._diagnostic(
            attempt,
            sink,
            count,
            "timeout",
            "isolated AI attempt exceeded its time limit",
        )
        if isinstance(sink_failure, AnalysisResponse):
            return sink_failure
        return self._timed_out(attempt, count + int(sink_failure))

    @staticmethod
    def _durable_count(task: asyncio.Task[Any]) -> int:
        if not task.done():
            return 0
        failure = task.exception()
        if isinstance(failure, (IPCFailure, TracePersistenceFailure)):
            return failure.trace_count
        if failure is None:
            return task.result()[0]
        return 0

    @staticmethod
    def _failed(
        attempt: AnalysisAttempt,
        count: int,
        code: str,
        detail: str,
    ) -> AnalysisResponse:
        return AnalysisResponse(
            attempt.attempt,
            AttemptStatus.FAILED,
            None,
            count,
            code,
            detail,
        )

    @staticmethod
    def _timed_out(attempt: AnalysisAttempt, count: int) -> AnalysisResponse:
        return AnalysisResponse(
            attempt.attempt,
            AttemptStatus.TIMED_OUT,
            None,
            count,
            "timeout",
            "isolated AI attempt exceeded its time limit",
        )

    @staticmethod
    def _response(
        attempt: AnalysisAttempt,
        trace_count: int,
        final: dict[str, Any] | None,
    ) -> AnalysisResponse:
        if final is None:
            return AIRunner._failed(
                attempt,
                trace_count,
                "incomplete-output",
                "AI worker ended without a terminal result",
            )
        if final["ok"] is not True:
            return AIRunner._failed(
                attempt,
                trace_count,
                final["code"],
                "isolated AI worker reported failure",
            )
        return AnalysisResponse(
            attempt.attempt,
            AttemptStatus.COMPLETE,
            final["structured_output"],
            trace_count,
        )
