"""Focused durable delivery record helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256

from msgloom.contracts import (
    ClaimToken,
    OperationRequest,
    ResultRef,
    StageResult,
    TerminalStatus,
    VersionRef,
)
from msgloom.persistence import Phase1Persistence
from msgloom.reporting import SavedReport

from .models import (
    ReportSubmissionPlan,
    SubmissionAttempt,
    SubmissionHandlerConfig,
    SubmissionHistory,
    SubmissionPartPlan,
)
from .transport import TransportReceipt


async def persist_history(
    persistence: Phase1Persistence,
    request: OperationRequest,
    config: SubmissionHandlerConfig,
    plan: ReportSubmissionPlan,
    report: SavedReport,
    part_plan: SubmissionPartPlan,
    assessments: tuple[VersionRef, ...],
    receipt_ref: ResultRef,
    transport: TransportReceipt,
    claim: ClaimToken,
) -> None:
    """Persist singular assessment history after a definite receipt."""
    receipt_version = VersionRef(
        "report-receipt", receipt_ref.result_id, receipt_ref.schema_version
    )
    for assessment in assessments:
        history = SubmissionHistory(
            report_ref=report.report_ref,
            policy_ref=report.policy_ref,
            assessment_ref=assessment,
            receipt_ref=receipt_version,
            effect=transport.effect,
            reported_at=datetime.now(UTC),
        )
        digest = sha256(
            (
                f"{part_plan.receipt_result_id}:"
                f"{assessment.identity}:{assessment.version}"
            ).encode()
        ).hexdigest()[:32]
        result_id = f"report-history-{digest}"
        data_ref = persistence.semantic_reference(
            f"data-{result_id}", "report_submission", "1", history
        )
        result = StageResult(
            result_id=result_id,
            kind="report_submission",
            schema_version="1",
            execution=request.execution,
            attempt=config.attempt,
            input_refs=(receipt_ref,),
            source_versions=(),
            prepared_versions=(),
            topic_versions=(assessment,),
            configuration_version=plan.policy_ref.version,
            code_version=config.code_version,
            status=TerminalStatus.COMPLETE,
            acceptable=True,
            semantic_data_ref=data_ref,
            exposed_output_ref=plan.report_ref,
        )
        await persistence.append_result_with_data(
            result, history, require_new=True, claim=claim
        )


async def load_attempt(
    persistence: Phase1Persistence, ref: ResultRef
) -> SubmissionAttempt:
    """Load and integrity-check exact persisted replay bytes."""
    result = await persistence.get_result(ref.result_id)
    if (
        result is None
        or ResultRef(result.result_id, result.kind, result.schema_version) != ref
        or result.semantic_data_ref is None
    ):
        raise ValueError("replay attempt evidence is missing")
    value = await persistence.load_semantic_data(result.semantic_data_ref)
    if not isinstance(value, SubmissionAttempt):
        raise TypeError("replay evidence is not a submission attempt")
    if sha256(value.send_bytes).hexdigest() != value.send_sha256:
        raise ValueError("replay bytes failed integrity validation")
    return value


def require_replay_binding(
    attempt: SubmissionAttempt,
    report: SavedReport,
    part_plan: SubmissionPartPlan,
    assessments: tuple[VersionRef, ...],
    plan: ReportSubmissionPlan,
) -> None:
    """Require replay evidence to bind the exact owner, report, and part."""
    if (
        attempt.report_ref != report.report_ref
        or attempt.policy_ref != report.policy_ref
        or attempt.part_number != part_plan.part_number
        or attempt.owner_identity != plan.owner_identity
        or attempt.destination_identity != plan.destination_identity
        or attempt.assessment_refs != assessments
    ):
        raise ValueError("replay attempt does not match exact report part")
