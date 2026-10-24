"""P2-04 hostile DOCX input: XXE, entity expansion, zip bombs and bounds."""

from __future__ import annotations

import io
import time
import zipfile

import pytest

from msgloom.a2_kedro.parsers import docx as dx
from msgloom.a2_kedro.parsers.docx import DocxLimit, parse_docx
from msgloom.contracts import TerminalStatus
from tests.a2_kedro.helpers import check

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
SECRET = "root:x:0:0:private-marker"
STATUS = TerminalStatus


def para(text: str) -> str:
    return f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"


def zipped(xml: str | bytes, extra: dict[str, bytes] | None = None) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", xml)
        for name, data in (extra or {}).items():
            archive.writestr(name, data)
    return buffer.getvalue()


def build(body: str, extra: dict[str, bytes] | None = None) -> bytes:
    xml = f'<w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>'
    return zipped(xml, extra)


def limits(data: bytes) -> tuple[str, ...]:
    return tuple(str(x) for x in parse_docx(data).limitations)


# --- XXE and entity expansion ---------------------------------------------


def test_external_entity_is_rejected_and_never_resolved(tmp_path) -> None:
    target = tmp_path / "secret.txt"
    target.write_text(SECRET)
    doctype = f'<!DOCTYPE d [<!ENTITY x SYSTEM "file://{target}">]>'
    xml = f'{doctype}<w:document xmlns:w="{W}"><w:body>{para("&x;")}</w:body></w:document>'
    result = parse_docx(zipped(xml))
    check(result.status is STATUS.FAILED, "XXE fails the parse")
    check(limits(zipped(xml)) == ("xml_forbidden",), "xml_forbidden")
    check(SECRET not in repr(result) + str(result.limitations), "no file content")
    check(result.blocks == (), "no block from a rejected document")


def test_network_entity_and_parameter_entity_are_rejected() -> None:
    for doctype in (
        '<!DOCTYPE d [<!ENTITY x SYSTEM "http://192.0.2.1/x">]>',
        '<!DOCTYPE d [<!ENTITY % p SYSTEM "http://192.0.2.1/p.dtd"> %p;]>',
        '<!DOCTYPE d SYSTEM "http://192.0.2.1/d.dtd">',
        "<!DOCTYPE d>",
    ):
        xml = f'{doctype}<w:document xmlns:w="{W}"><w:body/></w:document>'
        check(limits(zipped(xml)) == ("xml_forbidden",), "DTD is rejected")


def test_billion_laughs_is_rejected_fast_without_expansion() -> None:
    lines = ['<!ENTITY a0 "lol">']
    for i in range(1, 10):
        lines.append(f'<!ENTITY a{i} "{f"&a{i - 1};" * 10}">')
    doctype = "<!DOCTYPE d [" + "".join(lines) + "]>"
    xml = f'{doctype}<w:document xmlns:w="{W}"><w:body>{para("&a9;")}</w:body></w:document>'
    begin = time.perf_counter()
    result = parse_docx(zipped(xml))
    check(time.perf_counter() - begin < 2.0, "rejection is fast")
    check(result.status is STATUS.FAILED, "billion laughs fails")
    check(result.limitations == (DocxLimit.XML_FORBIDDEN,), "xml_forbidden")


def test_undefined_entity_and_utf16_declaration_mismatch_are_invalid_xml() -> None:
    xml = f'<w:document xmlns:w="{W}"><w:body>{para("&nope;")}</w:body></w:document>'
    check(limits(zipped(xml)) == ("invalid_xml",), "undefined entity")
    mismatch = '<?xml version="1.0" encoding="UTF-16"?><w:document/>'
    check(limits(zipped(mismatch)) == ("invalid_xml",), "bad encoding")


# --- zip bombs and bounds -------------------------------------------------


def test_zip_bomb_member_is_refused_by_declared_size_before_inflating() -> None:
    pad = b" " * (dx.MAX_MEMBER_BYTES + 1024)
    xml = f'<w:document xmlns:w="{W}"><w:body/>'.encode() + pad + b"</w:document>"
    data = zipped(xml)
    check(len(data) < 64 * 1024, "the bomb is small on disk")
    result = parse_docx(data)
    check(result.status is STATUS.INCOMPLETE, "bomb gives a partial result")
    check(DocxLimit.MEMBER_SIZE_LIMIT in result.limitations, "member size limit")


