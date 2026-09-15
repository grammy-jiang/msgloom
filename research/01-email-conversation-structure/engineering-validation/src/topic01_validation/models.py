"""Data contracts for Topic 01 engineering validation.

Research-only structures. They intentionally keep ambiguity and missing evidence
explicit instead of forcing a tree or a unique source.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Iterable

SCHEMA_VERSION = "topic01-engineering-v1"


@dataclass(frozen=True, order=True)
class Span:
    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < self.start:
            raise ValueError(f"invalid span: {self.start}:{self.end}")

    @property
    def length(self) -> int:
        return self.end - self.start

    def extract(self, text: str) -> str:
        if self.end > len(text):
            raise ValueError(f"span {self} outside text length {len(text)}")
        return text[self.start : self.end]

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
class SourceSpan:
    message_id: str
    span: Span

    def to_dict(self) -> dict[str, Any]:
        return {"message_id": self.message_id, "span": self.span.to_dict()}


@dataclass(frozen=True)
class QuoteGold:
    occurrence_id: str
    message_id: str
    occurrence_span: Span
    source_candidates: tuple[SourceSpan, ...] = ()
    source_missing: bool = False
    source_semantics: str = "alternatives"
    marker_style: str = "plain_gt"
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.occurrence_id or not self.message_id:
            raise ValueError("quote occurrence/message ID must be non-empty")
        if self.source_missing and self.source_candidates:
            raise ValueError("source_missing cannot coexist with available candidates")
        if self.source_semantics not in {"alternatives", "joint"}:
            raise ValueError(f"unsupported source semantics: {self.source_semantics}")

    @property
    def ambiguous(self) -> bool:
        return self.source_semantics == "alternatives" and len(self.source_candidates) > 1

    @property
    def jointly_required(self) -> bool:
        return self.source_semantics == "joint" and len(self.source_candidates) > 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "occurrence_id": self.occurrence_id,
            "message_id": self.message_id,
            "occurrence_span": self.occurrence_span.to_dict(),
            "source_candidates": [x.to_dict() for x in self.source_candidates],
            "source_missing": self.source_missing,
            "source_semantics": self.source_semantics,
            "marker_style": self.marker_style,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class RelationGold:
    message_id: str
    relation_type: str
    target_ids: tuple[str, ...] = ()
    missing_target_ids: tuple[str, ...] = ()
    ambiguous: bool = False
    notes: str = ""

    def __post_init__(self) -> None:
        if self.relation_type not in {"reply_parent", "ancestry"}:
            raise ValueError(f"unsupported relation type: {self.relation_type}")
        overlap = set(self.target_ids) & set(self.missing_target_ids)
        if overlap:
            raise ValueError(f"targets cannot be both available and missing: {overlap}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LabeledSpan:
    span_id: str
    message_id: str
    span: Span
    kind: str
    text: str
    notes: str = ""

    def __post_init__(self) -> None:
        if self.kind not in {"unique", "decision_bearing", "condition", "deadline", "new_content"}:
            raise ValueError(f"unsupported labeled span kind: {self.kind}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "span_id": self.span_id,
            "message_id": self.message_id,
            "span": self.span.to_dict(),
            "kind": self.kind,
            "text": self.text,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class MessageFixture:
    message_id: str
    raw_rfc822: bytes
    expected_text: str
    arrival_rank: int
    internet_message_id: str
    subject: str
    content_kind: str = "plain"
    notes: str = ""

    def to_dict(self, include_raw: bool = False) -> dict[str, Any]:
        d: dict[str, Any] = {
            "message_id": self.message_id,
            "expected_text": self.expected_text,
            "arrival_rank": self.arrival_rank,
            "internet_message_id": self.internet_message_id,
            "subject": self.subject,
            "content_kind": self.content_kind,
            "notes": self.notes,
        }
        if include_raw:
            d["raw_rfc822_utf8"] = self.raw_rfc822.decode("utf-8", errors="replace")
        return d


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    description: str
    family: str
    messages: tuple[MessageFixture, ...]
    relations: tuple[RelationGold, ...] = ()
    quotes: tuple[QuoteGold, ...] = ()
    spans: tuple[LabeledSpan, ...] = ()
    replay_orders: tuple[tuple[str, ...], ...] = ()
    tags: tuple[str, ...] = ()

    def message(self, message_id: str) -> MessageFixture:
        for message in self.messages:
            if message.message_id == message_id:
                return message
        raise KeyError(message_id)

    def validate(self) -> None:
        ids = [m.message_id for m in self.messages]
        if len(ids) != len(set(ids)):
            raise ValueError(f"{self.case_id}: duplicate message IDs")
        id_set = set(ids)
        for relation in self.relations:
            if relation.message_id not in id_set:
                raise ValueError(f"{self.case_id}: relation message missing: {relation.message_id}")
        for quote in self.quotes:
            if quote.message_id not in id_set:
                raise ValueError(f"{self.case_id}: quote message missing: {quote.message_id}")
            text = self.message(quote.message_id).expected_text
            quote.occurrence_span.extract(text)
            for candidate in quote.source_candidates:
                if candidate.message_id not in id_set:
                    raise ValueError(f"{self.case_id}: candidate missing: {candidate.message_id}")
                candidate.span.extract(self.message(candidate.message_id).expected_text)
        for labeled in self.spans:
            if labeled.message_id not in id_set:
                raise ValueError(f"{self.case_id}: labeled span message missing: {labeled.message_id}")
            actual = labeled.span.extract(self.message(labeled.message_id).expected_text)
            if actual != labeled.text:
                raise ValueError(
                    f"{self.case_id}/{labeled.span_id}: span text mismatch {actual!r} != {labeled.text!r}"
                )
        for order in self.replay_orders:
            if set(order) != id_set or len(order) != len(ids):
                raise ValueError(f"{self.case_id}: replay order is not a permutation: {order}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "case_id": self.case_id,
            "description": self.description,
            "family": self.family,
            "messages": [m.to_dict() for m in self.messages],
            "relations": [r.to_dict() for r in self.relations],
            "quotes": [q.to_dict() for q in self.quotes],
            "spans": [s.to_dict() for s in self.spans],
            "replay_orders": [list(x) for x in self.replay_orders],
            "tags": list(self.tags),
        }


def find_span(text: str, needle: str, *, occurrence: int = 0) -> Span:
    """Find a deterministic occurrence of *needle* in text."""
    start = -1
    pos = 0
    for _ in range(occurrence + 1):
        start = text.find(needle, pos)
        if start < 0:
            raise ValueError(f"needle not found: {needle!r}")
        pos = start + 1
    return Span(start, start + len(needle))


def validate_cases(cases: Iterable[BenchmarkCase]) -> None:
    seen: set[str] = set()
    for case in cases:
        if case.case_id in seen:
            raise ValueError(f"duplicate case_id: {case.case_id}")
        seen.add(case.case_id)
        case.validate()
