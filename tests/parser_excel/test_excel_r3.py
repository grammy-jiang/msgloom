"""R3 regressions for format identity and sparse-cell coverage."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import cast

import pytest
from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from msgloom.preparation.contracts import CellLocation, DocumentFormat, TableBlock
from msgloom.preparation.parsers.excel import parse
from tests.parser_excel.helpers import build_ods_fixture, request_for
from tests.parser_fixture_builders import build_xlsx_fixture

_FIXTURES = Path(__file__).with_name("fixtures")
_INCLUDE_UNKNOWN_VISIBILITY = (
    ("include_hidden_rows", "true"),
    ("include_hidden_columns", "true"),
)


def _cell_map(output):
    tables = [block for block in output.blocks if isinstance(block, TableBlock)]
    if len(tables) != 1:
        pytest.fail(f"expected one table, got {len(tables)}")
    return {
        cell.location.coordinate: cell
        for cell in tables[0].table.cells
        if isinstance(cell.location, CellLocation)
    }


def _fixture(name: str) -> bytes:
    return (_FIXTURES / name).read_bytes()


@pytest.mark.parametrize(
    "wrong_format",
    [
        DocumentFormat.XLSX,
        DocumentFormat.XLSM,
        DocumentFormat.XLSB,
        DocumentFormat.ODS,
    ],
)
def test_valid_xls_cannot_substitute_for_zip_formats(
    wrong_format: DocumentFormat,
) -> None:
    content = _fixture("synthetic-cell-values.xls")
    with pytest.raises(ValueError, match="does not match detected ZIP format"):
        parse(request_for(content, wrong_format), content)


def test_valid_xls_retains_typed_coordinates_and_discloses_empty_ambiguity() -> None:
    content = _fixture("synthetic-cell-values.xls")
    output = parse(
        request_for(
            content,
            DocumentFormat.XLS,
            settings=_INCLUDE_UNKNOWN_VISIBILITY,
        ),
        content,
    )
    cells = _cell_map(output)
    expected = {
        "B3": ("synthetic xls text", "string"),
        "C3": ("42", "numeric"),
        "B4": ("false", "bool"),
    }
    for coordinate, value in expected.items():
        cell = cells.get(coordinate)
        if cell is None or (cell.text, cell.value_type) != value:
            pytest.fail(f"XLS typed value changed at {coordinate}")
    if "C4" in cells:
        pytest.fail("ambiguous padded/empty XLS cell was claimed as a string")
    codes = {item.code for item in output.limitations}
    if "excel-cell-presence-unavailable" not in codes:
        pytest.fail("XLS empty-cell ambiguity was not disclosed")


@pytest.mark.parametrize(
    ("content_factory", "wrong_formats"),
    [
        (
            build_xlsx_fixture,
            (DocumentFormat.XLSM, DocumentFormat.XLSB, DocumentFormat.ODS),
        ),
        (
            build_ods_fixture,
            (DocumentFormat.XLSX, DocumentFormat.XLSB),
        ),
        (
            lambda: _fixture("synthetic-cell-values.xlsb"),
            (DocumentFormat.XLSX, DocumentFormat.ODS),
        ),
    ],
)
def test_zip_package_identity_rejects_cross_format_substitution(
    content_factory,
    wrong_formats: tuple[DocumentFormat, ...],
) -> None:
    content = content_factory()
    for wrong_format in wrong_formats:
        with pytest.raises(ValueError):
            parse(request_for(content, wrong_format), content)


def test_xlsx_presence_metadata_omits_holes_but_retains_explicit_empty() -> None:
    workbook = Workbook()
    sheet = cast(Worksheet, workbook.active)
    sheet["A1"] = 5
    sheet["C1"] = 10
    sheet["A2"] = ""
    sheet["C2"] = "text"
    buffer = BytesIO()
    workbook.save(buffer)
    workbook.close()
    content = buffer.getvalue()

    cells = _cell_map(parse(request_for(content, DocumentFormat.XLSX), content))
    if set(cells) != {"A1", "C1", "A2", "C2"}:
        pytest.fail(f"OOXML source-cell presence changed: {sorted(cells)!r}")
    empty = cells["A2"]
    if empty.text != "" or empty.value_type != "string":
        pytest.fail("explicit OOXML empty string was not retained")
    if "B1" in cells or "B2" in cells:
        pytest.fail("dense calamine padding was emitted as source cells")


def test_xlsb_backend_gap_is_visible_and_ambiguous_empties_are_omitted() -> None:
    content = _fixture("synthetic-cell-values.xlsb")
    output = parse(
        request_for(
            content,
            DocumentFormat.XLSB,
            settings=_INCLUDE_UNKNOWN_VISIBILITY,
        ),
        content,
    )
    cells = _cell_map(output)
    expected = {
        "B2": ("synthetic xlsb text", "string"),
        "B3": ("false", "bool"),
        "A4": ("explicit empty", "string"),
    }
    for coordinate, value in expected.items():
        cell = cells.get(coordinate)
        if cell is None or (cell.text, cell.value_type) != value:
            pytest.fail(f"supported XLSB value changed at {coordinate}")
    for coordinate in ("A2", "A3", "B4", "C2", "C4"):
        if coordinate in cells:
            pytest.fail(f"unqualified XLSB cell was emitted at {coordinate}")
    codes = {item.code for item in output.limitations}
    required = {
        "excel-cell-presence-unavailable",
        "excel-xlsb-value-coverage-unverified",
    }
    if not required.issubset(codes):
        pytest.fail(f"XLSB backend gaps were not explicit: {codes!r}")
