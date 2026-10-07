"""Synthetic acceptance-fixture tests for later parser implementation lanes."""

from __future__ import annotations

from email import policy
from email.parser import BytesParser
from io import BytesIO
from xml.etree import ElementTree
from zipfile import ZipFile

import pytest

from tests.parser_fixture_builders import (
    HTML_BODY,
    build_docx_fixture,
    build_mime_fixture,
    build_pdf_fixture,
    build_xlsx_fixture,
)

SHEET_NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def test_mime_fixture_covers_encoding_html_table_link_and_attachment() -> None:
    """MIME fixture retains encoded alternatives and attachment relationships."""
    message = BytesParser(policy=policy.default).parsebytes(build_mime_fixture())
    parts = list(message.walk())
    content_types = [part.get_content_type() for part in parts]
    for required in ("text/plain", "text/html", "application/octet-stream"):
        if required not in content_types:
            pytest.fail(f"Expected MIME part {required}")
    html_part = next(part for part in parts if part.get_content_type() == "text/html")
    html = html_part.get_content()
    order = [
        html.find("Alpha"),
        html.find("<a "),
        html.find("<table>"),
        html.find("Tail."),
    ]
    if order != sorted(order) or any(position < 0 for position in order):
        pytest.fail("Expected text, link, table, and tail in meaningful HTML order")
    attachment = next(
        part for part in parts if part.get_content_type() == "application/octet-stream"
    )
    if attachment.get_payload(decode=True) != b"synthetic attachment bytes":
        pytest.fail("Expected base64 attachment payload to decode exactly")


def test_xlsx_fixture_covers_offsets_types_formula_merge_and_hidden_sheet() -> None:
    """XLSX fixture encodes the acceptance cases without requiring openpyxl."""
    with ZipFile(BytesIO(build_xlsx_fixture())) as archive:
        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        sheets = workbook.find("s:sheets", SHEET_NS)
        if sheets is None:
            pytest.fail("Expected workbook sheet inventory")
        sheet_nodes = list(sheets)
        if [node.attrib["name"] for node in sheet_nodes] != ["Visible", "Hidden"]:
            pytest.fail("Expected visible and hidden synthetic sheets")
        if sheet_nodes[1].attrib.get("state") != "hidden":
            pytest.fail("Expected hidden-sheet metadata")

        sheet = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        cells = {node.attrib["r"]: node for node in sheet.findall(".//s:c", SHEET_NS)}
        if "A1" in cells or "B3" not in cells:
            pytest.fail("Expected leading blank rows/columns before first cell B3")
        if cells["C3"].attrib.get("t") != "inlineStr":
            pytest.fail("Expected explicit string cell type")
        if cells["D3"].attrib.get("t") != "b":
            pytest.fail("Expected explicit boolean cell type")
        formula = cells["C4"].find("s:f", SHEET_NS)
        cached = cells["C4"].find("s:v", SHEET_NS)
        if formula is None or formula.text != "SUM(B3,2)":
            pytest.fail("Expected formula text")
        if cached is None or cached.text != "3":
            pytest.fail("Expected cached formula value")
        merge = sheet.find(".//s:mergeCell", SHEET_NS)
        if merge is None or merge.attrib.get("ref") != "D3:E3":
            pytest.fail("Expected merged-cell range")


def test_pdf_fixture_covers_page_text_and_image_only_page() -> None:
    """PDF fixture exposes text page and image-only page for limitation tests."""
    data = build_pdf_fixture()
    if data.count(b"/Type /Page ") != 2:
        pytest.fail("Expected exactly two PDF pages")
    if b"(First line)" not in data or b"(Second line)" not in data:
        pytest.fail("Expected ordered text operators on page one")
    if b"/Subtype /Image" not in data or b"/Im0 Do" not in data:
        pytest.fail("Expected image-only page content for scanned limitation")


def test_docx_fixture_covers_paragraph_table_order_and_embedded_object() -> None:
    """DOCX fixture retains body order and an unsupported embedded object."""
    with ZipFile(BytesIO(build_docx_fixture())) as archive:
        root = ElementTree.fromstring(archive.read("word/document.xml"))
        body = root.find("w:body", WORD_NS)
        if body is None:
            pytest.fail("Expected Word document body")
        ordered_tags = [child.tag.rsplit("}", 1)[-1] for child in body]
        if ordered_tags[:4] != ["p", "tbl", "p", "p"]:
            pytest.fail("Expected paragraph, table, paragraph, object paragraph order")
        text = " ".join(node.text or "" for node in body.findall(".//w:t", WORD_NS))
        for value in ("Before table", "A1", "B2", "After table"):
            if value not in text:
                pytest.fail(f"Expected Word fixture text {value}")
        if "word/embeddings/oleObject1.bin" not in archive.namelist():
            pytest.fail("Expected unsupported embedded-object payload")


def test_html_fixture_uses_only_synthetic_nonfetchable_link() -> None:
    """HTML link is data and cannot resolve to a live external document."""
    if "https://example.invalid/reference" not in HTML_BODY:
        pytest.fail("Expected reserved synthetic .invalid link target")
