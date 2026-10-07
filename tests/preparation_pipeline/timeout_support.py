"""Test-only controls for deterministic preparation timeout boundaries."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from types import TracebackType
from typing import Any, Self

import msgloom.preparation_pipeline.handler as handler_module


class _BoundaryArmedTimeout:
    """Arm a real :func:`asyncio.timeout` after the configured boundary."""

    def __init__(self, control: HandlerDeadlineControl, delay: float | None) -> None:
        self._control = control
        self._delay = delay
        self._timeout = asyncio.timeout(None)
        self._watcher: asyncio.Task[None] | None = None

    async def __aenter__(self) -> Self:
        await self._timeout.__aenter__()
        self._control.active_watchers += 1
        self._watcher = asyncio.create_task(self._arm_after_boundary())
        return self

    async def _arm_after_boundary(self) -> None:
        try:
            await self._control.boundary_reached.wait()
            if self._delay is not None:
                deadline = asyncio.get_running_loop().time() + self._delay
                self._timeout.reschedule(deadline)
                self._control.arm_count += 1
        finally:
            self._control.active_watchers -= 1

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        watcher = self._watcher
        if watcher is not None and not watcher.done():
            watcher.cancel()
            try:
                await watcher
            except asyncio.CancelledError:
                pass
        return await self._timeout.__aexit__(exc_type, exc_value, traceback)


class _AsyncioProxy:
    """Delegate :mod:`asyncio` except for the handler timeout constructor."""

    def __init__(self, control: HandlerDeadlineControl) -> None:
        self._control = control

    def __getattr__(self, name: str) -> Any:
        return getattr(asyncio, name)

    def timeout(self, delay: float | None) -> _BoundaryArmedTimeout:
        """Create the boundary-armed :func:`asyncio.timeout`."""
        return _BoundaryArmedTimeout(self._control, delay)


class HandlerDeadlineControl:
    """Scope handler deadline injection to one boundary and restore it."""

    def __init__(self, boundary_reached: asyncio.Event) -> None:
        self.boundary_reached = boundary_reached
        self.active_watchers = 0
        self.arm_count = 0

    @contextmanager
    def installed(self) -> Iterator[None]:
        """Install on the handler module and restore on every exit path."""
        original = handler_module.asyncio
        handler_module.asyncio = _AsyncioProxy(self)
        try:
            yield
        finally:
            handler_module.asyncio = original
