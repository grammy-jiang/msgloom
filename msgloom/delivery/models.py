"""Closed immutable contracts for report submission and reconciliation."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from msgloom.contracts import (
    AttemptIdentity,
    ClaimToken,
    ExternalEffectState,
    ResultRef,
    VersionRef,
)

ShortText = Annotated[str, Field(min_length=1, max_length=512)]
SafeDetail = Annotated[str, Field(min_length=1, max_length=2_048)]
BoundedBytes = Annotated[bytes, Field(min_length=1, max_length=12 * 1024 * 1024)]


class _ClosedModel(BaseModel):
    """Reject coercion, mutation, and undeclared delivery fields."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


class SubmissionPartPlan(_ClosedModel):
    """Bind one report part to immutable result identities and replay bytes."""

    part_number: Annotated[int, Field(ge=1, le=128)]
    attempt_result_id: ShortText
    receipt_result_id: ShortText
    replay_attempt_ref: ResultRef | None = None


class ReportSubmissionPlan(_ClosedModel):
    """Trusted finite owner-only submission plan for one saved report."""

    schema_version: Literal["1"] = "1"
    report_result_ref: ResultRef
    report_ref: VersionRef
    policy_ref: VersionRef
    owner_identity: ShortText
    destination_identity: ShortText
    parts: Annotated[
        tuple[SubmissionPartPlan, ...], Field(min_length=1, max_length=128)
    ]
    expected_parameters: Annotated[tuple[tuple[str, str], ...], Field(max_length=16)]

    @model_validator(mode="after")
    def _closed(self) -> ReportSubmissionPlan:
        if (
            self.report_result_ref.kind != "report"
            or self.report_result_ref.schema_version != "1"
        ):
            raise ValueError("submission input must be exact report@1")
        if self.report_ref.kind != "report":
            raise ValueError("submission report reference kind is invalid")
        if self.policy_ref.kind != "report-policy":
            raise ValueError("submission policy reference kind is invalid")
        numbers = tuple(item.part_number for item in self.parts)
        if numbers != tuple(range(1, len(self.parts) + 1)):
            raise ValueError("submission parts must be consecutive and complete")
        keys = tuple(key for key, _value in self.expected_parameters)
        if len(keys) != len(set(keys)):
            raise ValueError("submission parameters must have unique keys")
        ids = tuple(
            identity
            for part in self.parts
            for identity in (part.attempt_result_id, part.receipt_result_id)
        )
        if len(ids) != len(set(ids)):
            raise ValueError("submission result identities must be unique")
        return self


class SubmissionHandlerConfig(_ClosedModel):
    """Trusted finite attempt and lifetime budget for one submission command."""

    attempt: AttemptIdentity
    code_version: ShortText
    timeout_seconds: Annotated[float, Field(gt=0.0, le=300.0)]
    claim_lease_seconds: Annotated[float, Field(gt=0.0, le=600.0)]

    @model_validator(mode="after")
    def _lease(self) -> SubmissionHandlerConfig:
        if self.claim_lease_seconds < self.timeout_seconds + 1.0:
            raise ValueError("claim lease must exceed the operation budget")
        return self


class SubmissionAttempt(_ClosedModel):
    """Durable exact bytes and lineage saved before an external effect."""

    record_type: Literal["attempt"] = "attempt"
    report_ref: VersionRef
    policy_ref: VersionRef
    part_number: Annotated[int, Field(ge=1, le=128)]
    owner_identity: ShortText
    destination_identity: ShortText
    assessment_refs: Annotated[
        tuple[VersionRef, ...], Field(min_length=1, max_length=256)
    ]
    send_bytes: BoundedBytes
    send_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

    @model_validator(mode="after")
    def _refs(self) -> SubmissionAttempt:
        _require_refs(self.report_ref, self.policy_ref, self.assessment_refs)
        return self


