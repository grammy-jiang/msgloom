"""Regressions for reviewed spreadsheet semantic boundaries."""

from __future__ import annotations

from dataclasses import replace
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from msgloom.preparation.contracts import (
    CellLocation,
    DocumentFormat,
    SheetLocation,
    TableBlock,
)
from msgloom.preparation.parsers import excel as excel_parser
from msgloom.preparation.parsers import excel_metadata
from msgloom.preparation.parsers.excel import parse
from tests.parser_excel.helpers import (
    build_ods_fixture,
    build_visibility_fixture,
    request_for,
)
from tests.parser_fixture_builders import build_xlsx_fixture


def _sheet_name(block: TableBlock) -> str:
    location = block.table.location
    if not isinstance(location, SheetLocation):
        pytest.fail("spreadsheet table lost its SheetLocation")
    return location.sheet_name


def _coordinate(cell) -> str:
    location = cell.location
    if not isinstance(location, CellLocation):
        pytest.fail("spreadsheet cell lost its CellLocation")
    return location.coordinate


def _table_cells(content: bytes, request_format: DocumentFormat):
    output = parse(request_for(content, request_format), content)
    tables = [block for block in output.blocks if isinstance(block, TableBlock)]
    if len(tables) != 1:
        pytest.fail(f"expected one visible table, got {len(tables)}")
    return tables[0].table.cells, output


def _rewrite_sheet(content: bytes, transform) -> bytes:
    source = ZipFile(BytesIO(content))
    target_buffer = BytesIO()
    try:
        with ZipFile(target_buffer, "w", ZIP_DEFLATED) as target:
            for info in source.infolist():
                data = source.read(info.filename)
                if info.filename == "xl/worksheets/sheet1.xml":
                    data = transform(data)
                target.writestr(info, data)
    finally:
        source.close()
    return target_buffer.getvalue()


def test_metadata_failure_omits_cells_when_hidden_exclusion_is_unverifiable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = build_visibility_fixture()

    def fail_metadata(_: bytes):
        raise ValueError("synthetic metadata failure")

    monkeypatch.setattr(excel_parser, "read_ooxml_metadata", fail_metadata)
    cells, output = _table_cells(content, DocumentFormat.XLSX)

    if cells:
        pytest.fail("unknown row/column visibility was treated as visible")
    codes = {item.code for item in output.limitations}
    required = {
        "excel-ooxml-metadata-failed",
        "excel-row-visibility-unavailable",
        "excel-column-visibility-unavailable",
        "excel-hidden-sheet-excluded",
    }
    if not required.issubset(codes):
        pytest.fail(f"missing fail-closed visibility limitations: {codes!r}")


def test_missing_per_sheet_metadata_fails_closed_but_explicit_include_allows_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = build_visibility_fixture()
    metadata = excel_metadata.read_ooxml_metadata(content)
    monkeypatch.setattr(
        excel_parser,
        "read_ooxml_metadata",
        lambda _: {"Hidden": metadata["Hidden"]},
    )
    cells, output = _table_cells(content, DocumentFormat.XLSX)
    if cells:
        pytest.fail("missing per-sheet visibility metadata leaked cell values")
    codes = {item.code for item in output.limitations}
    if "excel-row-visibility-unavailable" not in codes:
        pytest.fail("missing per-sheet row visibility was not disclosed")

    settings = (
        ("include_hidden_sheets", "true"),
        ("include_hidden_rows", "true"),
        ("include_hidden_columns", "true"),
    )
    output = parse(
        request_for(content, DocumentFormat.XLSX, settings=settings),
        content,
    )
    tables = [block for block in output.blocks if isinstance(block, TableBlock)]
    visible = next(
        (block for block in tables if _sheet_name(block) == "Visible"),
        None,
    )
    if visible is None or not visible.table.cells:
        pytest.fail(
            "explicit inclusion did not allow cells with unavailable visibility"
        )


