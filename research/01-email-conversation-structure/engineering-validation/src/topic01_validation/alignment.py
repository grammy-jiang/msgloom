"""Explainable quote/source matching baseline for Topic 01 experiments."""
from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Iterable

from .extraction import unquote_plain
from .models import Span


@dataclass(frozen=True)
class MatchCandidate:
    source_message_id: str
    source_span: Span
    score: float
    exact: bool
    matched_text: str


@dataclass(frozen=True)
class Resolution:
    candidates: tuple[MatchCandidate, ...]
    accepted_source_id: str | None
    confidence: float
    abstained: bool
    reason: str


def _collapse_with_map(text: str) -> tuple[str, list[int]]:
    """Case-fold and collapse whitespace while retaining source positions."""
    out: list[str] = []
    posmap: list[int] = []
    pending_space = False
    pending_pos = 0
    for i, ch in enumerate(text):
        if ch.isspace():
            if out:
                pending_space = True
                pending_pos = i
            continue
        if pending_space:
            out.append(" ")
            posmap.append(pending_pos)
            pending_space = False
        folded = ch.casefold()
        for c in folded:
            out.append(c)
            posmap.append(i)
    # No trailing spaces are emitted.
    return "".join(out), posmap


def normalize_quote(text: str, *, plain_markers: bool = True) -> str:
    if plain_markers:
        text = unquote_plain(text)
    normalized, _ = _collapse_with_map(text)
    return normalized.strip()


def _span_from_normalized(posmap: list[int], start: int, end: int, source_len: int) -> Span:
    if not posmap or end <= start:
        return Span(0, 0)
    start = max(0, min(start, len(posmap) - 1))
    end = max(start + 1, min(end, len(posmap)))
    original_start = posmap[start]
    original_end = posmap[end - 1] + 1
    return Span(original_start, min(original_end, source_len))


def best_match(
    quote_text: str,
    source_text: str,
    *,
    source_message_id: str,
    plain_markers: bool = True,
    min_score: float = 0.50,
) -> MatchCandidate | None:
    query = normalize_quote(quote_text, plain_markers=plain_markers)
    source_norm, posmap = _collapse_with_map(source_text)
    if not query or not source_norm:
        return None

    exact_start = source_norm.find(query)
    if exact_start >= 0:
        span = _span_from_normalized(posmap, exact_start, exact_start + len(query), len(source_text))
        return MatchCandidate(source_message_id, span, 1.0, True, span.extract(source_text))

    # Research baseline: best same-length local window. This handles small edits
    # while deliberately not pretending to be a complete sequence aligner.
    qlen = len(query)
    if len(source_norm) <= qlen:
        starts = [0]
    else:
        starts = range(0, len(source_norm) - qlen + 1)
    best_score = -1.0
    best_start = 0
    best_end = min(len(source_norm), qlen)
    for start in starts:
        end = min(len(source_norm), start + qlen)
        window = source_norm[start:end]
        score = SequenceMatcher(None, query, window, autojunk=False).ratio()
        if score > best_score:
            best_score = score
            best_start, best_end = start, end
    if best_score < min_score:
        return None
    span = _span_from_normalized(posmap, best_start, best_end, len(source_text))
    return MatchCandidate(source_message_id, span, best_score, False, span.extract(source_text))


def candidate_matches(
    quote_text: str,
    sources: dict[str, str],
    *,
    plain_markers: bool = True,
    min_score: float = 0.50,
) -> tuple[MatchCandidate, ...]:
    matches: list[MatchCandidate] = []
    for message_id, source_text in sorted(sources.items()):
        candidate = best_match(
            quote_text,
            source_text,
            source_message_id=message_id,
            plain_markers=plain_markers,
            min_score=min_score,
        )
        if candidate is not None:
            matches.append(candidate)
    return tuple(sorted(matches, key=lambda x: (-x.score, x.source_message_id, x.source_span.start)))


def resolve_candidates(
    matches: Iterable[MatchCandidate],
    *,
    accept_threshold: float = 0.82,
    ambiguity_margin: float = 0.08,
) -> Resolution:
    ordered = tuple(sorted(matches, key=lambda x: (-x.score, x.source_message_id, x.source_span.start)))
    if not ordered:
        return Resolution((), None, 0.0, True, "no_candidate")
    best = ordered[0]
    second = ordered[1].score if len(ordered) > 1 else 0.0
    margin = max(0.0, best.score - second)

    # Confidence is deliberately heuristic. It is evaluated, not asserted to be calibrated.
    if len(ordered) == 1:
        confidence = best.score
    else:
        confidence = best.score * min(1.0, 0.5 + margin / max(2 * ambiguity_margin, 1e-9))

    if best.score < accept_threshold:
        return Resolution(ordered, None, confidence, True, "score_below_threshold")
    if len(ordered) > 1 and margin < ambiguity_margin:
        return Resolution(ordered, None, confidence, True, "ambiguous_candidates")
    return Resolution(ordered, best.source_message_id, confidence, False, "accepted")
