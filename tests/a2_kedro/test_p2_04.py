"""P2-04 DOCX parser: body order, stable IDs, unsupported content, receipts."""

from __future__ import annotations

import io
import zipfile
from collections.abc import Mapping

import pytest

from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.a2_kedro.contracts.parse import ByteLink, ParsedParts, Part
from msgloom.a2_kedro.parsers import docx as dx
from msgloom.a2_kedro.parsers.docx import (
    DocxInputError,
    DocxLimit,
    DocxResult,
    UnsupportedKind,
    parse_docx,
)
from msgloom.contracts import TerminalStatus
from tests.a2_kedro.helpers import check

SECRET = "alice.private@example.invalid"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = (
    f'xmlns:w="{W}" '
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"'
)
STATUS = TerminalStatus


def para(text: str) -> str:
    return f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"


def cell(inner: str, span: int = 1) -> str:
    props = f'<w:tcPr><w:gridSpan w:val="{span}"/></w:tcPr>' if span != 1 else ""
    return f"<w:tc>{props}{inner}</w:tc>"


def table(*rows: str) -> str:
    return "<w:tbl>" + "".join(f"<w:tr>{r}</w:tr>" for r in rows) + "</w:tbl>"


def document(body: str) -> str:
    return f'<?xml version="1.0"?><w:document {NS}><w:body>{body}</w:body></w:document>'


def package(body: str, members: Mapping[str, str | bytes] | None = None) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", document(body))
        for name, data in (members or {}).items():
            archive.writestr(name, data)
    return buffer.getvalue()


def part_xml(inner: str) -> str:
    return f'<?xml version="1.0"?><w:hdr {NS}>{inner}</w:hdr>'


def ids(result: DocxResult) -> list[str]:
    return [b.source_block_id for b in result.blocks]


def kinds(result: DocxResult) -> list[str]:
    return [str(item.kind) for item in result.unsupported]


# --- order, positions and stable IDs -------------------------------------


def test_body_order_of_paragraphs_and_table_cells_is_exact() -> None:
    row = cell(para("A")) + cell(para("B"), span=2) + cell(para("C"))
    result = parse_docx(package(para("first") + table(row) + para("last")))
    check(result.status is STATUS.COMPLETE, "plain document is complete")
    got = [(b.source_block_id, b.kind, b.text, b.row, b.col) for b in result.blocks]
    want = [
        ("b0", "paragraph", "first", None, None),
        ("b1/r0c0", "table_cell", "A", 0, 0),
        ("b1/r0c1", "table_cell", "B", 0, 1),
        ("b1/r0c3", "table_cell", "C", 0, 3),
        ("b2", "paragraph", "last", None, None),
    ]
    check(got == want, "order, positions and IDs are exact")
    check([b.body_index for b in result.blocks] == [0, 1, 1, 1, 2], "body index")


def test_cell_joins_paragraphs_and_nested_table_follows_its_cell() -> None:
    inner = table(cell(para("deep")))
    outer = table(cell(para("p1") + inner + para("p2")) + cell(para("next")))
    result = parse_docx(package(outer))
    got = [(b.source_block_id, b.text) for b in result.blocks]
    want = [
        ("b0/r0c0", "p1\np2"),
        ("b0/r0c0/1/r0c0", "deep"),
        ("b0/r0c1", "next"),
    ]
    check(got == want, "nested table is a child of its cell")


def test_ids_depend_on_structure_not_text_and_empty_paragraph_keeps_index() -> None:
    one = parse_docx(package(para("x") + "<w:p/>" + table(cell(para("y")))))
    two = parse_docx(package(para(SECRET) + "<w:p/>" + table(cell(para("")))))
    check(ids(one) == ids(two) == ["b0", "b1", "b2/r0c0"], "IDs ignore text")
    check(one.blocks[1].text == "", "empty paragraph is a block")


