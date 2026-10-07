"""Finite awaited REPORT_SUBMIT operation handler."""

from __future__ import annotations

import asyncio

from msgloom.contracts import (
    ExternalEffectState,
    Failure,
    OperationOutcome,
    OperationRequest,
    PhaseCapability,
    ResultRef,
    TerminalStatus,
)
from msgloom.persistence import Phase1Persistence, Phase1PersistenceError
from msgloom.reporting import ReportCodec, SavedReport

from .history_recovery import recover_existing_history
from .lifecycle import cancel_and_drain, run_cpu
from .mime import validate_owner_address
from .models import ReportSubmissionPlan, SubmissionHandlerConfig
from .part import DeliveryProgress, PartSubmitter
from .transport import ReportTransport


class ReportSubmissionHandler:
    """Submit exact saved report parts under durable per-part effect claims."""

    def __init__(
        self,
        *,
        plan: ReportSubmissionPlan,
        config: SubmissionHandlerConfig,
        persistence: Phase1Persistence,
        transport: ReportTransport,
    ) -> None:
        self._plan = ReportSubmissionPlan.model_validate_json(
            plan.model_dump_json(warnings="error"), strict=True
        )
        self._config = SubmissionHandlerConfig.model_validate_json(
            config.model_dump_json(warnings="error"), strict=True
        )
        validate_owner_address(self._plan.destination_identity)
        self._persistence = persistence
        self._parts = PartSubmitter(
            plan=self._plan,
            config=self._config,
            persistence=persistence,
            transport=transport,
        )

    async def run(self, request: OperationRequest) -> OperationOutcome:
        """Run one finite submission and drain owned cleanup before cancellation."""
        mismatch = self._request_mismatch(request)
        if mismatch is not None:
            return self._failed(request, "request_binding_invalid", mismatch)
        progress = DeliveryProgress()
        task = asyncio.create_task(self._run_budgeted(request, progress))
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            await cancel_and_drain(task)
            raise

    async def _run_budgeted(
        self, request: OperationRequest, progress: DeliveryProgress
    ) -> OperationOutcome:
        try:
            async with asyncio.timeout(self._config.timeout_seconds):
                return await self._execute(request, progress)
        except TimeoutError:
            return self._outcome(request, progress, force_incomplete=True)
        except (Phase1PersistenceError, RuntimeError, TypeError, ValueError):
            if progress.refs or progress.effects:
                return self._outcome(request, progress, force_incomplete=True)
            return self._failed(
                request,
                "report_submission_invalid",
                "Saved report failed delivery validation",
            )

    async def _execute(
        self, request: OperationRequest, progress: DeliveryProgress
    ) -> OperationOutcome:
        report = await self._load_report()
        for part_plan in self._plan.parts:
            existing = await self._parts.existing_effect(part_plan)
            if existing is not None:
                progress.effects.append(existing)
                if existing in {
                    ExternalEffectState.ACCEPTED,
                    ExternalEffectState.CONFIRMED,
                }:
                    await recover_existing_history(
                        self._persistence,
                        self._config,
                        request,
                        report,
                        part_plan,
                        existing,
                    )
                    continue
                break
            await self._parts.submit(request, report, part_plan, progress)
            if progress.effects[-1] is ExternalEffectState.UNKNOWN:
                break
        return self._outcome(request, progress)

    async def _load_report(self) -> SavedReport:
        result = await self._persistence.get_result(
            self._plan.report_result_ref.result_id
        )
        if (
            result is None
            or ResultRef(result.result_id, result.kind, result.schema_version)
            != self._plan.report_result_ref
            or not result.acceptable
            or result.semantic_data_ref is None
        ):
            raise ValueError("saved report result is not accepted")
        value = await self._persistence.load_semantic_data(result.semantic_data_ref)
        if not isinstance(value, SavedReport):
            raise TypeError("saved report semantic type is invalid")
        await run_cpu(ReportCodec().encode, value)
        if (
            value.report_ref != self._plan.report_ref
            or value.policy_ref != self._plan.policy_ref
            or value.destination.owner_identity != self._plan.owner_identity
            or value.destination.destination_identity != self._plan.destination_identity
            or len(value.parts) != len(self._plan.parts)
        ):
            raise ValueError("saved report does not match trusted submission plan")
        return value

    def _request_mismatch(self, request: OperationRequest) -> str | None:
        if request.capability is not PhaseCapability.REPORT_SUBMIT:
            return "Request capability is not REPORT_SUBMIT"
        if request.target_inputs != (self._plan.report_ref, self._plan.policy_ref):
            return "Request target references do not match the trusted plan"
        if request.parameters != self._plan.expected_parameters:
            return "Request parameters do not match the trusted plan"
        return None

    def _outcome(
        self,
        request: OperationRequest,
        progress: DeliveryProgress,
        *,
        force_incomplete: bool = False,
    ) -> OperationOutcome:
        effects = tuple(progress.effects)
        if not effects:
            return self._failed(
                request, "report_submission_failed", "No report part was submitted"
            )
        all_accepted = len(effects) == len(self._plan.parts) and all(
            effect
            in {
                ExternalEffectState.ACCEPTED,
                ExternalEffectState.CONFIRMED,
            }
            for effect in effects
        )
        complete = all_accepted and not force_incomplete and not progress.incomplete
        if any(effect is ExternalEffectState.UNKNOWN for effect in effects):
            aggregate = ExternalEffectState.UNKNOWN
        elif all_accepted and all(
            effect is ExternalEffectState.CONFIRMED for effect in effects
        ):
            aggregate = ExternalEffectState.CONFIRMED
        elif any(
            effect
            in {
                ExternalEffectState.ACCEPTED,
                ExternalEffectState.CONFIRMED,
            }
            for effect in effects
        ):
            aggregate = ExternalEffectState.ACCEPTED
        elif all(effect is ExternalEffectState.NOT_STARTED for effect in effects):
            aggregate = ExternalEffectState.NOT_STARTED
        else:
            aggregate = ExternalEffectState.REJECTED
        return OperationOutcome(
            execution=request.execution,
            capability=request.capability,
            status=TerminalStatus.COMPLETE if complete else TerminalStatus.INCOMPLETE,
            result_refs=tuple(progress.refs),
            failures=(
                ()
                if complete
                else (
                    Failure(
                        "report_submission_incomplete",
                        "Report submission is partial, rejected, or uncertain",
                        retryable=aggregate is ExternalEffectState.REJECTED,
                    ),
                )
            ),
            external_effect=aggregate,
        )

    @staticmethod
    def _failed(request: OperationRequest, code: str, detail: str) -> OperationOutcome:
        return OperationOutcome(
            execution=request.execution,
            capability=request.capability,
            status=TerminalStatus.FAILED,
            failures=(Failure(code, detail, retryable=False),),
            external_effect=ExternalEffectState.NOT_STARTED,
        )
