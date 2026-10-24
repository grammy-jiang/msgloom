"""
Text normalization with a strict offset map (P2-07).

:func:`normalize_text` turns one parsed text into a frozen
:class:`NormalizedContent`. The result holds the normalized ``text`` and an
offset map. The map sends every normalized range back to the source range
it came from. :func:`validate_offset_map` proves the map again, so a stored
or tampered map can be checked against the source.

Units: every offset is a Unicode code point index into a Python ``str``.
It is not a UTF-8 byte offset. The C0-05 contract
(``contracts/zones.py``, ``NormalizedContent``) uses byte offsets. Its
field names are mirrored here (``normalized`` span, ``original_start``,
``original_end``, ``mode``) so a later merge only needs a unit conversion.

Transforms, in order:

1. Strip zero-width and bidi control characters (:data:`STRIP_CHARS`).
   IRREVERSIBLE: one marker per contiguous run.
2. ``CRLF`` and ``CR`` become ``LF``. A reversible rewrite.
3. Collapse a run of two or more spaces or tabs to one space, and a run of
   three or more ``LF`` to two. IRREVERSIBLE: one marker per run.
4. Unicode NFC, per cluster. NFC can change the length (``e`` plus an
   acute accent becomes one character; ``U+0958`` becomes two).

Map rules (all re-checked by :func:`validate_offset_map`):

* Segments are in normalized order. Each segment is non-empty on the
  normalized side. The first starts at 0, each starts where the one before
  ended, and the last ends at ``len(text)``: no gap, no overlap.
* Original ranges are in bounds, non-empty and ascend without overlap. A
  gap between two original ranges holds only stripped characters.
* ``identity`` means the source slice equals the normalized slice.
  ``transformed`` means it differs. Only the two ends of a ``transformed``
  segment map exactly.
* Segments are built from clusters, never from text lookup. Equal source
  fragments therefore keep their own distinct offsets.
* A marker names an irreversible loss: its kind, its source range and the
  number of characters lost. A segment is reversible when no marker
  overlaps its original range (:meth:`NormalizedContent.is_reversible`).

Failure handling: bad input, a lone surrogate (it has no UTF-8 form), a
bound hit or a map violation raises :exc:`NormalizeError`. Nothing is
truncated in silence. Messages are fixed text and never carry content.
``repr`` shows no text.

Bounds are checked in this order: input size, then marker count, then
segment count. All three fail closed.

CANDIDATE/RESEARCH, PROVISIONAL: names and bounds are not frozen. See
``docs/notes/a2-v2-p2-07-normalize.md``.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Literal

#: Provisional bounds. They are decisions of this task, not production limits.
MAX_CHARS = 1_000_000
MAX_SEGMENTS = 8192  # same as the C0-05 contract
MAX_IRREVERSIBLE_MARKERS = 1024

#: Zero-width (U+200B-D, U+2060, U+FEFF, U+180E) and bidi controls
#: (U+061C, U+200E-F, U+202A-E, U+2066-9).
STRIP_CHARS: frozenset[str] = frozenset(
    "\u200b\u200c\u200d\u2060\ufeff\u180e"
    "\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e"
    "\u2066\u2067\u2068\u2069"
)

SegmentMode = Literal["identity", "transformed"]
MarkerKind = Literal["strip", "collapse_space", "collapse_blank_lines"]

_MODES = frozenset({"identity", "transformed"})
_KINDS = frozenset({"strip", "collapse_space", "collapse_blank_lines"})
_SURROGATE = re.compile("[\ud800-\udfff]")

#: A kept unit: normalized-so-far text, source start, source end.
_Unit = tuple[str, int, int]


class NormalizeError(ValueError):
    """Raised for bad input, a bound hit or a map violation. Fixed text."""


@dataclass(frozen=True, slots=True)
class Span:
    """A half-open range ``[start, end)`` in code points."""

    start: int
    end: int


@dataclass(frozen=True, slots=True)
class Segment:
    """One map entry: a normalized range and its source range."""

    normalized: Span
    original_start: int
    original_end: int
    mode: SegmentMode


@dataclass(frozen=True, slots=True)
class IrreversibleMarker:
    """An irreversible loss: kind, source range and characters lost."""

    kind: MarkerKind
    original_start: int
    original_end: int
    count: int


@dataclass(frozen=True, slots=True)
class NormalizedContent:
    """
    Normalized text with its offset map.

    The dataclass does not validate itself. That lets a test build a
    tampered copy with :func:`dataclasses.replace`. Call
    :func:`validate_offset_map` before trust.
    """

    text: str = field(repr=False)
    source_length: int
    segments: tuple[Segment, ...]
    markers: tuple[IrreversibleMarker, ...]

    @property
    def irreversible_count(self) -> int:
        """Return the number of irreversible markers."""
        return len(self.markers)

    def is_reversible(self, index: int) -> bool:
        """Return True when no marker overlaps segment ``index``."""
        seg = self.segments[index]
        return not any(
            m.original_start < seg.original_end and seg.original_start < m.original_end
            for m in self.markers
        )


def _bound(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise NormalizeError(f"{label} must be a positive integer")
    return value


def _scan(raw: str) -> tuple[list[_Unit], list[tuple[int, int]]]:
    """Strip controls and fold line ends; return kept units and strip runs."""
    units: list[_Unit] = []
    strips: list[tuple[int, int]] = []
    i, size = 0, len(raw)
    while i < size:
        char = raw[i]
        if char in STRIP_CHARS:
            if strips and strips[-1][1] == i:
                strips[-1] = (strips[-1][0], i + 1)
            else:
                strips.append((i, i + 1))
            i += 1
        elif char == "\r":
            step = 2 if raw.startswith("\r\n", i) else 1
            units.append(("\n", i, i + step))
            i += step
        else:
            units.append((char, i, i + 1))
            i += 1
    return units, strips


def _collapse(
    units: list[_Unit], strips: list[tuple[int, int]]
) -> tuple[list[_Unit], list[tuple[int, int]], list[IrreversibleMarker]]:
    """Collapse space and blank-line runs; absorb strip runs inside them."""
    out: list[_Unit] = []
    marks: list[IrreversibleMarker] = []
    i, size = 0, len(units)
    while i < size:
        text = units[i][0]
        spacey = text in (" ", "\t")
        if not spacey and text != "\n":
            out.append(units[i])
            i += 1
            continue
        j = i
        while j < size and (
            units[j][0] in (" ", "\t") if spacey else units[j][0] == "\n"
        ):
            j += 1
        run = j - i
        start, end = units[i][1], units[j - 1][2]
        if run >= (2 if spacey else 3):
            merged, kind = (
                (" ", "collapse_space") if spacey else ("\n\n", "collapse_blank_lines")
            )
            out.append((merged, start, end))
            marks.append(
                IrreversibleMarker(kind, start, end, (end - start) - len(merged))
            )
        else:
            out.extend(units[i:j])
        i = j
    kept: list[tuple[int, int]] = []
    k = 0
    for run in strips:
        while k < len(marks) and marks[k].original_end <= run[0]:
            k += 1
        inside = k < len(marks) and marks[k].original_start <= run[0]
        if not inside:
            kept.append(run)
    return out, kept, marks


def _starts_cluster(prev_text: str, char: str) -> bool:
    """Return True when ``char`` cannot interact with ``prev_text`` in NFC."""
    if ord(char) < 0x300:
        return True
    if unicodedata.combining(char):
        return False
    last = unicodedata.normalize("NFC", prev_text)[-1]
    return unicodedata.normalize("NFC", last + char) == last + char


def _clusters(units: list[_Unit]) -> list[list[_Unit]]:
    groups: list[list[_Unit]] = []
    text = ""
    for unit in units:
        if groups and not _starts_cluster(text, unit[0][0]):
            groups[-1].append(unit)
            text += unit[0]
            continue
        groups.append([unit])
        text = unit[0]
    return groups


def _build(raw: str, max_segments: int, max_markers: int) -> NormalizedContent:
    if _SURROGATE.search(raw):
        raise NormalizeError("input holds a lone surrogate")
    units, strips = _scan(raw)
    units, strips, collapses = _collapse(units, strips)
    markers = [IrreversibleMarker("strip", a, b, b - a) for a, b in strips]
    markers = sorted(markers + collapses, key=lambda m: m.original_start)
    if len(markers) > max_markers:
        raise NormalizeError("irreversible marker bound exceeded")
    segments: list[Segment] = []
    parts: list[str] = []
    cursor = 0
    for group in _clusters(units):
        joined = "".join(u[0] for u in group)
        norm = joined if joined.isascii() else unicodedata.normalize("NFC", joined)
        start, end = group[0][1], group[-1][2]
        mode: SegmentMode = "identity" if raw[start:end] == norm else "transformed"
        prev = segments[-1] if segments else None
        if (
            prev
            and mode == "identity"
            and prev.mode == mode
            and prev.original_end == start
        ):
            segments[-1] = Segment(
                Span(prev.normalized.start, cursor + len(norm)),
                prev.original_start,
                end,
                mode,
            )
        else:
            segments.append(Segment(Span(cursor, cursor + len(norm)), start, end, mode))
        if len(segments) > max_segments:
            raise NormalizeError("segment bound exceeded")
        parts.append(norm)
        cursor += len(norm)
    return NormalizedContent("".join(parts), len(raw), tuple(segments), tuple(markers))


def normalize_text(
    raw: str,
    *,
    max_chars: int = MAX_CHARS,
    max_segments: int = MAX_SEGMENTS,
    max_irreversible_markers: int = MAX_IRREVERSIBLE_MARKERS,
) -> NormalizedContent:
    """
    Normalize ``raw`` and return the text with its strict offset map.

    ``max_chars`` bounds ``len(raw)`` in code points. ``max_segments``
    bounds the map size. ``max_irreversible_markers`` bounds the number of
    irreversible losses. Each bound must be a positive ``int``. Exceeding a
    bound raises :exc:`NormalizeError`. The empty string is valid and gives
    empty text with an empty map. A lone surrogate raises.
    """
    if not isinstance(raw, str):
        raise NormalizeError("input must be str")
    limit = _bound(max_chars, "max_chars")
    caps = (
        _bound(max_segments, "max_segments"),
        _bound(max_irreversible_markers, "max_irreversible_markers"),
    )
    if len(raw) > limit:
        raise NormalizeError("input size bound exceeded")
    return _build(raw, *caps)


def _fail(message: str) -> NormalizeError:
    return NormalizeError(message)


def _check_segment(seg: object, raw: str, text: str, cursor: int, last: int) -> Segment:
    if not isinstance(seg, Segment) or not isinstance(seg.normalized, Span):
        raise _fail("map entry has a wrong type")
    ints = (
        seg.normalized.start,
        seg.normalized.end,
        seg.original_start,
        seg.original_end,
    )
    if any(isinstance(n, bool) or not isinstance(n, int) for n in ints):
        raise _fail("map offset is not an integer")
    if seg.mode not in _MODES:
        raise _fail("map mode is unknown")
    if seg.normalized.end <= seg.normalized.start:
        raise _fail("normalized range is empty or reversed")
    if seg.normalized.start != cursor:
        raise _fail("normalized ranges leave a gap or overlap")
    if seg.normalized.end > len(text):
        raise _fail("normalized range is outside the text")
    if not 0 <= seg.original_start < seg.original_end <= len(raw):
        raise _fail("source range is empty, reversed or out of bounds")
    if seg.original_start < last:
        raise _fail("source ranges overlap or are not monotonic")
    return seg


def _check_gap(raw: str, start: int, end: int) -> None:
    if any(raw[k] not in STRIP_CHARS for k in range(start, end)):
        raise _fail("source gap holds a character that was not stripped")


def validate_offset_map(content: NormalizedContent, raw: str) -> None:
    """
    Re-check every map invariant of ``content`` against ``raw``.

    Raise :exc:`NormalizeError` on the first violation. The checks are:
    types and bounds; normalized ranges that are strictly increasing, with
    no gap or overlap, covering the whole text; ascending, non-overlapping,
    in-bounds source ranges; source gaps that hold only stripped
    characters; ``identity`` slices that are equal and ``transformed``
    slices that re-normalize to the normalized slice; and finally a full
    rebuild that must give the same text and markers. The rebuild proves
    that no irreversible loss is unmarked.
    """
    if not isinstance(content, NormalizedContent) or not isinstance(raw, str):
        raise _fail("validator input has a wrong type")
    if not isinstance(content.text, str) or not isinstance(content.segments, tuple):
        raise _fail("content fields have a wrong type")
    if not isinstance(content.markers, tuple):
        raise _fail("content fields have a wrong type")
    if content.source_length != len(raw):
        raise _fail("source length differs from the source")
    cursor = last = 0
    for entry in content.segments:
        seg = _check_segment(entry, raw, content.text, cursor, last)
        _check_gap(raw, last, seg.original_start)
        piece = raw[seg.original_start : seg.original_end]
        target = content.text[seg.normalized.start : seg.normalized.end]
        if seg.mode == "identity" and piece != target:
            raise _fail("identity segment differs from the source")
        if seg.mode == "transformed":
            if piece == target:
                raise _fail("transformed segment is an identity")
            inner = _build(piece, len(piece) + 1, len(piece) + 1)
            if inner.text != target:
                raise _fail("transformed segment does not re-normalize")
        cursor, last = seg.normalized.end, seg.original_end
    if cursor != len(content.text):
        raise _fail("segments do not cover the normalized text")
    _check_gap(raw, last, len(raw))
    for marker in content.markers:
        if not isinstance(marker, IrreversibleMarker) or marker.kind not in _KINDS:
            raise _fail("marker has a wrong type or kind")
    rebuilt = _build(raw, len(raw) + 1, len(raw) + 1)
    if rebuilt.markers != content.markers:
        raise _fail("markers differ from the source")
    if rebuilt.text != content.text:
        raise _fail("text differs from the source")
