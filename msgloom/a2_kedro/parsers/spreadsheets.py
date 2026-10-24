"""
Spreadsheet parser for saved XLSX and XLSM bytes (P2-05).

The parser reads the saved bytes of one component and returns a frozen
:class:`SheetResult`. It never raises for workbook content. A bad workbook
gives an outcome and closed, content-free :class:`Limitation` codes.
Dropped content is never ``COMPLETE``.

Admitted: XLSX and XLSM through ``openpyxl`` (read-only, ``keep_vba=False``,
``keep_links=False``: no macro runs, no external link is followed). Two
passes keep both views of a formula: ``data_only=False`` gives the formula
text and ``data_only=True`` gives the cached value. Nothing is evaluated.
A formula without a cached value is flagged.

Refused: ODS and XLSB (``UNSUPPORTED_FORMAT``, ``FAILED``).
``python-calamine`` reads them, but it allocates a dense grid from the
first to the last cell. One far cell (``A1`` plus ``XFD1048576``) aborts
the process with no Python exception. A bounded pre-scan does not fit this
module (500-line rule). See ``docs/notes/a2-v2-parser-p2-05.md``.

Hostile dimensions: the declared ``<dimension>`` is never trusted. A
bounded expat scan of each sheet finds the real extents of cells with a
value or formula, hidden rows and columns, and merges. ``openpyxl``
iterates only those extents, capped by ``MAX_GRID_AREA``.

Bounds: input bytes, ZIP entries, actual (not declared) uncompressed size,
sheets, cells, text characters, grid area, scanned XML elements, stored
hidden indexes and iterated rows (see :mod:`.sheet_scan`). The style and
shared strings parts, which ``openpyxl`` loads in full, are counted before
it opens the workbook (``SCAN_LIMIT``, no cells). A hit gives
``INCOMPLETE``. Rows or cells out of order give ``OUT_OF_ORDER``.
Present but unextracted content (merges, comments, charts, images, drawings,
pivot caches, external links, embedded objects, macros) gets a limitation.
``repr`` shows no text, name or value. Details are fixed text.

CANDIDATE/RESEARCH, PROVISIONAL: see ``docs/notes/a2-v2-parser-p2-05.md``.
"""

from __future__ import annotations

import datetime as dt
import zipfile
from dataclasses import dataclass, field
from enum import StrEnum
from io import BytesIO
from typing import Any

import openpyxl
from openpyxl.utils.cell import get_column_letter

from msgloom.a2_kedro.contracts.codec import A2ContractError, sha256_hex
from msgloom.a2_kedro.contracts.parse import (
    MAX_CELLS,
    MAX_SHEETS,
    CellKind,
    LimitHit,
    ParserReceipt,
)
from msgloom.a2_kedro.parsers.sheet_scan import (
    MAX_HIDDEN,
    MAX_ROW_SPAN,
    MAX_SCAN_ELEMENTS,
    Budget,
    Format,
    Scans,
    SheetScan,
    content_kinds,
    detect,
    drop_capped,
    scan_members,
    sheet_paths,
)

__all__ = [
    "MAX_HIDDEN",
    "MAX_ROW_SPAN",
    "MAX_SCAN_ELEMENTS",
    "Cell",
    "Limitation",
    "Outcome",
    "Sheet",
    "SheetResult",
    "parse_spreadsheet",
]

WORKER = "msgloom.a2_kedro.parsers.spreadsheets"

#: Provisional bounds. They are parser decisions, not production limits.
MAX_BYTES = 32 * 1024 * 1024
MAX_UNCOMPRESSED = 64 * 1024 * 1024
MAX_ENTRIES = 2048
MAX_TEXT_CHARS = 1_000_000
MAX_CELL_CHARS = 32_767
MAX_GRID_AREA = 2_000_000
_OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_OLE_ENCRYPTED = "EncryptedPackage".encode("utf-16-le")


class Outcome(StrEnum):
    """Closed result of one parse."""

    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    FAILED = "failed"


