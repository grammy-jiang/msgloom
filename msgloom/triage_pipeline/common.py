"""Small shared helpers for claim-owned A3 publications."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from hashlib import sha256

from msgloom.contracts import ResultRef, StageResult


def stable_id(prefix: str, *values: str) -> str:
    """Return a deterministic opaque identity from meaning-bearing versions."""
    digest = sha256("\x1f".join(values).encode()).hexdigest()
    return f"{prefix}:{digest}"


def result_ref(result: StageResult) -> ResultRef:
    """Return the exact public reference for a saved stage result."""
    return ResultRef(result.result_id, result.kind, result.schema_version)


async def drain[T](awaitable: Coroutine[object, object, T]) -> tuple[T, bool]:
    """Drain one accepted async action through repeated cancellation."""
    task = asyncio.create_task(awaitable)
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
    if task.cancelled():
        raise asyncio.CancelledError
    error = task.exception()
    if error is not None:
        raise error
    return task.result(), cancelled
