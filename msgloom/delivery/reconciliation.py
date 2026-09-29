"""Explicit async report effect reconciliation with durable recovery proof."""

from __future__ import annotations

from contextlib import suppress

from msgloom.contracts import (
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

from .models import ReconciliationEvidence, ReportReconciliationPlan


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

        recovery_claim = await self._persistence.acquire_claim(
            f"report-reconcile:{plan.identity}",
            ClaimKind.REPORT_SUBMIT,
            execution,
            plan.recovery_attempt,
            required_inputs=(),
            lease_seconds=plan.claim_lease_seconds,
        )
        evidence_ref: ResultRef | None = None
        try:
            if plan.provider_evidence:
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
                    result_id=plan.recovery_result_id,
                    kind="report_submission",
                    schema_version="1",
                    execution=execution,
                    attempt=plan.recovery_attempt,
                    input_refs=(),
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
                    result, evidence, require_new=True, claim=recovery_claim
                )
                evidence_ref = ResultRef(
                    result.result_id, result.kind, result.schema_version
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

        evidence_refs = () if evidence_ref is None else (evidence_ref,)
        return await self._persistence.reconcile_external_effect(
            ReconciliationRequest(
                ReconciliationIdentity(plan.identity),
                plan.target,
                plan.decision,
                evidence_refs,
            )
        )


def submission_claim_key(
    report_identity: str,
    report_version: str,
    policy_identity: str,
    policy_version: str,
    part_number: int,
) -> str:
    """Return the stable per-report, policy, and part submission scope."""
    return (
        f"report-submit:{report_identity}:{report_version}:"
        f"{policy_identity}:{policy_version}:{part_number}"
    )
