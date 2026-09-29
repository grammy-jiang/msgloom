"""Typed durable prior-report history boundary for report selection."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict, model_validator

from msgloom.contracts import (
    ExternalEffectState,
    ResultRef,
    SemanticDataRef,
    VersionRef,
)


class _HistoryModel(BaseModel):
    """Reject coercion, mutation, and undeclared history fields."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


class ReportHistoryMetadata(_HistoryModel):
    """Metadata available without loading a receipt semantic payload."""

    evidence_ref: ResultRef
    semantic_data_ref: SemanticDataRef | None = None

    @model_validator(mode="after")
    def _schema(self) -> ReportHistoryMetadata:
        if (
            self.evidence_ref.kind != "report_submission"
            or self.evidence_ref.schema_version != "1"
        ):
            raise ValueError("history metadata must reference report_submission@1")
        return self


class ReportHistoryEvidence(_HistoryModel):
    """Verified durable delivery evidence used for report suppression."""

    evidence_ref: ResultRef
    report_ref: VersionRef
    policy_ref: VersionRef
    assessment_ref: VersionRef
    reported_at: datetime
    receipt_ref: VersionRef
    external_effect: ExternalEffectState
    semantic_data_ref: SemanticDataRef | None = None

    @model_validator(mode="after")
    def _accepted_receipt(self) -> ReportHistoryEvidence:
        if (
            self.evidence_ref.kind != "report_submission"
            or self.evidence_ref.schema_version != "1"
        ):
            raise ValueError("history evidence must reference report_submission@1")
        if self.report_ref.kind != "report" or self.policy_ref.kind != "report-policy":
            raise ValueError("history report/policy reference kind is invalid")
        if self.assessment_ref.kind != "topic-assessment":
            raise ValueError("history assessment reference kind is invalid")
        if self.reported_at.tzinfo is None or self.reported_at.utcoffset() is None:
            raise ValueError("history reported time must be timezone-aware")
        if self.external_effect not in {
            ExternalEffectState.ACCEPTED,
            ExternalEffectState.CONFIRMED,
        }:
            raise ValueError("history receipt is not accepted or confirmed")
        return self


class ReportHistoryResolver(Protocol):
    """Resolve delivery-owned durable receipt evidence without transport access."""

    async def inspect(self, evidence_ref: ResultRef) -> ReportHistoryMetadata:
        """Return bounded metadata without loading semantic receipt data."""
        ...

    async def resolve(self, metadata: ReportHistoryMetadata) -> ReportHistoryEvidence:
        """Return verified accepted/confirmed durable receipt evidence."""
        ...
