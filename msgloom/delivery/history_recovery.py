"""No-send repair of singular history from durable accepted receipts."""

from __future__ import annotations

from contextlib import suppress
from hashlib import sha256

from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ExternalEffectState,
    OperationRequest,
    ResultRef,
    TerminalStatus,
    VersionRef,
)
from msgloom.persistence import Phase1Persistence, Phase1PersistenceError
from msgloom.reporting import SavedReport

from .history import DeliveryReportHistoryResolver
from .models import SubmissionHandlerConfig, SubmissionPartPlan
from .records import (
    history_recovery_claim_key,
    history_result_id,
    load_receipt_record,
    persist_history_records,
    require_receipt_lineage,
)


async def recover_existing_history(
    persistence: Phase1Persistence,
    config: SubmissionHandlerConfig,
    request: OperationRequest,
    report: SavedReport,
    part_plan: SubmissionPartPlan,
    effect: ExternalEffectState,
) -> None:
    """Repair missing history without resending an already accepted part."""
    assessments = tuple(
        topic.assessment_ref
        for topic in report.topics
        if topic.topic_ref in report.parts[part_plan.part_number - 1].topic_refs
    )
    if await _history_complete(
        persistence, report, part_plan.part_number, assessments, effect
    ):
        return
    receipt_ref = ResultRef(part_plan.receipt_result_id, "report_submission", "1")
    receipt_result, receipt = await load_receipt_record(persistence, receipt_ref)
    require_receipt_lineage(
        receipt_result,
        receipt,
        report_ref=report.report_ref,
        policy_ref=report.policy_ref,
        part_number=part_plan.part_number,
        assessments=assessments,
    )
    if receipt.effect is not effect:
        raise ValueError("accepted claim and durable receipt effect differ")
    seed = (config.attempt.value + receipt_ref.result_id).encode()
    recovery_attempt = AttemptIdentity(f"history-{sha256(seed).hexdigest()[:32]}")
    claim = await persistence.acquire_claim(
        history_recovery_claim_key(receipt_ref),
        ClaimKind.REPORT_SUBMIT,
        request.execution,
        recovery_attempt,
        required_inputs=(receipt_ref,),
        lease_seconds=config.claim_lease_seconds,
    )
    try:
        await persist_history_records(
            persistence,
            execution=request.execution,
            attempt=recovery_attempt,
            code_version=config.code_version,
            report_ref=report.report_ref,
            policy_ref=report.policy_ref,
            assessments=assessments,
            receipt_ref=receipt_ref,
            receipt=receipt,
            claim=claim,
        )
        await persistence.finish_claim(
            claim, TerminalStatus.COMPLETE, ExternalEffectState.NOT_STARTED
        )
    except BaseException:
        with suppress(Exception):
            await persistence.finish_claim(
                claim, TerminalStatus.FAILED, ExternalEffectState.NOT_STARTED
            )
        raise


async def _history_complete(
    persistence: Phase1Persistence,
    report: SavedReport,
    part_number: int,
    assessments: tuple[VersionRef, ...],
    effect: ExternalEffectState,
) -> bool:
    """Verify every singular assessment history through receipt lineage."""
    resolver = DeliveryReportHistoryResolver(persistence)
    for assessment in assessments:
        ref = ResultRef(
            history_result_id(
                report.report_ref,
                report.policy_ref,
                part_number,
                assessment,
            ),
            "report_submission",
            "1",
        )
        try:
            evidence = await resolver.resolve(await resolver.inspect(ref))
        except (Phase1PersistenceError, RuntimeError, TypeError, ValueError):
            return False
        if (
            evidence.report_ref != report.report_ref
            or evidence.policy_ref != report.policy_ref
            or evidence.assessment_ref != assessment
            or evidence.external_effect is not effect
        ):
            return False
    return True
