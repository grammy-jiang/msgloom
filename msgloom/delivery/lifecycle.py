"""Cancellation-safe helpers for finite delivery-owned work."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from functools import partial


async def run_cpu[T](operation: Callable[..., T], *args: object) -> T:
    """
    Run CPU-heavy work off the caller loop and drain it on cancellation.

    Python thread work cannot be force-stopped safely. Shielding the owned task
    ensures a deadline or caller cancellation is not returned while MIME or
    canonical validation is still mutating delivery-owned state.
    """
    task = asyncio.create_task(asyncio.to_thread(partial(operation, *args)))
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
    if cancelled:
        raise asyncio.CancelledError
    if task.cancelled():
        raise asyncio.CancelledError
    error = task.exception()
    if error is not None:
        raise error
    return task.result()


async def cancel_and_drain(task: asyncio.Task[object]) -> None:
    """
    Cancel one owned async task and wait through repeated caller cancellation.

    Cleanup failures are intentionally consumed here so the original
    cancellation remains authoritative.
    """
    if not task.done():
        task.cancel()
    while not task.done():
        try:
            await asyncio.wait((task,), return_when=asyncio.ALL_COMPLETED)
        except asyncio.CancelledError:
            continue
    if not task.cancelled():
        task.exception()
