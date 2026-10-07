"""Immutable contracts for Phase 1 report selection and saved reports."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, model_validator

from msgloom.contracts import Limitation, ResultRef, SemanticDataRef, VersionRef
from msgloom.triage import (
    Deadline,
    Development,
    Priority,
    Risk,
    TriageAction,
    TriageEvidence,
)

ShortText = Annotated[str, Field(min_length=1, max_length=512)]
DetailText = Annotated[str, Field(min_length=1, max_length=8_000)]


class _FrozenModel(BaseModel):
    """Reject coercion, mutation, and undeclared report fields."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


class DueMode(StrEnum):
    """Explicitly define how priority-eligible topics become due."""

    ALL_MATCHING = "all-matching"
    DEADLINE_BY = "deadline-by"


class RepeatMode(StrEnum):
    """Explicitly define whether a reported assessment can repeat."""

    NEVER = "never"
    AFTER_INTERVAL = "after-interval"


class ReminderMode(StrEnum):
    """Explicitly define reminder eligibility for prior assessments."""

    DISABLED = "disabled"
    AFTER_INTERVAL = "after-interval"


class ReportDestination(_FrozenModel):
    """Bind output to the configured owner destination identity."""

    owner_identity: ShortText
    destination_identity: ShortText


class ReportPolicy(_FrozenModel):
    """Trusted explicit report policy with no implicit schedule defaults."""

    policy_ref: VersionRef
    destination: ReportDestination
    due_at: datetime
    timezone: ShortText
    priorities: Annotated[tuple[Priority, ...], Field(min_length=1, max_length=4)]
    due_mode: DueMode
    repeat_mode: RepeatMode
    repeat_after_seconds: int | None
    reminder_mode: ReminderMode
    reminder_after_seconds: int | None

    @model_validator(mode="after")
    def _validate_policy(self) -> ReportPolicy:
        if self.due_at.tzinfo is None or self.due_at.utcoffset() is None:
            raise ValueError("report due time must be timezone-aware")
        try:
            zone = ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("report timezone must be a real IANA timezone") from None
        local = self.due_at.astimezone(zone)
        if (
            local.replace(tzinfo=None) != self.due_at.replace(tzinfo=None)
            or local.utcoffset() != self.due_at.utcoffset()
        ):
            raise ValueError("report due time must be coherent with its timezone")
        if len(self.priorities) != len(set(self.priorities)):
            raise ValueError("report priorities must be unique")
        self._validate_interval(self.repeat_mode, self.repeat_after_seconds, "repeat")
        self._validate_interval(
            self.reminder_mode, self.reminder_after_seconds, "reminder"
        )
        return self

    @staticmethod
    def _validate_interval(mode: StrEnum, seconds: int | None, field: str) -> None:
        enabled = mode.value == "after-interval"
        if enabled and (seconds is None or seconds < 1):
            raise ValueError(f"{field} interval must be positive when enabled")
        if not enabled and seconds is not None:
            raise ValueError(f"{field} interval requires after-interval mode")


class PriorReportState(_FrozenModel):
    """Narrow delivery-owned evidence keyed by policy and assessment."""

    policy_ref: VersionRef
    assessment_ref: VersionRef
    report_ref: VersionRef
    reported_at: datetime
    evidence_ref: ResultRef | None = None

    @model_validator(mode="after")
    def _aware(self) -> PriorReportState:
        if self.reported_at.tzinfo is None or self.reported_at.utcoffset() is None:
            raise ValueError("prior report time must be timezone-aware")
        return self


class PendingAssessmentWarning(_FrozenModel):
    """Expose newer unfinished work without replacing an accepted assessment."""

    topic_ref: VersionRef
    selected_assessment_ref: VersionRef
    pending_ref: VersionRef
    detail: DetailText


class AssessmentSelection(_FrozenModel):
    """Explicit trusted choice when several assessments exist for one topic."""

    topic_ref: VersionRef
    assessment_ref: VersionRef


class SourceLink(_FrozenModel):
    """Safe saved link for an exact source message reference."""

    source_ref: VersionRef
    url: Annotated[str, Field(min_length=1, max_length=2_048)]