class Limitation(StrEnum):
    """Closed, content-free reasons that a result is not complete."""

    EMPTY_FILE = "empty_file"
    UNSUPPORTED_FORMAT = "unsupported_format"
    PASSWORD_PROTECTED = "password_protected"
    CORRUPT = "corrupt"
    SIZE_LIMIT = "size_limit"
    ZIP_LIMIT = "zip_limit"
    SHEET_LIMIT = "sheet_limit"
    CELL_LIMIT = "cell_limit"
    TEXT_LIMIT = "text_limit"
    DIMENSION_LIMIT = "dimension_limit"
    SCAN_LIMIT = "scan_limit"
    OUT_OF_ORDER = "out_of_order"
    UNSUPPORTED_LAYOUT = "unsupported_layout"
    FORMULA_WITHOUT_CACHE = "formula_without_cache"
    MERGED_CELLS = "merged_cells"
    COMMENTS = "comments"
    CHARTS = "charts"
    IMAGES = "images"
    DRAWINGS = "drawings"
    PIVOT_CACHE = "pivot_cache"
    EXTERNAL_LINKS = "external_links"
    EMBEDDED_OBJECTS = "embedded_objects"
    MACROS = "macros"


L = Limitation
_FATAL = frozenset({L.EMPTY_FILE, L.UNSUPPORTED_FORMAT, L.PASSWORD_PROTECTED})
_FATAL |= {L.CORRUPT}
#: Lower-case package part prefix -> limitation.
_FEATURES = (
    ("xl/comments", L.COMMENTS),
    ("xl/threadedcomments/", L.COMMENTS),
    ("xl/charts/", L.CHARTS),
    ("xl/chartsheets/", L.CHARTS),
    ("xl/media/", L.IMAGES),
    ("xl/drawings/", L.DRAWINGS),
    ("xl/pivotcache", L.PIVOT_CACHE),
    ("xl/pivottables/", L.PIVOT_CACHE),
    ("xl/externallinks/", L.EXTERNAL_LINKS),
    ("xl/embeddings/", L.EMBEDDED_OBJECTS),
    ("xl/vbaproject.bin", L.MACROS),
)
#: Limitation -> receipt ``limit_hit``. The first mapped limitation, in
#: enum order, wins. ``LimitHit`` has no value for malformed or unsupported
#: content, merges, uncached formulas or row order. Those fall back to
#: ``"bytes"``, as in P2-02. Present but unextracted package parts map to
#: ``"parts"``.
_HITS: dict[Limitation, LimitHit] = {
    L.SIZE_LIMIT: "bytes",
    L.ZIP_LIMIT: "bytes",
    L.SHEET_LIMIT: "parts",
    L.CELL_LIMIT: "cells",
    L.DIMENSION_LIMIT: "cells",
    L.SCAN_LIMIT: "cells",
    L.TEXT_LIMIT: "bytes",
    L.COMMENTS: "parts",
    L.CHARTS: "parts",
    L.IMAGES: "parts",
    L.DRAWINGS: "parts",
    L.PIVOT_CACHE: "parts",
    L.EXTERNAL_LINKS: "parts",
    L.EMBEDDED_OBJECTS: "parts",
    L.MACROS: "parts",
}
_DATES = (dt.datetime, dt.date, dt.time, dt.timedelta)


@dataclass(frozen=True, slots=True)
class Cell:
    """One non-empty cell (zero-based position). ``repr`` hides content."""

    sheet_index: int
    row: int
    column: int
    kind: CellKind
    value: object = field(repr=False)
    formula: str | None = field(repr=False, default=None)
    formula_uncached: bool = False
    hidden_row: bool = False
    hidden_column: bool = False
    truncated: bool = False

    @property
    def ref(self) -> str:
        """Return the A1 reference."""
        return f"{get_column_letter(self.column + 1)}{self.row + 1}"

    @property
    def block_id(self) -> str:
        """Return the stable source block ID: sheet index and A1 ref."""
        return f"s{self.sheet_index}!{self.ref}"


@dataclass(frozen=True, slots=True)
class Sheet:
    """One sheet. ``repr`` hides the name. Hidden indexes are zero based."""

    index: int
    name: str = field(repr=False)
    state: str  # openpyxl: visible, hidden or veryHidden
    row_count: int
    column_count: int
    hidden_rows: tuple[int, ...] = field(repr=False, default=())
    hidden_columns: tuple[int, ...] = field(repr=False, default=())

    @property
    def block_id(self) -> str:
        """Return the stable source block ID of the sheet."""
        return f"s{self.index}"


