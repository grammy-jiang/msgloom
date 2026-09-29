"""Finite awaited REPORT_SUBMIT operation handler."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from hashlib import sha256
from time import monotonic

from msgloom.contracts import (
    ClaimKind,
    ClaimToken,
    ExternalEffectState,
    Failure,
    OperationOutcome,
    OperationRequest,
    PhaseCapability,
    ResultRef,
    StageResult,
    TerminalStatus,
    VersionRef,
)
from msgloom.persistence import Phase1Persistence, Phase1PersistenceError
from msgloom.reporting import ReportCodec, SavedReport

from .mime import build_mime, validate_owner_address
from .models import (
    ReportSubmissionPlan,
    SubmissionAttempt,
    SubmissionHandlerConfig,
    SubmissionPartPlan,
    SubmissionReceipt,
)
from .records import load_attempt, persist_history, require_replay_binding
from .transport import ReportTransport, TransportReceipt


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
        self._transport = transport

    async def run(self, request: OperationRequest) -> OperationOutcome:
        """Validate saved report, then submit each part within one total budget."""
        mismatch = self._request_mismatch(request)
        if mismatch is not None:
            return self._failed(request, "request_binding_invalid", mismatch)
        deadline = monotonic() + self._config.timeout_seconds
        try:
            report = await self._load_report()
        except (Phase1PersistenceError, TypeError, ValueError):
            return self._failed(
                request,
                "report_submission_invalid",
                "Saved report failed delivery validation",
            )

        receipt_refs: list[ResultRef] = []
        effects: list[ExternalEffectState] = []
        try:
            for part_plan in self._plan.parts:
                self._check_deadline(deadline)
                existing = await self._existing_effect(part_plan.part_number)
                if existing is not None:
                    effects.append(existing)
                    if existing is ExternalEffectState.UNKNOWN:
                        break
                    continue
                receipt_ref, effect = await self._submit_part(
                    request, report, part_plan, deadline
                )
                effects.append(effect)
                if receipt_ref is not None:
                    receipt_refs.append(receipt_ref)
                if effect is ExternalEffectState.UNKNOWN:
                    break
        except asyncio.CancelledError:
            raise
        except TimeoutError:
            effects.append(ExternalEffectState.NOT_STARTED)
        except Phase1PersistenceError:
            effects.append(ExternalEffectState.UNKNOWN)
        except (RuntimeError, TypeError, ValueError):
            effects.append(ExternalEffectState.UNKNOWN)

        return self._outcome(request, tuple(receipt_refs), tuple(effects))

    async def _existing_effect(self, part_number: int) -> ExternalEffectState | None:
        snapshot = await self._persistence.inspect_claim(
            self._claim_key(part_number), history_limit=1
        )
        if snapshot.current_token is None:
            return None
        if snapshot.current_effect in {
            ExternalEffectState.ACCEPTED,
            ExternalEffectState.CONFIRMED,
        }:
            return snapshot.current_effect
        return ExternalEffectState.UNKNOWN

    async def _submit_part(
        self,
        request: OperationRequest,
        report: SavedReport,
        part_plan: SubmissionPartPlan,
        deadline: float,
    ) -> tuple[ResultRef | None, ExternalEffectState]:
        part = report.parts[part_plan.part_number - 1]
        assessments = tuple(
            topic.assessment_ref
            for topic in report.topics
            if topic.topic_ref in part.topic_refs
        )
        claim: ClaimToken | None = None
        effect = ExternalEffectState.NOT_STARTED
        try:
            required = [self._plan.report_result_ref]
            if part_plan.replay_attempt_ref is not None:
                required.append(part_plan.replay_attempt_ref)
            claim = await self._persistence.acquire_claim(
                self._claim_key(part_plan.part_number),
                ClaimKind.REPORT_SUBMIT,
                request.execution,
                self._config.attempt,
                required_inputs=tuple(required),
                lease_seconds=self._config.claim_lease_seconds,
            )
            send_bytes, attempt_ref = await self._prepare_attempt(
                request, report, part_plan, assessments, claim
            )
            self._check_deadline(deadline)
            await self._persistence.mark_external_effect(
                claim, ExternalEffectState.PENDING
            )
            effect = ExternalEffectState.PENDING
            try:
                receipt = await self._call_transport(send_bytes, deadline)
            except asyncio.CancelledError:
                await self._finish_unknown(claim, TerminalStatus.CANCELLED)
                claim = None
                raise
            except (TimeoutError, RuntimeError):
                await self._finish_unknown(claim, TerminalStatus.FAILED)
                claim = None
                return None, ExternalEffectState.UNKNOWN

            receipt_ref = await self._persist_receipt(
                request,
                report,
                part_plan,
                assessments,
                attempt_ref,
                receipt,
                claim,
            )
            await self._persistence.mark_external_effect(claim, receipt.effect)
            effect = receipt.effect
            if effect in {
                ExternalEffectState.ACCEPTED,
                ExternalEffectState.CONFIRMED,
            }:
                await persist_history(
                    self._persistence,
                    request,
                    self._config,
                    self._plan,
                    report,
                    part_plan,
                    assessments,
                    receipt_ref,
                    receipt,
                    claim,
                )
                status = TerminalStatus.COMPLETE
            else:
                status = TerminalStatus.FAILED
            await self._persistence.finish_claim(claim, status, effect)
            claim = None
            return receipt_ref, effect
        except asyncio.CancelledError:
            if claim is not None:
                await self._finish_known(claim, TerminalStatus.CANCELLED, effect)
            raise
        except Phase1PersistenceError:
            if claim is not None:
                if effect in {
                    ExternalEffectState.ACCEPTED,
                    ExternalEffectState.CONFIRMED,
                }:
                    await self._finish_known(claim, TerminalStatus.FAILED, effect)
                elif effect is ExternalEffectState.PENDING:
                    await self._finish_unknown(claim, TerminalStatus.FAILED)
                else:
                    await self._finish_known(
                        claim,
                        TerminalStatus.FAILED,
                        ExternalEffectState.NOT_STARTED,
                    )
            raise
        except (TypeError, ValueError):
            if claim is not None:
                await self._finish_known(
                    claim, TerminalStatus.FAILED, ExternalEffectState.NOT_STARTED
                )
            raise

    async def _prepare_attempt(
        self,
        request: OperationRequest,
        report: SavedReport,
        part_plan: SubmissionPartPlan,
        assessments: tuple[VersionRef, ...],
        claim: ClaimToken,
    ) -> tuple[bytes, ResultRef]:
        if part_plan.replay_attempt_ref is not None:
            previous = await load_attempt(
                self._persistence, part_plan.replay_attempt_ref
            )
            require_replay_binding(previous, report, part_plan, assessments, self._plan)
            return previous.send_bytes, part_plan.replay_attempt_ref

        part = report.parts[part_plan.part_number - 1]
        send_bytes = build_mime(report, part, self._plan.destination_identity)
        attempt = SubmissionAttempt(
            report_ref=report.report_ref,
            policy_ref=report.policy_ref,
            part_number=part_plan.part_number,
            owner_identity=self._plan.owner_identity,
            destination_identity=self._plan.destination_identity,
            assessment_refs=assessments,
            send_bytes=send_bytes,
            send_sha256=sha256(send_bytes).hexdigest(),
        )
        result = self._stage_result(
            request,
            part_plan.attempt_result_id,
            TerminalStatus.INCOMPLETE,
            True,
            (self._plan.report_result_ref,),
            assessments,
            attempt,
        )
        await self._persistence.append_result_with_data(
            result, attempt, require_new=True, claim=claim
        )
        return send_bytes, ResultRef(
            result.result_id, result.kind, result.schema_version
        )

    async def _persist_receipt(
        self,
        request: OperationRequest,
        report: SavedReport,
        part_plan: SubmissionPartPlan,
        assessments: tuple[VersionRef, ...],
        attempt_ref: ResultRef,
        transport: TransportReceipt,
        claim: ClaimToken,
    ) -> ResultRef:
        receipt = SubmissionReceipt(
            report_ref=report.report_ref,
            policy_ref=report.policy_ref,
            part_number=part_plan.part_number,
            assessment_refs=assessments,
            attempt_ref=attempt_ref,
            effect=transport.effect,
            provider_status=transport.provider_status,
            provider_receipt=transport.provider_receipt,
            recorded_at=datetime.now(UTC),
        )
        acceptable = transport.effect in {
            ExternalEffectState.ACCEPTED,
            ExternalEffectState.CONFIRMED,
        }
        result = self._stage_result(
            request,
            part_plan.receipt_result_id,
            TerminalStatus.COMPLETE if acceptable else TerminalStatus.FAILED,
            acceptable,
            (self._plan.report_result_ref, attempt_ref),
            assessments,
            receipt,
        )
        await self._persistence.append_result_with_data(
            result, receipt, require_new=True, claim=claim
        )
        return ResultRef(result.result_id, result.kind, result.schema_version)

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
        ReportCodec().encode(value)
        if (
            value.report_ref != self._plan.report_ref
            or value.policy_ref != self._plan.policy_ref
            or value.destination.owner_identity != self._plan.owner_identity
            or value.destination.destination_identity != self._plan.destination_identity
            or len(value.parts) != len(self._plan.parts)
        ):
            raise ValueError("saved report does not match trusted submission plan")
        return value

    async def _call_transport(
        self, send_bytes: bytes, deadline: float
    ) -> TransportReceipt:
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise TimeoutError
        task = asyncio.create_task(
            self._transport.submit(send_bytes, timeout_seconds=remaining)
        )
        try:
            return await asyncio.wait_for(task, timeout=remaining)
        except asyncio.CancelledError:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            raise
        except TimeoutError:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            raise

    async def _finish_unknown(self, claim: ClaimToken, status: TerminalStatus) -> None:
        try:
            await self._persistence.finish_claim(
                claim, status, ExternalEffectState.UNKNOWN
            )
        except Phase1PersistenceError:
            return

    async def _finish_known(
        self,
        claim: ClaimToken,
        status: TerminalStatus,
        effect: ExternalEffectState,
    ) -> None:
        try:
            await self._persistence.finish_claim(claim, status, effect)
        except Phase1PersistenceError:
            return

    def _stage_result(
        self,
        request: OperationRequest,
        result_id: str,
        status: TerminalStatus,
        acceptable: bool,
        input_refs: tuple[ResultRef, ...],
        assessments: tuple[VersionRef, ...],
        value: object,
    ) -> StageResult:
        data_ref = self._persistence.semantic_reference(
            f"data-{result_id}", "report_submission", "1", value
        )
        return StageResult(
            result_id=result_id,
            kind="report_submission",
            schema_version="1",
            execution=request.execution,
            attempt=self._config.attempt,
            input_refs=input_refs,
            source_versions=(),
            prepared_versions=(),
            topic_versions=assessments,
            configuration_version=self._plan.policy_ref.version,
            code_version=self._config.code_version,
            status=status,
            acceptable=acceptable,
            semantic_data_ref=data_ref,
            exposed_output_ref=self._plan.report_ref,
        )

    def _claim_key(self, part_number: int) -> str:
        return (
            f"report-submit:{self._plan.report_ref.identity}:"
            f"{self._plan.report_ref.version}:{self._plan.policy_ref.identity}:"
            f"{self._plan.policy_ref.version}:{part_number}"
        )

    def _request_mismatch(self, request: OperationRequest) -> str | None:
        if request.capability is not PhaseCapability.REPORT_SUBMIT:
            return "Request capability is not REPORT_SUBMIT"
        if request.target_inputs != (self._plan.report_ref, self._plan.policy_ref):
            return "Request target references do not match the trusted plan"
        if request.parameters != self._plan.expected_parameters:
            return "Request parameters do not match the trusted plan"
        return None

    @staticmethod
    def _check_deadline(deadline: float) -> None:
        if monotonic() >= deadline:
            raise TimeoutError

    def _outcome(
        self,
        request: OperationRequest,
        refs: tuple[ResultRef, ...],
        effects: tuple[ExternalEffectState, ...],
    ) -> OperationOutcome:
        if not effects:
            return self._failed(
                request, "report_submission_failed", "No report part was submitted"
            )
        complete = len(effects) == len(self._plan.parts) and all(
            effect
            in {
                ExternalEffectState.ACCEPTED,
                ExternalEffectState.CONFIRMED,
            }
            for effect in effects
        )
        if any(effect is ExternalEffectState.UNKNOWN for effect in effects):
            aggregate = ExternalEffectState.UNKNOWN
        elif complete and all(
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
            result_refs=refs,
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
