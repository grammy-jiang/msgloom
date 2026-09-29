"""Cancellation-safe cleanup helpers for claim-owned report work."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Protocol

from msgloom.contracts import ClaimToken, ExternalEffectState, TerminalStatus
from msgloom.persistence import Phase1PersistenceError


class _ClaimFinisher(Protocol):
    async def finish_claim(
        self,
        token: ClaimToken,
        status: TerminalStatus,
        effect: ExternalEffectState,
    ) -> None:
        """Persist terminal claim state."""
        ...


async def finish_quietly(
    persistence: _ClaimFinisher,
    claim: ClaimToken,
    status: TerminalStatus,
) -> None:
    """Drain cleanup despite repeated cancellation without replacing root cause."""
    task = asyncio.create_task(
        persistence.finish_claim(claim, status, ExternalEffectState.NONE)
    )
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            continue
        except (Phase1PersistenceError, ValueError):
            break
    try:
        task.result()
    except (Phase1PersistenceError, ValueError):
        return


async def run_sync_owned[**P, T](
    callback: Callable[P, T], *args: P.args, **kwargs: P.kwargs
) -> T:
    """Drain one synchronous operation off-loop before propagating cancellation."""
    task = asyncio.create_task(asyncio.to_thread(callback, *args, **kwargs))
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
    if cancelled:
        raise asyncio.CancelledError
    if error is not None:
        raise error
    return task.result()
