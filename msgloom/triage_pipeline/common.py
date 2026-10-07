"""Small shared helpers for claim-owned A3 publications."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from contextvars import ContextVar
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any

from msgloom.contracts import ResultRef, StageResult, VersionRef


@dataclass(slots=True)
class RunState:
    """Per-invocation deadline, durable prefix, and exact prepared lineage."""

    acceptance_deadline: float
    result_refs: list[ResultRef] = field(default_factory=list)
    prepared_versions: tuple[VersionRef, ...] = ()


RUN_STATE: ContextVar[RunState | None] = ContextVar("triage_run_state", default=None)


def stable_id(prefix: str, *values: str) -> str:
    """Return a deterministic opaque identity from meaning-bearing versions."""
    digest = sha256("\x1f".join(values).encode()).hexdigest()
    return f"{prefix}:{digest}"


def result_ref(result: StageResult) -> ResultRef:
    """Return the exact public reference for a saved stage result."""
    return ResultRef(result.result_id, result.kind, result.schema_version)


def record_result(reference: ResultRef) -> ResultRef:
    """Append one successfully durable result to the current exact prefix."""
    state = RUN_STATE.get()
    if state is not None and reference not in state.result_refs:
        state.result_refs.append(reference)
    return reference


def durable_prefix() -> tuple[ResultRef, ...]:
    """Return the exact successfully published prefix for this invocation."""
    state = RUN_STATE.get()
    return () if state is None else tuple(state.result_refs)


def ensure_acceptance_time() -> float:
    """Return remaining semantic acceptance time or raise timeout."""
    state = RUN_STATE.get()
    if state is None:
        raise RuntimeError("triage run state is not bound")
    remaining = state.acceptance_deadline - asyncio.get_running_loop().time()
    if remaining <= 0:
        raise TimeoutError("triage acceptance deadline expired")
    return remaining


async def cpu_bound[T](operation: Callable[..., T], *args: Any) -> T:
    """
    Run owned pure work off-loop and drain it before propagating cancellation.
    """
    result, cancelled = await drain(asyncio.to_thread(operation, *args))
    if cancelled:
        raise asyncio.CancelledError
    return result


async def drain[T](awaitable: Coroutine[object, object, T]) -> tuple[T, bool]:
    """Drain one accepted async action through repeated cancellation."""
    task = asyncio.create_task(awaitable)
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
        except Exception:  # noqa: BLE001
            break
    if task.cancelled():
        raise asyncio.CancelledError
    error = task.exception()
    if cancelled and error is not None:
        raise asyncio.CancelledError
    if error is not None:
        raise error
    return task.result(), cancelled
