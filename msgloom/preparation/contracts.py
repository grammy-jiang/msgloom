"""Typed contracts for isolated, untrusted attachment parsing."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from string import hexdigits


class DocumentFormat(StrEnum):
    """Detected input formats accepted by the preparation boundary."""

    MIME = "mime"
    HTML = "html"
    TEXT = "text"
    JSON = "json"
    XLSX = "xlsx"
    XLSM = "xlsm"
    XLS = "xls"
    XLSB = "xlsb"
    ODS = "ods"
    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"


class LimitationKind(StrEnum):
    """Explicit reasons parser output cannot represent all source content."""

    MISSING = "missing"
    UNSUPPORTED = "unsupported"
    PARTIAL = "partial"
    ENCRYPTED = "encrypted"
    SCANNED = "scanned"


class BlockRole(StrEnum):
    """Meaning-bearing block roles without parser-specific node types."""

    TEXT = "text"
    PARAGRAPH = "paragraph"
    HEADING = "heading"


def _require_text(value: str, field: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")


def _require_positive_finite_number(value: float, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field} must be a finite positive number")
    if value <= 0 or (isinstance(value, float) and not isfinite(value)):
        raise ValueError(f"{field} must be a finite positive number")


def _require_integer(value: int, field: str, *, minimum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field} must be an integer")
    if value < minimum:
        qualifier = "positive" if minimum == 1 else "zero or greater"
        raise ValueError(f"{field} must be {qualifier}")


def _require_tuple(value: object, field: str) -> None:
    if not isinstance(value, tuple):
        raise TypeError(f"{field} must be a tuple")


@dataclass(frozen=True, slots=True)
class SavedByteReference:
    """Reference already-persisted source bytes without owning file access."""

    reference: str
    sha256: str
    byte_count: int

    def __post_init__(self) -> None:
        _require_text(self.reference, "reference")
        _require_integer(self.byte_count, "byte_count", minimum=0)
        if len(self.sha256) != 64 or any(c not in hexdigits for c in self.sha256):
            raise ValueError("sha256 must contain exactly 64 hexadecimal characters")


@dataclass(frozen=True, slots=True)
class ParserIdentity:
    """Exact parser implementation identity recorded for provenance."""

    name: str
    version: str
    backend: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.name, "name")
        _require_text(self.version, "version")
        if self.backend is not None:
            _require_text(self.backend, "backend")


@dataclass(frozen=True, slots=True)
class ParserConfig:
    """Versionable parser profile and deterministic string settings."""

    profile: str
    settings: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.profile, "profile")
        _require_tuple(self.settings, "settings")
        keys: set[str] = set()
        for setting in self.settings:
            _require_tuple(setting, "parser setting")
            if len(setting) != 2:
                raise ValueError("parser settings must contain key/value pairs")
            key, value = setting
            _require_text(key, "setting key")
            if key in keys:
                raise ValueError(f"duplicate parser setting: {key}")
            keys.add(key)
            if not isinstance(value, str):
                raise TypeError("parser setting values must be strings")


@dataclass(frozen=True, slots=True)
class ParserLimits:
    """Resource ceilings and an acceptance deadline enforced by the caller.

    ``wall_time_seconds`` limits acceptance of a complete isolated result.
    Accepted parent work and required cleanup drain before timeout returns;
    their completion can exceed that deadline without making a result valid.
    Native worker memory and content budgets remain enforced separately.
    """

    wall_time_seconds: float
    memory_bytes: int
    decompressed_bytes: int
    output_bytes: int
    container_members: int

    def __post_init__(self) -> None:
        _require_positive_finite_number(self.wall_time_seconds, "wall_time_seconds")
        _require_integer(self.memory_bytes, "memory_bytes", minimum=1)
        _require_integer(self.decompressed_bytes, "decompressed_bytes", minimum=1)
        _require_integer(self.output_bytes, "output_bytes", minimum=1)
        _require_integer(self.container_members, "container_members", minimum=1)


@dataclass(frozen=True, slots=True)
class PageLocation:
    """One-based PDF page location."""

    page_number: int

    def __post_init__(self) -> None:
        _require_integer(self.page_number, "page_number", minimum=1)


@dataclass(frozen=True, slots=True)
class SheetLocation:
    """Spreadsheet sheet location, preserving provider-visible identity."""

    sheet_name: str

    def __post_init__(self) -> None:
        _require_text(self.sheet_name, "sheet_name")


@dataclass(frozen=True, slots=True)
class CellLocation:
    """One-based spreadsheet cell location."""

    sheet_name: str
    row: int
    column: int
    coordinate: str

    def __post_init__(self) -> None:
        _require_text(self.sheet_name, "sheet_name")
        _require_integer(self.row, "row", minimum=1)
        _require_integer(self.column, "column", minimum=1)
        _require_text(self.coordinate, "coordinate")


@dataclass(frozen=True, slots=True)
class DocumentLocation:
    """Location inside a named document part and ordered block."""

    part: str
    block_index: int | None = None

    def __post_init__(self) -> None:
        _require_text(self.part, "part")
        if self.block_index is not None:
            _require_integer(self.block_index, "block_index", minimum=0)


@dataclass(frozen=True, slots=True)
class MimePartLocation:
    """Stable parser-local MIME tree reference such as 1.2."""

    part_ref: str

    def __post_init__(self) -> None:
        _require_text(self.part_ref, "part_ref")


type SourceLocation = (
    PageLocation | SheetLocation | CellLocation | DocumentLocation | MimePartLocation
)


@dataclass(frozen=True, slots=True)
class ParsedLink:
    """A source link retained as data; parsers never fetch its target."""

    target: str
    text: str | None
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        _require_text(self.target, "target")


@dataclass(frozen=True, slots=True)
class ParsedCell:
    """A table cell with parser-observed value and optional formula metadata."""

    row_index: int
    column_index: int
    text: str | None
    value_type: str | None
    location: SourceLocation
    formula: str | None = None
    cached_value: str | None = None
    merged_range: str | None = None
    links: tuple[ParsedLink, ...] = ()

    def __post_init__(self) -> None:
        _require_integer(self.row_index, "row_index", minimum=1)
        _require_integer(self.column_index, "column_index", minimum=1)
        _require_tuple(self.links, "links")
        if self.value_type is not None:
            _require_text(self.value_type, "value_type")
        if self.formula is not None:
            _require_text(self.formula, "formula")
        if self.merged_range is not None:
            _require_text(self.merged_range, "merged_range")


@dataclass(frozen=True, slots=True)
class ParsedTable:
    """A rectangular table whose cells retain their own source locations."""

    row_count: int
    column_count: int
    cells: tuple[ParsedCell, ...]
    location: SourceLocation

    def __post_init__(self) -> None:
        _require_integer(self.row_count, "row_count", minimum=1)
        _require_integer(self.column_count, "column_count", minimum=1)
        _require_tuple(self.cells, "cells")
        seen: set[tuple[int, int]] = set()
        for cell in self.cells:
            key = (cell.row_index, cell.column_index)
            if key in seen:
                raise ValueError(f"duplicate table cell at {key}")
            seen.add(key)
            if cell.row_index > self.row_count or cell.column_index > self.column_count:
                raise ValueError("table cell falls outside declared dimensions")


@dataclass(frozen=True, slots=True)
class TextBlock:
    """Ordered text-like content with a source location."""

    order: int
    role: BlockRole
    text: str
    location: SourceLocation
    links: tuple[ParsedLink, ...] = ()

    def __post_init__(self) -> None:
        _require_integer(self.order, "order", minimum=0)
        _require_tuple(self.links, "links")


@dataclass(frozen=True, slots=True)
class TableBlock:
    """Ordered table content."""

    order: int
    table: ParsedTable

    def __post_init__(self) -> None:
        _require_integer(self.order, "order", minimum=0)


@dataclass(frozen=True, slots=True)
class LinkBlock:
    """Ordered standalone link content."""

    order: int
    link: ParsedLink

    def __post_init__(self) -> None:
        _require_integer(self.order, "order", minimum=0)


type ParsedBlock = TextBlock | TableBlock | LinkBlock


@dataclass(frozen=True, slots=True)
class MimePartReference:
    """MIME relationship metadata without duplicating source bytes."""

    part_ref: str
    parent_ref: str | None
    content_type: str
    disposition: str | None
    content_id: str | None
    location: MimePartLocation

    def __post_init__(self) -> None:
        _require_text(self.part_ref, "part_ref")
        _require_text(self.content_type, "content_type")
        if self.parent_ref is not None:
            _require_text(self.parent_ref, "parent_ref")


@dataclass(frozen=True, slots=True)
class ParserLimitation:
    """A visible extraction gap tied to a feature or source location."""

    kind: LimitationKind
    code: str
    detail: str
    feature: str | None = None
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        _require_text(self.code, "code")
        _require_text(self.detail, "detail")
        if self.feature is not None:
            _require_text(self.feature, "feature")


@dataclass(frozen=True, slots=True)
class ParserRequest:
    """Finite request supplied to an isolated parser worker."""

    source: SavedByteReference
    detected_format: DocumentFormat
    parser: ParserIdentity
    config: ParserConfig
    limits: ParserLimits


@dataclass(frozen=True, slots=True)
class ParserProvenance:
    """Exact source, detection, parser and configuration behind output."""

    source: SavedByteReference
    detected_format: DocumentFormat
    parser: ParserIdentity
    config: ParserConfig

    @classmethod
    def from_request(cls, request: ParserRequest) -> ParserProvenance:
        """Copy immutable provenance from a parser request."""
        return cls(
            source=request.source,
            detected_format=request.detected_format,
            parser=request.parser,
            config=request.config,
        )


@dataclass(frozen=True, slots=True)
class ParserOutput:
    """
    Untrusted structured parser output requiring Application validation.

    This contract deliberately has no attempt status or persistence operation.
    A worker cannot mark preparation complete; its caller verifies isolated
    output, records limitations, and owns any durable stage transition.
    """

    provenance: ParserProvenance
    blocks: tuple[ParsedBlock, ...] = ()
    mime_parts: tuple[MimePartReference, ...] = ()
    limitations: tuple[ParserLimitation, ...] = ()

    def __post_init__(self) -> None:
        _require_tuple(self.blocks, "blocks")
        _require_tuple(self.mime_parts, "mime_parts")
        _require_tuple(self.limitations, "limitations")
        orders = tuple(block.order for block in self.blocks)
        if orders != tuple(range(len(self.blocks))):
            raise ValueError("block order must be contiguous and zero-based")
        refs = tuple(part.part_ref for part in self.mime_parts)
        if len(refs) != len(set(refs)):
            raise ValueError("MIME part references must be unique")
        parents = {part.part_ref: part.parent_ref for part in self.mime_parts}
        for part_ref, parent_ref in parents.items():
            if parent_ref is not None and parent_ref not in parents:
                raise ValueError(
                    f"MIME parent {parent_ref!r} is not a declared MIME part"
                )
            seen = {part_ref}
            while parent_ref is not None:
                if parent_ref in seen:
                    raise ValueError("MIME parent relationships must not form a cycle")
                seen.add(parent_ref)
                parent_ref = parents[parent_ref]
