"""P2-03 hostile PDF input: linear time, random damage, invariants."""

from __future__ import annotations

import random
import time

import pytest

from msgloom.a2_kedro.parsers.pdf import PdfParseResult, parse_pdf
from msgloom.contracts import TerminalStatus
from tests.a2_kedro.helpers import check
from tests.a2_kedro.test_p2_03 import IMAGE, build_pdf

#: name -> (prefix, repeated unit, suffix)
SHAPES = {
    "open_arrays": (b"%PDF-1.4\n1 0 obj\n", b"[", b"\nendobj\n%%EOF\n"),
    "open_dicts": (b"%PDF-1.4\n1 0 obj\n", b"<<", b"\nendobj\n%%EOF\n"),
    "open_strings": (b"%PDF-1.4\n1 0 obj\n", b"(", b"\nendobj\n%%EOF\n"),
    "objects": (b"%PDF-1.4\n", b"1 0 obj null endobj\n", b"%%EOF\n"),
    "xref_words": (b"%PDF-1.4\n", b"xref\n0 1\n", b"%%EOF\n"),
    "end_markers": (b"%PDF-1.4\n", b"%%EOF\n", b""),
    "header_repeats": (b"", b"%PDF-1.4\n", b"%%EOF\n"),
    "stream_words": (b"%PDF-1.4\n", b"stream\nendstream\n", b"%%EOF\n"),
}


def hostile(kind: str, size: int) -> bytes:
    prefix, unit, suffix = SHAPES[kind]
    return prefix + unit * (size // len(unit)) + suffix


def invariant(result: PdfParseResult) -> None:
    """A complete result always holds text; nothing leaks into messages."""
    if result.status is TerminalStatus.COMPLETE:
        check(result.text_chars > 0 and not result.limitations, "complete needs text")
    else:
        check(len(result.limitations) > 0, "not complete needs a limitation")
    for item in result.limitations:
        check(len(item.detail) < 80, "limitation detail is fixed short text")


def best_time(data: bytes) -> float:
    times = []
    for _ in range(2):
        begin = time.perf_counter()
        invariant(parse_pdf(data))
        times.append(time.perf_counter() - begin)
    return min(times)


@pytest.mark.parametrize("kind", sorted(SHAPES))
def test_hostile_one_megabyte_body_is_fast_and_linear(kind: str) -> None:
    check(
        parse_pdf(hostile(kind, 10**6)).status is not TerminalStatus.COMPLETE,
        "not complete",
    )
    small = best_time(hostile(kind, 250_000))
    large = best_time(hostile(kind, 10**6))
    check(large < 5.0, f"1 MB took too long: {large:.2f}s")
    check(large < max(small, 0.05) * 12, "time grows faster than linear")


def test_circular_page_tree_does_not_hang_or_complete_empty() -> None:
    data = build_pdf([b"Hello"]).replace(b"/Kids [4 0 R]", b"/Kids [2 0 R 4 0 R]")
    result = parse_pdf(data)
    invariant(result)


def test_random_byte_damage_keeps_the_invariants() -> None:
    base = build_pdf([b"Hello", IMAGE, b"World"])
    rng = random.Random(20261024)
    for _ in range(150):
        data = bytearray(base)
        for _ in range(rng.randint(1, 6)):
            data[rng.randrange(len(data))] = rng.randrange(256)
        invariant(parse_pdf(bytes(data)))


def test_random_splices_and_cuts_keep_the_invariants() -> None:
    base = build_pdf([b"Hello", b"World"], password=b"")
    rng = random.Random(7)
    for _ in range(100):
        a, b = sorted(rng.randrange(len(base)) for _ in range(2))
        invariant(parse_pdf(base[:a] + base[b:]))
        invariant(parse_pdf(base[a:b]))
