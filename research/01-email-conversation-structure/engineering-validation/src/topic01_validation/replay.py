"""Arrival-order replay baseline for E3.

The baseline recomputes structural assessments from the currently observed set.
It is deliberately simple and exists to test replay/correction contracts rather
than to prescribe msgloom's production architecture.
"""
from __future__ import annotations

from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from typing import Iterable

from .alignment import candidate_matches, resolve_candidates
from .extraction import extract_body, quote_texts
from .models import BenchmarkCase, MessageFixture, Span


@dataclass(frozen=True)
class Assessment:
    relation_id: str
    message_id: str
    kind: str
    status: str
    targets: tuple[str, ...]
    confidence: float
    reason: str
    occurrence_span: Span | None = None

    def canonical(self) -> tuple:
        span = None if self.occurrence_span is None else (self.occurrence_span.start, self.occurrence_span.end)
        return (
            self.relation_id,
            self.message_id,
            self.kind,
            self.status,
            self.targets,
            round(self.confidence, 6),
            self.reason,
            span,
        )


@dataclass(frozen=True)
class Snapshot:
    step: int
    arrived_message_id: str
    observed: tuple[str, ...]
    assessments: tuple[Assessment, ...]


@dataclass(frozen=True)
class ReplayResult:
    order: tuple[str, ...]
    snapshots: tuple[Snapshot, ...]

    @property
    def final(self) -> tuple[tuple, ...]:
        return tuple(sorted(a.canonical() for a in self.snapshots[-1].assessments)) if self.snapshots else ()


def _internet_id_to_fixtures(messages: Iterable[MessageFixture]) -> dict[str, tuple[str, ...]]:
    grouped: dict[str, list[str]] = {}
    for m in messages:
        if not m.internet_message_id:
            continue
        grouped.setdefault(m.internet_message_id, []).append(m.message_id)
    return {key: tuple(sorted(values)) for key, values in grouped.items()}


