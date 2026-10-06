"""Per-part report submission lifecycle with durable effect fencing."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256

from msgloom.contracts import (
    ClaimKind,
    ClaimToken,
    ExternalEffectState,
    OperationRequest,
    ResultRef,
    StageResult,
    TerminalStatus,
    VersionRef,
)
from msgloom.persistence import Phase1Persistence, Phase1PersistenceError
from msgloom.reporting import SavedReport

from .lifecycle import cancel_and_drain, run_cpu
from .mime import build_mime
from .models import (
    ReportSubmissionPlan,
    SubmissionAttempt,
    SubmissionHandlerConfig,
    SubmissionPartPlan,
    SubmissionReceipt,
)
from .reconciliation import submission_claim_key
from .records import (
    load_attempt,
    load_receipt_record,
    persist_history_records,
    require_receipt_lineage,
    require_replay_binding,
)
from .transport import ReportTransport, TransportReceipt, validate_transport_receipt


@dataclass(slots=True)
class DeliveryProgress:
    """Retain the exact durable prefix for incomplete operation outcomes."""

    refs: list[ResultRef] = field(default_factory=list)
    effects: list[ExternalEffectState] = field(default_factory=list)
    incomplete: bool = False

    def add_ref(self, ref: ResultRef) -> None:
        """Append one durable reference once in persistence order."""
        if ref not in self.refs:
            self.refs.append(ref)


class PartSubmitter:
    """Own one report part from claim acquisition through durable terminal state."""

    def __init__(
        self,
        *,
        plan: ReportSubmissionPlan,
        config: SubmissionHandlerConfig,
        persistence: Phase1Persistence,
        transport: ReportTransport,
    ) -> None:
        self._plan = plan
        self._config = config
        self._persistence = persistence
        self._transport = transport

    async def existing_effect(
        self, part_plan: SubmissionPartPlan
    ) -> ExternalEffectState | None:
        """Return a retry-blocking effect and require exact rejected replay."""
        snapshot = await self._persistence.inspect_claim(
            self.claim_key(part_plan.part_number), history_limit=1
        )
        if snapshot.current_token is not None:
            if snapshot.current_effect in {
                ExternalEffectState.ACCEPTED,
                ExternalEffectState.CONFIRMED,
            }:
                return snapshot.current_effect
            return ExternalEffectState.UNKNOWN
        rejected_target = None
        if (
            snapshot.reconciliations
            and snapshot.reconciliations[0].decision is ExternalEffectState.REJECTED
        ):
            rejected_target = snapshot.reconciliations[0].target
        elif (
            snapshot.attempts
            and snapshot.attempts[0].external_effect is ExternalEffectState.REJECTED
        ):
            rejected_target = snapshot.attempts[0].token
        if rejected_target is not None:
            replay_ref = part_plan.replay_attempt_ref
            if replay_ref is None:
                raise ValueError("rejected retry requires exact saved attempt bytes")
            replay_result = await self._persistence.get_result(replay_ref.result_id)
            if (
                replay_result is None
                or ResultRef(
                    replay_result.result_id,
                    replay_result.kind,
                    replay_result.schema_version,
                )
                != replay_ref
                or replay_result.execution != rejected_target.execution
                or replay_result.attempt != rejected_target.attempt
            ):
                raise ValueError("rejected retry attempt evidence mismatches")
        return None

    async def submit(
        self,
        request: OperationRequest,
        report: SavedReport,
        part_plan: SubmissionPartPlan,
        progress: DeliveryProgress,
    ) -> None:
        """Submit one part once and retain the strongest durable effect."""
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
                self.claim_key(part_plan.part_number),
                ClaimKind.REPORT_SUBMIT,
                request.execution,
                self._config.attempt,
                required_inputs=tuple(required),
                lease_seconds=self._config.claim_lease_seconds,
            )
            send_bytes, attempt_ref = await self._prepare_attempt(
                request, report, part_plan, assessments, claim
            )
            progress.add_ref(attempt_ref)
            await self._persistence.mark_external_effect(
                claim, ExternalEffectState.PENDING
            )
            effect = ExternalEffectState.PENDING

            transport = await self._call_transport(send_bytes)
            transport = validate_transport_receipt(transport)
            receipt_ref, receipt = await self._persist_receipt(
                request,
                report,
                part_plan,
                assessments,
                attempt_ref,
                transport,
                claim,
            )
            progress.add_ref(receipt_ref)
            effect = receipt.effect
            await self._persistence.mark_external_effect(claim, effect)
            if effect in {
                ExternalEffectState.ACCEPTED,
                ExternalEffectState.CONFIRMED,
            }:
                await persist_history_records(
                    self._persistence,
                    execution=request.execution,
                    attempt=self._config.attempt,
                    code_version=self._config.code_version,
                    report_ref=report.report_ref,
                    policy_ref=report.policy_ref,
                    assessments=assessments,
                    receipt_ref=receipt_ref,
                    receipt=receipt,
                    claim=claim,
                )
                status = TerminalStatus.COMPLETE
            else:
                status = TerminalStatus.FAILED
            await self._persistence.finish_claim(claim, status, effect)
            claim = None
        except (
            asyncio.CancelledError,
            Phase1PersistenceError,
            RuntimeError,
            TimeoutError,
            TypeError,
            ValueError,
        ) as error:
            progress.incomplete = True
            # Settlement publishes recovered truth even if a terminal write
            # fails. Drain it before propagating the first cancellation.
            settlement = asyncio.create_task(
                self._settle_interrupted(
                    claim, effect, report, part_plan, assessments, progress
                )
            )
            cancelled = error if isinstance(error, asyncio.CancelledError) else None
            while not settlement.done():
                try:
                    await asyncio.wait((settlement,), return_when=asyncio.ALL_COMPLETED)
                except asyncio.CancelledError as stop:
                    if cancelled is None:
                        cancelled = stop
            if cancelled is not None:
                if not settlement.cancelled():
                    settlement.exception()
                raise cancelled
            settlement.result()
            return
        progress.effects.append(effect)

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
            require_replay_binding(
                previous,
                report_ref=report.report_ref,
                policy_ref=report.policy_ref,
                part_number=part_plan.part_number,
                assessments=assessments,
                owner_identity=self._plan.owner_identity,
                destination_identity=self._plan.destination_identity,
            )
            return previous.send_bytes, part_plan.replay_attempt_ref

        send_bytes, attempt = await run_cpu(
            self._build_attempt, report, part_plan, assessments
        )
        result = await run_cpu(
            self._stage_result,
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

    def _build_attempt(
        self,
        report: SavedReport,
        part_plan: SubmissionPartPlan,
        assessments: tuple[VersionRef, ...],
    ) -> tuple[bytes, SubmissionAttempt]:
        part = report.parts[part_plan.part_number - 1]
        send_bytes = build_mime(report, part, self._plan.destination_identity)
        return send_bytes, SubmissionAttempt(
            report_ref=report.report_ref,
            policy_ref=report.policy_ref,
            part_number=part_plan.part_number,
            owner_identity=self._plan.owner_identity,
            destination_identity=self._plan.destination_identity,
            assessment_refs=assessments,
            send_bytes=send_bytes,
            send_sha256=sha256(send_bytes).hexdigest(),
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
    ) -> tuple[ResultRef, SubmissionReceipt]:
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
        acceptable = receipt.effect in {
            ExternalEffectState.ACCEPTED,
            ExternalEffectState.CONFIRMED,
        }
        result = await run_cpu(
            self._stage_result,
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
        return (
            ResultRef(result.result_id, result.kind, result.schema_version),
            receipt,
        )

    async def _settle_interrupted(
        self,
        claim: ClaimToken | None,
        effect: ExternalEffectState,
        report: SavedReport,
        part_plan: SubmissionPartPlan,
        assessments: tuple[VersionRef, ...],
        progress: DeliveryProgress,
    ) -> None:
        """Publish recovered truth even when terminal acknowledgement fails."""
        try:
            if claim is None:
                return
            recovered = await self._recover_durable_effect(
                claim, report, part_plan, assessments, progress
            )
            if recovered is not None:
                effect = recovered
            if effect is ExternalEffectState.PENDING:
                effect = ExternalEffectState.UNKNOWN
            status = (
                TerminalStatus.COMPLETE
                if effect
                in {
                    ExternalEffectState.ACCEPTED,
                    ExternalEffectState.CONFIRMED,
                }
                else TerminalStatus.FAILED
            )
            await self._finish_known(claim, status, effect)
        finally:
            # Receipt recovery may already have extended the durable prefix.
            # A later cleanup error must not discard that prefix or its effect.
            progress.effects.append(
                ExternalEffectState.UNKNOWN
                if effect is ExternalEffectState.PENDING
                else effect
            )

    async def _recover_durable_effect(
        self,
        claim: ClaimToken,
        report: SavedReport,
        part_plan: SubmissionPartPlan,
        assessments: tuple[VersionRef, ...],
        progress: DeliveryProgress,
    ) -> ExternalEffectState | None:
        uncertain = False
        with suppress(Phase1PersistenceError, RuntimeError, TypeError, ValueError):
            snapshot = await self._persistence.inspect_claim(claim.claim_key)
            if snapshot.current_token == claim:
                if snapshot.current_effect in {
                    ExternalEffectState.ACCEPTED,
                    ExternalEffectState.CONFIRMED,
                    ExternalEffectState.REJECTED,
                }:
                    return snapshot.current_effect
                uncertain = snapshot.current_effect in {
                    ExternalEffectState.PENDING,
                    ExternalEffectState.UNKNOWN,
                }
        receipt_ref = ResultRef(part_plan.receipt_result_id, "report_submission", "1")
        with suppress(Phase1PersistenceError, RuntimeError, TypeError, ValueError):
            result, receipt = await load_receipt_record(
                self._persistence, receipt_ref, acceptable_only=False
            )
            require_receipt_lineage(
                result,
                receipt,
                report_ref=report.report_ref,
                policy_ref=report.policy_ref,
                part_number=part_plan.part_number,
                assessments=assessments,
            )
            progress.add_ref(receipt_ref)
            return receipt.effect
        if uncertain:
            return ExternalEffectState.UNKNOWN
        return None

    async def _call_transport(self, send_bytes: bytes) -> TransportReceipt:
        task = asyncio.create_task(
            self._transport.submit(
                send_bytes,
                timeout_seconds=self._config.timeout_seconds,
            )
        )
        try:
            return await task
        except asyncio.CancelledError:
            await cancel_and_drain(task)
            raise

    async def _finish_known(
        self,
        claim: ClaimToken,
        status: TerminalStatus,
        effect: ExternalEffectState,
    ) -> None:
        with suppress(Phase1PersistenceError):
            await self._persistence.finish_claim(claim, status, effect)

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

    def claim_key(self, part_number: int) -> str:
        """Return the stable collision-resistant scope for one report part."""
        return submission_claim_key(
            self._plan.report_ref.identity,
            self._plan.report_ref.version,
            self._plan.policy_ref.identity,
            self._plan.policy_ref.version,
            part_number,
        )
