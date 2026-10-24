"""P2-04 tracked-deleted table rows and cells, and dropped DOCX content."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from msgloom.a2_kedro.parsers.docx import DocxLimit, parse_docx
from msgloom.contracts import TerminalStatus
from tests.a2_kedro.helpers import check

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
STATUS = TerminalStatus


def para(text: str) -> str:
    return f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"


def tc(text: str, props: str = "") -> str:
    prefix = f"<w:tcPr>{props}</w:tcPr>" if props else ""
    return f"<w:tc>{prefix}{para(text)}</w:tc>"


def tr(*cells: str, props: str = "") -> str:
    prefix = f"<w:trPr>{props}</w:trPr>" if props else ""
    return f"<w:tr>{prefix}{''.join(cells)}</w:tr>"


def docx_file(tmp_path: Path, body: str) -> bytes:
    xml = f'<w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>'
    path = tmp_path / "sample.docx"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", xml)
    return path.read_bytes()


DELETED_ROW = '<w:del w:id="1" w:author="a" w:date="2020-01-01T00:00:00Z"/>'


def test_deleted_row_is_skipped_and_recorded(tmp_path: Path) -> None:
    body = f"<w:tbl>{tr(tc('live'))}{tr(tc('gone'), props=DELETED_ROW)}</w:tbl>"
    result = parse_docx(docx_file(tmp_path, body))
    check([b.text for b in result.blocks] == ["live"], "deleted row is not read")
    check(result.status is STATUS.INCOMPLETE, "skipped content is not complete")
    check(DocxLimit.UNSUPPORTED_CONTENT in result.limitations, "limitation set")
    kinds = [str(item.kind) for item in result.unsupported]
    check(kinds == ["tracked_deletion"], "same item as paragraph deletions")
    check(result.unsupported[0].source_block_id == "b0/r1", "row position")


def test_document_with_only_a_deleted_row_is_not_complete(tmp_path: Path) -> None:
    body = f"<w:tbl>{tr(tc('gone'), props=DELETED_ROW)}</w:tbl>"
    result = parse_docx(docx_file(tmp_path, body))
    check(result.status is STATUS.INCOMPLETE, "not complete")
    check(result.blocks == (), "no deleted text is returned")
    check("gone" not in repr(result.blocks), "deleted text does not leak")
    check(len(result.unsupported) == 1, "deletion is recorded")


def test_deleted_cell_is_skipped_and_keeps_the_column_index(tmp_path: Path) -> None:
    span = '<w:gridSpan w:val="2"/><w:cellDel w:id="2" w:author="a"/>'
    body = f"<w:tbl>{tr(tc('gone', span), tc('live'))}</w:tbl>"
    result = parse_docx(docx_file(tmp_path, body))
    check([b.text for b in result.blocks] == ["live"], "deleted cell is not read")
    check(result.blocks[0].source_block_id == "b0/r0c2", "column index is stable")
    check(result.unsupported[0].source_block_id == "b0/r0c0", "cell position")
    check(result.status is STATUS.INCOMPLETE, "not complete")


def test_nested_content_of_a_deleted_row_is_skipped(tmp_path: Path) -> None:
    inner = f"<w:tbl>{tr(tc('inner'))}</w:tbl>"
    outer = f"<w:tbl>{tr(f'<w:tc>{inner}<w:p/></w:tc>', props=DELETED_ROW)}</w:tbl>"
    result = parse_docx(docx_file(tmp_path, outer))
    check(result.blocks == (), "nested table is skipped with its row")
    check(len(result.unsupported) == 1, "one deletion item")


def test_row_insertion_mark_is_still_read(tmp_path: Path) -> None:
    ins = '<w:ins w:id="1" w:author="a"/>'
    body = f"<w:tbl>{tr(tc('added'), props=ins)}</w:tbl>"
    result = parse_docx(docx_file(tmp_path, body))
    check([b.text for b in result.blocks] == ["added"], "inserted row is read")
    check(result.status is STATUS.COMPLETE, "insertion alone is complete")


@pytest.mark.parametrize("tag", ["w:sym", "w:ptab"])
def test_inline_sym_and_ptab_are_recorded_not_dropped_silently(
    tmp_path: Path, tag: str
) -> None:
    body = f'<w:p><w:r><w:t>a</w:t><{tag} w:char="F0A7"/></w:r></w:p>'
    result = parse_docx(docx_file(tmp_path, body))
    check(result.blocks[0].text == "a", "other text is read")
    check(result.status is STATUS.INCOMPLETE, "dropped content is not complete")
    check(
        [str(i.kind) for i in result.unsupported] == ["unknown_block"],
        "closed kind is recorded",
    )
    check(result.unsupported[0].source_block_id == "b0", "position is recorded")


def test_unknown_table_and_row_children_are_recorded(tmp_path: Path) -> None:
    body = (
        f"<w:tbl><w:other/>{tr(tc('a'))}</w:tbl>"
        f"<w:tbl><w:tr><w:other/>{tc('b')}</w:tr></w:tbl>"
    )
    result = parse_docx(docx_file(tmp_path, body))
    check([b.text for b in result.blocks] == ["a", "b"], "known cells are read")
    ids = [(str(i.kind), i.source_block_id) for i in result.unsupported]
    check(ids == [("unknown_block", "b0"), ("unknown_block", "b1/r0")], "recorded")


def test_harmless_table_markers_stay_silent(tmp_path: Path) -> None:
    body = (
        "<w:tbl><w:tblPr/><w:tblGrid/><w:bookmarkStart/><w:proofErr/>"
        "<w:tr><w:trPr/><w:tblPrEx/><w:bookmarkEnd/>"
        f"{tc('a')}</w:tr></w:tbl>"
    )
    result = parse_docx(docx_file(tmp_path, body))
    check(result.status is STATUS.COMPLETE, "markers are not content")
    check(result.unsupported == (), "nothing recorded")
