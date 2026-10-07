"""Immutable semantic contracts for Phase 1 triage."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from msgloom.contracts import Limitation, VersionRef
from msgloom.preparation import SourceMapping

ShortText = Annotated[str, Field(min_length=1, max_length=256)]
ReasonText = Annotated[str, Field(min_length=1, max_length=2_000)]
DetailText = Annotated[str, Field(min_length=1, max_length=8_000)]


class _FrozenModel(BaseModel):
    """Reject mutation, coercion, and undeclared structured-output fields."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


class Priority(StrEnum):
    """Triage priority in descending business significance."""

    CRITICAL = "critical"
    IMPORTANT = "important"
    NORMAL = "normal"
    LOW_VALUE = "low-value"


_PRIORITY_RANK = {
    Priority.LOW_VALUE: 0,
    Priority.NORMAL: 1,
    Priority.IMPORTANT: 2,
    Priority.CRITICAL: 3,
}


def priority_rank(priority: Priority) -> int:
    """Return the stable comparison rank for a priority."""
    return _PRIORITY_RANK[priority]


class OwnerState(StrEnum):
    """Distinguish a stated owner from unknown and explicitly absent owners."""

    KNOWN = "known"
    UNKNOWN = "unknown"
    ABSENT = "absent"


class ActionOwner(_FrozenModel):
    """Preserve owner knowledge without inventing a placeholder identity."""

    state: OwnerState
    value: ShortText | None = None

    @model_validator(mode="after")
    def _validate_value(self) -> ActionOwner:
        if self.state is OwnerState.KNOWN and self.value is None:
            raise ValueError("known owner requires a value")
        if self.state is not OwnerState.KNOWN and self.value is not None:
            raise ValueError("unknown or absent owner cannot carry a value")
        return self


class EvidenceKind(StrEnum):
    """Separate source statements from semantic interpretation."""

    SOURCE_STATEMENT = "source-statement"
    INTERPRETATION = "interpretation"


class TriageEvidence(_FrozenModel):
    """Ground one bounded statement in an exact prepared source version."""

    kind: EvidenceKind
    source_ref: VersionRef
    statement: DetailText
    mapping: SourceMapping | None = None


EvidenceList = Annotated[tuple[TriageEvidence, ...], Field(min_length=1, max_length=32)]


class Development(_FrozenModel):
    """One source-backed development for a topic."""

    text: DetailText
    evidence: EvidenceList


class TriageAction(_FrozenModel):
    """One source-backed action while preserving owner uncertainty."""

    text: DetailText
    owner: ActionOwner
    evidence: EvidenceList


class Deadline(_FrozenModel):
    """Preserve original deadline language and any bounded interpretation."""

    original_wording: DetailText
    interpreted_at: datetime | None = None
    timezone_basis: ShortText | None = None
    ambiguous: bool
    evidence: EvidenceList

    @model_validator(mode="after")
    def _validate_interpretation(self) -> Deadline:
        if self.interpreted_at is None:
            if self.timezone_basis is not None:
                raise ValueError("timezone basis requires an interpreted deadline")
            return self
        if (
            self.interpreted_at.tzinfo is None
            or self.interpreted_at.utcoffset() is None
        ):
            raise ValueError("interpreted deadline must be timezone-aware")
        if self.timezone_basis is None:
            raise ValueError("interpreted deadline requires a timezone basis")
        return self


class Risk(_FrozenModel):
    """One source-backed risk retained for reporting."""

    text: DetailText
    evidence: EvidenceList


class SourceDispositionKind(StrEnum):
    """Explicit non-topic outcomes for a selected prepared source."""

    EXCLUDED = "excluded"
    INSUFFICIENT_INFORMATION = "insufficient-information"
    NO_REPORTABLE_CONTENT = "no-reportable-content"
    REVIEW_REQUIRED = "review-required"


class SourceDisposition(_FrozenModel):
    """Explain why one selected source is not mapped to a topic."""

    source_ref: VersionRef
    kind: SourceDispositionKind
    reason: ReasonText
    evidence: Annotated[tuple[TriageEvidence, ...], Field(max_length=16)] = ()


class RelationshipStatus(StrEnum):
    """Evidence status for continuity with a prior topic assessment."""

    CONFIRMED = "confirmed"
    UNCERTAIN = "uncertain"


