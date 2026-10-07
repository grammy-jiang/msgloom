"""Drain accepted parser lifecycle work without losing caller cancellation."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable


async def await_owned[T](awaitable: Awaitable[T]) -> T:
    """Await owned work and preserve cancellation through a late worker error.

    Accepted file or process work must finish before ownership returns to the
    caller. Retrieve a late worker exception, but keep caller cancellation as
    the outcome when cancellation arrived first.
    """
    task = asyncio.ensure_future(awaitable)
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
        except Exception:  # noqa: BLE001 - retrieve the owned failure below
            break
    if task.cancelled():
        raise asyncio.CancelledError
    error = task.exception()
    if cancelled:
        raise asyncio.CancelledError
    if error is not None:
        raise error
    return task.result()
