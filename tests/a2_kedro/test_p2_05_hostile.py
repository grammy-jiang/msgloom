"""P2-05 hostile workbooks: huge dimension claims, bombs, DTDs, time."""

from __future__ import annotations

import time
import zipfile
from io import BytesIO

import pytest

from msgloom.a2_kedro.parsers.spreadsheets import Limitation as L
from msgloom.a2_kedro.parsers.spreadsheets import Outcome, parse_spreadsheet
from tests.a2_kedro.helpers import check

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
BOOK = "application/vnd.openxmlformats-officedocument.spreadsheetml"


def mini(sheet_xml: str, extra: dict[str, bytes] | None = None) -> bytes:
    """Build a tiny workbook by hand with one sheet body."""
    parts = {
        "[Content_Types].xml": (
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/'
            'content-types"><Override PartName="/xl/workbook.xml" '
            f'ContentType="{BOOK}.sheet.main+xml"/><Override '
            f'PartName="/xl/worksheets/sheet1.xml" ContentType="{BOOK}.worksheet+xml"/>'
            "</Types>"
        ),
        "_rels/.rels": (
            f'<Relationships xmlns="{PKG}"><Relationship Id="r1" '
            f'Type="{REL}/officeDocument" Target="xl/workbook.xml"/></Relationships>'
        ),
        "xl/workbook.xml": (
            f'<workbook xmlns="{MAIN}" xmlns:r="{REL}"><sheets>'
            '<sheet name="S" sheetId="1" r:id="rId1"/></sheets></workbook>'
        ),
        "xl/_rels/workbook.xml.rels": (
            f'<Relationships xmlns="{PKG}"><Relationship Id="rId1" '
            f'Type="{REL}/worksheet" Target="worksheets/sheet1.xml"/></Relationships>'
        ),
        "xl/worksheets/sheet1.xml": f'<worksheet xmlns="{MAIN}">{sheet_xml}</worksheet>',
    }
    out = BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, body in parts.items():
            zf.writestr(name, body)
        for name, body in (extra or {}).items():
            zf.writestr(name, body)
    return out.getvalue()


def inline(ref: str, text: str) -> str:
    return f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>'


def test_hand_built_workbook_parses() -> None:
    body = f'<sheetData><row r="1">{inline("A1", "hi")}</row></sheetData>'
    result = parse_spreadsheet(mini(body))
    check(result.outcome is Outcome.COMPLETE, "complete")
    check(result.cells[0].value == "hi" and result.cells[0].ref == "A1", "cell")


def test_declared_full_grid_dimension_does_not_allocate() -> None:
    body = (
        '<dimension ref="A1:XFD1048576"/><sheetData><row r="1">'
        f"{inline('A1', 'x')}</row></sheetData>"
    )
    begin = time.perf_counter()
    result = parse_spreadsheet(mini(body))
    check(time.perf_counter() - begin < 2.0, "declared dimension cost time")
    check(result.outcome is Outcome.COMPLETE and len(result.cells) == 1, "ok")
    check((result.sheets[0].row_count, result.sheets[0].column_count) == (1, 1), "dims")


def test_far_sparse_cell_is_bounded_and_flagged() -> None:
    body = (
        '<dimension ref="A1:XFD1048576"/><sheetData>'
        f'<row r="1">{inline("A1", "x")}</row>'
        f'<row r="1048576">{inline("XFD1048576", "far")}</row></sheetData>'
    )
    begin = time.perf_counter()
    result = parse_spreadsheet(mini(body))
    check(time.perf_counter() - begin < 5.0, "far cell cost too much time")
    check(result.outcome is Outcome.INCOMPLETE, "partial")
    check(L.DIMENSION_LIMIT in result.limitations, "dimension limit")
    check(result.cells[0].block_id == "s0!A1", "near cell kept")


def test_styled_empty_cells_do_not_inflate_extents() -> None:
    row = "".join(f'<c r="{c}5" s="1"/>' for c in ("A", "B", "XFD"))
    body = f'<sheetData><row r="5">{row}</row></sheetData>'
    result = parse_spreadsheet(mini(body))
    check(result.outcome is Outcome.COMPLETE and not result.cells, "empty styled row")


@pytest.mark.parametrize(
    "prefix",
    [
        '<!DOCTYPE x [<!ENTITY a "aaaa">]>',
        '<!DOCTYPE x SYSTEM "http://example.invalid/x.dtd">',
    ],
)
def test_doctype_and_entities_are_rejected(prefix) -> None:
    data = mini("<sheetData/>")
    with zipfile.ZipFile(BytesIO(data)) as zf:
        files = {n: zf.read(n) for n in zf.namelist()}
    files["xl/worksheets/sheet1.xml"] = (
        prefix.encode() + files["xl/worksheets/sheet1.xml"]
    )
    out = BytesIO()
    with zipfile.ZipFile(out, "w") as zf:
        for name, body in files.items():
            zf.writestr(name, body)
    result = parse_spreadsheet(out.getvalue())
    check(result.outcome is Outcome.FAILED, "failed")
    check(result.limitations == (L.CORRUPT,), "corrupt")


def test_zip_bomb_stops_at_uncompressed_bound() -> None:
    bomb = {"xl/media/big.bin": b"\x00" * (80 * 1024 * 1024)}
    data = mini("<sheetData/>", bomb)
    check(len(data) < 1024 * 1024, "fixture must be small")
    begin = time.perf_counter()
    result = parse_spreadsheet(data)
    check(time.perf_counter() - begin < 10.0, "bomb took too long")
    check(result.outcome is Outcome.INCOMPLETE, "partial")
    check(L.ZIP_LIMIT in result.limitations and not result.cells, "zip limit")


def test_declared_size_smaller_than_actual_is_corrupt() -> None:
    data = bytearray(mini("<sheetData/>", {"xl/media/lie.bin": b"A" * 5000}))
    for sig, off in ((b"PK\x03\x04", 22), (b"PK\x01\x02", 24)):
        pos = data.find(sig)
        while pos >= 0:
            if b"lie.bin" in bytes(data[pos : pos + 80]):
                data[pos + off : pos + off + 4] = (10).to_bytes(4, "little")
            pos = data.find(sig, pos + 4)
    result = parse_spreadsheet(bytes(data))
    check(L.CORRUPT in result.limitations, "lying size is corrupt")


def test_many_cells_parse_in_linear_time() -> None:
    def book(count: int) -> bytes:
        rows = "".join(
            f'<row r="{i}"><c r="A{i}"><v>{i}</v></c></row>' for i in range(1, count)
        )
        return mini(f"<sheetData>{rows}</sheetData>")

    small, large = book(2000), book(8000)
    t0 = time.perf_counter()
    parse_spreadsheet(small)
    t1 = time.perf_counter()
    parse_spreadsheet(large)
    t2 = time.perf_counter()
    check(t2 - t1 < 5.0, "8000 rows took too long")
    check((t2 - t1) < max(t1 - t0, 0.05) * 12, "time grows faster than linear")


def test_failure_messages_do_not_echo_input() -> None:
    marker = b"private-marker-9917"
    result = parse_spreadsheet(b"PK\x03\x04" + marker * 4)
    check(marker.decode() not in repr(result), "repr echoes input")
    check(all(marker.decode() not in i.value for i in result.limitations), "limits")
