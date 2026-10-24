"""
``parsed_parts@1``: typed parts, pages, sheets and cells of one occurrence.

A :class:`ParsedParts` record is the output of one parser worker run. It
lists the parts found in the saved component bytes and, for paged and
sheet formats, page, sheet and cell records. The record never holds parsed
text. A cell keeps a position, a closed value kind and a digest of the
value, so the record stays free of message content.

Byte link: every part holds a :class:`ByteLink`. The link names a
component of :class:`~msgloom.a2_kedro.contracts.extract.ExtractedComponents`
by ``component_id`` and ``component_sha256`` and selects a byte window
(``offset`` and ``length``) inside the component. The model proves that
the window fits inside ``component_size``. :meth:`ParsedParts.validate_against`
proves that the link names a saved ``present`` or ``partial`` component with
the same digest. ``component_size`` is a producer claim; the parser worker
must read it from the saved bytes. No contract here can check it alone.

Format rule: each part holds a ``declared_format`` (from the source
metadata) and a ``detected_format`` (from the bytes). The two must be
equal. A mismatch is rejected and the occurrence must go to a held record.
The parser never trusts the declared format over the bytes.

Index rules: pages exist only for ``pdf``, ``docx`` and ``pptx`` parts.
Sheets and cells exist only for ``xlsx`` and ``csv`` parts. A page index
is less than ``page_count`` of its part. A sheet index is less than
``sheet_count``. A cell row and column are less than the row and column
count of its sheet. Part order is the producer order and a parent part
precedes its children. Page, sheet and cell records are sorted and unique,
so one record has one canonical byte form.

Failure handling: any violation raises :exc:`A2ContractError` (or a pydantic
``ValueError`` subclass at model construction). Messages are fixed text.
They never carry a part ID, a component ID or any parsed content. The
models hide the input value in pydantic error text.

CANDIDATE/RESEARCH, PROVISIONAL: field names, enums and limits are not
frozen. See ``docs/notes/a2-v2-contract-c0-04.md``.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import ConfigDict, Field, model_validator

from msgloom.a2_kedro.contracts.codec import (
    A2ContractError,
    A2Model,
    Digest,
    Text,
    canonical_model_bytes,
    decode_model_bytes,
)
from msgloom.a2_kedro.contracts.extract import ExtractedComponents
from msgloom.a2_kedro.contracts.header import StageHeader

KIND = "parsed_parts"
VERSION = "1"

#: Provisional bounds. They are wire decisions, not production limits.
MAX_PARTS = 256
MAX_PAGES = 4096
MAX_SHEETS = 256
MAX_CELLS = 8192
MAX_ROWS = 1_048_576
MAX_COLUMNS = 16_384
MAX_COMPONENT_BYTES = 2**40

PartRole = Literal["body", "alternate", "attachment", "embedded"]
PartFormat = Literal[
    "rfc822", "html", "plain_text", "pdf", "docx", "xlsx", "pptx", "csv", "image"
]
CellKind = Literal["empty", "text", "number", "boolean", "date", "error"]
WorkerOutcome = Literal["complete", "partial"]
LimitHit = Literal["none", "bytes", "parts", "pages", "cells", "time"]

PAGED_FORMATS: frozenset[str] = frozenset({"pdf", "docx", "pptx"})
SHEET_FORMATS: frozenset[str] = frozenset({"xlsx", "csv"})
USABLE_STATUSES: frozenset[str] = frozenset({"present", "partial"})

Count = Annotated[int, Field(ge=0, le=MAX_COMPONENT_BYTES)]
PageIndex = Annotated[int, Field(ge=0, lt=MAX_PAGES)]
SheetIndex = Annotated[int, Field(ge=0, lt=MAX_SHEETS)]
RowIndex = Annotated[int, Field(ge=0, lt=MAX_ROWS)]
ColumnIndex = Annotated[int, Field(ge=0, lt=MAX_COLUMNS)]


class _ParseModel(A2Model):
    """A2 base that also hides input values in validation errors."""

    model_config = ConfigDict(hide_input_in_errors=True)


class ByteLink(_ParseModel):
    """A byte window inside one saved component."""

    component_id: Text
    component_sha256: Digest
    component_size: Count
    offset: Count
    length: Annotated[int, Field(ge=1, le=MAX_COMPONENT_BYTES)]

    @model_validator(mode="after")
    def _inside_component(self) -> ByteLink:
        if self.offset + self.length > self.component_size:
            raise A2ContractError("byte window is outside the component")
        return self


class Part(_ParseModel):
    """One parsed part with its byte link and its format claim."""

    part_id: Text
    role: PartRole
    declared_format: PartFormat
    detected_format: PartFormat
    link: ByteLink
    parent_part_id: Text | None = None
    page_count: Annotated[int, Field(ge=0, le=MAX_PAGES)] = 0
    sheet_count: Annotated[int, Field(ge=0, le=MAX_SHEETS)] = 0

    @model_validator(mode="after")
    def _consistent(self) -> Part:
        if self.declared_format != self.detected_format:
            raise A2ContractError("declared format differs from detected format")
        if self.parent_part_id == self.part_id:
            raise A2ContractError("part is its own parent")
        if self.page_count and self.detected_format not in PAGED_FORMATS:
            raise A2ContractError("format has no pages")
        if self.sheet_count and self.detected_format not in SHEET_FORMATS:
            raise A2ContractError("format has no sheets")
        return self


class PageRecord(_ParseModel):
    """One page of a paged part; ``char_count`` is a size, not content."""

    part_id: Text
    page_index: PageIndex
    char_count: Count


class SheetRecord(_ParseModel):
    """One sheet of a sheet part with its used dimensions."""

    part_id: Text
    sheet_index: SheetIndex
    row_count: Annotated[int, Field(ge=0, le=MAX_ROWS)]
    column_count: Annotated[int, Field(ge=0, le=MAX_COLUMNS)]


class CellRecord(_ParseModel):
    """One non-content cell record: position, value kind and digest."""

    part_id: Text
    sheet_index: SheetIndex
    row: RowIndex
    column: ColumnIndex
    value_kind: CellKind
    value_sha256: Digest | None = None

    @model_validator(mode="after")
    def _digest_rule(self) -> CellRecord:
        if (self.value_kind == "empty") != (self.value_sha256 is None):
            raise A2ContractError("only an empty cell has no value digest")
        return self


class ParserReceipt(_ParseModel):
    """Receipt of one parser worker run: identity, outcome and limits."""

    worker: Text
    worker_version: Text
    outcome: WorkerOutcome
    limit_hit: LimitHit = "none"
    input_bytes: Count
    part_count: Annotated[int, Field(ge=1, le=MAX_PARTS)]

    @model_validator(mode="after")
    def _outcome_rule(self) -> ParserReceipt:
        if (self.outcome == "complete") != (self.limit_hit == "none"):
            raise A2ContractError("outcome conflicts with limit hit")
        return self


def _sorted_unique(keys: list[tuple[object, ...]], label: str) -> None:
    if len(set(keys)) != len(keys):
        raise A2ContractError(f"duplicate {label} record")
    if keys != sorted(keys):  # type: ignore[type-var]
        raise A2ContractError(f"{label} records are not sorted")


class ParsedParts(_ParseModel):
    """All parts of one occurrence, with a parser worker receipt."""

    header: StageHeader = Field(
        default_factory=lambda: StageHeader(kind=KIND, version=VERSION)
    )
    parts: tuple[Part, ...]
    pages: tuple[PageRecord, ...] = ()
    sheets: tuple[SheetRecord, ...] = ()
    cells: tuple[CellRecord, ...] = ()
    receipt: ParserReceipt

    @model_validator(mode="after")
    def _closed(self) -> ParsedParts:
        if (self.header.kind, self.header.version) != (KIND, VERSION):
            raise A2ContractError("header is not parsed_parts@1")
        self._check_parts()
        self._check_pages()
        self._check_sheets()
        self._check_cells()
        return self

    def _check_parts(self) -> None:
        if not 1 <= len(self.parts) <= MAX_PARTS:
            raise A2ContractError("part count is out of bounds")
        if self.receipt.part_count != len(self.parts):
            raise A2ContractError("receipt part count differs from parts")
        seen: set[str] = set()
        for part in self.parts:
            if part.part_id in seen:
                raise A2ContractError("duplicate part id")
            if part.parent_part_id is not None and part.parent_part_id not in seen:
                raise A2ContractError("parent part is missing or later")
            seen.add(part.part_id)

    def _check_pages(self) -> None:
        if len(self.pages) > MAX_PAGES:
            raise A2ContractError("page count is out of bounds")
        counts = {p.part_id: p.page_count for p in self.parts}
        for page in self.pages:
            if page.page_index >= counts.get(page.part_id, 0):
                raise A2ContractError("page index is out of range")
        _sorted_unique([(p.part_id, p.page_index) for p in self.pages], "page")

    def _check_sheets(self) -> None:
        if len(self.sheets) > MAX_SHEETS:
            raise A2ContractError("sheet count is out of bounds")
        counts = {p.part_id: p.sheet_count for p in self.parts}
        for sheet in self.sheets:
            if sheet.sheet_index >= counts.get(sheet.part_id, 0):
                raise A2ContractError("sheet index is out of range")
        _sorted_unique([(s.part_id, s.sheet_index) for s in self.sheets], "sheet")

    def _check_cells(self) -> None:
        if len(self.cells) > MAX_CELLS:
            raise A2ContractError("cell count is out of bounds")
        sizes = {(s.part_id, s.sheet_index): s for s in self.sheets}
        for cell in self.cells:
            sheet = sizes.get((cell.part_id, cell.sheet_index))
            if sheet is None:
                raise A2ContractError("cell names no sheet record")
            if cell.row >= sheet.row_count or cell.column >= sheet.column_count:
                raise A2ContractError("cell position is out of range")
        _sorted_unique(
            [(c.part_id, c.sheet_index, c.row, c.column) for c in self.cells], "cell"
        )

    def validate_against(self, extracted: ExtractedComponents) -> None:
        """
        Prove that every byte link names saved bytes of ``extracted``.

        A link must name an existing component with status ``present`` or
        ``partial`` and the same SHA-256 digest. Raise
        :exc:`A2ContractError` for a dangling link, a ``missing`` or
        ``unsupported`` component or a digest mismatch.
        """
        known = {c.component_id: c for c in extracted.components}
        for part in self.parts:
            component = known.get(part.link.component_id)
            if component is None:
                raise A2ContractError("byte link names no extracted component")
            if component.status not in USABLE_STATUSES:
                raise A2ContractError("byte link names an unusable component")
            if component.sha256 != part.link.component_sha256:
                raise A2ContractError("byte link digest differs from component")

    def encode(self) -> bytes:
        """Return the bounded canonical bytes of this record."""
        return canonical_model_bytes(self)

    @classmethod
    def decode(cls, data: bytes) -> ParsedParts:
        """Strictly decode canonical bytes; reject anything else."""
        return decode_model_bytes(cls, data)
