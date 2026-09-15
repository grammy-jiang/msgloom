"""Alternative research quote-occurrence detectors for E2 comparisons."""
from __future__ import annotations

from .alignment import normalize_quote
from .models import Span


def _overlaps(span: Span, others: tuple[Span, ...]) -> bool:
    return any(span.overlap(x) > 0 for x in others)


def reuse_augmented_spans(
    text: str,
    structural_spans: tuple[Span, ...],
    source_texts: tuple[str, ...],
    *,
    min_chars: int = 20,
) -> tuple[Span, ...]:
    """Add exact reused non-quoted lines to structural quote spans.

    This intentionally simple transfer baseline illustrates a precision/recall
    trade-off. It does not claim that repeated text is semantically a quotation.
    """
    spans = list(structural_spans)
    normalized_sources = [normalize_quote(x, plain_markers=False) for x in source_texts]
    cursor = 0
    for line in text.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        span = Span(cursor, cursor + len(content))
        cursor += len(line)
        if len(content.strip()) < min_chars or _overlaps(span, structural_spans):
            continue
        normalized = normalize_quote(content, plain_markers=False)
        if normalized and any(normalized in source for source in normalized_sources):
            spans.append(span)
    return tuple(sorted(set(spans)))