class ReportSelectionPlan(_FrozenModel):
    """Finite trusted inputs used to freeze one report selection."""

    request_targets: Annotated[
        tuple[VersionRef, ...], Field(min_length=1, max_length=128)
    ]
    triage_results: Annotated[
        tuple[ResultRef, ...], Field(min_length=1, max_length=128)
    ]
    assessment_selections: Annotated[
        tuple[AssessmentSelection, ...], Field(max_length=256)
    ]
    prior_state: Annotated[tuple[PriorReportState, ...], Field(max_length=512)]
    pending_warnings: Annotated[
        tuple[PendingAssessmentWarning, ...], Field(max_length=256)
    ]
    source_links: Annotated[tuple[SourceLink, ...], Field(max_length=1024)]

    @model_validator(mode="after")
    def _unique_inputs(self) -> ReportSelectionPlan:
        if len(self.request_targets) != len(set(self.request_targets)):
            raise ValueError("request target references must be unique")
        if len(self.triage_results) != len(set(self.triage_results)):
            raise ValueError("triage result references must be unique")
        pairs = tuple(
            (x.topic_ref, x.assessment_ref) for x in self.assessment_selections
        )
        if len(pairs) != len(set(pairs)):
            raise ValueError("assessment selections must be unique")
        topics = tuple(x.topic_ref for x in self.assessment_selections)
        if len(topics) != len(set(topics)):
            raise ValueError("assessment selection topics must be unique")
        if any(x.evidence_ref is None for x in self.prior_state):
            raise ValueError("prior report state requires durable evidence")
        states = tuple((x.policy_ref, x.assessment_ref) for x in self.prior_state)
        if len(states) != len(set(states)):
            raise ValueError(
                "prior report state must be unique per policy and assessment"
            )
        links = tuple(x.source_ref for x in self.source_links)
        if len(links) != len(set(links)):
            raise ValueError("source links must be unique")
        return self


class FrozenReportInput(_FrozenModel):
    """Bind one admitted result to its exact semantic payload reference."""

    result_ref: ResultRef
    semantic_data_ref: SemanticDataRef


class FrozenRendererConfig(_FrozenModel):
    """Persist the exact finite rendering choices used for a selection."""

    max_part_bytes: Annotated[int, Field(ge=1_024, le=4 * 1024 * 1024)]
    max_total_bytes: Annotated[int, Field(ge=2_048, le=8 * 1024 * 1024)]
    max_parts: Annotated[int, Field(ge=1, le=128)]

    @model_validator(mode="after")
    def _coherent(self) -> FrozenRendererConfig:
        if self.max_total_bytes < self.max_part_bytes:
            raise ValueError("total output bound must allow one full part")
        return self


class FrozenReportHistory(_FrozenModel):
    """Freeze one verified delivery-history dependency and integrity basis."""

    evidence_ref: ResultRef
    report_ref: VersionRef
    policy_ref: VersionRef
    assessment_ref: VersionRef
    reported_at: datetime
    receipt_ref: VersionRef
    semantic_data_ref: SemanticDataRef | None = None

    @model_validator(mode="after")
    def _closed_history(self) -> FrozenReportHistory:
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
        return self


class FrozenReportSelection(_FrozenModel):
    """Durable pre-render snapshot of one report selection decision."""

    schema_version: Literal["1"] = "1"
    report_ref: VersionRef
    policy: ReportPolicy
    plan: ReportSelectionPlan
    renderer: FrozenRendererConfig
    code_version: ShortText
    expected_parameters: Annotated[tuple[tuple[str, str], ...], Field(max_length=32)]
    inputs: Annotated[
        tuple[FrozenReportInput, ...], Field(min_length=1, max_length=128)
    ]
    selected: Annotated[
        tuple[AssessmentSelection, ...], Field(min_length=1, max_length=256)
    ]
    history: Annotated[tuple[FrozenReportHistory, ...], Field(max_length=512)] = ()

    @model_validator(mode="after")
    def _closed_selection(self) -> FrozenReportSelection:
        if self.report_ref.kind != "report":
            raise ValueError("frozen report reference must be report kind")
        if self.policy.policy_ref.kind != "report-policy":
            raise ValueError("frozen policy reference must be report-policy kind")
        if tuple(item.result_ref for item in self.inputs) != self.plan.triage_results:
            raise ValueError("frozen inputs must exactly match the selection plan")
        for item in self.inputs:
            if (
                item.result_ref.kind != "triage"
                or item.result_ref.schema_version != "1"
                or item.semantic_data_ref.kind != "triage"
                or item.semantic_data_ref.schema_version != "1"
            ):
                raise ValueError("frozen input must bind exact triage@1 schemas")
        pairs = tuple((x.topic_ref, x.assessment_ref) for x in self.selected)
        if len(pairs) != len(set(pairs)):
            raise ValueError("frozen selected assessments must be unique")
        for item in self.selected:
            if (
                item.topic_ref.kind != "topic"
                or item.assessment_ref.kind != "topic-assessment"
            ):
                raise ValueError("frozen selected assessment identities are malformed")
        expected_history = tuple(x.evidence_ref for x in self.plan.prior_state)
        if tuple(x.evidence_ref for x in self.history) != expected_history:
            raise ValueError("frozen history must exactly match prior-state evidence")
        return self