def _header_ids(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    ids: list[str] = []
    start = 0
    while True:
        left = value.find("<", start)
        if left < 0:
            break
        right = value.find(">", left + 1)
        if right < 0:
            break
        ids.append(value[left : right + 1])
        start = right + 1
    return tuple(ids)


def _transitive_ancestors(message_id: str, direct: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    immediate = set(direct.get(message_id, ()))
    seen: set[str] = set()
    stack = list(immediate)
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        stack.extend(x for x in direct.get(current, ()) if x not in seen)
    return tuple(sorted(seen - immediate))


def assess_observed(
    messages: Iterable[MessageFixture], *, preserve_id_ambiguity: bool = False
) -> tuple[Assessment, ...]:
    observed = tuple(messages)
    by_id = {m.message_id: m for m in observed}
    internet_multi = _internet_id_to_fixtures(observed)

    # Unsafe comparator deliberately collapses duplicate identifiers according to
    # observation order; safe comparator retains the full alternative set.
    internet_single: dict[str, str] = {}
    for m in observed:
        if m.internet_message_id:
            internet_single[m.internet_message_id] = m.message_id

    assessments: list[Assessment] = []
    direct_available: dict[str, tuple[str, ...]] = {}
    parent_status: dict[str, str] = {}

    # Parent relations first so ancestry can be computed from the currently
    # observed graph without treating References adjacency as a direct edge.
    for message in sorted(observed, key=lambda x: x.message_id):
        parsed = BytesParser(policy=policy.default).parsebytes(message.raw_rfc822)
        refs = _header_ids(parsed.get("In-Reply-To"))
        if not refs:
            continue
        missing = tuple(sorted(x for x in refs if x not in internet_multi))
        duplicate_ref = any(len(internet_multi.get(x, ())) > 1 for x in refs)
        if preserve_id_ambiguity:
            available = tuple(sorted({mid for x in refs for mid in internet_multi.get(x, ())}))
        else:
            available = tuple(sorted(internet_single[x] for x in refs if x in internet_single))

        if duplicate_ref and preserve_id_ambiguity:
            status = "ambiguous"
            reason = "duplicate_internet_message_id"
            confidence = 0.5
        elif missing and not available:
            status = "missing"
            reason = "referenced_parent_not_observed"
            confidence = 1.0
        elif missing:
            status = "partial"
            reason = "some_referenced_parents_not_observed"
            confidence = 1.0
        else:
            status = "resolved"
            reason = "in_reply_to_observed"
            confidence = 1.0

        direct_available[message.message_id] = available
        parent_status[message.message_id] = status
        targets = available + tuple(f"MISSING:{x}" for x in missing)
        assessments.append(
            Assessment(
                f"parent:{message.message_id}",
                message.message_id,
                "reply_parent",
                status,
                targets,
                confidence,
                reason,
            )
        )

    for message in sorted(observed, key=lambda x: x.message_id):
        ancestors = _transitive_ancestors(message.message_id, direct_available)
        if ancestors:
            ambiguous_path = parent_status.get(message.message_id) == "ambiguous"
            assessments.append(
                Assessment(
                    f"ancestry:{message.message_id}",
                    message.message_id,
                    "ancestry",
                    "ambiguous" if ambiguous_path else "resolved",
                    ancestors,
                    0.5 if ambiguous_path else 1.0,
                    "transitive_closure_of_observed_reply_parents",
                )
            )

    # Quote-source relations retain occurrence identity through the detected span.
    for message in sorted(observed, key=lambda x: x.message_id):
        body = extract_body(message.raw_rfc822)
        qtexts = quote_texts(body)
        for span, qtext in zip(body.quote_spans, qtexts, strict=True):
            sources = {
                mid: extract_body(src.raw_rfc822).text
                for mid, src in by_id.items()
                if mid != message.message_id
            }
            matches = candidate_matches(qtext, sources, plain_markers=False, min_score=0.50)
            resolution = resolve_candidates(matches)
            if resolution.abstained:
                status = "unresolved"
                targets = tuple(x.source_message_id for x in resolution.candidates[:5])
            else:
                status = "resolved"
                targets = (resolution.accepted_source_id,) if resolution.accepted_source_id else ()
            assessments.append(
                Assessment(
                    f"quote:{message.message_id}:{span.start}:{span.end}",
                    message.message_id,
                    "quote_source",
                    status,
                    targets,
                    resolution.confidence,
                    resolution.reason,
                    span,
                )
            )
    return tuple(sorted(assessments, key=lambda x: x.relation_id))


def replay(
    case: BenchmarkCase, order: tuple[str, ...], *, preserve_id_ambiguity: bool = False
) -> ReplayResult:
    case.validate()
    by_id = {m.message_id: m for m in case.messages}
    if set(order) != set(by_id) or len(order) != len(by_id):
        raise ValueError("order must be an exact message permutation")
    observed: list[MessageFixture] = []
    snapshots: list[Snapshot] = []
    for step, message_id in enumerate(order, 1):
        observed.append(by_id[message_id])
        assessments = assess_observed(observed, preserve_id_ambiguity=preserve_id_ambiguity)
        snapshots.append(Snapshot(step, message_id, tuple(x.message_id for x in observed), assessments))
    return ReplayResult(order, tuple(snapshots))


def replay_metrics(results: Iterable[ReplayResult]) -> dict[str, int | float | None]:
    rs = list(results)
    if not rs:
        return {
            "orders": 0,
            "final_state_agreement": None,
            "relations_changed": 0,
            "relations_removed_before_final": 0,
        }
    reference = rs[0].final
    agreeing = sum(1 for r in rs if r.final == reference)
    changed = 0
    removed = 0
    for r in rs:
        history: dict[str, list[tuple]] = {}
        ever_ids: set[str] = set()
        for snap in r.snapshots:
            for a in snap.assessments:
                ever_ids.add(a.relation_id)
                history.setdefault(a.relation_id, []).append(a.canonical())
        changed += sum(1 for vals in history.values() if len(set(vals)) > 1)
        final_ids = {x[0] for x in r.final}
        removed += len(ever_ids - final_ids)
    return {
        "orders": len(rs),
        "final_state_agreement": agreeing / len(rs),
        "relations_changed": changed,
        "relations_removed_before_final": removed,
    }
