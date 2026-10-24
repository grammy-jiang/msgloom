"""
P2-07 validator guards: one hostile map per guard.

Each map keeps the true markers, so the rebuild check cannot reject it for
a marker reason. Each map is valid except for one fault. Removing the one
guard that finds the fault makes the validator accept the map.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from msgloom.a2_kedro.normalize import (
    NormalizedContent,
    NormalizeError,
    Segment,
    Span,
    normalize_text,
    validate_offset_map,
)
from tests.a2_kedro.helpers import check


def hostile(raw: str, text: str, segments: tuple[Segment, ...]) -> NormalizedContent:
    """Return a map for ``raw`` with the true markers and the given parts."""
    true = normalize_text(raw)
    validate_offset_map(true, raw)
    return replace(true, text=text, segments=segments)


def rejected(content: NormalizedContent, raw: str, reason: str) -> None:
    with pytest.raises(NormalizeError, match=reason):
        validate_offset_map(content, raw)


def test_gap_between_segments_must_hold_only_stripped_characters() -> None:
    # The map skips the real space at source index 3.
    raw = "ab  ab"
    content = hostile(
        raw,
        "ab ab",
        (
            Segment(Span(0, 2), 0, 2, "identity"),
            Segment(Span(2, 3), 2, 3, "identity"),
            Segment(Span(3, 5), 4, 6, "identity"),
        ),
    )
    rejected(content, raw, "source gap holds")


def test_source_ranges_must_not_overlap() -> None:
    # Both segments claim the zero-width space at source index 1.
    raw = "a\u200bb"
    content = hostile(
        raw,
        "ab",
        (
            Segment(Span(0, 1), 0, 2, "transformed"),
            Segment(Span(1, 2), 1, 3, "transformed"),
        ),
    )
    rejected(content, raw, "overlap or are not monotonic")


def test_gap_after_the_last_segment_must_hold_only_stripped_characters() -> None:
    # The map leaves the real space at source index 2 uncovered.
    raw = "a  "
    content = hostile(raw, "a ", (Segment(Span(0, 2), 0, 2, "identity"),))
    rejected(content, raw, "source gap holds")


def test_text_must_equal_the_rebuilt_text() -> None:
    # Two identity pieces join to "a  b". The rebuild gives "a b".
    raw = "a  b"
    content = hostile(
        raw,
        "a  b",
        (
            Segment(Span(0, 2), 0, 2, "identity"),
            Segment(Span(2, 4), 2, 4, "identity"),
        ),
    )
    check(content.markers == normalize_text(raw).markers, "true markers kept")
    rejected(content, raw, "text differs from the source")


def test_true_maps_for_the_same_sources_validate() -> None:
    for raw in ("ab  ab", "a\u200bb", "a  ", "a  b"):
        validate_offset_map(normalize_text(raw), raw)
