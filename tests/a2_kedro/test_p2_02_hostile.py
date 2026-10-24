"""P2-02 hostile JSON input: linear time and depth-scan verdicts."""

from __future__ import annotations

import time

import pytest

from msgloom.a2_kedro.parsers.json_scan import exceeds_depth
from msgloom.a2_kedro.parsers.plain_json import Outcome, parse_json
from tests.a2_kedro.helpers import check

# --- hostile input: linear time -----------------------------------------

#: name -> (prefix, repeated unit, suffix)
SHAPES = {
    "escaped_quotes": (b'"', b'\\"', b"\\"),
    "quotes": (b"", b'"', b""),
    "backslashes": (b'"', b"\\", b""),
    "open_brackets": (b"", b"[", b""),
    "unterminated": (b'["', b"a", b""),
    "alternating": (b"", b'"\\""', b"\\"),
    "empty_pairs": (b"", b"[]", b""),
}


def hostile(kind: str, size: int) -> bytes:
    prefix, unit, suffix = SHAPES[kind]
    return prefix + unit * (size // len(unit)) + suffix


def best_time(data: bytes) -> float:
    times = []
    for _ in range(2):
        begin = time.perf_counter()
        parse_json(data)
        times.append(time.perf_counter() - begin)
    return min(times)


@pytest.mark.parametrize("kind", sorted(SHAPES))
def test_hostile_one_megabyte_body_parses_fast_and_linear(kind) -> None:
    check(parse_json(hostile(kind, 10**6)).outcome is Outcome.INCOMPLETE, "incomplete")
    small = best_time(hostile(kind, 250_000))
    large = best_time(hostile(kind, 10**6))
    check(large < 2.0, f"1 MB took too long: {large:.2f}s")
    check(large < max(small, 0.02) * 12, "time grows faster than linear")


DEPTH_CASES = [
    ("[[[]]]", False),
    ("[[[[]]]]", True),
    ('{"a":[[{}]]}', True),
    ('["[[[[[[", "\\"[[[["]', False),
    ('["x\\\\"]', False),
    ('["x\\\\", [[[1]]]]', True),
    ('[[["abc', False),
    ('[[["abc\\', False),
    ("]]]]]]", False),
    ("]]][[[[", True),
]


@pytest.mark.parametrize(("text", "deep"), DEPTH_CASES)
def test_depth_scan_counts_depth_outside_strings_only(text, deep) -> None:
    check(exceeds_depth(text, 3) is deep, "depth verdict")