def test_ods_default_exclusion_omits_unverifiable_row_and_column_content() -> None:
    content = build_ods_fixture()
    cells, output = _table_cells(content, DocumentFormat.ODS)
    if cells:
        pytest.fail("ODS unknown row/column visibility was treated as visible")
    codes = {item.code for item in output.limitations}
    if not {
        "excel-row-visibility-unavailable",
        "excel-column-visibility-unavailable",
    }.issubset(codes):
        pytest.fail(f"ODS visibility boundary was not explicit: {codes!r}")


def test_explicit_empty_and_formula_cached_result_types_are_distinct() -> None:
    def add_cells(xml: bytes) -> bytes:
        marker = b'<row r="3">'
        inserted = (
            b'<row r="2">'
            b'<c r="A2" t="inlineStr"><is><t></t></is></c>'
            b'<c r="B2" t="e"><f>1/0</f><v>#DIV/0!</v></c>'
            b'<c r="C2" t="str"><f>""</f><v></v></c>'
            b'<c r="D2" t="n"><f>0</f><v>0</v></c>'
            b'<c r="E2" t="b"><f>FALSE</f><v>0</v></c>'
            b"</row>"
        )
        return xml.replace(marker, inserted + marker, 1)

    content = _rewrite_sheet(build_xlsx_fixture(), add_cells)
    cells, _ = _table_cells(content, DocumentFormat.XLSX)
    by_coordinate = {_coordinate(cell): cell for cell in cells}

    empty = by_coordinate.get("A2")
    if empty is None or empty.text != "" or empty.value_type != "string":
        pytest.fail("explicit OOXML empty string was merged with absent/null")
    expected = {
        "B2": ("#DIV/0!", "error", "#DIV/0!"),
        "C2": ("", "string", ""),
        "D2": ("0", "numeric", "0"),
        "E2": ("false", "bool", "false"),
    }
    for coordinate, (text, value_type, cached) in expected.items():
        cell = by_coordinate.get(coordinate)
        if cell is None:
            pytest.fail(f"missing formula cell {coordinate}")
        if (cell.text, cell.value_type, cell.cached_value) != (
            text,
            value_type,
            cached,
        ):
            pytest.fail(
                f"cached result changed at {coordinate}: "
                f"{cell.text!r}/{cell.value_type!r}/{cell.cached_value!r}"
            )


def test_partial_metadata_open_failure_closes_first_workbook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FirstWorkbook:
        closed = False

        def close(self) -> None:
            self.closed = True

    first = FirstWorkbook()
    calls = 0

    def fake_load(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return first
        raise ValueError("synthetic second open failure")

    monkeypatch.setattr(excel_metadata, "load_workbook", fake_load)
    with pytest.raises(ValueError, match="second open failure"):
        excel_metadata.read_ooxml_metadata(b"synthetic")
    if not first.closed:
        pytest.fail("first metadata workbook leaked after second open failed")


def test_unknown_profile_is_rejected_without_echoing_profile_content() -> None:
    content = build_visibility_fixture()
    request = request_for(content, DocumentFormat.XLSX)
    marker = "PRIVATE-CONTENT-MUST-NOT-ECHO"
    request = replace(
        request,
        config=replace(request.config, profile=marker),
    )
    with pytest.raises(ValueError) as captured:
        parse(request, content)
    message = str(captured.value)
    if "unsupported Excel parser profile" not in message:
        pytest.fail(f"unexpected profile error: {message!r}")
    if marker in message:
        pytest.fail("profile error echoed untrusted profile content")


def test_ole_magic_alone_is_not_reported_as_encryption() -> None:
    content = bytes.fromhex("d0cf11e0a1b11ae1") + bytes(504)
    request = request_for(content, DocumentFormat.XLSX)
    with pytest.raises(ValueError) as captured:
        parse(request, content)
    if "encrypted" in str(captured.value).lower():
        pytest.fail("arbitrary OLE bytes were misidentified as encryption")
