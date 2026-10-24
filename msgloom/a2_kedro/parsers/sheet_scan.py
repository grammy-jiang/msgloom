"""
Bounded expat scans of the saved workbook bytes (P2-05).

This module serves :mod:`msgloom.a2_kedro.parsers.spreadsheets`. It reads
sheet XML in chunks with expat and never builds a tree. It finds the real
extents of cells with a value or formula, hidden rows and columns, merges,
and rows or cells that ``openpyxl`` read-only mode would drop.

Every scan has a shared :class:`Budget`. A sheet that exhausts a budget
stops at once: the rest of the member is only counted for the byte bound.
The sheet then has ``capped`` set and the caller reports a limitation.
``openpyxl`` parses a whole sheet part when it opens a workbook, so the
caller reads a capped sheet from :func:`drop_capped`: a copy of the package
where each capped sheet part is an empty stub. A capped sheet gives no cells.

Bounds, all provisional parser decisions:

- ``MAX_SCAN_ELEMENTS``: start tags of all sheets together. Bounds time and
  the size of any one ``openpyxl`` row.
- ``MAX_HIDDEN``: stored hidden row and column indexes of all sheets
  together. Bounds the size of the result.
- ``MAX_ROW_SPAN``: rows that ``openpyxl`` may iterate for all sheets
  together. The caller spends it. Empty rows between cells cost one each.

Nothing here keeps text, names or values from the workbook.
"""

from __future__ import annotations

import posixpath
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from io import BytesIO
from typing import Any
from xml.parsers import expat

from openpyxl.utils.cell import coordinate_to_tuple

MAX_SCAN_ELEMENTS = 250_000
MAX_HIDDEN = 20_000
MAX_ROW_SPAN = 200_000
_SMALL, _CHUNK, _MAX_COLUMN = 1024 * 1024, 64 * 1024, 16_384
_TRUE = ("1", "true")
_WORKSHEET = "/relationships/worksheet"
_STUB = (
    b'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/'
    b'2006/main"><sheetData/></worksheet>'
)

Hook = Callable[[str, dict[str, str]], None]


@dataclass(slots=True)
class Budget:
    """Remaining shared budgets of one parse."""

    elements: int = MAX_SCAN_ELEMENTS
    hidden: int = MAX_HIDDEN
    span: int = MAX_ROW_SPAN


@dataclass(slots=True)
class SheetScan:
    """Real extents (1-based counts) and flags of one sheet."""

    hidden_rows: set[int] = field(default_factory=set)
    hidden_cols: set[int] = field(default_factory=set)
    max_row: int = 0
    max_col: int = 0
    merged: int = 0
    capped: bool = False  # a budget ended the scan early
    disordered: bool = False  # non-increasing row or cell position


Scans = dict[str, SheetScan]


class Reject(Exception):
    """DTD, entity, size mismatch or bad package."""


class _Stop(Exception):
    """A budget ended the scan of one sheet."""


def _reject(*_args: object) -> None:
    raise Reject


def _local(name: str) -> str:
    return name.rsplit(" ", 1)[-1]


def xml_parser(
    wanted: frozenset[str], hook: Hook, every: Callable[[], None] | None = None
) -> Any:
    """Return an expat parser that rejects DTDs and entities.

    ``hook`` gets the local tag and the local attribute names of each
    wanted element. ``every`` runs first for every start tag.
    """
    parser = expat.ParserCreate(namespace_separator=" ")

    def start(name: str, attrs: dict[str, str]) -> None:
        if every is not None:
            every()
        if (local := _local(name)) in wanted:
            hook(local, {_local(k): v for k, v in attrs.items()})

    parser.StartElementHandler = start
    parser.StartDoctypeDeclHandler = _reject
    parser.EntityDeclHandler = _reject
    return parser


def _int(text: str | None, default: int) -> int:
    if text is None or not text.isascii() or not text.isdigit() or len(text) > 9:
        return default
    return int(text)


def _hide(budget: Budget, store: set[int], items: range | tuple[int, ...]) -> bool:
    """Store new indexes. Return false and store nothing if over budget."""
    fresh = [i for i in items if i not in store]
    if len(fresh) > budget.hidden:
        return False
    budget.hidden -= len(fresh)
    store.update(fresh)
    return True


