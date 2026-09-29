"""Explicit async report effect reconciliation with durable recovery proof."""

from __future__ import annotations

import json
from contextlib import suppress
from hashlib import sha256

from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ExecutionIdentity,
    ExternalEffectState,
    ResultRef,
    StageResult,
    TerminalStatus,
)
from msgloom.persistence import (
    Phase1Persistence,
    ReconciliationIdentity,
    ReconciliationRequest,
    ReconciliationResult,
)

from .models import (
    ReconciliationEvidence,
    ReportReconciliationPlan,
    SubmissionReceipt,
)
from .records import (
    history_recovery_claim_key,
    load_attempt_record,
    load_receipt_record,
    persist_history_records,
    require_receipt_lineage,
)


class ReportReconciler:
    """Persist trusted provider proof, then atomically resolve one unknown effect."""

    def __init__(self, persistence: Phase1Persistence) -> None:
        self._persistence = persistence

    async def reconcile(
        self,
        plan: ReportReconciliationPlan,
        *,
        execution: ExecutionIdentity,
    ) -> ReconciliationResult:
        """Resolve one terminal or expired submission attempt without sending."""
        plan = ReportReconciliationPlan.model_validate_json(
            plan.model_dump_json(warnings="error"), strict=True
        )
        expected = submission_claim_key(
            plan.report_ref.identity,
            plan.report_ref.version,
            plan.policy_ref.identity,
            plan.policy_ref.version,
            plan.part_number,
        )
        if plan.target.claim_key != expected:
            raise ValueError("reconciliation target does not match report part")
        inspection = await self._persistence.inspect_claim(plan.target.claim_key)
        if plan.target not in tuple(item.token for item in inspection.attempts):
            raise ValueError("reconciliation target attempt is not retained")

        receipt: SubmissionReceipt | None = None
        if plan.decision in {
            ExternalEffectState.ACCEPTED,
            ExternalEffectState.CONFIRMED,
        }:
            receipt = await self._validated_receipt(plan)

        evidence_ref = ResultRef(plan.recovery_result_id, "report_submission", "1")
        evidence_refs = (evidence_ref,)
        if plan.receipt_ref is not None:
            evidence_refs += (plan.receipt_ref,)
        for saved in inspection.reconciliations:
            if saved.identity.value != plan.identity:
                continue
            if (
                saved.target != plan.target
                or saved.decision is not plan.decision
                or saved.evidence != evidence_refs
            ):
                raise ValueError("reconciliation identity has changed proof")
            await self._require_saved_proof(plan, execution, evidence_ref)
            if receipt is not None and plan.receipt_ref is not None:
                await self._recover_history(
                    plan,
                    execution,
                    evidence_ref,
                    plan.receipt_ref,
                    receipt,
                )
            return saved

        await self._persist_proof(plan, execution, evidence_ref)
        result = await self._persistence.reconcile_external_effect(
            ReconciliationRequest(
                ReconciliationIdentity(plan.identity),
                plan.target,
                plan.decision,
                evidence_refs,
            )
        )
        if receipt is not None and plan.receipt_ref is not None:
            await self._recover_history(
                plan,
                execution,
                evidence_ref,
                plan.receipt_ref,
                receipt,
            )
        return result

    async def _require_saved_proof(
        self,
        plan: ReportReconciliationPlan,
        execution: ExecutionIdentity,
        evidence_ref: ResultRef,
    ) -> None:
        """Require an exact retry to reuse identical durable proof semantics."""
        result = await self._persistence.get_result(evidence_ref.result_id)
        if (
            result is None
            or ResultRef(result.result_id, result.kind, result.schema_version)
            != evidence_ref
            or result.execution != execution
            or result.attempt != plan.recovery_attempt
            or result.semantic_data_ref is None
        ):
            raise ValueError("reconciliation proof lineage has changed")
        value = await self._persistence.load_semantic_data(result.semantic_data_ref)
        expected = ReconciliationEvidence(
            report_ref=plan.report_ref,
            policy_ref=plan.policy_ref,
            part_number=plan.part_number,
            target=plan.target,
            decision=plan.decision,
            evidence=plan.provider_evidence,
        )
        if value != expected:
            raise ValueError("reconciliation identity has changed proof")

    async def _persist_proof(
        self,
        plan: ReportReconciliationPlan,
        execution: ExecutionIdentity,
        evidence_ref: ResultRef,
    ) -> None:
        required = () if plan.receipt_ref is None else (plan.receipt_ref,)
        recovery_claim = await self._persistence.acquire_claim(
            _recovery_claim_key(plan.identity),
            ClaimKind.REPORT_SUBMIT,
            execution,
            plan.recovery_attempt,
            required_inputs=required,
            lease_seconds=plan.claim_lease_seconds,
        )
        try:
            evidence = ReconciliationEvidence(
                report_ref=plan.report_ref,
                policy_ref=plan.policy_ref,
                part_number=plan.part_number,
                target=plan.target,
                decision=plan.decision,
                evidence=plan.provider_evidence,
            )
            data_ref = self._persistence.semantic_reference(
                f"data-{plan.recovery_result_id}",
                "report_submission",
                "1",
                evidence,
            )
            result = StageResult(
                result_id=evidence_ref.result_id,
                kind=evidence_ref.kind,
                schema_version=evidence_ref.schema_version,
                execution=execution,
                attempt=plan.recovery_attempt,
                input_refs=required,
                source_versions=(),
                prepared_versions=(),
                topic_versions=(),
                configuration_version=plan.policy_ref.version,
                code_version=plan.code_version,
                status=TerminalStatus.COMPLETE,
                acceptable=True,
                semantic_data_ref=data_ref,
                exposed_output_ref=plan.report_ref,
            )
            await self._persistence.append_result_with_data(
                result, evidence, require_new=False, claim=recovery_claim
            )
            await self._persistence.finish_claim(
                recovery_claim,
                TerminalStatus.COMPLETE,
                ExternalEffectState.NOT_STARTED,
            )
        except BaseException:
            with suppress(Exception):
                await self._persistence.finish_claim(
                    recovery_claim,
                    TerminalStatus.FAILED,
                    ExternalEffectState.NOT_STARTED,
                )
            raise

    async def _validated_receipt(
        self, plan: ReportReconciliationPlan
    ) -> SubmissionReceipt:
        receipt_ref = plan.receipt_ref
        if receipt_ref is None:
            raise ValueError("accepted reconciliation requires a durable receipt")
        receipt_result, receipt = await load_receipt_record(
            self._persistence, receipt_ref
        )
        require_receipt_lineage(
            receipt_result,
            receipt,
            report_ref=plan.report_ref,
            policy_ref=plan.policy_ref,
            part_number=plan.part_number,
            assessments=receipt.assessment_refs,
        )
        attempt_result, attempt = await load_attempt_record(
            self._persistence, receipt.attempt_ref
        )
        if (
            receipt.effect is not plan.decision
            or receipt_result.execution != plan.target.execution
            or receipt_result.attempt != plan.target.attempt
            or attempt_result.execution != plan.target.execution
            or attempt_result.attempt != plan.target.attempt
            or attempt.report_ref != plan.report_ref
            or attempt.policy_ref != plan.policy_ref
            or attempt.part_number != plan.part_number
            or attempt.assessment_refs != receipt.assessment_refs
        ):
            raise ValueError("reconciliation receipt does not match target attempt")
        return receipt

    async def _recover_history(
        self,
        plan: ReportReconciliationPlan,
        execution: ExecutionIdentity,
        evidence_ref: ResultRef,
        receipt_ref: ResultRef,
        receipt: SubmissionReceipt,
    ) -> None:
        claim = await self._persistence.acquire_claim(
            history_recovery_claim_key(receipt_ref),
            ClaimKind.REPORT_SUBMIT,
            execution,
            _history_attempt(plan.identity),
            required_inputs=(receipt_ref, evidence_ref),
            lease_seconds=plan.claim_lease_seconds,
        )
        try:
            await persist_history_records(
                self._persistence,
                execution=execution,
                attempt=claim.attempt,
                code_version=plan.code_version,
                report_ref=plan.report_ref,
                policy_ref=plan.policy_ref,
                assessments=receipt.assessment_refs,
                receipt_ref=receipt_ref,
                receipt=receipt,
                claim=claim,
            )
            await self._persistence.finish_claim(
                claim, TerminalStatus.COMPLETE, ExternalEffectState.NOT_STARTED
            )
        except BaseException:
            with suppress(Exception):
                await self._persistence.finish_claim(
                    claim, TerminalStatus.FAILED, ExternalEffectState.NOT_STARTED
                )
            raise


def submission_claim_key(
    report_identity: str,
    report_version: str,
    policy_identity: str,
    policy_version: str,
    part_number: int,
) -> str:
    """Return a collision-resistant canonical per-report submission scope."""
    payload = json.dumps(
        [
            "report-submit",
            report_identity,
            report_version,
            policy_identity,
            policy_version,
            part_number,
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"report-submit:{sha256(payload).hexdigest()}"


def _recovery_claim_key(identity: str) -> str:
    digest = sha256(
        json.dumps(["report-reconcile", identity], separators=(",", ":")).encode()
    ).hexdigest()
    return f"report-reconcile:{digest}"


def _history_attempt(identity: str) -> AttemptIdentity:
    digest = sha256(identity.encode("utf-8")).hexdigest()[:32]
    return AttemptIdentity(f"report-history-recovery-{digest}")
