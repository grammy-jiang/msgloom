"""Explicit async Application boundary for Phase 1 operations."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from msgloom.contracts import (
    ExternalEffectState,
    Failure,
    Limitation,
    OperationHandler,
    OperationOutcome,
    OperationRequest,
    OutcomePersistence,
    PhaseCapability,
    TerminalStatus,
    TrustedAdmission,
)

HandlerFactory = Callable[[], OperationHandler]
_BLOCKED_LATER = frozenset(
    {
        PhaseCapability.INVESTIGATE,
        PhaseCapability.PROPOSE_ACTION,
        PhaseCapability.EXECUTE_ACTION,
    }
)


class Application:
    """Admit and await one finite operation without owning an event loop."""

    def __init__(
        self,
        outcomes: OutcomePersistence,
        *,
        trusted_admissions: tuple[TrustedAdmission, ...] = (),
        prepare_factory: HandlerFactory | None = None,
        triage_factory: HandlerFactory | None = None,
        report_build_factory: HandlerFactory | None = None,
        report_submit_factory: HandlerFactory | None = None,
    ) -> None:
        self._outcomes = outcomes
        # Empty trusted configuration deliberately denies every enabled
        # capability. The future CLI resolves trusted config/approval state and
        # supplies exact bindings; OperationRequest strings never grant access.
        self._trusted_admissions = trusted_admissions
        self._prepare_factory = prepare_factory
        self._triage_factory = triage_factory
        self._report_build_factory = report_build_factory
        self._report_submit_factory = report_submit_factory

    async def run(self, request: OperationRequest) -> OperationOutcome:
        """Admit, await, save, and return one terminal operation outcome."""
        if request.capability in _BLOCKED_LATER:
            return await self._save(self._blocked(request, "capability_not_in_phase1"))

        if not any(item.admits(request) for item in self._trusted_admissions):
            return await self._save(self._blocked(request, "authority_not_trusted"))

        factory = self._factory(request.capability)
        if factory is None:
            return await self._save(self._blocked(request, "capability_not_configured"))

        try:
            handler = factory()
            outcome = await handler.run(request)
            mismatch = self._outcome_mismatch(request, outcome)
            if mismatch is not None:
                outcome = self._failed(request, mismatch)
        except asyncio.CancelledError:
            cancelled = OperationOutcome(
                execution=request.execution,
                capability=request.capability,
                status=TerminalStatus.CANCELLED,
                limitations=(
                    Limitation(
                        "caller_cancelled", "The caller cancelled the operation"
                    ),
                ),
                external_effect=self._failure_effect(request.capability),
            )
            try:
                await self._save(cancelled)
            except asyncio.CancelledError:
                # Repeated cancellation is remembered by _save only after the
                # persistence task has reached a terminal state.
                pass
            raise
        except Exception as error:  # noqa: BLE001
            outcome = self._failed(
                request,
                f"Operation failed with {type(error).__name__}",
            )

        return await self._save(outcome)

    def _factory(self, capability: PhaseCapability) -> HandlerFactory | None:
        if capability is PhaseCapability.PREPARE:
            return self._prepare_factory
        if capability is PhaseCapability.TRIAGE:
            return self._triage_factory
        if capability is PhaseCapability.REPORT_BUILD:
            return self._report_build_factory
        if capability is PhaseCapability.REPORT_SUBMIT:
            return self._report_submit_factory
        return None

    @staticmethod
    def _outcome_mismatch(
        request: OperationRequest, outcome: OperationOutcome
    ) -> str | None:
        if outcome.execution != request.execution:
            return "Operation handler returned a different execution identity"
        if outcome.capability is not request.capability:
            return "Operation handler returned a different capability"
        return None

    @classmethod
    def _failed(cls, request: OperationRequest, detail: str) -> OperationOutcome:
        return OperationOutcome(
            execution=request.execution,
            capability=request.capability,
            status=TerminalStatus.FAILED,
            failures=(Failure("operation_failed", detail),),
            external_effect=cls._failure_effect(request.capability),
        )

    @staticmethod
    def _failure_effect(capability: PhaseCapability) -> ExternalEffectState:
        if capability is PhaseCapability.REPORT_SUBMIT:
            return ExternalEffectState.UNKNOWN
        return ExternalEffectState.NONE

    @staticmethod
    def _blocked(request: OperationRequest, code: str) -> OperationOutcome:
        return OperationOutcome(
            execution=request.execution,
            capability=request.capability,
            status=TerminalStatus.BLOCKED,
            limitations=(
                Limitation(
                    code, "Requested capability is unavailable in this composition"
                ),
            ),
            external_effect=ExternalEffectState.NONE,
        )

    async def _save(self, outcome: OperationOutcome) -> OperationOutcome:
        """
        Persist a terminal outcome to completion despite caller cancellation.

        Shielding alone is insufficient because repeated cancellation can make
        the caller return while the shielded save is still running. This method
        drains the save task before propagating any cancellation it observed.
        """
        task = asyncio.create_task(self._outcomes.save_outcome(outcome))
        cancelled = False
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                cancelled = True
        if task.cancelled():
            raise RuntimeError("terminal outcome persistence was cancelled")
        error = task.exception()
        if error is not None:
            raise error
        if cancelled:
            raise asyncio.CancelledError
        return outcome
