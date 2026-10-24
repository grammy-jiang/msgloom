"""P2-05 row floods, out-of-order rows, sheet layout and receipt hits."""

from __future__ import annotations

import time
import zipfile
from io import BytesIO

from msgloom.a2_kedro.parsers import spreadsheets as sp
from msgloom.a2_kedro.parsers.spreadsheets import Limitation as L
from msgloom.a2_kedro.parsers.spreadsheets import Outcome, parse_spreadsheet
from tests.a2_kedro.helpers import check
from tests.a2_kedro.test_p2_05_hostile import SLOW, inline, mini

FLOOD = 2_000_000
HIDDEN_ROW = '<row hidden="1"/>'


def cell_row(number: int, text: str = "x") -> str:
    return f'<row r="{number}">{inline(f"A{number}", text)}</row>'


def refs(result: sp.SheetResult) -> list[str]:
    return [c.block_id for c in result.cells]


def check_bounded(result: sp.SheetResult) -> None:
    check(result.outcome is Outcome.INCOMPLETE, "flood is never complete")
    check(L.SCAN_LIMIT in result.limitations, "scan limit")
    held = sum(len(s.hidden_rows) + len(s.hidden_columns) for s in result.sheets)
    check(held <= sp.MAX_HIDDEN, "hidden entries are bounded")


def test_hidden_row_flood_with_far_cell_is_bounded() -> None:
    body = (
        f"<sheetData>{cell_row(1)}{FLOOD * HIDDEN_ROW}"
        f"{cell_row(3_000_000, 'far')}</sheetData>"
    )
    begin = time.perf_counter()
    result = parse_spreadsheet(mini(body))
    check(time.perf_counter() - begin < SLOW, "flood cost too much time")
    check_bounded(result)
    check(not result.cells, "a capped sheet gives no cells")
    check(len(result.sheets) == 1, "the sheet is still listed")


def test_empty_row_flood_is_bounded() -> None:
    body = f"<sheetData>{cell_row(1)}{FLOOD * '<row/>'}</sheetData>"
    begin = time.perf_counter()
    result = parse_spreadsheet(mini(body))
    check(time.perf_counter() - begin < SLOW, "flood cost too much time")
    check(result.outcome is Outcome.INCOMPLETE, "never complete")
    check(L.SCAN_LIMIT in result.limitations, "scan limit")


def test_hidden_rows_over_the_hidden_cap_stop_the_scan() -> None:
    rows = "".join(f'<row r="{i}" hidden="1"/>' for i in range(1, sp.MAX_HIDDEN + 10))
    result = parse_spreadsheet(mini(f"<sheetData>{rows}</sheetData>"))
    check_bounded(result)


def test_wide_cell_flood_is_bounded() -> None:
    cells = "".join(f'<c r="A{i}" s="1"/>' for i in range(1, 20)) * 40_000
    body = f'<sheetData><row r="1">{cells}</row></sheetData>'
    result = parse_spreadsheet(mini(body))
    check(result.outcome is not Outcome.COMPLETE, "never complete")


def test_rows_out_of_order_flag_and_keep_readable_cells() -> None:
    body = f"<sheetData>{cell_row(3, 'c')}{cell_row(1, 'a')}</sheetData>"
    result = parse_spreadsheet(mini(body))
    check(result.outcome is Outcome.INCOMPLETE, "not complete")
    check(L.OUT_OF_ORDER in result.limitations, "out of order")
    check("s0!A3" in refs(result), "readable cell kept")


def test_row_five_then_two_is_flagged() -> None:
    body = f"<sheetData>{cell_row(5)}{cell_row(2)}</sheetData>"
    result = parse_spreadsheet(mini(body))
    check(L.OUT_OF_ORDER in result.limitations, "out of order")
    check(result.outcome is not Outcome.COMPLETE, "not complete")