def test_sdt_wrapper_is_transparent_and_markers_take_no_index() -> None:
    wrapped = f"<w:sdt><w:sdtPr/><w:sdtContent>{para('in')}</w:sdtContent></w:sdt>"
    markers = '<w:bookmarkStart w:id="0" w:name="x"/><w:bookmarkEnd w:id="0"/>'
    result = parse_docx(package(markers + wrapped + para("out") + "<w:sectPr/>"))
    check(result.status is STATUS.COMPLETE, "wrappers and markers are not content")
    check(ids(result) == ["b0", "b1"], "sdt content takes body indexes")
    check([b.text for b in result.blocks] == ["in", "out"], "sdt text is read")


def test_run_content_tab_break_hyperlink_and_field_result() -> None:
    runs = (
        "<w:r><w:t>a</w:t><w:tab/><w:t>b</w:t><w:br/><w:t>c</w:t></w:r>"
        '<w:hyperlink w:anchor="x"><w:r><w:t>link</w:t></w:r></w:hyperlink>'
        "<w:r><w:instrText>HIDDEN</w:instrText></w:r>"
        '<w:r><w:t xml:space="preserve"> </w:t><w:noBreakHyphen/></w:r>'
    )
    result = parse_docx(package(f"<w:p>{runs}</w:p>"))
    check(result.blocks[0].text == "a\tb\nclink -", "run content is read")


def test_python_docx_document_parses_in_order() -> None:
    document_api = pytest.importorskip("docx")
    doc = document_api.Document()
    doc.add_paragraph("one")
    grid = doc.add_table(rows=1, cols=2)
    grid.cell(0, 1).text = "two"
    doc.add_paragraph("three")
    buffer = io.BytesIO()
    doc.save(buffer)
    result = parse_docx(buffer.getvalue())
    check(result.status is STATUS.COMPLETE, "python-docx output is complete")
    texts = [b.text for b in result.blocks]
    check(texts == ["one", "", "two", "three"], "python-docx order")


# --- tracked changes ------------------------------------------------------


def test_tracked_changes_policy_reads_insertions_and_skips_deletions() -> None:
    changed = (
        "<w:p><w:r><w:t>keep </w:t></w:r>"
        '<w:ins w:id="1"><w:r><w:t>added</w:t></w:r></w:ins>'
        '<w:del w:id="2"><w:r><w:delText>gone</w:delText></w:r></w:del></w:p>'
    )
    result = parse_docx(package(changed))
    check(result.blocks[0].text == "keep added", "final view is read")
    check(result.status is STATUS.INCOMPLETE, "dropped text is never complete")
    check(kinds(result) == ["tracked_deletion"], "deletion is recorded")
    check(result.unsupported[0].source_block_id == "b0", "deletion has position")


# --- unsupported content --------------------------------------------------

DRAWING = "<w:r><w:drawing><a:graphic><a:graphicData>{}</a:graphicData></a:graphic></w:drawing></w:r>"
INLINE_CASES = {
    "image": DRAWING.format('<a:blip r:embed="rId1" xmlns:r="urn:r"/>'),
    "textbox": DRAWING.format("<w:txbxContent><w:p/></w:txbxContent>"),
    "drawing": DRAWING.format("<a:other/>"),
    "ole_object": "<w:r><w:object/></w:r>",
    "form_control": "<w:r><w:control/></w:r>",
    "comment": '<w:r><w:commentReference w:id="0"/></w:r>',
    "footnote": '<w:r><w:footnoteReference w:id="1"/></w:r>',
    "endnote": '<w:r><w:endnoteReference w:id="1"/></w:r>',
    "equation": "<m:oMath><m:r><m:t>x</m:t></m:r></m:oMath>",
}


@pytest.mark.parametrize("kind", sorted(INLINE_CASES))
def test_inline_unsupported_content_is_recorded_not_complete(kind: str) -> None:
    result = parse_docx(package(para("before") + f"<w:p>{INLINE_CASES[kind]}</w:p>"))
    check(result.status is STATUS.INCOMPLETE, f"{kind} makes a partial result")
    check(kinds(result) == [kind], f"{kind} is recorded once")
    check(result.unsupported[0].source_block_id == "b1", "position is the block")
    check(DocxLimit.UNSUPPORTED_CONTENT in result.limitations, "limitation set")
    check(len(result.blocks) == 2, "text blocks are still read")


