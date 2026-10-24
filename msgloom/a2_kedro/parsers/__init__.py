"""
A2 v2 parsers: pure-Python workers that produce typed parse records.

This package holds the result models that :mod:`.mime_html` returns and
its small, pure decoding helpers (``decode_transfer``, ``decode_text`` and
``marker_regions``). They live here to keep each module under 500 lines. A
:class:`MimePart` keeps what the C0-04 wire record cannot hold: the
content type, the charset, flags and the reduced text. The text is
excluded from ``repr`` so a log line never echoes message content.

Offsets: ``start`` and ``end`` are a half-open byte window of the input
and cover the headers and the body of the part. ``body_start`` is the
byte offset of the body. ``text_map`` and ``quoted`` use character
offsets. See :mod:`.mime_html` for the rules.
"""

from __future__ import annotations

import base64
import binascii
import quopri
import re
from dataclasses import dataclass, field
from typing import Literal

from msgloom.a2_kedro.contracts.extract import ComponentStatus
from msgloom.a2_kedro.contracts.parse import ParsedParts, PartFormat, PartRole
from msgloom.contracts import Limitation, TerminalStatus

#: Provisional bound for quote and text map records per part.
MAX_MAP_ITEMS = 4096

_BAD_QP = re.compile(rb"=(?![0-9A-Fa-f]{2}|[ \t]*\r?\n|[ \t]*\Z)")
_NOT_B64 = re.compile(rb"[^A-Za-z0-9+/]")

QuoteKind = Literal["marker", "blockquote"]


@dataclass(frozen=True, slots=True)
class TextSpan:
    """Map ``text[text_start:text_end]`` to a range of the decoded body."""

    text_start: int
    text_end: int
    source_start: int
    source_end: int


@dataclass(frozen=True, slots=True)
class QuotedRegion:
    """A labelled quoted range ``text[start:end]``; the text stays in place."""

    start: int
    end: int
    depth: int
    kind: QuoteKind


@dataclass(frozen=True, slots=True)
class MimePart:
    """One MIME entity with its byte window, flags and optional text."""

    path: str
    parent: str | None
    content_type: str
    charset: str | None
    disposition: str | None
    role: PartRole
    format: PartFormat | None
    start: int
    end: int
    body_start: int
    flags: tuple[str, ...] = ()
    text: str | None = field(default=None, repr=False)
    text_map: tuple[TextSpan, ...] = ()
    quoted: tuple[QuotedRegion, ...] = ()


@dataclass(frozen=True, slots=True)
class MimeParseResult:
    """Outcome of :func:`parse_mime`; ``parsed`` is ``None`` if empty."""

    status: TerminalStatus
    body_status: ComponentStatus
    limitations: tuple[Limitation, ...]
    parts: tuple[MimePart, ...]
    parsed: ParsedParts | None
    input_size: int
    input_sha256: str


def part_bytes(data: bytes, part: MimePart) -> bytes:
    """Return the exact source bytes of ``part`` (headers and body)."""
    return data[part.start : part.end]


def _quote_depth(line: str) -> int:
    depth = 0
    for char in line:
        if char == ">":
            depth += 1
        elif char not in " \t":
            break
    return depth


def marker_regions(text: str) -> tuple[list[QuotedRegion], bool]:
    """Label runs of ``>`` lines; return regions and a cut flag."""
    regions: list[QuotedRegion] = []
    begin, depth, pos = -1, 0, 0
    for line in text.split("\n"):
        here = _quote_depth(line)
        if here and begin < 0:
            begin, depth = pos, here
        elif here:
            depth = max(depth, here)
        elif begin >= 0:
            regions.append(QuotedRegion(begin, pos - 1, depth, "marker"))
            begin = -1
        if len(regions) > MAX_MAP_ITEMS:
            return regions[:MAX_MAP_ITEMS], True
        pos += len(line) + 1
    if begin >= 0:
        regions.append(QuotedRegion(begin, len(text), depth, "marker"))
    return regions[:MAX_MAP_ITEMS], len(regions) > MAX_MAP_ITEMS


def decode_transfer(raw: bytes, encoding: str, flags: set[str]) -> bytes:
    """Undo a transfer encoding; add a flag code for any defect."""
    if encoding == "base64":
        clean = b"".join(raw.split())
        try:
            return base64.b64decode(clean, validate=True)
        except binascii.Error:
            flags.add("base64_corrupt")
        good = _NOT_B64.sub(b"", clean)
        good = good[: len(good) - (len(good) % 4 == 1)]
        return base64.b64decode(good + b"=" * (-len(good) % 4))
    if encoding == "quoted-printable":
        if _BAD_QP.search(raw):
            flags.add("qp_corrupt")
        return quopri.decodestring(raw)
    if encoding not in ("", "7bit", "8bit", "binary"):
        flags.add("cte_unknown")
    return raw


def decode_text(raw: bytes, charset: str | None, flags: set[str]) -> str:
    """Decode text; never raise. Add a flag code for any defect."""
    name = charset or "us-ascii"
    try:
        "".encode(name)  # a non-text or unknown codec raises here
    except (LookupError, ValueError):
        flags.add("charset_unknown")
        name, charset = "utf-8", "utf-8"
    for attempt in (name,) if charset else ("us-ascii", "utf-8"):
        try:
            return raw.decode(attempt)
        except UnicodeDecodeError:
            continue
    flags.add("charset_decode_error")
    return raw.decode(name if charset else "utf-8", errors="replace")
