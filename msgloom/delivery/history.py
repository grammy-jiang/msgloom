"""Durable report history resolver backed only by accepted receipt evidence."""

from __future__ import annotations

from msgloom.contracts import ResultRef
from msgloom.persistence import Phase1Persistence
from msgloom.reporting import ReportHistoryEvidence, ReportHistoryMetadata

from .models import SubmissionHistory


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
        ):
            raise ValueError("report history evidence is not acceptable")
        if result.kind != "report_submission" or result.schema_version != "1":
            raise ValueError("report history evidence schema is invalid")
        return ReportHistoryMetadata(
            evidence_ref=evidence_ref,
            semantic_data_ref=result.semantic_data_ref,
        )

    async def resolve(self, metadata: ReportHistoryMetadata) -> ReportHistoryEvidence:
        """Load only accepted or confirmed singular delivery history."""
        if metadata.semantic_data_ref is None:
            raise ValueError("report history evidence has no semantic data")
        value = await self._persistence.load_semantic_data(metadata.semantic_data_ref)
        if not isinstance(value, SubmissionHistory):
            raise TypeError("report history evidence is not a history record")
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