def test_text_inside_a_text_box_is_not_read() -> None:
    box = DRAWING.format(f"<w:txbxContent>{para(SECRET)}</w:txbxContent>")
    result = parse_docx(package(f"<w:p>{box}</w:p>"))
    check(all(SECRET not in b.text for b in result.blocks), "box text is skipped")


def test_block_level_alt_chunk_and_unknown_element_are_recorded() -> None:
    result = parse_docx(package(para("a") + "<w:altChunk/><w:mystery/>"))
    check(kinds(result) == ["alt_chunk", "unknown_block"], "block-level kinds")
    check(result.status is STATUS.INCOMPLETE, "not complete")


def test_package_media_embeddings_and_macros_always_count() -> None:
    members = {
        "word/media/image1.png": b"\x89PNG",
        "word/embeddings/oleObject1.bin": b"ole",
        "word/charts/chart1.xml": "<c/>",
        "word/vbaProject.bin": b"vba",
    }
    result = parse_docx(package(para("a"), members))
    check(sorted(kinds(result)) == ["chart", "image", "macro", "ole_object"], "kinds")
    check(all(i.source_block_id is None for i in result.unsupported), "no position")
    check(result.status is STATUS.INCOMPLETE, "not complete")


def test_header_footer_comments_and_notes_count_only_with_content() -> None:
    text = part_xml(para("page header"))
    empty = part_xml("<w:p/>")
    full = parse_docx(package(para("a"), {"word/header1.xml": text}))
    check(kinds(full) == ["header"], "header text is recorded")
    footer = parse_docx(package(para("a"), {"word/footer2.xml": text}))
    check(kinds(footer) == ["footer"], "footer text is recorded")
    notes = parse_docx(package(para("a"), {"word/footnotes.xml": text}))
    check(kinds(notes) == ["footnote"], "footnote text is recorded")
    comments = part_xml('<w:comment w:id="0"/>')
    review = parse_docx(package(para("a"), {"word/comments.xml": comments}))
    check(kinds(review) == ["comment"], "a comment is recorded")
    quiet = {"word/header1.xml": empty, "word/footnotes.xml": empty}
    clean = parse_docx(package(para("a"), quiet))
    check(clean.status is STATUS.COMPLETE, "empty parts drop nothing")
    unreadable = parse_docx(package(para("a"), {"word/header1.xml": "<w:hdr"}))
    check(kinds(unreadable) == ["header"], "unreadable part counts as content")


# --- failed packages ------------------------------------------------------


def failed(data: bytes, limit: DocxLimit) -> None:
    result = parse_docx(data)
    check(result.status is STATUS.FAILED, f"{limit} fails the parse")
    check(result.limitations == (limit,), f"{limit} is the only limitation")
    check(result.blocks == () and result.unsupported == (), "failed holds no block")
    check(result.to_receipt("1") is None, "no receipt for a failure")


