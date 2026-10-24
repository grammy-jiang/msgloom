"""P2-08 hostile input: 1 MB repetitive texts finish fast and stay bounded."""

from __future__ import annotations

import time

import pytest

from msgloom.a2_kedro.normalize import NormalizedContent, Segment, Span, normalize_text
from msgloom.a2_kedro.zones import ZoneResult, build_zones
from tests.a2_kedro.helpers import check

LIMIT_SECONDS = 10.0
SIZE = 1_000_000


def identity(raw: str) -> NormalizedContent:
    """Build a valid one-segment map for text that needs no rewrite."""
    n = len(raw)
    return NormalizedContent(raw, n, (Segment(Span(0, n), 0, n, "identity"),), ())


def timed(raw: str, source: NormalizedContent) -> ZoneResult:
    begin = time.perf_counter()
    res = build_zones(raw, source, part_id="part-1", author="alice@example.com")
    check(time.perf_counter() - begin < LIMIT_SECONDS, "zone scan is too slow")
    return res


def cover(raw: str, res: ZoneResult) -> None:
    """Zones and unknown ranges tile the text exactly."""
    zones = res.zones.zones if res.zones else ()
    spans = [(z.normalized.start, z.normalized.end) for z in zones]
    spans += [(u.start, u.end) for u in res.unknown]
    cursor = 0
    for start, end in sorted(spans):
        check(start == cursor, "gap or overlap")
        cursor = end
    check(cursor == len(raw.encode("utf-8")), "text not covered")


CASES = {
    "gt_run": ">" * SIZE,
    "gt_space_run": "> " * (SIZE // 2),
    "signature_lines": "-- \n" * (SIZE // 4),
    "alternating_cap": "a\n> b\n" * (SIZE // 6),
    "depth_alternating": "> > > a\n> b\n" * (SIZE // 12),
    "from_lines": "From: x\n" * (SIZE // 8),
    "marker_lines": "On x wrote:\n" * (SIZE // 12),
    "blank_lines": "\n" * SIZE,
    "one_long_line": "a" * SIZE,
    "words": "ab " * (SIZE // 3),
    "wrote_no_newline": "On " + "wrote: " * (SIZE // 7),
    "separators": "-----\n" * (SIZE // 6),
    "non_ascii": "\u00e9\n> \u00fc\n" * (SIZE // 8),
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_one_megabyte_input_is_fast_and_tiled(name: str) -> None:
    raw = CASES[name]
    res = timed(raw, identity(raw))
    cover(raw, res)
    if res.zones:
        check(len(res.zones.zones) <= 1024, "zone cap exceeded")


def test_alternating_lines_hit_the_zone_cap() -> None:
    raw = CASES["alternating_cap"]
    res = timed(raw, identity(raw))
    check(res.limitations == ("zone_limit",), "zone_limit expected")
    check(res.zones is not None and len(res.zones.zones) == 1024, "cap size")


def test_over_deep_prefix_is_bounded_and_unknown() -> None:
    raw = CASES["gt_run"]
    res = timed(raw, identity(raw))
    check(res.zones is None and res.limitations == ("quote_depth_limit",), "unknown")


def test_normalized_quote_text_end_to_end() -> None:
    raw = "> repeated quoted line\n" * 40_000
    source = normalize_text(raw)
    res = timed(raw, source)
    check(res.zones is not None and len(res.zones.zones) == 1, "one quote zone")
    cover(source.text, res)