def test_duplicate_row_number_is_flagged() -> None:
    body = f"<sheetData>{cell_row(2)}{cell_row(2, 'y')}</sheetData>"
    result = parse_spreadsheet(mini(body))
    check(L.OUT_OF_ORDER in result.limitations, "duplicate row")


def test_cells_out_of_order_inside_a_row_are_flagged() -> None:
    row = inline("B1", "b") + inline("A1", "a")
    result = parse_spreadsheet(mini(f'<sheetData><row r="1">{row}</row></sheetData>'))
    check(L.OUT_OF_ORDER in result.limitations, "cell order")


def test_ordered_sparse_rows_stay_complete() -> None:
    body = f"<sheetData>{cell_row(1)}{cell_row(4)}{cell_row(9)}</sheetData>"
    result = parse_spreadsheet(mini(body))
    check(result.outcome is Outcome.COMPLETE, "ordered rows are complete")
    check(refs(result) == ["s0!A1", "s0!A4", "s0!A9"], "cell ids")


def move_sheet(data: bytes, target: str, rel: str | None = None) -> bytes:
    """Move the sheet part to ``xl/<target>``. ``rel`` is the rels target."""
    out = BytesIO()
    with zipfile.ZipFile(BytesIO(data)) as src, zipfile.ZipFile(out, "w") as dst:
        for name in src.namelist():
            body = src.read(name)
            if name == "xl/worksheets/sheet1.xml":
                name = f"xl/{target}"
            if name == "xl/_rels/workbook.xml.rels":
                body = body.replace(b"worksheets/sheet1.xml", (rel or target).encode())
            dst.writestr(name, body)
    return out.getvalue()


def test_sheet_part_outside_worksheets_dir_is_read() -> None:
    data = move_sheet(mini(f"<sheetData>{cell_row(1)}</sheetData>"), "data/s.xml")
    result = parse_spreadsheet(data)
    check(result.outcome is Outcome.COMPLETE, "valid layout is complete")
    check(refs(result) == ["s0!A1"], "cell ids stay stable")


def test_dangling_sheet_relationship_is_never_complete() -> None:
    base = mini(f"<sheetData>{cell_row(1)}</sheetData>")
    result = parse_spreadsheet(move_sheet(base, "data/s.xml", rel="data/z.xml"))
    check(result.outcome is not Outcome.COMPLETE, "not complete")
    check(L.UNSUPPORTED_LAYOUT in result.limitations, "layout code")


def test_duplicate_sheet_names_give_unsupported_layout() -> None:
    base = mini(f"<sheetData>{cell_row(1)}</sheetData>")
    with zipfile.ZipFile(BytesIO(base)) as src:
        files = {n: src.read(n) for n in src.namelist()}
    files["xl/workbook.xml"] = files["xl/workbook.xml"].replace(
        b"</sheets>", b'<sheet name="S" sheetId="2" r:id="rId1"/></sheets>'
    )
    out = BytesIO()
    with zipfile.ZipFile(out, "w") as dst:
        for name, body in files.items():
            dst.writestr(name, body)
    result = parse_spreadsheet(out.getvalue())
    check(L.CORRUPT not in result.limitations, "not corrupt")
    check(L.UNSUPPORTED_LAYOUT in result.limitations, "layout code")
    check(result.outcome is not Outcome.COMPLETE, "not complete")


def test_receipt_limit_hit_follows_the_limitation() -> None:
    merged = mini(
        '<sheetData/><mergeCells count="1"><mergeCell ref="A1:B1"/></mergeCells>'
    )
    macro = mini("<sheetData/>", {"xl/vbaProject.bin": b"x"})
    far = mini(f"<sheetData>{cell_row(1)}{cell_row(1_048_576, 'f')}</sheetData>")
    hits = []
    for data in (merged, macro, far):
        receipt = parse_spreadsheet(data).to_receipt("1")
        hits.append(None if receipt is None else receipt.limit_hit)
    check(hits == ["bytes", "parts", "cells"], "limit hit values")
