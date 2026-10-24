"""
Content zones over normalized text (P2-08).

:func:`build_zones` takes the parsed text and its P2-07
:class:`~msgloom.a2_kedro.normalize.NormalizedContent`. It returns a
:class:`ZoneResult` with a contract
:class:`~msgloom.a2_kedro.contracts.zones.wire.ContentZones`: authored, quote,
forward header and signature zones. Each zone has a range in the normalized
text and, through the P2-07 offset map, in the parsed text.

Units: P2-07 counts code points, the contract counts UTF-8 bytes. This
module converts once and proves the zones with the contract checks
``validate_against`` and ``verify_bytes``.

Contract fit: the contract has no ``unknown`` kind, no forwarded-body kind
and no empty zone list. So unknown text stays unzoned and is listed in
``ZoneResult.unknown``. Zones plus ``unknown`` tile the normalized text
with no gap and no overlap. ``zones`` is ``None`` when no zone exists. The
forwarded body is a depth 1 ``quote`` zone after a ``forward_header``.

Line rules, in order:

* A blank line joins the zone before it (after it, at the text start).
* ``>`` prefix: quote (depth over 16: unknown).
* The exact line ``-- `` starts a signature up to the next boundary. Over
  12 lines it is unknown. ``--``, ``---`` and ``-- x`` are plain text.
* ``On ... wrote:`` must be followed at once by a depth 1 ``>`` line. It
  then opens that quote. Else it and the rest of the text are unknown.
* ``From:``/``Sent:``/``To:``/optional ``Cc:``/``Subject:`` lines (after an
  optional ``-----Original Message-----`` style line) are a forward
  header. The rest of the text is the forwarded quote. A partial or
  reordered block and the rest of the text are unknown.
* Anything else is authored text.
Attribution: ``quote_author_sha256`` is the SHA-256 of a claim (the text
between ``On`` and ``wrote:``, the ``From:`` value, or the marker line one
level up), casefolded with single spaces. A claim is not a verified
address. If it contains the current author, the digest is ``None``.

Bounds: one forward pass, bounded lookahead, no regular expression. At the
``max_zones`` cap the rest of the text is unknown (limitation
``zone_limit``). An edge inside a ``transformed`` segment cannot map: the
zone shrinks to the segment edge and the segment is unknown (limitation
``unmapped_boundary``). A bad argument raises :exc:`A2ContractError` with
fixed text. Messages and ``repr`` never carry text. The P2-07 map is not
re-proved here; use ``validate_offset_map`` for that.

CANDIDATE/RESEARCH, PROVISIONAL: names and bounds are not frozen. See
``docs/notes/a2-v2-p2-08-zones.md``.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import accumulate
from typing import Literal, cast

from msgloom.a2_kedro.contracts import zones as wire
from msgloom.a2_kedro.contracts.codec import A2ContractError, sha256_hex
from msgloom.a2_kedro.normalize import NormalizedContent as SourceContent

MAX_ZONES = wire.MAX_ZONES
#: Provisional bounds. They are decisions of this task, not production limits.
MAX_MARKER_CHARS = 512
MAX_SIGNATURE_LINES = 12
MAX_HEADER_LINES = 8

ZoneLimitation = Literal["zone_limit", "quote_depth_limit", "unmapped_boundary"]
_PieceKind = wire.ZoneKind | Literal["unknown", "blank"]

_HEADER_LABELS = frozenset({"From", "Sent", "Date", "To", "Cc", "Bcc", "Subject"})
_FORWARD_LABELS = (
    ("From", "Sent", "To", "Subject"),
    ("From", "Sent", "To", "Cc", "Subject"),
)
_MERGING = ("authored", "quote", "unknown", "blank")
_SEPARATOR_NAMES = frozenset({"original message", "forwarded message"})


@dataclass(frozen=True, slots=True)
class ZoneResult:
    """Zones (``None`` if none), their proof map, unknown ranges, limits."""

    zones: wire.ContentZones | None
    content: wire.NormalizedContent
    unknown: tuple[wire.Span, ...]
    limitations: tuple[ZoneLimitation, ...]


@dataclass(slots=True)
class _Piece:
    """A run of whole lines in code points of the normalized text."""

    kind: _PieceKind
    start: int
    end: int
    depth: int = 0
    claim: str | None = None
    fresh: bool = False  # starts a new quote: never merge with the piece before


class _Capped(Exception):
    """Internal stop signal: the zone cap was reached."""


def _fold(text: str) -> str:
    return " ".join(text.split()).casefold()


def _names_author(claim: str, author: str) -> bool:
    return author in claim  # both folded; errs toward dropping a claim


def _is_signature_delimiter(line: str) -> bool:
    return line == "-- "  # the exact RFC 3676 delimiter


def _quote_depth(text: str, start: int, end: int) -> tuple[int, int]:
    """Return ``(depth, offset)`` of the ``>`` prefix of one line."""
    depth, pos = 0, start
    while pos < end and text[pos] == ">" and depth <= wire.MAX_QUOTE_DEPTH:
        depth += 1
        pos += 1
        if pos < end and text[pos] == " ":
            pos += 1
    return depth, pos - start


def _marker_claim(line: str) -> str | None:
    """Return the text between ``On`` and ``wrote:`` or ``None``."""
    if len(line) > MAX_MARKER_CHARS or not line.startswith("On "):
        return None
    stripped = line.rstrip()
    return stripped[3:-6] if stripped.endswith("wrote:") else None


def _is_separator(line: str) -> bool:
    core = line.strip()
    if len(core) < 5 or len(core) > 80:
        return False
    return not core.strip("_-= ") or core.strip("-_= ").casefold() in _SEPARATOR_NAMES


def _line_starts(text: str) -> list[int]:
    """Return line start offsets plus ``len(text)``. One pass."""
    starts = [0] if text else []
    pos = text.find("\n")
    while 0 <= pos < len(text) - 1:
        starts.append(pos + 1)
        pos = text.find("\n", pos + 1)
    return [*starts, len(text)]


def _mergeable(left: _Piece, right: _Piece) -> bool:
    same = left.kind == right.kind and left.depth == right.depth
    return (
        same and left.kind in _MERGING and left.end == right.start and not right.fresh
    )


class _Scanner:
    """One forward pass over the lines of the normalized text."""

    def __init__(self, text: str, author: str, max_zones: int) -> None:
        self.text = text
        self.author = author
        self.max_zones = max_zones
        self.starts = _line_starts(text)
        self.count = len(self.starts) - 1
        self.pieces: list[_Piece] = []
        self.zones = self.capped_at = 0
        self.limits: set[ZoneLimitation] = set()

    def run(self) -> list[_Piece]:
        k = 0
        try:
            while k < self.count:
                k = self._step(k)
        except _Capped:
            self.limits.add("zone_limit")
            self._add(_Piece("unknown", self.capped_at, len(self.text)))
        return self.pieces

    def body(self, k: int) -> str:
        """Return line ``k`` without its newline."""
        return self.text[self.starts[k] : self.starts[k + 1]].removesuffix("\n")

    def _tag(self, k: int) -> str:
        text, a, b = self.text, self.starts[k], self.starts[k + 1]
        if text[a:b].isspace():
            return "blank"
        if _quote_depth(text, a, b)[0] > 0:
            return "quote"
        first = text[a]
        if first == "-" and _is_signature_delimiter(self.body(k)):
            return "sig"
        short = b - a <= MAX_MARKER_CHARS + 1
        if first == "O" and short and _marker_claim(self.body(k)) is not None:
            return "marker"
        if text.startswith("From:", a):
            return "hdr"
        if first in "_-=" and b - a <= 82 and _is_separator(self.body(k)):
            return "sep"
        return "text"

    def _add(self, piece: _Piece) -> None:
        pieces = self.pieces
        if pieces and _mergeable(pieces[-1], piece):
            pieces[-1].end = piece.end
            return
        if (
            len(pieces) >= 2
            and pieces[-1].kind == "blank"
            and _mergeable(pieces[-2], piece)
        ):
            pieces.pop()
            pieces[-1].end = piece.end
            return
        if piece.kind not in ("blank", "unknown"):
            if self.zones >= self.max_zones:
                self.capped_at = piece.start
                raise _Capped
            self.zones += 1
        pieces.append(piece)

    def _tail(self, k: int) -> int:
        """Mark everything from line ``k`` on as unknown; end the scan."""
        self._add(_Piece("unknown", self.starts[k], len(self.text)))
        return self.count

    def _digest(self, claim: str) -> str | None:
        folded = _fold(claim)
        if not folded or _names_author(folded, self.author):
            return None
        return sha256_hex(folded.encode("utf-8"))

    def _step(self, k: int) -> int:
        a = self.starts[k]
        tag = self._tag(k)
        if tag == "blank":
            j = k + 1
            while j < self.count and self._tag(j) == "blank":
                j += 1
            self._add(_Piece("blank", a, self.starts[j]))
            return j
        if tag == "quote":
            return self._quote(k)
        if tag == "marker":
            return self._marker(k)
        if tag == "sig":
            return self._signature(k)
        if tag in ("sep", "hdr") and (probe := self._probe(k)) is not None:
            return self._forward(k, *probe)
        self._add(_Piece("authored", a, self.starts[k + 1]))
        return k + 1

    def _quote(self, k: int) -> int:
        a, b = self.starts[k], self.starts[k + 1]
        depth = _quote_depth(self.text, a, b)[0]
        if depth > wire.MAX_QUOTE_DEPTH:
            self.limits.add("quote_depth_limit")
            self._add(_Piece("unknown", a, b))
            return k + 1
        claim, fresh = None, False
        if depth >= 2 and k > 0 and self._tag(k - 1) == "quote":
            pa, pb = self.starts[k - 1], self.starts[k]
            pdepth, offset = _quote_depth(self.text, pa, pb)
            nested = _marker_claim(self.body(k - 1)[offset:])
            if pdepth == depth - 1 and nested is not None and nested.strip():
                claim, fresh = self._digest(nested), True
        self._add(_Piece("quote", a, b, depth, claim, fresh))
        return k + 1

    def _marker(self, k: int) -> int:
        claim = _marker_claim(self.body(k)) or ""
        nxt = k + 1
        if not claim.strip() or nxt >= self.count or self._tag(nxt) != "quote":
            return self._tail(k)
        a, b = self.starts[nxt], self.starts[nxt + 1]
        if _quote_depth(self.text, a, b)[0] != 1:
            return self._tail(k)
        piece = _Piece("quote", self.starts[k], b, 1, self._digest(claim), True)
        self._add(piece)
        return nxt + 1

    def _boundary(self, k: int) -> bool:
        tag = self._tag(k)
        return tag in ("quote", "marker") or (
            tag in ("sep", "hdr") and self._probe(k) is not None
        )

    def _signature(self, k: int) -> int:
        end = k + 1
        while end < self.count and not self._boundary(end):
            end += 1
        # A long region after ``-- `` is a delimiter inside a body: unknown.
        kind: _PieceKind = "signature"
        if end - k > MAX_SIGNATURE_LINES:
            kind = "unknown"
        self._add(_Piece(kind, self.starts[k], self.starts[end]))
        return end

    def _header_block(self, k: int) -> tuple[tuple[str, ...], int]:
        labels: list[str] = []
        j = k
        while j < self.count and len(labels) < MAX_HEADER_LINES:
            a = self.starts[j]
            head = self.text[a : min(a + 12, self.starts[j + 1])]
            colon = head.find(":")
            if colon <= 0 or head[:colon] not in _HEADER_LABELS:
                break
            labels.append(head[:colon])
            j += 1
        return tuple(labels), j

    def _probe(self, k: int) -> tuple[int, tuple[str, ...], int] | None:
        """Return ``(first header line, labels, end line)`` or ``None``."""
        first = k + 1 if self._tag(k) == "sep" else k
        labels, end = self._header_block(first)
        if len(labels) < 2 or labels[0] != "From":
            return None
        return first, labels, end

    def _forward(self, k: int, first: int, labels: tuple[str, ...], end: int) -> int:
        if labels not in _FORWARD_LABELS:
            return self._tail(k)
        self._add(_Piece("forward_header", self.starts[k], self.starts[end]))
        line = end
        while line < self.count and self._tag(line) == "blank":
            line += 1
        rest = self.starts[line]
        self._add(_Piece("blank", self.starts[end], rest))
        if line >= self.count:
            return self.count
        value = self.body(first)[5:]
        claim = self._digest(value) if len(value) <= MAX_MARKER_CHARS else None
        self._add(_Piece("quote", rest, len(self.text), 1, claim, True))
        return self.count


def _resolve(pieces: list[_Piece], total: int) -> list[_Piece]:
    """Give each blank run to the piece before it (or after, at the start)."""
    out: list[_Piece] = []
    lead: int | None = None
    for piece in pieces:
        if piece.kind == "blank":
            if out:
                out[-1].end = piece.end
            elif lead is None:
                lead = piece.start
            continue
        if lead is not None and not out:
            piece.start, lead = lead, None
        out.append(piece)
    if not out:
        return [_Piece("unknown", 0, total)] if total else []
    return out


class _Edges:
    """Edge lookup: ``(edge, source)``; a rewrite snaps to its segment edge."""

    def __init__(self, source: SourceContent) -> None:
        self.segments = source.segments
        self.starts = [s.normalized.start for s in self.segments]
        self.ends = [s.normalized.end for s in self.segments]

    def start(self, pos: int) -> tuple[int, int]:
        i = bisect_right(self.starts, pos) - 1
        seg = self.segments[i]
        if pos == seg.normalized.start:
            return pos, seg.original_start
        if seg.mode == "identity":
            return pos, seg.original_start + pos - seg.normalized.start
        if i + 1 == len(self.segments):
            return seg.normalized.end, seg.original_end
        return seg.normalized.end, self.segments[i + 1].original_start

    def end(self, pos: int) -> tuple[int, int]:
        i = bisect_left(self.ends, pos)
        seg = self.segments[i]
        if pos == seg.normalized.end:
            return pos, seg.original_end
        if seg.mode == "identity":
            return pos, seg.original_start + pos - seg.normalized.start
        before = self.segments[i - 1].original_end if i else 0
        return seg.normalized.start, before


def _byte_index(text: str) -> Sequence[int]:
    """Return ``index[i]``, the UTF-8 byte offset of code point ``i``."""
    if text.isascii():
        return range(len(text) + 1)
    widths = (1 + (c > 0x7F) + (c > 0x7FF) + (c > 0xFFFF) for c in map(ord, text))
    return list(accumulate(widths, initial=0))


def build_zones(
    raw: str,
    source: SourceContent,
    *,
    part_id: str,
    author: str,
    max_zones: int = MAX_ZONES,
) -> ZoneResult:
    """
    Build and prove the content zones of one normalized text.

    ``raw`` is the parsed text and ``source`` its P2-07 result. ``author``
    names the current author. No quote is ever attributed to it.
    Raise :exc:`A2ContractError` for a bad argument or a contract refusal.
    """
    typed = isinstance(raw, str) and isinstance(source, SourceContent)
    typed = typed and isinstance(part_id, str) and isinstance(author, str)
    if not typed or not part_id or not _fold(author):
        raise A2ContractError("raw, content, part_id or author is invalid")
    if source.source_length != len(raw) or isinstance(max_zones, bool):
        raise A2ContractError("content does not describe raw")
    if not 1 <= max_zones <= MAX_ZONES:
        raise A2ContractError("max_zones is out of bounds")
    text = source.text
    scanner = _Scanner(text, _fold(author), max_zones)
    pieces = _resolve(scanner.run(), len(text))
    edges = _Edges(source) if text else None
    kept: list[tuple[_Piece, int, int, int, int]] = []
    for piece in pieces:
        if piece.kind == "unknown" or edges is None:
            continue
        (s, lo), (e, hi) = edges.start(piece.start), edges.end(piece.end)
        if (s, e) != (piece.start, piece.end):
            scanner.limits.add("unmapped_boundary")
        if s < e:
            kept.append((piece, s, e, lo, hi))
    return _assemble(raw, source, part_id, kept, scanner.limits)


def _assemble(
    raw: str,
    source: SourceContent,
    part_id: str,
    kept: list[tuple[_Piece, int, int, int, int]],
    limits: set[ZoneLimitation],
) -> ZoneResult:
    text = source.text
    nb, ob = _byte_index(text), _byte_index(raw)
    try:
        raw_bytes, text_bytes = raw.encode("utf-8"), text.encode("utf-8")
    except UnicodeEncodeError as error:
        raise A2ContractError("text is not UTF-8") from error
    span = wire.Span
    segments = tuple(
        wire.Segment(
            normalized=span(start=nb[g.normalized.start], end=nb[g.normalized.end]),
            original_start=ob[g.original_start],
            original_end=ob[g.original_end],
            mode=g.mode,
        )
        for g in source.segments
    )
    texts = {
        "parsed_sha256": sha256_hex(raw_bytes),
        "parsed_length": len(raw_bytes),
        "normalized_sha256": sha256_hex(text_bytes),
        "normalized_length": len(text_bytes),
    }
    content = wire.NormalizedContent(part_id=part_id, segments=segments, **texts)  # type: ignore[arg-type]
    zones: list[wire.Zone] = []
    unknown: list[wire.Span] = []
    cursor = ordinal = 0
    for index, (piece, s, e, lo, hi) in enumerate(kept):
        if nb[s] > cursor:
            unknown.append(span(start=cursor, end=nb[s]))
        cursor = nb[e]
        occurrence = None
        if piece.kind == "quote":
            occurrence = wire.QuoteOccurrence(ordinal=ordinal, depth=piece.depth)
            ordinal += 1
        zones.append(
            wire.Zone(
                zone_id=f"z{index}",
                kind=cast(wire.ZoneKind, piece.kind),
                original=span(start=ob[lo], end=ob[hi]),
                normalized=span(start=nb[s], end=cursor),
                quote_occurrence=occurrence,
                quote_author_sha256=piece.claim if occurrence else None,
            )
        )
    if cursor < len(text_bytes):
        unknown.append(span(start=cursor, end=len(text_bytes)))
    found = tuple(sorted(limits))
    result = None
    if zones:
        result = wire.ContentZones(part_id=part_id, zones=tuple(zones), **texts)  # type: ignore[arg-type]
        result.validate_against(content)
        result.verify_bytes(raw_bytes, text_bytes)
    return ZoneResult(result, content, tuple(unknown), found)
