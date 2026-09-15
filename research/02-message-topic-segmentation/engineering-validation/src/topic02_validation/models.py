"""Independent data contracts for Topic 02 engineering validation.

The contracts distinguish joint membership from alternative/uncertain assignment.
They are research-only and do not prescribe msgloom production architecture.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Iterable

SCHEMA_VERSION = "topic02-engineering-v1"


@dataclass(frozen=True, order=True)
class Span:
    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < self.start:
            raise ValueError(f"invalid span {self.start}:{self.end}")

    @property
    def length(self) -> int:
        return self.end - self.start

    def extract(self, text: str) -> str:
        if self.end > len(text):
            raise ValueError(f"span {self} exceeds text length {len(text)}")
        return text[self.start:self.end]

    def overlap(self, other: "Span") -> int:
        return max(0, min(self.end, other.end) - max(self.start, other.start))

    def iou(self, other: "Span") -> float:
        inter = self.overlap(other)
        union = self.length + other.length - inter
        return inter / union if union else 1.0

    def to_dict(self) -> dict[str, int]:
        return {"start": self.start, "end": self.end}

    @classmethod
    def from_dict(cls, value: dict[str, int]) -> "Span":
        return cls(int(value["start"]), int(value["end"]))


@dataclass(frozen=True)
class TopicDefinition:
    topic_id: str
    description: str
    signature_terms: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.topic_id or not self.description:
            raise ValueError("topic_id/description must be non-empty")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceSpan:
    span_id: str
    span: Span
    text: str
    origin: str = "authored"  # authored | quoted | context
    kind: str = "topic_evidence"  # topic_evidence or decision-bearing subtype

    def __post_init__(self) -> None:
        if self.origin not in {"authored", "quoted", "context"}:
            raise ValueError(f"unsupported origin {self.origin}")
        allowed = {
            "topic_evidence", "condition", "exception", "deadline",
            "approval_constraint", "decision", "supporting_evidence",
            "new_content", "heading", "context_reference",
        }
        if self.kind not in allowed:
            raise ValueError(f"unsupported span kind {self.kind}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "span_id": self.span_id,
            "span": self.span.to_dict(),
            "text": self.text,
            "origin": self.origin,
            "kind": self.kind,
        }


@dataclass(frozen=True)
class MembershipGold:
    """Gold assignment for one evidence span.

    `required_topics` means all listed topics jointly apply.
    `alternative_topic_sets` means the evidence is genuinely ambiguous and any one
    listed set would be acceptable; this is not the same as joint membership.
    """

    span_id: str
    required_topics: tuple[str, ...] = ()
    alternative_topic_sets: tuple[tuple[str, ...], ...] = ()
    abstention_allowed: bool = False
    notes: str = ""

    def __post_init__(self) -> None:
        if self.required_topics and self.alternative_topic_sets:
            raise ValueError("required_topics and alternatives are mutually exclusive")
        if not self.required_topics and not self.alternative_topic_sets and not self.abstention_allowed:
            raise ValueError("membership must specify required topics, alternatives, or allowed abstention")
        for alt in self.alternative_topic_sets:
            if not alt:
                raise ValueError("alternative topic set cannot be empty")

    @property
    def ambiguous(self) -> bool:
        return bool(self.alternative_topic_sets)

    def to_dict(self) -> dict[str, Any]:
        return {
            "span_id": self.span_id,
            "required_topics": list(self.required_topics),
            "alternative_topic_sets": [list(x) for x in self.alternative_topic_sets],
            "abstention_allowed": self.abstention_allowed,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class TopicObjectGold:
    topic_id: str
    span_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.span_ids:
            raise ValueError("topic object must contain at least one span")

    @property
    def non_contiguous(self) -> bool:
        return len(self.span_ids) > 1

    def to_dict(self) -> dict[str, Any]:
        return {"topic_id": self.topic_id, "span_ids": list(self.span_ids)}


@dataclass(frozen=True)
class ContextStepGold:
    step_id: str
    available_context_ids: tuple[str, ...]
    expected_span_topic_sets: tuple[tuple[str, tuple[str, ...]], ...]
    expected_abstentions: tuple[str, ...] = ()
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "available_context_ids": list(self.available_context_ids),
            "expected_span_topic_sets": [
                {"span_id": sid, "topics": list(topics)} for sid, topics in self.expected_span_topic_sets
            ],
            "expected_abstentions": list(self.expected_abstentions),
            "notes": self.notes,
        }


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    description: str
    text: str
    topics: tuple[TopicDefinition, ...]
    spans: tuple[EvidenceSpan, ...]
    memberships: tuple[MembershipGold, ...]
    topic_objects: tuple[TopicObjectGold, ...]
    context_texts: tuple[tuple[str, str], ...] = ()
    context_steps: tuple[ContextStepGold, ...] = ()
    tags: tuple[str, ...] = ()

    def span(self, span_id: str) -> EvidenceSpan:
        for span in self.spans:
            if span.span_id == span_id:
                return span
        raise KeyError(span_id)

    def topic(self, topic_id: str) -> TopicDefinition:
        for topic in self.topics:
            if topic.topic_id == topic_id:
                return topic
        raise KeyError(topic_id)

    def validate(self) -> None:
        span_ids = [s.span_id for s in self.spans]
        topic_ids = [t.topic_id for t in self.topics]
        if len(span_ids) != len(set(span_ids)):
            raise ValueError(f"{self.case_id}: duplicate span IDs")
        if len(topic_ids) != len(set(topic_ids)):
            raise ValueError(f"{self.case_id}: duplicate topic IDs")
        spans = set(span_ids); topics = set(topic_ids)
        for s in self.spans:
            if s.span.extract(self.text) != s.text:
                raise ValueError(f"{self.case_id}:{s.span_id}: span text mismatch")
        membership_ids = [m.span_id for m in self.memberships]
        if len(membership_ids) != len(set(membership_ids)):
            raise ValueError(f"{self.case_id}: duplicate membership rows")
        for m in self.memberships:
            if m.span_id not in spans:
                raise ValueError(f"{self.case_id}: unknown membership span {m.span_id}")
            all_topics = set(m.required_topics)
            for alt in m.alternative_topic_sets:
                all_topics.update(alt)
            if not all_topics <= topics:
                raise ValueError(f"{self.case_id}:{m.span_id}: unknown topics {all_topics-topics}")
        for obj in self.topic_objects:
            if obj.topic_id not in topics or not set(obj.span_ids) <= spans:
                raise ValueError(f"{self.case_id}: invalid topic object {obj}")
        ctx_ids = {k for k, _ in self.context_texts}
        for step in self.context_steps:
            if not set(step.available_context_ids) <= ctx_ids:
                raise ValueError(f"{self.case_id}:{step.step_id}: unknown context")
            for sid, tids in step.expected_span_topic_sets:
                if sid not in spans or not set(tids) <= topics:
                    raise ValueError(f"{self.case_id}:{step.step_id}: invalid expected assignment")
            if not set(step.expected_abstentions) <= spans:
                raise ValueError(f"{self.case_id}:{step.step_id}: unknown expected abstention")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "case_id": self.case_id,
            "description": self.description,
            "text": self.text,
            "topics": [t.to_dict() for t in self.topics],
            "spans": [s.to_dict() for s in self.spans],
            "memberships": [m.to_dict() for m in self.memberships],
            "topic_objects": [o.to_dict() for o in self.topic_objects],
            "context_texts": [{"context_id": k, "text": v} for k, v in self.context_texts],
            "context_steps": [x.to_dict() for x in self.context_steps],
            "tags": list(self.tags),
        }


def validate_cases(cases: Iterable[BenchmarkCase]) -> None:
    seen: set[str] = set()
    for case in cases:
        if case.case_id in seen:
            raise ValueError(f"duplicate case ID {case.case_id}")
        seen.add(case.case_id)
        case.validate()
