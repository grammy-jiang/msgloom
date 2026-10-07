"""Lossless research representation for EV1.

This module demonstrates what must remain representable; it is not a production
schema proposal.
"""
from __future__ import annotations
from dataclasses import dataclass
import json
from typing import Any
from .models import BenchmarkCase, MembershipGold, Span, EvidenceSpan, TopicDefinition, TopicObjectGold, ContextStepGold


@dataclass(frozen=True)
class AssignmentRecord:
    assignment_id: str
    span_id: str
    topic_ids: tuple[str, ...]
    status: str  # resolved | ambiguous | abstained
    alternative_topic_sets: tuple[tuple[str, ...], ...] = ()
    abstention_allowed: bool = False

    def __post_init__(self) -> None:
        if self.status not in {"resolved", "ambiguous", "abstained"}:
            raise ValueError(self.status)
        if self.status == "resolved" and not self.topic_ids:
            raise ValueError("resolved assignment requires topic_ids")
        if self.status == "ambiguous" and not self.alternative_topic_sets:
            raise ValueError("ambiguous assignment requires alternatives")
        if self.status == "abstained" and (self.topic_ids or self.alternative_topic_sets):
            raise ValueError("abstained assignment cannot assert topics")

    def to_dict(self) -> dict[str, Any]:
        return {
            "assignment_id": self.assignment_id,
            "span_id": self.span_id,
            "topic_ids": list(self.topic_ids),
            "status": self.status,
            "alternative_topic_sets": [list(x) for x in self.alternative_topic_sets],
            "abstention_allowed": self.abstention_allowed,
        }


@dataclass(frozen=True)
class TopicRepresentation:
    case_id: str
    text: str
    topics: tuple[TopicDefinition, ...]
    spans: tuple[EvidenceSpan, ...]
    assignments: tuple[AssignmentRecord, ...]
    topic_objects: tuple[TopicObjectGold, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "text": self.text,
            "topics": [t.to_dict() for t in self.topics],
            "spans": [s.to_dict() for s in self.spans],
            "assignments": [a.to_dict() for a in self.assignments],
            "topic_objects": [o.to_dict() for o in self.topic_objects],
        }

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TopicRepresentation":
        topics = tuple(TopicDefinition(x["topic_id"], x["description"], tuple(x.get("signature_terms", []))) for x in d["topics"])
        spans = tuple(EvidenceSpan(x["span_id"], Span.from_dict(x["span"]), x["text"], x.get("origin", "authored"), x.get("kind", "topic_evidence")) for x in d["spans"])
        assignments = tuple(
            AssignmentRecord(
                x["assignment_id"], x["span_id"], tuple(x.get("topic_ids", [])), x["status"],
                tuple(tuple(a) for a in x.get("alternative_topic_sets", [])),
                bool(x.get("abstention_allowed", False)),
            )
            for x in d["assignments"]
        )
        objects = tuple(TopicObjectGold(x["topic_id"], tuple(x["span_ids"])) for x in d["topic_objects"])
        return cls(d["case_id"], d["text"], topics, spans, assignments, objects)


def from_gold(case: BenchmarkCase) -> TopicRepresentation:
    assignments: list[AssignmentRecord] = []
    for m in case.memberships:
        aid = f"assign:{case.case_id}:{m.span_id}"
        if m.required_topics:
            assignments.append(AssignmentRecord(aid, m.span_id, tuple(sorted(m.required_topics)), "resolved", (), m.abstention_allowed))
        elif m.alternative_topic_sets:
            assignments.append(AssignmentRecord(
                aid, m.span_id, (), "ambiguous",
                tuple(tuple(sorted(x)) for x in m.alternative_topic_sets),
                m.abstention_allowed,
            ))
        else:
            assignments.append(AssignmentRecord(aid, m.span_id, (), "abstained", (), m.abstention_allowed))
    return TopicRepresentation(case.case_id, case.text, case.topics, case.spans, tuple(assignments), case.topic_objects)


def round_trip(case: BenchmarkCase) -> TopicRepresentation:
    original = from_gold(case)
    encoded = original.canonical_json()
    decoded = TopicRepresentation.from_dict(json.loads(encoded))
    if decoded.canonical_json() != encoded:
        raise AssertionError("representation round-trip changed canonical content")
    return decoded