class TopicContinuation(_FrozenModel):
    """Propose continuity against an explicitly supplied prior assessment."""

    prior_topic_ref: VersionRef
    prior_assessment_ref: VersionRef
    status: RelationshipStatus
    reason: ReasonText
    evidence: Annotated[tuple[TriageEvidence, ...], Field(max_length=32)] = ()

    @model_validator(mode="after")
    def _confirmed_has_evidence(self) -> TopicContinuation:
        if self.status is RelationshipStatus.CONFIRMED and not self.evidence:
            raise ValueError("confirmed continuation requires evidence")
        return self


class TopicCandidate(_FrozenModel):
    """
    Carry AI-facing topic content before trusted identity binding.

    The allocation key is opaque application-issued input. Titles are display
    text only and are never used to allocate or reconcile topic identity.
    """

    allocation_key: ShortText
    title: Annotated[str, Field(min_length=1, max_length=512)]
    source_refs: Annotated[tuple[VersionRef, ...], Field(min_length=1, max_length=128)]
    rule_matches: Annotated[tuple[VersionRef, ...], Field(max_length=256)] = ()
    priority: Priority
    reason: ReasonText
    developments: Annotated[tuple[Development, ...], Field(max_length=64)] = ()
    actions: Annotated[tuple[TriageAction, ...], Field(max_length=64)] = ()
    deadlines: Annotated[tuple[Deadline, ...], Field(max_length=32)] = ()
    risks: Annotated[tuple[Risk, ...], Field(max_length=64)] = ()
    limitations: Annotated[tuple[Limitation, ...], Field(max_length=64)] = ()
    continuation: TopicContinuation | None = None

    @model_validator(mode="after")
    def _unique_refs(self) -> TopicCandidate:
        if len(self.source_refs) != len(set(self.source_refs)):
            raise ValueError("topic source references must be unique")
        if len(self.rule_matches) != len(set(self.rule_matches)):
            raise ValueError("topic rule references must be unique")
        return self


class TriageCandidate(_FrozenModel):
    """Bounded structured output accepted from a later isolated AI runner."""

    schema_version: Literal["1"] = "1"
    topics: Annotated[tuple[TopicCandidate, ...], Field(max_length=128)]
    dispositions: Annotated[tuple[SourceDisposition, ...], Field(max_length=256)]


class TopicAllocation(_FrozenModel):
    """Trusted application allocation for one candidate assessment."""

    allocation_key: ShortText
    topic_ref: VersionRef
    assessment_ref: VersionRef


class PriorTopicAssessment(_FrozenModel):
    """Caller-supplied prior assessment eligible for continuity evidence."""

    topic_ref: VersionRef
    assessment_ref: VersionRef
    source_refs: Annotated[tuple[VersionRef, ...], Field(min_length=1, max_length=128)]
    evidence: Annotated[tuple[TriageEvidence, ...], Field(max_length=64)] = ()

    @model_validator(mode="after")
    def _unique_sources(self) -> PriorTopicAssessment:
        if len(self.source_refs) != len(set(self.source_refs)):
            raise ValueError("prior assessment source references must be unique")
        allowed = set(self.source_refs)
        if any(item.source_ref not in allowed for item in self.evidence):
            raise ValueError("prior evidence must reference a prior source")
        return self


class TopicRelationship(_FrozenModel):
    """Saved continuity judgment with exact endpoints and retained evidence."""

    current_topic_ref: VersionRef
    current_assessment_ref: VersionRef
    prior_topic_ref: VersionRef
    prior_assessment_ref: VersionRef
    status: RelationshipStatus
    reason: ReasonText
    evidence: Annotated[tuple[TriageEvidence, ...], Field(max_length=32)] = ()

    @model_validator(mode="after")
    def _validate_relationship(self) -> TopicRelationship:
        if self.current_assessment_ref == self.prior_assessment_ref:
            raise ValueError("continuation requires a new assessment version")
        if self.status is RelationshipStatus.CONFIRMED:
            if self.current_topic_ref != self.prior_topic_ref:
                raise ValueError("confirmed relationship must reuse topic identity")
            if not self.evidence:
                raise ValueError("confirmed relationship requires retained evidence")
        elif self.current_topic_ref == self.prior_topic_ref:
            raise ValueError(
                "uncertain relationship requires a distinct topic identity"
            )
        return self