class ReportTopic(_FrozenModel):
    """Frozen complete topic detail retained in a saved report."""

    topic_ref: VersionRef
    assessment_ref: VersionRef
    title: ShortText
    source_refs: Annotated[tuple[VersionRef, ...], Field(min_length=1, max_length=128)]
    priority: Priority
    reason: DetailText
    developments: Annotated[tuple[Development, ...], Field(max_length=64)]
    actions: Annotated[tuple[TriageAction, ...], Field(max_length=64)]
    deadlines: Annotated[tuple[Deadline, ...], Field(max_length=32)]
    risks: Annotated[tuple[Risk, ...], Field(max_length=64)]
    evidence: Annotated[tuple[TriageEvidence, ...], Field(max_length=512)]
    limitations: Annotated[tuple[Limitation, ...], Field(max_length=64)]
    source_links: Annotated[tuple[SourceLink, ...], Field(max_length=128)]


class ReportOverviewItem(_FrozenModel):
    """Overview coverage for one exact selected topic assessment."""

    topic_ref: VersionRef
    assessment_ref: VersionRef
    title: ShortText
    priority: Priority
    developments: Annotated[tuple[str, ...], Field(max_length=64)]
    actions: Annotated[tuple[str, ...], Field(max_length=64)]
    deadlines: Annotated[tuple[str, ...], Field(max_length=32)]
    risks: Annotated[tuple[str, ...], Field(max_length=64)]


class ReportPart(_FrozenModel):
    """Exact saved HTML/plain output part for deterministic replay."""

    part_number: int
    topic_refs: Annotated[tuple[VersionRef, ...], Field(min_length=1, max_length=128)]
    plain_text: str
    html: str

    @model_validator(mode="after")
    def _positive_part(self) -> ReportPart:
        if self.part_number < 1:
            raise ValueError("report part number must be positive")
        return self


class SavedReport(_FrozenModel):
    """Canonical report@1 semantic product and exact rendered outputs."""

    schema_version: Literal["1"] = "1"
    report_ref: VersionRef
    policy_ref: VersionRef
    destination: ReportDestination
    due_at: datetime
    timezone: ShortText
    source_triage_results: Annotated[
        tuple[ResultRef, ...], Field(min_length=1, max_length=128)
    ]
    topics: Annotated[tuple[ReportTopic, ...], Field(min_length=1, max_length=256)]
    overview: Annotated[
        tuple[ReportOverviewItem, ...], Field(min_length=1, max_length=256)
    ]
    pending_warnings: Annotated[
        tuple[PendingAssessmentWarning, ...], Field(max_length=256)
    ]
    limitations: Annotated[tuple[Limitation, ...], Field(max_length=256)]
    renderer_version: ShortText
    parts: Annotated[tuple[ReportPart, ...], Field(min_length=1, max_length=128)]

    @model_validator(mode="after")
    def _aware_and_unique(self) -> SavedReport:
        if self.due_at.tzinfo is None or self.due_at.utcoffset() is None:
            raise ValueError("saved report due time must be timezone-aware")
        if self.report_ref.kind != "report" or self.policy_ref.kind != "report-policy":
            raise ValueError("saved report reference kinds are invalid")
        if any(
            x.kind != "triage" or x.schema_version != "1"
            for x in self.source_triage_results
        ):
            raise ValueError("saved report source results must be triage@1")
        topics = tuple(x.topic_ref for x in self.topics)
        if len(topics) != len(set(topics)):
            raise ValueError("saved report topic identities must be unique")
        if any(x.kind != "topic" for x in topics):
            raise ValueError("saved report topic reference kind is invalid")
        numbers = tuple(x.part_number for x in self.parts)
        if numbers != tuple(range(1, len(self.parts) + 1)):
            raise ValueError("saved report parts must be uniquely consecutive")
        mapped = tuple(ref for part in self.parts for ref in part.topic_refs)
        if mapped != topics:
            raise ValueError(
                "saved report topic-to-part mapping must be exact and ordered"
            )
        return self
