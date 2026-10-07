"""Value, coordinate, type, merge, formula, and ODS regressions."""

from __future__ import annotations

import pytest

from msgloom.preparation.contracts import (
    CellLocation,
    DocumentFormat,
    ParsedCell,
    ParserOutput,
    ParserProvenance,
    SheetLocation,
    TableBlock,
)
from msgloom.preparation.parsers.excel import parse
from tests.parser_excel.helpers import build_ods_fixture, request_for
from tests.parser_fixture_builders import build_xlsx_fixture


def _only_table(output: ParserOutput) -> TableBlock:
    blocks = output.blocks
    if len(blocks) != 1 or not isinstance(blocks[0], TableBlock):
        pytest.fail(f"expected exactly one table block, got {blocks!r}")
    return blocks[0]


def _cells(block: TableBlock) -> dict[tuple[int, int], ParsedCell]:
    return {(cell.row_index, cell.column_index): cell for cell in block.table.cells}


def test_xlsx_preserves_offsets_types_formula_cache_and_merge() -> None:
    content = build_xlsx_fixture()
    request = request_for(content, DocumentFormat.XLSX)

    output = parse(request, content)

    if output.provenance != ParserProvenance.from_request(request):
        pytest.fail("parser provenance did not exactly match the request")
    block = _only_table(output)
    location = block.table.location
    if not isinstance(location, SheetLocation):
        pytest.fail("table lost its SheetLocation")
    if location.sheet_name != "Visible":
        pytest.fail("visible sheet identity was not preserved")
    if block.table.row_count != 5 or block.table.column_count != 5:
        pytest.fail("sheet extent did not retain leading offsets and merged range")
    cells = _cells(block)
    expected = {
        (3, 2): ("1.0", "numeric"),
        (3, 3): ("alpha", "string"),
        (3, 4): ("true", "bool"),
        (4, 2): ("2024-10-02", "date"),
        (5, 2): ("tail", "string"),
    }
    for coordinate, (text, value_type) in expected.items():
        cell = cells.get(coordinate)
        if cell is None:
            pytest.fail(f"missing source cell {coordinate}")
        if cell.text != text or cell.value_type != value_type:
            pytest.fail(
                f"unexpected typed value at {coordinate}: "
                f"{cell.text!r}/{cell.value_type!r}"
            )
        if not isinstance(cell.location, CellLocation):
            pytest.fail(f"cell {coordinate} lost its CellLocation")
        if cell.location.row != coordinate[0] or cell.location.column != coordinate[1]:
            pytest.fail(f"cell {coordinate} was renumbered")

    formula = cells.get((4, 3))
    if formula is None:
        pytest.fail("formula cell C4 is missing")
    if formula.formula != "=SUM(B3,2)":
        pytest.fail(f"formula text was not preserved: {formula.formula!r}")
    if formula.cached_value != "3":
        pytest.fail(f"formula cached value was not preserved: {formula.cached_value!r}")
    if formula.text != "3" or formula.value_type != "numeric":
        pytest.fail("formula cell did not expose the cached typed result")

    merged_anchor = cells.get((3, 4))
    merged_follower = cells.get((3, 5))
    if merged_anchor is None or merged_follower is None:
        pytest.fail("merged range did not retain both source coordinates")
    if merged_anchor.merged_range != "D3:E3" or merged_follower.merged_range != "D3:E3":
        pytest.fail("merged range metadata was not preserved")
    if merged_follower.value_type != "null":
        pytest.fail("merged follower must remain a null structural cell")

    codes = {item.code for item in output.limitations}
    if "excel-hidden-sheet-excluded" not in codes:
        pytest.fail("default hidden-sheet policy was not disclosed")
    if "excel-number-format-metadata" not in codes:
        pytest.fail("date number-format visibility was not disclosed")


def test_ods_uses_calamine_values_and_discloses_metadata_limit() -> None:
    content = build_ods_fixture()
    request = request_for(
        content,
        DocumentFormat.ODS,
        settings=(
            ("include_hidden_rows", "true"),
            ("include_hidden_columns", "true"),
        ),
    )

    output = parse(request, content)

    block = _only_table(output)
    location = block.table.location
    if not isinstance(location, SheetLocation):
        pytest.fail("ODS table lost its SheetLocation")
    if location.sheet_name != "Data":
        pytest.fail("ODS sheet identity was not preserved")
    cells = _cells(block)
    expected = {
        (2, 2): ("ods-value", "string"),
        (2, 3): ("2.5", "numeric"),
        (2, 4): ("true", "bool"),
        (2, 5): ("2026-09-29", "date"),
        (2, 6): ("10:11:12", "time"),
    }
    for coordinate, (text, value_type) in expected.items():
        cell = cells.get(coordinate)
        if cell is None:
            pytest.fail(f"missing ODS cell {coordinate}")
        if cell.text != text or cell.value_type != value_type:
            pytest.fail(
                f"unexpected ODS value at {coordinate}: "
                f"{cell.text!r}/{cell.value_type!r}"
            )
    if (1, 1) in cells:
        pytest.fail("leading empty ODS area was flattened into emitted cells")
    codes = {item.code for item in output.limitations}
    if "excel-detailed-metadata-unavailable" not in codes:
        pytest.fail("ODS metadata backend limitation was not explicit")
