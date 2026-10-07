"""Focused synthetic acceptance tests for the PDF parser lane."""

from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from typing import Any

import pytest

from msgloom.preparation.contracts import (
    DocumentFormat,
    LimitationKind,
    PageLocation,
    ParserConfig,
    ParserIdentity,
    ParserLimits,
    ParserRequest,
    SavedByteReference,
    TextBlock,
)
from msgloom.preparation.parsers import pdf as pdf_parser
from tests.parser_fixture_builders import build_pdf_fixture
from tests.parser_pdf.fixtures import (
    build_empty_page_pdf,
    build_encrypted_pdf,
    build_mixed_pdf,
    build_text_pdf,
    build_unicode_pdf,
)


def _request(
    content: bytes,
    *,
    profile: str = "pdf-primary-v1",
    output_bytes: int = 1024 * 1024,
    decompressed_bytes: int = 1024 * 1024,
    pages: int = 100,
) -> ParserRequest:
    return ParserRequest(
        source=SavedByteReference(
            reference="blob:sha256:synthetic-pdf",
            sha256=sha256(content).hexdigest(),
            byte_count=len(content),
        ),
        detected_format=DocumentFormat.PDF,
        parser=ParserIdentity(
            name=pdf_parser.PARSER_NAME,
            version=pdf_parser.PARSER_VERSION,
            backend=pdf_parser.BACKEND,
        ),
        config=ParserConfig(profile=profile),
        limits=ParserLimits(
            wall_time_seconds=10,
            memory_bytes=256 * 1024 * 1024,
            decompressed_bytes=decompressed_bytes,
            output_bytes=output_bytes,
            container_members=pages,
        ),
    )


def _codes(output: Any) -> set[str]:
    return {item.code for item in output.limitations}


def test_extracts_page_order_provenance_and_scanned_limitation() -> None:
    """Text stays on page one while image-only page two remains explicit."""
    content = build_pdf_fixture()
    request = _request(content)
    output = pdf_parser.parse(request, content)

    if output.provenance.source != request.source:
        pytest.fail("Expected exact saved-byte provenance")
    if output.provenance.parser != request.parser:
        pytest.fail("Expected exact parser identity provenance")
    if len(output.blocks) != 1:
        pytest.fail("Expected one extractable page-text block")
    block = output.blocks[0]
    if not isinstance(block, TextBlock):
        pytest.fail("Expected PDF page text as TextBlock")
    if block.order != 0 or block.location != PageLocation(1):
        pytest.fail("Expected one-based page location and contiguous block order")
    if block.text != "First line\r\nSecond line":
        pytest.fail(f"Unexpected PDFium page text: {block.text!r}")
    scanned = [item for item in output.limitations if item.code == "image-only-page"]
    if len(scanned) != 1 or scanned[0].location != PageLocation(2):
        pytest.fail("Expected page-two scanned/image-only limitation")
    if scanned[0].kind is not LimitationKind.SCANNED:
        pytest.fail("Expected scanned limitation kind")


def test_preserves_full_unicode_and_pdfium_detected_web_links() -> None:
    """Bounded text keeps astral Unicode; detected URLs remain unfetched data."""
    unicode_content = build_unicode_pdf()
    unicode_output = pdf_parser.parse(_request(unicode_content), unicode_content)
    unicode_block = unicode_output.blocks[0]
    if not isinstance(unicode_block, TextBlock):
        pytest.fail("Expected Unicode content in a text block")
    if unicode_block.text != "AéΩ漢😀":
        pytest.fail("Expected full Unicode extraction through bounded text API")

    link_content = build_text_pdf(b"Visit https://example.invalid/path now")
    link_output = pdf_parser.parse(_request(link_content), link_content)
    link_block = link_output.blocks[0]
    if not isinstance(link_block, TextBlock):
        pytest.fail("Expected URL content in a text block")
    links = link_block.links
    if len(links) != 1:
        pytest.fail("Expected one PDFium-detected web link")
    if links[0].target != "https://example.invalid/path":
        pytest.fail("Expected exact link target as data")
    if links[0].location != PageLocation(1):
        pytest.fail("Expected link to retain its source page")


def test_empty_mixed_and_text_success_disclose_understanding_limits() -> None:
    """Text success never claims layout, tables, reading order, or images."""
    empty = build_empty_page_pdf()
    empty_output = pdf_parser.parse(_request(empty), empty)
    if empty_output.blocks:
        pytest.fail("Expected empty page to produce no invented text")
    if "empty-page" not in _codes(empty_output):
        pytest.fail("Expected explicit empty-page limitation")

    mixed = build_mixed_pdf()
    mixed_output = pdf_parser.parse(_request(mixed), mixed)
    required = {
        "image-content-unextracted",
        "reading-order-unverified",
        "layout-unrepresented",
        "table-structure-unavailable",
    }
    missing = required - _codes(mixed_output)
    if missing:
        pytest.fail(f"Expected explicit PDF understanding limitations: {missing}")


@pytest.mark.parametrize("profile", ["pdf-ocr-v1", "pdf-layout-v1", "docling-v1"])
def test_unavailable_ocr_and_layout_profiles_fail_visibly(profile: str) -> None:
    """Absent Docling profiles fail rather than returning empty success."""
    content = build_pdf_fixture()
    with pytest.raises(pdf_parser.PdfParseError, match="Docling is absent"):
        pdf_parser.parse(_request(content, profile=profile), content)