def _sheet_parser(scan: SheetScan, budget: Budget) -> Any:
    at = {"row": 0, "col": 0, "cell_row": 0, "cell_col": 0}

    def stop() -> None:
        scan.capped = True
        raise _Stop

    def every() -> None:
        budget.elements -= 1
        if budget.elements < 0:
            stop()

    def row(a: dict[str, str]) -> None:
        number = _int(a.get("r"), at["row"] + 1)
        scan.disordered = scan.disordered or number <= at["row"]
        at["row"], at["col"] = number, 0
        hidden = a.get("hidden") in _TRUE and number > 0
        if hidden and not _hide(budget, scan.hidden_rows, (number - 1,)):
            stop()

    def cell(a: dict[str, str]) -> None:
        column = at["col"] + 1
        if "r" in a:
            column = coordinate_to_tuple(a["r"])[1]
        scan.disordered = scan.disordered or column <= at["col"]
        at["col"] = column
        at["cell_row"], at["cell_col"] = at["row"], column

    def hook(tag: str, a: dict[str, str]) -> None:
        if tag == "row":
            row(a)
        elif tag == "c":
            cell(a)
        elif tag == "col" and a.get("hidden") in _TRUE:
            low, high = _int(a.get("min"), 0), _int(a.get("max"), 0)
            span = range(max(low, 1) - 1, min(high, _MAX_COLUMN))
            if not _hide(budget, scan.hidden_cols, span):
                stop()
        elif tag == "mergeCell":
            scan.merged += 1
        elif tag in ("v", "f", "is"):
            scan.max_row = max(scan.max_row, at["cell_row"])
            scan.max_col = max(scan.max_col, at["cell_col"])

    wanted = frozenset({"row", "c", "v", "f", "is", "col", "mergeCell"})
    return xml_parser(wanted, hook, every)


def small(zf: zipfile.ZipFile, name: str) -> bytes:
    """Return a small member. Reject a member over the small bound."""
    info = zf.getinfo(name)
    if info.file_size > _SMALL:
        raise Reject
    with zf.open(info) as handle:
        return handle.read(_SMALL + 1)


def _resolve(target: str) -> str:
    """Return the lower-case package path of a workbook relationship."""
    joined = target[1:] if target.startswith("/") else f"xl/{target}"
    return posixpath.normpath(joined).lower()


def sheet_paths(zf: zipfile.ZipFile) -> dict[str, str]:
    """
    Map each sheet name to the lower-case package path of its worksheet.

    The workbook relationships give the path, so a sheet part may live
    outside ``xl/worksheets/``. A duplicate sheet name maps to ``""``.
    """
    names = {n.lower(): n for n in zf.namelist()}
    rels: dict[str, str] = {}

    def rel(_tag: str, a: dict[str, str]) -> None:
        is_sheet = a.get("Type", "").lower().endswith(_WORKSHEET)
        if is_sheet and a.get("TargetMode", "").lower() != "external":
            rels[a.get("Id", "")] = a.get("Target", "")

    sheets: list[tuple[str, str]] = []

    def sheet(_tag: str, a: dict[str, str]) -> None:
        sheets.append((a.get("name", ""), a.get("id", "")))

    if (rel_name := names.get("xl/_rels/workbook.xml.rels")) is None:
        return {}
    xml_parser(frozenset({"Relationship"}), rel).Parse(small(zf, rel_name), True)
    xml_parser(frozenset({"sheet"}), sheet).Parse(small(zf, "xl/workbook.xml"), True)
    paths: dict[str, str] = {}
    for name, rid in sheets:
        target = rels.get(rid)
        if target is None:
            continue
        path = _resolve(target)
        paths[name] = "" if name in paths or path.startswith("..") else path
    return paths


def scan_members(
    zf: zipfile.ZipFile,
    sheet_parts: frozenset[str],
    max_uncompressed: int,
    budget: Budget,
) -> tuple[Scans, bool]:
    """
    Stream every member once. Count actual bytes, never declared bytes.

    A member is a sheet if it is in ``sheet_parts`` or under
    ``xl/worksheets/``. Return the scans and whether the uncompressed bound
    ended the walk. A member that exceeds its declared size raises
    :exc:`Reject`.
    """
    scan: Scans = {}
    total = 0
    for info in zf.infolist():
        if info.is_dir():
            continue
        name = info.filename.lower()
        parser = None
        if name in sheet_parts or (
            name.startswith("xl/worksheets/") and name.endswith(".xml")
        ):
            parser = _sheet_parser(scan.setdefault(name, SheetScan()), budget)
        seen = 0
        with zf.open(info) as handle:
            while chunk := handle.read(_CHUNK):
                seen, total = seen + len(chunk), total + len(chunk)
                if total > max_uncompressed:
                    return scan, True
                if seen > info.file_size:
                    raise Reject
                if parser is None:
                    continue
                try:
                    parser.Parse(chunk, False)
                except _Stop:
                    parser = None
        if parser is not None:
            parser.Parse(b"", True)
    return scan, False


def drop_capped(zf: zipfile.ZipFile, scan: Scans) -> bytes | None:
    """
    Return package bytes with each capped sheet part replaced by a stub.

    Return ``None`` if no sheet is capped. The members are stored without
    compression. Their actual sizes passed :func:`scan_members`. The capped
    members are never read again.
    """
    capped = {name for name, item in scan.items() if item.capped}
    if not capped:
        return None
    out = BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as dst:
        for info in zf.infolist():
            if info.is_dir():
                continue
            stub = info.filename.lower() in capped
            dst.writestr(info.filename, _STUB if stub else zf.read(info))
    return out.getvalue()
