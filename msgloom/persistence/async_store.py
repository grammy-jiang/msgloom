"""Awaited async facade over the proven synchronous SQLAlchemy boundary."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from functools import partial

from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ClaimToken,
    ExecutionIdentity,
    ExternalEffectState,
    OperationOutcome,
    ResultRef,
    ResultSchemaRegistry,
    SemanticDataRef,
    StageResult,
    TerminalStatus,
)
from msgloom.persistence.reconciliation import (
    ClaimInspection,
    ReconciliationRequest,
    ReconciliationResult,
)
from msgloom.persistence.semantic import SemanticDataRegistry
from msgloom.persistence.store import Phase1Store
from msgloom.preparation_pipeline.intake_models import (
    IndexedHeldIntakeEntry,
    IntakeAnchor,
    IntakeScope,
    IntakeWorksetState,
    PreparationIntakeWorkset,
)


class Phase1Persistence:
    """Await bounded SQLite work without nesting an event loop."""

    def __init__(self, store: Phase1Store, *, max_concurrent_threads: int = 1) -> None:
        if max_concurrent_threads < 1:
            raise ValueError("max_concurrent_threads must be positive")
        self._store = store
        self._slots = asyncio.Semaphore(max_concurrent_threads)
        self._active_calls = 0
        self._idle = asyncio.Event()
        self._idle.set()
        self._closing = False
        self._closed = False
        self._close_done = asyncio.Event()
        self._close_task: asyncio.Task[None] | None = None

    @classmethod
    async def open(
        cls,
        database_url: str,
        *,
        registry: ResultSchemaRegistry | None = None,
        semantic_registry: SemanticDataRegistry | None = None,
        max_concurrent_threads: int = 1,
    ) -> Phase1Persistence:
        """Open the neutral schema without leaking on cancellation."""
        if max_concurrent_threads < 1:
            raise ValueError("max_concurrent_threads must be positive")
        selected = registry or ResultSchemaRegistry.phase1()
        constructed: list[Phase1Store] = []

        def construct() -> Phase1Store:
            if semantic_registry is None:
                store = Phase1Store(database_url, selected)
            else:
                store = Phase1Store(database_url, selected, semantic_registry)
            constructed.append(store)
            return store

        try:
            store = await _drain_thread(construct)
        except asyncio.CancelledError:
            if constructed:
                try:
                    await _drain_thread(constructed[0].close)
                except asyncio.CancelledError:
                    pass
            raise
        return cls(store, max_concurrent_threads=max_concurrent_threads)

    async def append_result(
        self, result: StageResult, *, claim: ClaimToken | None = None
    ) -> None:
        """Await an append-only result write, optionally fenced by a claim."""
        if claim is None:
            await self._call(self._store.append_result, result)
            return
        operation = partial(self._store.append_result, result, claim=claim)
        await self._call(operation)

    def semantic_reference(
        self,
        data_id: str,
        kind: str,
        schema_version: str,
        value: object,
    ) -> SemanticDataRef:
        """Build a validated semantic-data integrity reference without I/O."""
        return self._store.semantic_reference(data_id, kind, schema_version, value)

    async def append_result_with_data(
        self,
        result: StageResult,
        value: object,
        *,
        require_new: bool = False,
        claim: ClaimToken | None = None,
    ) -> None:
        """Atomically persist a result/data pair with optional claim fences."""
        if claim is None and not require_new:
            await self._call(self._store.append_result_with_data, result, value)
            return
        keywords: dict[str, object] = {}
        if require_new:
            keywords["require_new"] = True
        if claim is not None:
            keywords["claim"] = claim
        operation = partial(
            self._store.append_result_with_data,
            result,
            value,
            **keywords,
        )
        await self._call(operation)

    async def load_semantic_data(self, reference: SemanticDataRef) -> object:
        """Load semantic data through its exact integrity reference."""
        return await self._call(self._store.load_semantic_data, reference)

    async def get_result(self, result_id: str) -> StageResult | None:
        """Await an exact stage-result read."""
        return await self._call(self._store.get_result, result_id)

    async def save_outcome(self, outcome: OperationOutcome) -> None:
        """Await durable storage of one immutable Application outcome."""
        await self._call(self._store.save_outcome, outcome)

    async def get_outcome(
        self, execution: ExecutionIdentity
    ) -> OperationOutcome | None:
        """Await one saved terminal Application outcome."""
        return await self._call(self._store.get_outcome, execution)

    async def acquire_claim(
        self,
        claim_key: str,
        kind: ClaimKind,
        execution: ExecutionIdentity,
        attempt: AttemptIdentity,
        *,
        required_inputs: tuple[ResultRef, ...] = (),
        lease_seconds: float = 300.0,
    ) -> ClaimToken:
        """Atomically acquire a durable claim after validating saved inputs."""
        return await self._call(
            self._store.acquire_claim,
            claim_key,
            kind,
            execution,
            attempt,
            required_inputs,
            lease_seconds,
        )

    async def mark_external_effect(
        self, token: ClaimToken, effect: ExternalEffectState
    ) -> None:
        """Save effect state before a caller changes retry policy."""
        await self._call(self._store.mark_external_effect, token, effect)

    async def finish_claim(
        self,
        token: ClaimToken,
        status: TerminalStatus,
        effect: ExternalEffectState,
        *,
        accepted_preparation_results: tuple[ResultRef, ...] | None = None,
    ) -> None:
        """Drain terminal history and optional exact preparation acceptance."""
        if accepted_preparation_results is None:
            await self._call(self._store.finish_claim, token, status, effect)
            return
        operation = partial(
            self._store.finish_claim,
            token,
            status,
            effect,
            accepted_preparation_results=accepted_preparation_results,
        )
        await self._call(operation)

    async def reconcile_external_effect(
        self, request: ReconciliationRequest
    ) -> ReconciliationResult:
        """Await atomic reconciliation proof and retry-gate persistence."""
        return await self._call(self._store.reconcile_external_effect, request)

    async def inspect_claim(
        self, claim_key: str, *, history_limit: int = 100
    ) -> ClaimInspection:
        """Await bounded restart inspection without exposing private SQL."""
        operation = partial(
            self._store.inspect_claim, claim_key, history_limit=history_limit
        )
        return await self._call(operation)

    async def get_preparation_intake_cursor(self, scope: IntakeScope) -> IntakeAnchor:
        """Await the stable consumer cursor read."""
        return await self._call(self._store.get_preparation_intake_cursor, scope)

    async def finalize_preparation_intake(
        self,
        result: StageResult,
        workset: PreparationIntakeWorkset,
        *,
        claim: ClaimToken,
    ) -> None:
        """
        Drain atomic workset/pending/cursor finalization before cancellation.
        """
        await self._call(
            partial(
                self._store.finalize_preparation_intake,
                result,
                workset,
                claim=claim,
            )
        )

    async def list_preparation_intake_worksets(
        self,
        scope: IntakeScope,
        *,
        limit: int = 100,
        after_seq: int = 0,
        pending_only: bool = True,
    ) -> tuple[IntakeWorksetState, ...]:
        """
        Await bounded pending discovery independent of source cursor progress.
        """
        return await self._call(
            partial(
                self._store.list_preparation_intake_worksets,
                scope,
                limit=limit,
                after_seq=after_seq,
                pending_only=pending_only,
            )
        )

    async def select_preparation_intake_worksets(
        self,
        scope: IntakeScope,
        *,
        limit: int = 100,
    ) -> tuple[IntakeWorksetState, ...]:
        """Drain durable discovery rotation before cancellation can escape."""
        return await self._call(
            partial(
                self._store.select_preparation_intake_worksets,
                scope,
                limit=limit,
            )
        )

    async def list_preparation_intake_held_entries(
        self,
        scope: IntakeScope,
        *,
        limit: int = 100,
        after_seq: int = 0,
    ) -> tuple[IndexedHeldIntakeEntry, ...]:
        """Await bounded operator/replay lookup of held admissions."""
        return await self._call(
            partial(
                self._store.list_preparation_intake_held_entries,
                scope,
                limit=limit,
                after_seq=after_seq,
            )
        )

    async def finalize_preparation_intake_workset(
        self,
        result_id: str,
        status: TerminalStatus,
        result_refs: tuple[ResultRef, ...],
        *,
        claim: ClaimToken,
    ) -> None:
        """
        Drain the claim-fenced terminal update without hiding pending work.
        """
        await self._call(
            partial(
                self._store.finalize_preparation_intake_workset,
                result_id,
                status,
                result_refs,
                claim=claim,
            )
        )

    async def close(self) -> None:
        """
        Reject new calls, drain every accepted call, and dispose exactly once.

        Calls become accepted before waiting for a worker slot. Marking the
        facade closing creates a deterministic boundary: earlier queued calls
        drain, while later calls fail without touching the store.
        """
        if self._closed:
            return
        if self._closing:
            cancelled = await _wait_event(self._close_done)
            close_task = self._close_task
            if close_task is None:
                raise RuntimeError("persistence close did not start disposal")
            if close_task.cancelled():
                raise RuntimeError("persistence disposal task was cancelled")
            error = close_task.exception()
            if error is not None:
                raise error
            if cancelled:
                raise asyncio.CancelledError
            return

        self._closing = True
        cancelled = await _wait_event(self._idle)
        close_task = asyncio.create_task(asyncio.to_thread(self._store.close))
        self._close_task = close_task
        try:
            _result, close_cancelled = await _await_task_uninterrupted(close_task)
            cancelled = cancelled or close_cancelled
        finally:
            self._closed = (
                close_task.done()
                and not close_task.cancelled()
                and close_task.exception() is None
            )
            self._close_done.set()

        if cancelled:
            raise asyncio.CancelledError

    async def _call[T](self, operation: Callable[..., T], *args: object) -> T:
        if self._closing or self._closed:
            raise RuntimeError("Phase 1 persistence is closing or closed")

        self._active_calls += 1
        self._idle.clear()
        try:
            async with self._slots:
                return await _drain_thread(operation, *args)
        finally:
            self._active_calls -= 1
            if self._active_calls == 0:
                self._idle.set()


async def _wait_event(event: asyncio.Event) -> bool:
    """Wait for an event to become set and report observed cancellation."""
    task = asyncio.create_task(event.wait())
    _result, cancelled = await _await_task_uninterrupted(task)
    return cancelled


async def _await_task_uninterrupted[T](
    task: asyncio.Task[T],
) -> tuple[T, bool]:
    """Drain one owned task and return whether the caller was cancelled."""
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


async def _drain_thread[T](operation: Callable[..., T], *args: object) -> T:
    """
    Await a thread call to physical completion even after caller cancellation.

    A running to_thread SQLite transaction cannot be force-stopped. Delaying
    cancellation until it drains prevents later claim release or close from
    racing a write that can still commit.
    """
    task = asyncio.create_task(asyncio.to_thread(partial(operation, *args)))
    result, cancelled = await _await_task_uninterrupted(task)
    if cancelled:
        raise asyncio.CancelledError
    return result