@dataclass(frozen=True, slots=True)
class SheetResult:
    """Result of one parse. ``repr`` carries counts only."""

    format: Format | None
    outcome: Outcome
    limitations: tuple[Limitation, ...]
    input_bytes: int
    input_sha256: str
    sheets: tuple[Sheet, ...] = field(default=(), repr=False)
    cells: tuple[Cell, ...] = field(default=(), repr=False)

    def __repr__(self) -> str:
        counts = (len(self.limitations), len(self.sheets), len(self.cells))
        return f"SheetResult({self.format}, {self.outcome.value}, counts={counts})"

    def to_receipt(self, worker_version: str) -> ParserReceipt | None:
        """Return the parser receipt, or ``None`` for a ``FAILED`` result."""
        if self.outcome is Outcome.FAILED:
            return None
        hit: LimitHit = "none"
        if self.limitations:
            hit = "bytes"
            for item in self.limitations:
                if item in _HITS:
                    hit = _HITS[item]
                    break
        return ParserReceipt(
            worker=WORKER,
            worker_version=worker_version,
            outcome="partial" if self.limitations else "complete",
            limit_hit=hit,
            input_bytes=self.input_bytes,
            part_count=1,
        )


# --- bounded scans of the saved bytes -------------------------------------


def _kind(value: object, error: bool) -> CellKind:
    if value is None or value == "":
        return "empty"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, _DATES):
        return "date"
    return "error" if error else "text"


class _Build:
    """Collects sheets and cells under the shared cell and text budgets."""

    def __init__(self) -> None:
        self.found: set[Limitation] = set()
        self.sheets: list[Sheet] = []
        self.cells: list[Cell] = []
        self.chars, self.index, self.full = 0, 0, False
        self.scan = SheetScan()
        self.budget = Budget()

    def add(
        self, row: int, col: int, value: Any, formula: str | None, error: bool
    ) -> None:
        kind = _kind(value, error)
        if formula is None and kind == "empty":
            return
        if len(self.cells) >= MAX_CELLS:
            self.found.add(L.CELL_LIMIT)
            self.full = True
            return
        long = isinstance(value, str) and len(value) > MAX_CELL_CHARS
        long = long or len(formula or "") > MAX_CELL_CHARS
        value = value[:MAX_CELL_CHARS] if isinstance(value, str) else value
        formula = formula[:MAX_CELL_CHARS] if formula is not None else None
        self.chars += (len(value) if isinstance(value, str) else 0) + len(formula or "")
        if self.chars > MAX_TEXT_CHARS or long:
            self.found.add(L.TEXT_LIMIT)
            self.full = self.full or self.chars > MAX_TEXT_CHARS
            if self.full:
                return
        uncached = formula is not None and value is None
        if uncached:
            self.found.add(L.FORMULA_WITHOUT_CACHE)
        hidden = (row in self.scan.hidden_rows, col in self.scan.hidden_cols)
        args = (self.index, row, col, kind, value, formula, uncached, *hidden, long)
        self.cells.append(Cell(*args))

    def close_sheet(self, name: str, state: str, first: int) -> None:
        mine = self.cells[first:]
        rows = max((c.row + 1 for c in mine), default=0)
        cols = max((c.column + 1 for c in mine), default=0)
        hidden = [
            tuple(sorted(x)) for x in (self.scan.hidden_rows, self.scan.hidden_cols)
        ]
        self.sheets.append(Sheet(self.index, name, state, rows, cols, *hidden))


def _read_openpyxl(
    raw: bytes, scan: Scans, paths: dict[str, str], build: _Build
) -> None:
    opts: dict[str, Any] = {"read_only": True, "keep_links": False, "keep_vba": False}
    books: list[Any] = []
    try:
        for data_only in (False, True):
            books.append(
                openpyxl.load_workbook(BytesIO(raw), data_only=data_only, **opts)
            )
        sheets = list(zip(*(b.worksheets for b in books), strict=False))
        if len(sheets) != len(paths):  # openpyxl skips a part it cannot find
            build.found.add(L.UNSUPPORTED_LAYOUT)
        for index, (wf, wc) in enumerate(sheets):
            if index >= MAX_SHEETS:
                build.found.add(L.SHEET_LIMIT)
                break
            # The path comes from the workbook relationships, by sheet name.
            if (info := scan.get(paths.get(wf.title, ""))) is None:
                build.found.add(L.UNSUPPORTED_LAYOUT)
                continue
            build.index, build.scan = index, info
            _walk_sheet(wf, wc, build)
    except Exception:  # noqa: BLE001 - library errors must not leak their text
        build.found.add(L.CORRUPT)
    finally:
        for book in books:
            book.close()