def test_declared_total_size_over_bound_skips_probes_and_is_partial() -> None:
    big = b"\x00" * (dx.MAX_TOTAL_BYTES // 4 + 1)
    extra = {f"word/media/{i}.bin": big for i in range(5)}
    result = parse_docx(build(para("a"), extra))
    check(result.status is STATUS.INCOMPLETE, "total bound gives partial")
    check(DocxLimit.TOTAL_SIZE_LIMIT in result.limitations, "total size limit")
    check(len(result.blocks) == 1, "the body is still read")


def test_oversized_input_is_not_parsed() -> None:
    result = parse_docx(b"PK" + b"\x00" * dx.MAX_INPUT_BYTES)
    check(result.status is STATUS.INCOMPLETE, "size limit is partial")
    check(result.limitations == (DocxLimit.SIZE_LIMIT,), "size_limit only")
    check(result.blocks == (), "nothing parsed")


def test_bounds_give_partial_results_with_blocks_read_so_far(monkeypatch) -> None:
    body = para("one") + para("two") + para("three")
    monkeypatch.setattr(dx, "MAX_PARAGRAPHS", 2)
    result = parse_docx(build(body))
    check([b.text for b in result.blocks] == ["one", "two"], "partial blocks stay")
    check(result.status is STATUS.INCOMPLETE, "paragraph limit is partial")
    check(DocxLimit.PARAGRAPH_LIMIT in result.limitations, "paragraph_limit")
    monkeypatch.setattr(dx, "MAX_PARAGRAPHS", 100)
    monkeypatch.setattr(dx, "MAX_TEXT_CHARS", 5)
    result = parse_docx(build(body))
    check([b.text for b in result.blocks] == ["one", "tw"], "text is cut at bound")
    check(DocxLimit.TEXT_LIMIT in result.limitations, "text_limit")


def test_member_count_and_depth_and_table_nesting_bounds(monkeypatch) -> None:
    extra = {f"x{i}.txt": b"x" for i in range(5)}
    monkeypatch.setattr(dx, "MAX_MEMBERS", 3)
    check(
        DocxLimit.MEMBER_LIMIT in parse_docx(build(para("a"), extra)).limitations,
        "members",
    )
    monkeypatch.setattr(dx, "MAX_XML_DEPTH", 6)
    deep = "<w:sdt>" * 4 + para("a") + "</w:sdt>" * 4
    check(limits(build(deep)) == ("xml_limit",), "xml depth bound")
    monkeypatch.setattr(dx, "MAX_XML_DEPTH", 128)
    monkeypatch.setattr(dx, "MAX_XML_ELEMENTS", 5)
    check(limits(build(para("a") * 3)) == ("xml_limit",), "element bound")
    monkeypatch.setattr(dx, "MAX_XML_ELEMENTS", 10**6)
    monkeypatch.setattr(dx, "MAX_TABLE_DEPTH", 2)
    nest = "<w:tbl><w:tr><w:tc>{}</w:tc></w:tr></w:tbl>"
    result = parse_docx(build(nest.format(nest.format(nest.format(para("deep"))))))
    check(DocxLimit.TABLE_DEPTH_LIMIT in result.limitations, "table nesting bound")
    check(result.status is STATUS.INCOMPLETE, "nesting bound is partial")


def test_bad_grid_span_is_flagged_not_trusted() -> None:
    cell = '<w:tc><w:tcPr><w:gridSpan w:val="{}"/></w:tcPr>' + para("a") + "</w:tc>"
    for raw in ("0", "-3", "99999999999999999999", "x"):
        body = f"<w:tbl><w:tr>{cell.format(raw)}</w:tr></w:tbl>"
        result = parse_docx(build(body))
        check(DocxLimit.MALFORMED_TABLE in result.limitations, f"span {raw}")
        check(result.status is STATUS.INCOMPLETE, "bad span is partial")


# --- linear time ----------------------------------------------------------


def count_visits(monkeypatch: pytest.MonkeyPatch, data: bytes) -> int:
    """Count element-name lookups; each parser step makes a bounded number."""
    calls = 0
    original = dx._qname

    def counting(tag: str) -> str:
        nonlocal calls
        calls += 1
        return original(tag)

    monkeypatch.setattr(dx, "_qname", counting)
    parse_docx(data)
    return calls


@pytest.mark.parametrize("shape", ["paragraphs", "runs", "drawings", "members"])
def test_large_hostile_documents_parse_in_linear_time(
    shape: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def make(n: int) -> bytes:
        if shape == "paragraphs":
            return build(para("x") * n)
        if shape == "runs":
            return build("<w:p>" + "<w:r><w:t>x</w:t></w:r>" * n + "</w:p>")
        if shape == "drawings":
            return build(
                "<w:p>" + "<w:r><w:drawing><a/></w:drawing></w:r>" * n + "</w:p>"
            )
        return build(para("x"), {f"x/{i}.txt": b"" for i in range(n // 20)})

    small_n, large_n = 5_000, 40_000
    small = count_visits(monkeypatch, make(small_n))
    large = count_visits(monkeypatch, make(large_n))
    # The size ratio is 8. A quadratic parser would show a ratio near 64.
    check(large <= small * 10 + 100, f"visits grow faster than linear: {small}/{large}")
    check(large <= large_n * 20, f"too many visits per element: {large}")


def test_unsupported_item_overflow_is_bounded_and_recorded() -> None:
    body = (
        "<w:p>"
        + "<w:r><w:drawing><a/></w:drawing></w:r>" * (dx.MAX_UNSUPPORTED_ITEMS + 5)
        + "</w:p>"
    )
    result = parse_docx(build(body))
    check(len(result.unsupported) == dx.MAX_UNSUPPORTED_ITEMS, "items are capped")
    check(DocxLimit.UNSUPPORTED_OVERFLOW in result.limitations, "overflow flagged")
