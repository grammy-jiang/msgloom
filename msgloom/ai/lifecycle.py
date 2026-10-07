"""Ownership helpers for accepted AI process lifecycle work."""

from __future__ import annotations

import asyncio
from typing import Any

from msgloom.ai.sandbox import finish_uncancellable, terminate_and_reap


def remaining(deadline: float) -> float:
    """Return non-negative time remaining on the original attempt deadline."""
    return max(0.0, deadline - asyncio.get_running_loop().time())


async def await_until(
    task: asyncio.Task[Any],
    deadline: float,
) -> tuple[bool, bool]:
    """Wait for one task until the original deadline or caller cancellation."""
    seconds = remaining(deadline)
    if seconds <= 0:
        return True, False
    try:
        done, _pending = await asyncio.wait({task}, timeout=seconds)
    except asyncio.CancelledError:
        return False, True
    return not bool(done), False


async def await_accepted(
    task: asyncio.Task[Any],
    deadline: float,
) -> tuple[bool, bool]:
    """Drain accepted work even after timeout or repeated cancellation."""
    timed_out, cancelled = await await_until(task, deadline)
    if not task.done():
        try:
            extra_cancelled = await finish_uncancellable(task)
        except Exception:
            if cancelled:
                raise asyncio.CancelledError from None
            raise
        cancelled = cancelled or extra_cancelled
    if task.done() and cancelled and not task.cancelled():
        _ = task.exception()
    return timed_out, cancelled


async def _drain_pipe(stream: Any) -> None:
    """Discard an owned pipe to EOF.

    Child-controlled bytes are never retained.
    """
    while await stream.read(4096):
        pass


async def cleanup_owned(
    process: asyncio.subprocess.Process,
    grace_seconds: float,
    *tasks: asyncio.Task[Any],
    cancel_tasks: tuple[asyncio.Task[Any], ...] = (),
    drain_unclaimed_pipes: bool = False,
) -> bool:
    """Terminate, drain, and reap all work accepted for one child.

    The unclaimed-pipe mode is used before the normal bounded consumers have
    taken ownership. Those discard drains start before termination so a child
    blocked on a full pipe cannot prevent reaping.
    """

    async def cleanup() -> None:
        drains: list[asyncio.Task[Any]] = []
        if drain_unclaimed_pipes:
            if process.stdout is not None:
                drains.append(asyncio.create_task(_drain_pipe(process.stdout)))
            if process.stderr is not None:
                drains.append(asyncio.create_task(_drain_pipe(process.stderr)))
        for task in cancel_tasks:
            if not task.done():
                task.cancel()
        termination = asyncio.create_task(terminate_and_reap(process, grace_seconds))
        await asyncio.gather(termination, *tasks, *drains, return_exceptions=True)
        # Stream failures are classified by the caller. Cleanup itself must
        # succeed before that caller can accept any output.
        termination.result()

    cleanup_task = asyncio.create_task(cleanup())
    return await finish_uncancellable(cleanup_task)
