"""P2-02 hostile JSON input: linear scan steps and depth-scan verdicts."""

from __future__ import annotations

import pytest

from msgloom.a2_kedro.parsers import json_scan
from msgloom.a2_kedro.parsers.json_scan import exceeds_depth
from msgloom.a2_kedro.parsers.plain_json import Outcome, parse_json
from tests.a2_kedro.helpers import check

# --- hostile input: linear scan steps -----------------------------------------

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


class CountingSearch:
    """Wrap a compiled pattern. Record every ``search`` start position."""

    def __init__(self, pattern) -> None:
        self.pattern = pattern
        self.starts: list[int] = []

    def search(self, text, pos=0):
        self.starts.append(pos)
        return self.pattern.search(text, pos)


@pytest.mark.parametrize("kind", sorted(SHAPES))
def test_hostile_one_megabyte_body_scans_in_linear_steps(kind, monkeypatch) -> None:
    data = hostile(kind, 10**6)
    check(parse_json(data).outcome is Outcome.INCOMPLETE, "incomplete")
    outside = CountingSearch(json_scan._OUTSIDE)
    inside = CountingSearch(json_scan._INSIDE)
    monkeypatch.setattr(json_scan, "_OUTSIDE", outside)
    monkeypatch.setattr(json_scan, "_INSIDE", inside)
    json_scan.exceeds_depth(data.decode(), 64)
    for name, scan in (("outside", outside), ("inside", inside)):
        starts = scan.starts
        check(len(starts) <= len(data) + 1, f"{name}: more steps than bytes")
        check(starts == sorted(set(starts)), f"{name}: scan went backward")


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
