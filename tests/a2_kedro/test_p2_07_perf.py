"""P2-07 normalization: linear cost on hostile runs and cluster differential."""

from __future__ import annotations

import random
import re
import time
import unicodedata

import pytest

from msgloom.a2_kedro.normalize import (
    NormalizedContent,
    normalize_text,
    validate_offset_map,
)
from tests.a2_kedro.helpers import check

#: Generous bound for one normalize plus validate run on a slow host. The
#: measured time on a Raspberry Pi 5 is well under 10 s for every case.
TIME_LIMIT = 20.0
UNBOUNDED = 10**7


def run(raw: str) -> NormalizedContent:
    """Normalize and validate ``raw`` inside the time bound."""
    started = time.monotonic()
    content = normalize_text(
        raw, max_segments=UNBOUNDED, max_irreversible_markers=UNBOUNDED
    )
    validate_offset_map(content, raw)
    elapsed = time.monotonic() - started
    check(elapsed < TIME_LIMIT, f"normalize and validate took {elapsed:.1f} s")
    return content


@pytest.mark.parametrize("char", ["\u0958", "\uf900", "\u212a", "\u2126"])
def test_run_of_unstable_non_marks_is_linear(char: str) -> None:
    raw = char * 200_000
    content = run(raw)
    check(content.text == unicodedata.normalize("NFC", raw), "NFC text")
    check(len(content.segments) == 1, "one cluster, one segment")
    check(content.segments[0].mode == "transformed", "run is transformed")


def test_unstable_run_interleaved_with_combining_marks_is_linear() -> None:
    raw = "\u0958\u0301\u0323" * 100_000
    content = run(raw)
    check(content.text == unicodedata.normalize("NFC", raw), "NFC text")


def test_run_with_non_starter_decomposition_is_linear() -> None:
    raw = "\u0f73\u0f75\u0f81" * 70_000
    content = run(raw)
    check(content.text == unicodedata.normalize("NFC", raw), "NFC text")


def test_one_million_ascii_is_linear() -> None:
    raw = "abcdefg" * 142_857 + "h"
    content = run(raw)
    check(len(raw) == 1_000_000, "fixture size")
    check(content.text == raw, "ASCII is unchanged")
    check(len(content.segments) == 1, "one identity segment")


def test_one_million_combining_marks_are_linear() -> None:
    raw = "a" + "\u0301" * 999_999
    content = run(raw)
    check(content.text == unicodedata.normalize("NFC", raw), "NFC text")
    check(len(content.segments) == 1, "one cluster")


def test_long_combining_tail_before_hangul_jamo_is_linear() -> None:
    raw = "a" + "\u0301" * 300_000 + "\u1100\u1161\u11a8" * 30_000
    content = run(raw)
    check(content.text == unicodedata.normalize("NFC", raw), "NFC text")


@pytest.mark.parametrize(
    "raw",
    [
        "\u1100\u1161\u11a8" * 60_000,
        "\u1100" + "\u1161" * 120_000,
        "\uac00" + "\u11a8" * 120_000,
        "\u1161\u11a8" * 60_000,
    ],
    ids=["lvt", "l-then-v-run", "lv-then-t-run", "v-t-pairs"],
)
def test_hangul_jamo_runs_are_linear(raw: str) -> None:
    content = run(raw)
    check(content.text == unicodedata.normalize("NFC", raw), "NFC text")


# --- literal expectations (taken from the first, quadratic version) -------

# Expected values come from the first (quadratic) version of the scanner.
LITERALS = (
    ("\u0958", "\u0915\u093c", [(0, 2, 0, 1, "transformed")]),
    ("\u0958\u0958", "\u0915\u093c\u0915\u093c", [(0, 4, 0, 2, "transformed")]),
    ("\u212a", "K", [(0, 1, 0, 1, "transformed")]),
    (
        "e\u0301x",
        "\u00e9x",
        [(0, 1, 0, 2, "transformed"), (1, 2, 2, 3, "identity")],
    ),
    ("\u1100\u1161\u11a8", "\uac01", [(0, 1, 0, 3, "transformed")]),
    (
        "\u1100\u1161\u1161",
        "\uac00\u1161",
        [(0, 1, 0, 2, "transformed"), (1, 2, 2, 3, "identity")],
    ),
    ("\uac01\u11a8", "\uac01\u11a8", [(0, 2, 0, 2, "identity")]),
    (
        "\u0f73\u0f73",
        "\u0f71\u0f71\u0f72\u0f72",
        [(0, 4, 0, 2, "transformed")],
    ),
    ("\u0915\u0958", "\u0915\u0915\u093c", [(0, 3, 0, 2, "transformed")]),
    (
        "\u0b47\u0b3e\u0b3e",
        "\u0b4b\u0b3e",
        [(0, 1, 0, 2, "transformed"), (1, 2, 2, 3, "identity")],
    ),
    (
        "\u0958\u0301\u0958\u0323",
        "\u0915\u093c\u0301\u0915\u093c\u0323",
        [(0, 6, 0, 4, "transformed")],
    ),
    (
        "a\u0301\u0323\u0958",
        "\u1ea1\u0301\u0915\u093c",
        [(0, 4, 0, 4, "transformed")],
    ),
    (
        "\u0f73\u1100\u1161",
        "\u0f71\u0f72\uac00",
        [(0, 2, 0, 1, "transformed"), (2, 3, 1, 3, "transformed")],
    ),
    (
        "\uf900\uf900x",
        "\u8c48\u8c48x",
        [(0, 2, 0, 2, "transformed"), (2, 3, 2, 3, "identity")],
    ),
)


@pytest.mark.parametrize(("raw", "text", "segments"), LITERALS)
def test_literal_cluster_expectations(
    raw: str, text: str, segments: list[tuple[int, int, int, int, str]]
) -> None:
    content = normalize_text(raw)
    validate_offset_map(content, raw)
    got = [
        (s.normalized.start, s.normalized.end, s.original_start, s.original_end, s.mode)
        for s in content.segments
    ]
    check(content.text == text, "normalized text")
    check(got == segments, f"segments {got}")


# --- differential against the reference pipeline --------------------------

POOL = (
    "a",
    "b",
    " ",
    "\n",
    "\u0958",
    "\uf900",
    "\u212a",
    "\u0301",
    "\u0323",
    "\u1100",
    "\u1161",
    "\u11a8",
    "\u1100\u1161\u11a8",
)


def reference(raw: str) -> str:
    """Return the text of the documented transforms done the plain way."""
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return unicodedata.normalize("NFC", text)


def test_random_strings_match_whole_text_nfc_and_validate() -> None:
    rng = random.Random(7)
    for _ in range(2000):
        raw = "".join(rng.choice(POOL) for _ in range(rng.randint(1, 14)))
        content = normalize_text(raw)
        validate_offset_map(content, raw)
        check(content.text == reference(raw), f"text differs for {raw!r}")