def _walk_sheet(wf: Any, wc: Any, build: _Build) -> None:
    first, rows, cols = len(build.cells), build.scan.max_row, build.scan.max_col
    if build.scan.capped:  # the sheet part is a stub: no cells to read
        build.found.add(L.SCAN_LIMIT)
        rows = 0
    if build.scan.disordered:
        build.found.add(L.OUT_OF_ORDER)
    if rows * cols > MAX_GRID_AREA:
        build.found.add(L.DIMENSION_LIMIT)
        rows = max(1, MAX_GRID_AREA // cols)
    if rows > build.budget.span:  # empty rows between cells cost time too
        build.found.add(L.DIMENSION_LIMIT)
        rows = build.budget.span
    build.budget.span -= rows
    if rows * cols and not build.full:
        opts = {"max_row": rows, "max_col": cols}
        both = zip(wf.iter_rows(**opts), wc.iter_rows(**opts), strict=False)
        for r, (frow, crow) in enumerate(both):
            for c, (fc, cc) in enumerate(zip(frow, crow, strict=False)):
                formula = None
                if fc.data_type == "f":
                    formula = str(getattr(fc.value, "text", fc.value))
                build.add(r, c, cc.value, formula, cc.data_type == "e")
            if build.full:
                break
    build.close_sheet(wf.title, wf.sheet_state, first)


# --- entry point ----------------------------------------------------------


def _run(raw: bytes, build: _Build) -> Format | None:
    found = build.found
    if not raw:
        found.add(L.EMPTY_FILE)
    elif len(raw) > MAX_BYTES:
        found.add(L.SIZE_LIMIT)
    elif raw.startswith(_OLE):
        encrypted = _OLE_ENCRYPTED in raw
        found.add(L.PASSWORD_PROTECTED if encrypted else L.UNSUPPORTED_FORMAT)
    elif not raw.startswith(b"PK\x03\x04"):
        found.add(L.UNSUPPORTED_FORMAT)
    else:
        return _run_zip(zipfile.ZipFile(BytesIO(raw)), raw, build)
    return None


def _run_zip(zf: zipfile.ZipFile, raw: bytes, build: _Build) -> Format | None:
    found, infos = build.found, zf.infolist()
    if len(infos) > MAX_ENTRIES:
        found.add(L.ZIP_LIMIT)
    elif len({i.filename for i in infos}) != len(infos):
        found.add(L.CORRUPT)
    elif any(i.flag_bits & 1 for i in infos):
        found.add(L.PASSWORD_PROTECTED)
    elif (fmt := detect(zf, kinds := content_kinds(zf))) is None:
        found.add(L.UNSUPPORTED_FORMAT)
    else:
        found.update(
            f
            for i in infos
            for prefix, f in _FEATURES
            if i.filename.lower().startswith(prefix)
        )
        paths = sheet_paths(zf)
        parts = frozenset(paths.values()) - {""}
        args = (zf, parts, MAX_UNCOMPRESSED, build.budget, kinds)
        scan, too_big, loaded_too_big = scan_members(*args)
        if too_big:
            found.add(L.ZIP_LIMIT)
        elif loaded_too_big:  # openpyxl would load an unbounded part
            found.add(L.SCAN_LIMIT)
        else:
            if any(s.merged for s in scan.values()):
                found.add(L.MERGED_CELLS)
            safe = drop_capped(zf, scan)
            _read_openpyxl(raw if safe is None else safe, scan, paths, build)
        return fmt
    return None


def parse_spreadsheet(data: bytes) -> SheetResult:
    """
    Parse saved workbook bytes into sheets and cells.

    The format comes from the bytes, never from a name or a claim. Only a
    non-bytes argument raises :exc:`A2ContractError`.
    """
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise A2ContractError("workbook must be bytes")
    raw, build, fmt = bytes(data), _Build(), None
    try:
        fmt = _run(raw, build)
    except Exception:  # noqa: BLE001 - library errors must not leak their text
        build.found.add(L.CORRUPT)
    found = build.found
    if found & _FATAL and not build.sheets:
        outcome = Outcome.FAILED
    else:
        outcome = Outcome.INCOMPLETE if found else Outcome.COMPLETE
    return SheetResult(
        format=fmt,
        outcome=outcome,
        limitations=tuple(item for item in Limitation if item in found),
        input_bytes=len(raw),
        input_sha256=sha256_hex(raw),
        sheets=tuple(build.sheets),
        cells=tuple(build.cells),
    )