def test_encrypted_malformed_signature_and_identity_fail_visibly() -> None:
    """Security, malformed bytes, wrong magic, and wrong identity fail."""
    encrypted = build_encrypted_pdf()
    with pytest.raises(pdf_parser.PdfParseError, match="encrypted"):
        pdf_parser.parse(_request(encrypted), encrypted)

    malformed = b"%PDF-1.7\nnot a valid object graph"
    with pytest.raises(pdf_parser.PdfParseError, match="malformed or unsupported"):
        pdf_parser.parse(_request(malformed), malformed)

    wrong_signature = b"not-pdf"
    with pytest.raises(ValueError, match="invalid PDF signature"):
        pdf_parser.parse(_request(wrong_signature), wrong_signature)

    content = build_pdf_fixture()
    request = _request(content)
    wrong_parser = replace(
        request,
        parser=replace(request.parser, backend="pypdfium2-wrong"),
    )
    with pytest.raises(ValueError, match="identity"):
        pdf_parser.parse(wrong_parser, content)


@pytest.mark.parametrize(
    ("request_change", "message"),
    [
        ({"pages": 1}, "page count"),
        ({"output_bytes": 4}, "output_bytes"),
        ({"decompressed_bytes": 4}, "decompressed_bytes"),
    ],
)
def test_page_output_and_work_ceilings_fail_closed(
    request_change: dict[str, Any],
    message: str,
) -> None:
    """ParserLimits bound page count, returned text, and extraction work."""
    content = build_pdf_fixture()
    with pytest.raises(pdf_parser.PdfParseError, match=message):
        pdf_parser.parse(_request(content, **request_change), content)


def test_wall_time_ceiling_fails_cooperatively(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The parser observes the wall ceiling before beginning page work."""
    content = build_pdf_fixture()
    ticks = iter((0.0, 20.0))
    monkeypatch.setattr(pdf_parser, "monotonic", lambda: next(ticks))
    with pytest.raises(pdf_parser.PdfParseError, match="wall_time_seconds"):
        pdf_parser.parse(_request(content), content)


def test_saved_byte_hash_and_count_are_rechecked() -> None:
    """Direct parser calls cannot silently return mismatched provenance."""
    content = build_pdf_fixture()
    request = _request(content)
    wrong_count = replace(
        request,
        source=replace(request.source, byte_count=len(content) + 1),
    )
    with pytest.raises(ValueError, match="byte_count"):
        pdf_parser.parse(wrong_count, content)
    wrong_hash = replace(
        request,
        source=replace(request.source, sha256="00" * 32),
    )
    with pytest.raises(ValueError, match="sha256"):
        pdf_parser.parse(wrong_hash, content)


def test_closes_native_handles_on_success_and_output_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Document/page/text/web-link handles close on both terminal paths."""
    counts = {"document": 0, "page": 0, "text": 0, "links": 0}
    original_document_close = pdf_parser.pdfium.PdfDocument.close
    original_page_close = pdf_parser.pdfium.PdfPage.close
    original_text_close = pdf_parser.pdfium.PdfTextPage.close
    original_links_close = pdf_parser.pdfium_c.FPDFLink_CloseWebLinks

    def document_close(self: Any, *args: Any, **kwargs: Any) -> Any:
        counts["document"] += 1
        return original_document_close(self, *args, **kwargs)

    def page_close(self: Any, *args: Any, **kwargs: Any) -> Any:
        counts["page"] += 1
        return original_page_close(self, *args, **kwargs)

    def text_close(self: Any, *args: Any, **kwargs: Any) -> Any:
        counts["text"] += 1
        return original_text_close(self, *args, **kwargs)

    def links_close(handle: Any) -> Any:
        counts["links"] += 1
        return original_links_close(handle)

    monkeypatch.setattr(pdf_parser.pdfium.PdfDocument, "close", document_close)
    monkeypatch.setattr(pdf_parser.pdfium.PdfPage, "close", page_close)
    monkeypatch.setattr(pdf_parser.pdfium.PdfTextPage, "close", text_close)
    monkeypatch.setattr(
        pdf_parser.pdfium_c,
        "FPDFLink_CloseWebLinks",
        links_close,
    )

    content = build_text_pdf(b"success")
    pdf_parser.parse(_request(content), content)
    after_success = counts.copy()
    for key in ("document", "page", "text", "links"):
        if after_success[key] < 1:
            pytest.fail(f"Expected {key} handle cleanup on success")

    failing = build_text_pdf(b"too much output")
    with pytest.raises(pdf_parser.PdfParseError, match="output_bytes"):
        pdf_parser.parse(_request(failing, output_bytes=1), failing)
    for key in ("document", "page", "text", "links"):
        if counts[key] <= after_success[key]:
            pytest.fail(f"Expected {key} handle cleanup on failure")


def test_digital_signature_presence_is_not_claimed_as_verified() -> None:
    """Text parsing never implies cryptographic signature verification."""
    content = build_text_pdf(b"Signed marker") + b"\n% /Type /Sig\n"
    request = _request(content)
    output = pdf_parser.parse(request, content)
    if "digital-signature-unverified" not in _codes(output):
        pytest.fail("Expected explicit digital-signature verification limitation")
