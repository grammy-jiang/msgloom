"""Transparent deterministic unit baselines for EV2.

These are intentionally simple research partitions, not production NLP models.
The primary question is representational ceiling, not segmentation accuracy.
"""
from __future__ import annotations
from dataclasses import dataclass
import re
from .models import Span


@dataclass(frozen=True)
class Unit:
    unit_id: str
    span: Span
    text: str
    unit_type: str


def _trimmed_span(text: str, start: int, end: int) -> Span | None:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return Span(start, end) if end > start else None


def _from_boundaries(text: str, boundaries: set[int], unit_type: str) -> tuple[Unit, ...]:
    pts = sorted({0, len(text), *[p for p in boundaries if 0 < p < len(text)]})
    result: list[Unit] = []
    for a, b in zip(pts, pts[1:]):
        span = _trimmed_span(text, a, b)
        if span is None:
            continue
        result.append(Unit(f"{unit_type}:{len(result)}", span, span.extract(text), unit_type))
    return tuple(result)


def line_units(text: str) -> tuple[Unit, ...]:
    boundaries = {m.end() for m in re.finditer(r"\n+", text)}
    return _from_boundaries(text, boundaries, "line")


def sentence_units(text: str) -> tuple[Unit, ...]:
    boundaries: set[int] = {m.end() for m in re.finditer(r"\n+", text)}
    # Boundary after terminal punctuation when followed by whitespace/end.
    for m in re.finditer(r"[.!?](?=\s|$)", text):
        boundaries.add(m.end())
    return _from_boundaries(text, boundaries, "sentence")


def clause_units(text: str) -> tuple[Unit, ...]:
    boundaries: set[int] = {m.end() for m in re.finditer(r"[;\n]+", text)}
    # Coordinating/subordinating markers begin a new clause. Keep comma with the
    # preceding clause when present; whitespace is trimmed by the unit builder.
    marker = re.compile(r"(?i)(?:(?<=,)|(?<=;)|(?<=\s))\s*\b(?:but|if|only if|except|until|provided|unless)\b")
    for m in marker.finditer(text):
        boundaries.add(m.start())
    # A comma followed by a strong contrasting coordinator is also a boundary.
    for m in re.finditer(r",\s+(?=(?:but|while|whereas)\b)", text, re.I):
        boundaries.add(m.end())
    # Sentence terminal boundaries remain available.
    for u in sentence_units(text):
        boundaries.add(u.span.end)
    return _from_boundaries(text, boundaries, "clause")


def edu_like_units(text: str) -> tuple[Unit, ...]:
    boundaries: set[int] = {u.span.end for u in clause_units(text)}
    # Finer discourse-style boundary starts. This is not claimed to reproduce an
    # RST/SDRT EDU parser; it is a deterministic stress-test partition.
    marker = re.compile(r"(?i)\b(?:because|although|while|whereas|which|that|so that|therefore|however)\b")
    for m in marker.finditer(text):
        boundaries.add(m.start())
    for m in re.finditer(r",\s+", text):
        boundaries.add(m.end())
    return _from_boundaries(text, boundaries, "edu_like")


def hybrid_units(text: str) -> tuple[Unit, ...]:
    # Hybrid exposes every boundary observed by sentence/clause/line/EDU-like
    # baselines as one fine partition, avoiding overlapping units in evaluation.
    boundaries: set[int] = set()
    for fn in (sentence_units, clause_units, edu_like_units, line_units):
        for u in fn(text):
            boundaries.add(u.span.start)
            boundaries.add(u.span.end)
    return _from_boundaries(text, boundaries, "hybrid")


def unitize(text: str, kind: str) -> tuple[Unit, ...]:
    funcs = {
        "sentence": sentence_units,
        "clause": clause_units,
        "edu_like": edu_like_units,
        "hybrid": hybrid_units,
        "line": line_units,
    }
    if kind not in funcs:
        raise KeyError(kind)
    return funcs[kind](text)


def best_cover(gold: Span, units: tuple[Unit, ...]) -> tuple[Span | None, bool]:
    """Return minimal boundary-aligned hull that covers `gold` and exactness.

    For a partition, a gold span can be represented as a consecutive sequence of
    units iff its start and end are available unit boundaries. The hull makes
    broadening/omission explicit when those boundaries are unavailable.
    """
    if not units:
        return None, False
    starts = sorted({u.span.start for u in units})
    ends = sorted({u.span.end for u in units})
    exact = gold.start in starts and gold.end in ends
    left = max((s for s in starts if s <= gold.start), default=min(starts))
    right = min((e for e in ends if e >= gold.end), default=max(ends))
    if right <= left:
        return None, False
    return Span(left, right), exact and left == gold.start and right == gold.end