class SubmissionReceipt(_ClosedModel):
    """Durable provider receipt saved before effect state advances."""

    record_type: Literal["receipt"] = "receipt"
    report_ref: VersionRef
    policy_ref: VersionRef
    part_number: Annotated[int, Field(ge=1, le=128)]
    assessment_refs: Annotated[
        tuple[VersionRef, ...], Field(min_length=1, max_length=256)
    ]
    attempt_ref: ResultRef
    effect: ExternalEffectState
    provider_status: ShortText
    provider_receipt: ShortText | None = None
    recorded_at: datetime

    @model_validator(mode="after")
    def _receipt(self) -> SubmissionReceipt:
        _require_refs(self.report_ref, self.policy_ref, self.assessment_refs)
        if self.attempt_ref.kind != "report_submission":
            raise ValueError("receipt attempt reference kind is invalid")
        if self.effect not in {
            ExternalEffectState.ACCEPTED,
            ExternalEffectState.CONFIRMED,
            ExternalEffectState.REJECTED,
        }:
            raise ValueError("receipt effect must be definite")
        if self.recorded_at.tzinfo is None or self.recorded_at.utcoffset() is None:
            raise ValueError("receipt time must be timezone-aware")
        return self


class SubmissionHistory(_ClosedModel):
    """Singular accepted or confirmed reporting evidence for one assessment."""

    record_type: Literal["history"] = "history"
    report_ref: VersionRef
    policy_ref: VersionRef
    assessment_ref: VersionRef
    receipt_ref: VersionRef
    effect: ExternalEffectState
    reported_at: datetime

    @model_validator(mode="after")
    def _history(self) -> SubmissionHistory:
        _require_refs(self.report_ref, self.policy_ref, (self.assessment_ref,))
        if self.receipt_ref.kind != "report-receipt":
            raise ValueError("history receipt reference kind is invalid")
        if self.effect not in {
            ExternalEffectState.ACCEPTED,
            ExternalEffectState.CONFIRMED,
        }:
            raise ValueError("history requires accepted or confirmed receipt")
        if self.reported_at.tzinfo is None or self.reported_at.utcoffset() is None:
            raise ValueError("history time must be timezone-aware")
        return self


class ProviderEvidence(_ClosedModel):
    """Trusted bounded provider evidence supplied for explicit reconciliation."""

    provider: Literal["microsoft-graph", "synthetic"]
    reference: ShortText
    detail: SafeDetail


class ReconciliationEvidence(_ClosedModel):
    """Durable recovery proof saved under a separate authorized claim."""

    record_type: Literal["reconciliation"] = "reconciliation"
    report_ref: VersionRef
    policy_ref: VersionRef
    part_number: Annotated[int, Field(ge=1, le=128)]
    target: ClaimToken
    decision: ExternalEffectState
    evidence: Annotated[tuple[ProviderEvidence, ...], Field(max_length=16)]

    @model_validator(mode="after")
    def _proof(self) -> ReconciliationEvidence:
        _require_refs(self.report_ref, self.policy_ref, ())
        if self.decision not in {
            ExternalEffectState.UNKNOWN,
            ExternalEffectState.ACCEPTED,
            ExternalEffectState.CONFIRMED,
            ExternalEffectState.REJECTED,
        }:
            raise ValueError("reconciliation decision is invalid")
        if self.decision is not ExternalEffectState.UNKNOWN and not self.evidence:
            raise ValueError("definite reconciliation requires provider evidence")
        return self


class ReportReconciliationPlan(_ClosedModel):
    """Bind explicit recovery to one exact report part and original attempt."""

    schema_version: Literal["1"] = "1"
    identity: ShortText
    target: ClaimToken
    report_ref: VersionRef
    policy_ref: VersionRef
    part_number: Annotated[int, Field(ge=1, le=128)]
    decision: ExternalEffectState
    provider_evidence: Annotated[tuple[ProviderEvidence, ...], Field(max_length=16)]
    recovery_attempt: AttemptIdentity
    recovery_result_id: ShortText
    code_version: ShortText
    claim_lease_seconds: Annotated[float, Field(gt=0.0, le=600.0)]

    @model_validator(mode="after")
    def _closed(self) -> ReportReconciliationPlan:
        _require_refs(self.report_ref, self.policy_ref, ())
        if (
            self.decision is not ExternalEffectState.UNKNOWN
            and not self.provider_evidence
        ):
            raise ValueError("definite reconciliation requires provider evidence")
        return self


SubmissionRecord = (
    SubmissionAttempt | SubmissionReceipt | SubmissionHistory | ReconciliationEvidence
)


def _require_refs(
    report_ref: VersionRef,
    policy_ref: VersionRef,
    assessment_refs: tuple[VersionRef, ...],
) -> None:
    if report_ref.kind != "report" or policy_ref.kind != "report-policy":
        raise ValueError("delivery report/policy reference kind is invalid")
    if any(ref.kind != "topic-assessment" for ref in assessment_refs):
        raise ValueError("delivery assessment reference kind is invalid")