def test_empty_non_zip_ole_and_truncated_inputs_fail_with_a_limitation() -> None:
    good = package(para("a"))
    failed(b"", DocxLimit.EMPTY_INPUT)
    failed(b"plain text, not a package", DocxLimit.NOT_A_ZIP)
    failed(
        b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 64, DocxLimit.ENCRYPTED_OR_OLE
    )
    failed(good[: len(good) // 2], DocxLimit.NOT_A_ZIP)


def test_zip_without_a_document_part_is_not_docx() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("other.txt", "x")
    failed(buffer.getvalue(), DocxLimit.NOT_DOCX)
    failed(
        package("", {}).replace(b"word/document.xml", b"word/documenX.xml"),
        DocxLimit.NOT_DOCX,
    )


def test_corrupt_member_data_fails_without_leaking_error_text() -> None:
    data = bytearray(package(para("abc" * 40)))
    data[40] ^= 0xFF  # inside the compressed document data
    result = parse_docx(bytes(data))
    check(result.status is STATUS.FAILED, "corrupt data fails")
    check(DocxLimit.CORRUPT_PACKAGE in result.limitations, "corrupt limitation")


def test_duplicate_member_names_and_encrypted_flag_fail() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", document(para("one")))
        with pytest.warns(UserWarning):
            archive.writestr("word/document.xml", document(para("two")))
    failed(buffer.getvalue(), DocxLimit.DUPLICATE_MEMBER)
    raw = bytearray(package(para("x")))
    raw[raw.index(b"PK\x03\x04") + 6] |= 0x1  # local header flag bits
    raw[raw.index(b"PK\x01\x02") + 8] |= 0x1  # central directory flag bits
    flagged = io.BytesIO(bytes(raw))
    failed(flagged.getvalue(), DocxLimit.ENCRYPTED_MEMBER)


def test_wrong_root_and_malformed_xml_fail() -> None:
    def raw(xml: str) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("word/document.xml", xml)
        return buffer.getvalue()

    failed(raw("<root/>"), DocxLimit.NOT_DOCX)
    failed(raw(f'<w:document xmlns:w="{W}"/>'), DocxLimit.NOT_DOCX)
    failed(raw(f'<w:document xmlns:w="{W}"><w:body>'), DocxLimit.INVALID_XML)
    failed(raw("not xml at all"), DocxLimit.INVALID_XML)


# --- receipts, contract limitations and PII -------------------------------


def test_receipt_maps_status_and_builds_parsed_parts() -> None:
    done = parse_docx(package(para("a")))
    receipt = done.to_receipt("1")
    if receipt is None:
        pytest.fail("complete result has a receipt")
    check(receipt.outcome == "complete" and receipt.limit_hit == "none", "complete")
    link = ByteLink(
        component_id="c1",
        component_sha256=done.input_sha256,
        component_size=done.input_bytes,
        offset=0,
        length=done.input_bytes,
    )
    part = Part(
        part_id="c1:docx",
        role="body",
        declared_format="docx",
        detected_format="docx",
        link=link,
    )
    check(ParsedParts(parts=(part,), receipt=receipt).receipt == receipt, "record")
    partial = parse_docx(package(para("a") + "<w:altChunk/>")).to_receipt("1")
    if partial is None:
        pytest.fail("partial result has a receipt")
    check(partial.outcome == "partial" and partial.limit_hit == "parts", "partial")


def test_contract_limitations_are_fixed_text_per_kind() -> None:
    check(parse_docx(package(para("a"))).to_contract_limitations() == (), "none")
    data = package(para(SECRET) + f"<w:p>{INLINE_CASES['image']}</w:p>")
    limits = parse_docx(data).to_contract_limitations()
    check([x.code for x in limits] == ["unsupported_image"], "one code per kind")
    check(all(SECRET not in x.detail for x in limits), "detail has no content")


def test_repr_limitations_and_errors_never_show_document_content() -> None:
    data = package(para(SECRET) + f"<w:p>{INLINE_CASES['comment']}</w:p>")
    result = parse_docx(data)
    shown = repr(result) + repr(result.blocks[0]) + repr(result.unsupported)
    shown += repr(result.limitations) + str(result.to_contract_limitations())
    check(SECRET not in shown, "no document text in repr")
    with pytest.raises(DocxInputError) as caught:
        parse_docx(SECRET)  # type: ignore[arg-type]
    check(SECRET not in str(caught.value), "error hides the input")
    check(isinstance(caught.value, A2ContractError), "error is a contract error")


def test_result_refuses_complete_status_with_dropped_content() -> None:
    sha = "0" * 64
    for status, limits in (
        (STATUS.COMPLETE, (DocxLimit.TEXT_LIMIT,)),
        (STATUS.INCOMPLETE, ()),
    ):
        with pytest.raises(DocxInputError):
            DocxResult(status, limits, 1, sha)
    item = dx.UnsupportedItem(UnsupportedKind.IMAGE)
    with pytest.raises(DocxInputError):
        DocxResult(STATUS.COMPLETE, (), 1, sha, unsupported=(item,))


def test_same_bytes_give_equal_results_and_empty_document_is_not_complete() -> None:
    data = package(para("a") + table(cell(para("b"))))
    again = parse_docx(bytes(bytearray(data)))
    check(parse_docx(data) == again, "deterministic")
    empty = parse_docx(package(""))
    check(empty.status is STATUS.INCOMPLETE, "no block is never complete")
    check(empty.limitations == (DocxLimit.EMPTY_DOCUMENT,), "empty document")
    check(empty.to_receipt("1") is not None, "empty document has a partial receipt")
