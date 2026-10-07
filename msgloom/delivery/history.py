"""Durable report history resolver backed only by accepted receipt evidence."""

from __future__ import annotations

from msgloom.contracts import ResultRef
from msgloom.persistence import Phase1Persistence
from msgloom.reporting import ReportHistoryEvidence, ReportHistoryMetadata

from .models import SubmissionHistory
from .records import load_attempt_record, load_receipt_record, require_receipt_lineage


class DeliveryReportHistoryResolver:
    """Resolve singular assessment history from durable delivery records."""

    def __init__(self, persistence: Phase1Persistence) -> None:
        self._persistence = persistence

    async def inspect(self, evidence_ref: ResultRef) -> ReportHistoryMetadata:
        """Return bounded metadata without trusting caller-supplied timestamps."""
        result = await self._persistence.get_result(evidence_ref.result_id)
        if (
            result is None
            or ResultRef(result.result_id, result.kind, result.schema_version)
            != evidence_ref
            or not result.acceptable
            or result.semantic_data_ref is None
            or result.kind != "report_submission"
            or result.schema_version != "1"
        ):
            raise ValueError("report history evidence is not acceptable")
        return ReportHistoryMetadata(
            evidence_ref=evidence_ref,
            semantic_data_ref=result.semantic_data_ref,
        )

    async def resolve(self, metadata: ReportHistoryMetadata) -> ReportHistoryEvidence:
        """Load only receipt-backed accepted or confirmed singular history."""
        if metadata.semantic_data_ref is None:
            raise ValueError("report history evidence has no semantic data")
        history_result = await self._persistence.get_result(
            metadata.evidence_ref.result_id
        )
        if (
            history_result is None
            or history_result.semantic_data_ref != metadata.semantic_data_ref
            or ResultRef(
                history_result.result_id,
                history_result.kind,
                history_result.schema_version,
            )
            != metadata.evidence_ref
        ):
            raise ValueError("report history metadata no longer matches storage")
        value = await self._persistence.load_semantic_data(metadata.semantic_data_ref)
        if not isinstance(value, SubmissionHistory):
            raise TypeError("report history evidence is not a history record")

        receipt_ref = ResultRef(
            value.receipt_ref.identity,
            "report_submission",
            value.receipt_ref.version,
        )
        receipt_result, receipt = await load_receipt_record(
            self._persistence, receipt_ref
        )
        require_receipt_lineage(
            receipt_result,
            receipt,
            report_ref=value.report_ref,
            policy_ref=value.policy_ref,
            part_number=receipt.part_number,
            assessments=receipt.assessment_refs,
        )
        attempt_result, attempt = await load_attempt_record(
            self._persistence, receipt.attempt_ref
        )
        if (
            attempt_result.execution != receipt_result.execution
            or attempt_result.attempt != receipt_result.attempt
            or attempt_result.input_refs != (receipt_result.input_refs[0],)
            or attempt.report_ref != receipt.report_ref
            or attempt.policy_ref != receipt.policy_ref
            or attempt.part_number != receipt.part_number
            or attempt.assessment_refs != receipt.assessment_refs
            or value.assessment_ref not in receipt.assessment_refs
            or value.effect is not receipt.effect
            or value.reported_at != receipt.recorded_at
            or history_result.input_refs != (receipt_ref,)
            or history_result.topic_versions != (value.assessment_ref,)
            or history_result.exposed_output_ref != value.report_ref
        ):
            raise ValueError("report history is not backed by exact receipt lineage")
        return ReportHistoryEvidence(
            evidence_ref=metadata.evidence_ref,
            report_ref=value.report_ref,
            policy_ref=value.policy_ref,
            assessment_ref=value.assessment_ref,
            reported_at=value.reported_at,
            receipt_ref=value.receipt_ref,
            external_effect=value.effect,
            semantic_data_ref=metadata.semantic_data_ref,
        )
