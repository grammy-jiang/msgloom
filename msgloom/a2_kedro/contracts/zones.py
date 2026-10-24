"""
``normalized_content@1`` and ``zones@1``: exact spans into parsed text.

Both records describe one saved text, called the parsed text. The parsed
text is the UTF-8 text that a parser produced for one part of
:class:`~msgloom.a2_kedro.contracts.parse.ParsedParts`. No record here holds
text. Text can hold control characters such as a newline, and the A2 text
rules refuse them. A record holds digests, byte lengths and byte spans.

Coordinates: every offset is a byte offset into UTF-8 text. A span is
half open: ``start`` is in, ``end`` is out. A span must start and end on a
character boundary.

:class:`NormalizedContent` maps the normalized text back to the parsed
text with ordered segments:

* An ``identity`` segment has the same length on both sides and the same
  bytes. Any offset inside it maps exactly.
* A ``transformed`` segment is a rewrite, for example collapsed
  whitespace. Only its two ends map. An offset inside it does not map.

Segments cover the normalized text with no gap. Original ranges ascend and
never overlap. Parsed bytes between two original ranges were dropped.

Non-reversible limit: the map goes from normalized text to parsed text
only. The normalized text plus the map cannot rebuild the parsed text.
A ``transformed`` segment loses its original bytes and a dropped range
leaves no trace except the gap. The parsed text must stay saved, and its
digest binds the record. A reader must never invent original bytes from a
segment.

:class:`ContentZones` marks zones. Each zone holds the same range twice:
``original`` in the parsed text and ``normalized`` in the normalized text.
:meth:`ContentZones.validate_against` proves that the two ranges are the
exact projection of each other through the segments. Zones are sorted and
never overlap in either coordinate. Zones may leave text unzoned.

Quote fields: ``quote_occurrence`` says where a quote occurs: its order and
nesting depth inside this text. ``quote_author_sha256`` is a digest of the
attribution claim in the quoted text, never an address. The two fields are
separate. An author claim never creates or moves an occurrence, and an
occurrence never names an author. Only a ``quote`` zone carries them.

Failure handling: any violation raises :exc:`A2ContractError` (or a pydantic
``ValueError`` subclass at model construction). Messages are fixed text.
They never carry text, IDs or offsets. The models hide input values.

CANDIDATE/RESEARCH, PROVISIONAL: field names, enums and limits are not
frozen. See ``docs/notes/a2-v2-contract-c0-05.md``.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from typing import Annotated, Literal

from pydantic import ConfigDict, Field, model_validator

from msgloom.a2_kedro.contracts.codec import (
    A2ContractError,
    A2Model,
    Digest,
    Text,
    canonical_model_bytes,
    decode_model_bytes,
    sha256_hex,
)
from msgloom.a2_kedro.contracts.header import StageHeader

NORMALIZED_KIND = "normalized_content"
ZONES_KIND = "zones"
VERSION = "1"

#: Provisional bounds. They are wire decisions, not production limits.
MAX_TEXT_BYTES = 2**30
MAX_SEGMENTS = 8192
MAX_ZONES = 1024
MAX_QUOTE_DEPTH = 16

SegmentMode = Literal["identity", "transformed"]
ZoneKind = Literal[
    "authored", "quote", "signature", "disclaimer", "forward_header", "boilerplate"
]

Offset = Annotated[int, Field(ge=0, le=MAX_TEXT_BYTES)]
Length = Annotated[int, Field(ge=0, le=MAX_TEXT_BYTES)]


class _ZoneModel(A2Model):
    """A2 base that also hides input values in validation errors."""

    model_config = ConfigDict(hide_input_in_errors=True)


class Span(_ZoneModel):
    """A non-empty half-open byte range."""

    start: Offset
    end: Offset

    @model_validator(mode="after")
    def _non_empty(self) -> Span:
        if self.end <= self.start:
            raise A2ContractError("span is empty or reversed")
        return self


class Segment(_ZoneModel):
    """One mapped piece: a normalized range and its parsed-text range."""

    normalized: Span
    original_start: Offset
    original_end: Offset
    mode: SegmentMode

    @model_validator(mode="after")
    def _shape(self) -> Segment:
        if self.original_end < self.original_start:
            raise A2ContractError("original range is reversed")
        size = self.normalized.end - self.normalized.start
        if self.mode == "identity" and self.original_end - self.original_start != size:
            raise A2ContractError("identity segment changes the length")
        return self


def _text_bytes(data: bytes, label: str) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise A2ContractError(f"{label} is not UTF-8") from error


def _slice_text(data: bytes, start: int, end: int, label: str) -> bytes:
    if end > len(data):
        raise A2ContractError(f"{label} span is outside the text")
    piece = data[start:end]
    _text_bytes(piece, label)  # a split character fails here
    return piece


class NormalizedContent(_ZoneModel):
    """Segment map from normalized text to parsed text for one part."""

    header: StageHeader = Field(
        default_factory=lambda: StageHeader(kind=NORMALIZED_KIND, version=VERSION)
    )
    part_id: Text
    parsed_sha256: Digest
    parsed_length: Length
    normalized_sha256: Digest
    normalized_length: Length
    segments: tuple[Segment, ...]

    @model_validator(mode="after")
    def _closed(self) -> NormalizedContent:
        if (self.header.kind, self.header.version) != (NORMALIZED_KIND, VERSION):
            raise A2ContractError("header is not normalized_content@1")
        if len(self.segments) > MAX_SEGMENTS:
            raise A2ContractError("segment count is out of bounds")
        if bool(self.segments) != bool(self.normalized_length):
            raise A2ContractError("segments and normalized length disagree")
        cursor = original = 0
        for seg in self.segments:
            if seg.normalized.start != cursor:
                raise A2ContractError("segments leave a gap or overlap")
            if seg.original_start < original:
                raise A2ContractError("original ranges overlap or go back")
            cursor, original = seg.normalized.end, seg.original_end
        if cursor != self.normalized_length:
            raise A2ContractError("segments do not cover the normalized text")
        if original > self.parsed_length:
            raise A2ContractError("original range is outside the parsed text")
        return self

    def project(self, start: int, end: int) -> tuple[int, int]:
        """
        Return the exact parsed-text range of a normalized range.

        Raise :exc:`A2ContractError` when the range is outside the text or
        when an end falls inside a ``transformed`` segment.
        """
        if not 0 <= start < end <= self.normalized_length:
            raise A2ContractError("normalized range is outside the text")
        starts = [s.normalized.start for s in self.segments]
        ends = [s.normalized.end for s in self.segments]
        first = self.segments[bisect_right(starts, start) - 1]
        last = self.segments[bisect_left(ends, end)]
        if start == first.normalized.start:
            lo = first.original_start
        elif first.mode == "identity":
            lo = first.original_start + start - first.normalized.start
        else:
            raise A2ContractError("range starts inside a transformed segment")
        if end == last.normalized.end:
            hi = last.original_end
        elif last.mode == "identity":
            hi = last.original_start + end - last.normalized.start
        else:
            raise A2ContractError("range ends inside a transformed segment")
        return lo, hi

    def verify_bytes(self, parsed: bytes, normalized: bytes) -> None:
        """
        Prove the map against the real parsed and normalized bytes.

        Both digests and lengths must match. Both texts must be UTF-8. Every
        segment range must start and end on a character boundary. An
        ``identity`` segment must have equal bytes on both sides.
        """
        for data, sha, size in (
            (parsed, self.parsed_sha256, self.parsed_length),
            (normalized, self.normalized_sha256, self.normalized_length),
        ):
            if len(data) != size or sha256_hex(data) != sha:
                raise A2ContractError("text differs from the saved digest")
            _text_bytes(data, "text")
        for seg in self.segments:
            old = _slice_text(parsed, seg.original_start, seg.original_end, "parsed")
            new = _slice_text(
                normalized, seg.normalized.start, seg.normalized.end, "normalized"
            )
            if seg.mode == "identity" and old != new:
                raise A2ContractError("identity segment does not match the bytes")

    def encode(self) -> bytes:
        """Return the bounded canonical bytes of this record."""
        return canonical_model_bytes(self)

    @classmethod
    def decode(cls, data: bytes) -> NormalizedContent:
        """Strictly decode canonical bytes; reject anything else."""
        return decode_model_bytes(cls, data)


class QuoteOccurrence(_ZoneModel):
    """Where a quote occurs: order among quotes and nesting depth."""

    ordinal: Annotated[int, Field(ge=0, lt=MAX_ZONES)]
    depth: Annotated[int, Field(ge=1, le=MAX_QUOTE_DEPTH)]


class Zone(_ZoneModel):
    """One zone with the same range in parsed and normalized text."""

    zone_id: Text
    kind: ZoneKind
    original: Span
    normalized: Span
    quote_occurrence: QuoteOccurrence | None = None
    quote_author_sha256: Digest | None = None

    @model_validator(mode="after")
    def _quote_fields(self) -> Zone:
        if self.kind == "quote":
            if self.quote_occurrence is None:
                raise A2ContractError("quote zone needs an occurrence")
            return self
        if self.quote_occurrence is not None or self.quote_author_sha256 is not None:
            raise A2ContractError("only a quote zone carries quote fields")
        return self


def _check_order(spans: list[Span], limit: int) -> None:
    cursor = 0
    for span in spans:
        if span.start < cursor:
            raise A2ContractError("zones overlap or are not sorted")
        if span.end > limit:
            raise A2ContractError("zone is outside the text")
        cursor = span.end


class ContentZones(_ZoneModel):
    """Sorted, non-overlapping zones over one normalized text."""

    header: StageHeader = Field(
        default_factory=lambda: StageHeader(kind=ZONES_KIND, version=VERSION)
    )
    part_id: Text
    parsed_sha256: Digest
    parsed_length: Length
    normalized_sha256: Digest
    normalized_length: Length
    zones: tuple[Zone, ...]

    @model_validator(mode="after")
    def _closed(self) -> ContentZones:
        if (self.header.kind, self.header.version) != (ZONES_KIND, VERSION):
            raise A2ContractError("header is not zones@1")
        if not 1 <= len(self.zones) <= MAX_ZONES:
            raise A2ContractError("zone count is out of bounds")
        ids = [zone.zone_id for zone in self.zones]
        if len(set(ids)) != len(ids):
            raise A2ContractError("duplicate zone id")
        _check_order([z.original for z in self.zones], self.parsed_length)
        _check_order([z.normalized for z in self.zones], self.normalized_length)
        quotes = [z.quote_occurrence for z in self.zones if z.quote_occurrence]
        if [q.ordinal for q in quotes] != list(range(len(quotes))):
            raise A2ContractError("quote occurrences are not in order")
        return self

    def validate_against(self, content: NormalizedContent) -> None:
        """
        Prove that each zone is the exact projection through ``content``.

        The part, both digests and both lengths must match. For every zone
        the ``original`` range must equal the projection of its
        ``normalized`` range. A range that ends inside a ``transformed``
        segment is rejected.
        """
        same = (
            self.part_id == content.part_id
            and self.parsed_sha256 == content.parsed_sha256
            and self.parsed_length == content.parsed_length
            and self.normalized_sha256 == content.normalized_sha256
            and self.normalized_length == content.normalized_length
        )
        if not same:
            raise A2ContractError("zones do not bind the same texts")
        for zone in self.zones:
            lo, hi = content.project(zone.normalized.start, zone.normalized.end)
            if (lo, hi) != (zone.original.start, zone.original.end):
                raise A2ContractError("zone original span differs from projection")

    def verify_bytes(self, parsed: bytes, normalized: bytes) -> None:
        """
        Prove every zone range against the real bytes.

        Digests and lengths must match and every range must start and end
        on a character boundary in its text.
        """
        for data, sha, size in (
            (parsed, self.parsed_sha256, self.parsed_length),
            (normalized, self.normalized_sha256, self.normalized_length),
        ):
            if len(data) != size or sha256_hex(data) != sha:
                raise A2ContractError("text differs from the saved digest")
            _text_bytes(data, "text")
        for zone in self.zones:
            _slice_text(parsed, zone.original.start, zone.original.end, "parsed")
            _slice_text(
                normalized, zone.normalized.start, zone.normalized.end, "normalized"
            )

    def encode(self) -> bytes:
        """Return the bounded canonical bytes of this record."""
        return canonical_model_bytes(self)

    @classmethod
    def decode(cls, data: bytes) -> ContentZones:
        """Strictly decode canonical bytes; reject anything else."""
        return decode_model_bytes(cls, data)