class TopicAssessment(_FrozenModel):
    """Saved triage assessment after trusted identity reconciliation."""

    topic_ref: VersionRef
    assessment_ref: VersionRef
    title: Annotated[str, Field(min_length=1, max_length=512)]
    source_refs: Annotated[tuple[VersionRef, ...], Field(min_length=1, max_length=128)]
    rule_matches: Annotated[tuple[VersionRef, ...], Field(max_length=256)] = ()
    priority: Priority
    reason: ReasonText
    developments: Annotated[tuple[Development, ...], Field(max_length=64)] = ()
    actions: Annotated[tuple[TriageAction, ...], Field(max_length=64)] = ()
    deadlines: Annotated[tuple[Deadline, ...], Field(max_length=32)] = ()
    risks: Annotated[tuple[Risk, ...], Field(max_length=64)] = ()
    limitations: Annotated[tuple[Limitation, ...], Field(max_length=64)] = ()

    @model_validator(mode="after")
    def _unique_refs(self) -> TopicAssessment:
        if len(self.source_refs) != len(set(self.source_refs)):
            raise ValueError("topic source references must be unique")
        if len(self.rule_matches) != len(set(self.rule_matches)):
            raise ValueError("topic rule references must be unique")
        return self


class TriageData(_FrozenModel):
    """Canonical triage@1 semantic product consumed by later stages."""

    schema_version: Literal["1"] = "1"
    topics: Annotated[tuple[TopicAssessment, ...], Field(max_length=128)]
    dispositions: Annotated[tuple[SourceDisposition, ...], Field(max_length=256)]
    relationships: Annotated[tuple[TopicRelationship, ...], Field(max_length=128)] = ()

    @model_validator(mode="after")
    def _validate_endpoints(self) -> TriageData:
        topic_refs = tuple(topic.topic_ref for topic in self.topics)
        assessment_refs = tuple(topic.assessment_ref for topic in self.topics)
        if len(topic_refs) != len(set(topic_refs)):
            raise ValueError("topic references must be unique within a result")
        if len(assessment_refs) != len(set(assessment_refs)):
            raise ValueError("topic assessment references must be unique")
        disposition_refs = tuple(item.source_ref for item in self.dispositions)
        if len(disposition_refs) != len(set(disposition_refs)):
            raise ValueError("source dispositions must be unique")
        topic_sources = {
            source for topic in self.topics for source in topic.source_refs
        }
        if topic_sources & set(disposition_refs):
            raise ValueError("a source cannot have both topic and disposition")
        current = {(topic.topic_ref, topic.assessment_ref) for topic in self.topics}
        relationship_current = tuple(
            (item.current_topic_ref, item.current_assessment_ref)
            for item in self.relationships
        )
        if any(item not in current for item in relationship_current):
            raise ValueError("relationship current endpoint must be in topics")
        if len(relationship_current) != len(set(relationship_current)):
            raise ValueError("topic relationships must have unique current endpoints")
        topic_by_endpoint = {
            (topic.topic_ref, topic.assessment_ref): topic for topic in self.topics
        }
        for relationship in self.relationships:
            if relationship.status is not RelationshipStatus.CONFIRMED:
                continue
            current_topic = topic_by_endpoint[
                (
                    relationship.current_topic_ref,
                    relationship.current_assessment_ref,
                )
            ]
            current_sources = set(current_topic.source_refs)
            evidence_sources = {item.source_ref for item in relationship.evidence}
            if not evidence_sources & current_sources:
                raise ValueError(
                    "confirmed relationship requires current assessment evidence"
                )
            # A new assessment can reuse the same exact source versions, for
            # example after an explicit prompt change. Reconciliation checks
            # prior-side evidence against the trusted saved prior assessment;
            # source-set disjointness cannot establish that authority here.
        return self


MAX_TRIAGE_CANDIDATE_BYTES = 4 * 1024 * 1024


class TriageCandidateValidationError(ValueError):
    """Expose a safe structured-output validation classification."""


def validate_triage_candidate(payload: str | bytes) -> TriageCandidate:
    """Validate bounded structured JSON without echoing model source values."""
    size = len(payload.encode("utf-8")) if isinstance(payload, str) else len(payload)
    if size > MAX_TRIAGE_CANDIDATE_BYTES:
        raise TriageCandidateValidationError("triage candidate exceeds size limit")
    try:
        return TriageCandidate.model_validate_json(payload, strict=True)
    except (ValidationError, ValueError):
        raise TriageCandidateValidationError(
            "triage candidate failed validation"
        ) from None
