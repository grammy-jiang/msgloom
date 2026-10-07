"""OOXML metadata, hidden-content policy, and unsupported-feature tests."""

from __future__ import annotations

import pytest

from msgloom.preparation.contracts import (
    CellLocation,
    DocumentFormat,
    ParsedCell,
    ParserOutput,
    SheetLocation,
    TableBlock,
)
from msgloom.preparation.parsers.excel import parse
from tests.parser_excel.helpers import (
    add_unsupported_ooxml_parts,
    build_visibility_fixture,
    request_for,
)


def _tables(output: ParserOutput) -> tuple[TableBlock, ...]:
    blocks = output.blocks
    if any(not isinstance(block, TableBlock) for block in blocks):
        pytest.fail(f"unexpected non-table spreadsheet block: {blocks!r}")
    return tuple(block for block in blocks if isinstance(block, TableBlock))


def _coordinate(cell: ParsedCell) -> str:
    location = cell.location
    if not isinstance(location, CellLocation):
        pytest.fail("spreadsheet cell lost its CellLocation")
    return location.coordinate


def _sheet_name(block: TableBlock) -> str:
    location = block.table.location
    if not isinstance(location, SheetLocation):
        pytest.fail("spreadsheet table lost its SheetLocation")
    return location.sheet_name


def _coordinates(block: TableBlock) -> set[str]:
    return {_coordinate(cell) for cell in block.table.cells}


def test_default_hidden_policy_excludes_sheet_row_and_column() -> None:
    content = build_visibility_fixture()
    output = parse(request_for(content, DocumentFormat.XLSX), content)

    blocks = _tables(output)
    if len(blocks) != 1 or _sheet_name(blocks[0]) != "Visible":
        pytest.fail("default policy did not exclude the hidden sheet")
    coordinates = _coordinates(blocks[0])
    if "B4" in coordinates or "C4" in coordinates:
        pytest.fail("default policy did not exclude the hidden row")
    if "D3" in coordinates:
        pytest.fail("default policy did not exclude the hidden column")
    codes = {item.code for item in output.limitations}
    required = {
        "excel-hidden-sheet-excluded",
        "excel-hidden-rows-excluded",
        "excel-hidden-columns-excluded",
    }
    if not required.issubset(codes):
        pytest.fail(f"hidden-content limitations are incomplete: {codes!r}")
    if "excel-formula-cache-unavailable" in codes:
        pytest.fail("excluded hidden formula metadata leaked through limitations")


def test_explicit_hidden_policy_includes_hidden_content() -> None:
    content = build_visibility_fixture()
    settings = (
        ("include_hidden_sheets", "true"),
        ("include_hidden_rows", "true"),
        ("include_hidden_columns", "true"),
    )
    output = parse(
        request_for(
            content,
            DocumentFormat.XLSX,
            settings=settings,
        ),
        content,
    )

    blocks = _tables(output)
    names = [_sheet_name(block) for block in blocks]
    if names != ["Visible", "Hidden"]:
        pytest.fail(f"sheet order/identity changed: {names!r}")
    coordinates = _coordinates(blocks[0])
    for coordinate in ("B4", "C4", "D3"):
        if coordinate not in coordinates:
            pytest.fail(f"explicit hidden policy lost {coordinate}")
    formula = next(
        (cell for cell in blocks[0].table.cells if _coordinate(cell) == "C4"),
        None,
    )
    if formula is None or formula.formula != "=SUM(1,2)":
        pytest.fail("formula metadata was not preserved")
    if formula.cached_value is not None:
        pytest.fail("parser invented a cached value for an unevaluated formula")
    codes = {item.code for item in output.limitations}
    if "excel-formula-cache-unavailable" not in codes:
        pytest.fail("missing formula cache was not disclosed")


def test_error_link_merge_date_time_and_format_visibility() -> None:
    content = build_visibility_fixture()
    output = parse(request_for(content, DocumentFormat.XLSX), content)
    block = _tables(output)[0]
    cells = {_coordinate(cell): cell for cell in block.table.cells}

    error = cells.get("C3")
    if error is None or error.value_type != "error":
        pytest.fail("OOXML error cell was not typed as an error")
    if error.text != "#DIV/0!":
        pytest.fail(f"error text changed: {None if error is None else error.text!r}")

    link_cell = cells.get("E3")
    if link_cell is None or len(link_cell.links) != 1:
        pytest.fail("cell hyperlink metadata was not retained")
    if link_cell.links[0].target != "https://example.invalid/workbook":
        pytest.fail("cell hyperlink target changed")

    merged = [cells.get("F3"), cells.get("G3")]
    if any(cell is None for cell in merged):
        pytest.fail("merged structural cells are incomplete")
    if any(cell.merged_range != "F3:G3" for cell in merged if cell is not None):
        pytest.fail("merged range reference changed")

    if cells["B5"].value_type != "date":
        pytest.fail("OOXML date was not preserved as a typed temporal value")
    if cells["C5"].value_type != "time":
        pytest.fail("OOXML time was not preserved as a typed temporal value")
    format_details = [
        item.detail
        for item in output.limitations
        if item.code == "excel-number-format-metadata"
    ]
    if not any("yyyy-mm-dd" in detail for detail in format_details):
        pytest.fail("date number format was not visible in limitations")
    if not any("hh:mm:ss" in detail for detail in format_details):
        pytest.fail("time number format was not visible in limitations")


def test_macros_embedded_objects_and_external_links_are_never_activated() -> None:
    content = add_unsupported_ooxml_parts(build_visibility_fixture())
    output = parse(request_for(content, DocumentFormat.XLSM), content)

    codes = {item.code for item in output.limitations}
    expected = {
        "excel-macros-not-executed",
        "excel-embedded-content-not-extracted",
        "excel-external-links-not-accessed",
    }
    if not expected.issubset(codes):
        pytest.fail(f"unsupported workbook features were not explicit: {codes!r}")
