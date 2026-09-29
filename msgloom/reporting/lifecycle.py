"""Cancellation-safe cleanup helpers for claim-owned report work."""

from __future__ import annotations

import asyncio
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
    try:
        task.result()
    except (Phase1PersistenceError, ValueError):
        return
