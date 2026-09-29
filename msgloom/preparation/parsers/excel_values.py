"""Convert calamine worksheet values without losing source coordinates."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from math import isfinite

from openpyxl.utils import get_column_letter

from msgloom.preparation.contracts import CellLocation, ParsedCell, ParsedLink


def value_text_and_type(value: object) -> tuple[str | None, str]:
    """Return deterministic text plus an observed spreadsheet value type."""
    if value is None:
        return None, "null"
    if isinstance(value, bool):
        return ("true" if value else "false"), "bool"
    if isinstance(value, datetime):
        return value.isoformat(), "datetime"
    if isinstance(value, date):
        return value.isoformat(), "date"
    if isinstance(value, time):
        return value.isoformat(), "time"
    if isinstance(value, timedelta):
        return str(value.total_seconds()), "duration-seconds"
    if isinstance(value, int):
        return str(value), "numeric"
    if isinstance(value, float):
        if not isfinite(value):
            return str(value), "numeric-nonfinite"
        return repr(value), "numeric"
    if isinstance(value, str):
        return value, "string"
    return str(value), type(value).__name__


def cell_location(sheet_name: str, row: int, column: int) -> CellLocation:
    """Build a one-based cell location and canonical A1 coordinate."""
    return CellLocation(
        sheet_name=sheet_name,
        row=row,
        column=column,
        coordinate=f"{get_column_letter(column)}{row}",
    )


def build_cell(
    *,
    sheet_name: str,
    row: int,
    column: int,
    value: object,
    formula: str | None = None,
    cached_value: str | None = None,
    merged_range: str | None = None,
    links: tuple[ParsedLink, ...] = (),
    text_override: str | None = None,
    type_override: str | None = None,
) -> ParsedCell:
    """Build a parsed cell while keeping the original absolute coordinates."""
    text, value_type = value_text_and_type(value)
    if type_override is not None:
        value_type = type_override
    if text_override is not None:
        text = text_override
    if formula is not None and cached_value is None and text is None:
        value_type = "formula"
    return ParsedCell(
        row_index=row,
        column_index=column,
        text=text,
        value_type=value_type,
        location=cell_location(sheet_name, row, column),
        formula=formula,
        cached_value=cached_value,
        merged_range=merged_range,
        links=links,
    )


class OutputBudget:
    """Conservatively bound emitted parser data before returning it."""

    _CELL_OVERHEAD = 192
    _BLOCK_OVERHEAD = 256

    def __init__(self, ceiling: int) -> None:
        self._ceiling = ceiling
        self._used = 0

    def charge_block(self, sheet_name: str) -> None:
        self._charge(self._BLOCK_OVERHEAD + len(sheet_name.encode("utf-8")))

    def charge_cell(self, cell: ParsedCell) -> None:
        strings = (
            cell.text,
            cell.value_type,
            cell.formula,
            cell.cached_value,
            cell.merged_range,
            (
                cell.location.coordinate
                if isinstance(cell.location, CellLocation)
                else None
            ),
        )
        size = self._CELL_OVERHEAD + sum(
            len(value.encode("utf-8")) for value in strings if value is not None
        )
        for link in cell.links:
            size += len(link.target.encode("utf-8"))
            if link.text is not None:
                size += len(link.text.encode("utf-8"))
        self._charge(size)

    def charge_limitation(self, code: str, detail: str, feature: str | None) -> None:
        size = 128 + len(code.encode("utf-8")) + len(detail.encode("utf-8"))
        if feature is not None:
            size += len(feature.encode("utf-8"))
        self._charge(size)

    def _charge(self, amount: int) -> None:
        self._used += amount
        if self._used > self._ceiling:
            raise ValueError("spreadsheet parser output ceiling exceeded")
