"""Synchronous PDFium extraction for the isolated preparation worker."""

from __future__ import annotations

from ctypes import addressof, c_ushort, string_at
from hashlib import sha256
from time import monotonic

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c

from msgloom.preparation.contracts import (
    BlockRole,
    DocumentFormat,
    LimitationKind,
    PageLocation,
    ParsedLink,
    ParserLimitation,
    ParserOutput,
    ParserProvenance,
    ParserRequest,
    TextBlock,
)

PARSER_NAME = "msgloom.pdf"
PARSER_VERSION = "1"
BACKEND = "pypdfium2-5.14.0"

_PRIMARY_PROFILE = "pdf-primary-v1"
_UNAVAILABLE_PROFILE_TERMS = ("ocr", "layout", "docling")


class PdfParseError(RuntimeError):
    """Report a visible PDF extraction failure."""


def _validate_request(request: ParserRequest, content: bytes) -> None:
    """Reject provenance, format, and profile mismatches before PDFium runs."""
    if request.detected_format is not DocumentFormat.PDF:
        raise ValueError("PDF parser requires detected_format=pdf")
    expected = (PARSER_NAME, PARSER_VERSION, BACKEND)
    actual = (
        request.parser.name,
        request.parser.version,
        request.parser.backend,
    )
    if actual != expected:
        raise ValueError("PDF parser identity does not match the selected worker")
    profile = request.config.profile.casefold()
    if any(term in profile for term in _UNAVAILABLE_PROFILE_TERMS):
        raise PdfParseError(
            "requested PDF OCR/layout profile is unavailable; Docling is absent"
        )
    if request.config.profile != _PRIMARY_PROFILE:
        raise ValueError(f"unsupported PDF parser profile: {request.config.profile}")
    if request.config.settings:
        raise ValueError("pdf-primary-v1 does not accept parser settings")
    if request.source.byte_count != len(content):
        raise ValueError("PDF content byte_count does not match saved provenance")
    if sha256(content).hexdigest().lower() != request.source.sha256.lower():
        raise ValueError("PDF content sha256 does not match saved provenance")
    if not content.startswith(b"%PDF-"):
        raise ValueError("invalid PDF signature: expected %PDF- header")


def _check_deadline(started: float, request: ParserRequest) -> None:
    """Fail cooperatively as well as relying on the parent hard timeout."""
    if monotonic() - started > request.limits.wall_time_seconds:
        raise PdfParseError("PDF parsing exceeded wall_time_seconds limit")


def _consume(
    amount: int,
    *,
    used: int,
    limit: int,
    label: str,
) -> int:
    """Advance a byte budget or fail before returning oversized output."""
    total = used + amount
    if total > limit:
        raise PdfParseError(f"PDF parsing exceeded {label} limit")
    return total


def _web_links(
    textpage: pdfium.PdfTextPage, page_number: int
) -> tuple[ParsedLink, ...]:
    """Extract PDFium-detected web links without fetching their targets."""
    handle = pdfium_c.FPDFLink_LoadWebLinks(textpage.raw)
    if not handle:
        raise PdfParseError("PDFium failed to load web-link metadata")
    try:
        count = pdfium_c.FPDFLink_CountWebLinks(handle)
        if count < 0:
            raise PdfParseError("PDFium failed to count web links")
        links: list[ParsedLink] = []
        for index in range(count):
            units = pdfium_c.FPDFLink_GetURL(handle, index, None, 0)
            if units <= 0:
                raise PdfParseError("PDFium failed to size a web-link URL")
            buffer = (c_ushort * units)()
            written = pdfium_c.FPDFLink_GetURL(handle, index, buffer, units)
            if written <= 0:
                raise PdfParseError("PDFium failed to read a web-link URL")
            raw = string_at(addressof(buffer), max(0, written - 1) * 2)
            target = raw.decode("utf-16-le", errors="strict")
            links.append(
                ParsedLink(
                    target=target,
                    text=None,
                    location=PageLocation(page_number),
                )
            )
        return tuple(links)
    finally:
        pdfium_c.FPDFLink_CloseWebLinks(handle)


def _limitation(
    kind: LimitationKind,
    code: str,
    detail: str,
    *,
    page_number: int | None = None,
    feature: str | None = None,
) -> ParserLimitation:
    """Build a limitation with an optional exact page location."""
    location = PageLocation(page_number) if page_number is not None else None
    return ParserLimitation(
        kind=kind,
        code=code,
        detail=detail,
        feature=feature,
        location=location,
    )


def _open_document(content: bytes) -> pdfium.PdfDocument:
    """Translate PDFium load failures into stable parser failures."""
    try:
        return pdfium.PdfDocument(content)
    except pdfium.PdfiumError as exc:
        if exc.err_code == pdfium_c.FPDF_ERR_PASSWORD:
            raise PdfParseError(
                "encrypted/password-protected PDF is unsupported"
            ) from exc
        if exc.err_code == pdfium_c.FPDF_ERR_SECURITY:
            raise PdfParseError("unsupported PDF security handler") from exc
        raise PdfParseError("malformed or unsupported PDF document") from exc


def parse(request: ParserRequest, content: bytes) -> ParserOutput:
    """
    Extract deterministic page text and limitations from saved PDF bytes.

    PDFium calls stay synchronous for the caller's isolated process. Every
    document, page, text-page, and web-link handle is closed before return or
    failure. Page text is retained in page order, but PDFium text extraction
    does not establish semantic reading order, tables, layout, or image
    meaning; those gaps are always explicit.
    """
    _validate_request(request, content)
    started = monotonic()
    document = _open_document(content)
    blocks: list[TextBlock] = []
    limitations: list[ParserLimitation] = []
    work_bytes = 0
    output_bytes = 0
    try:
        page_count = len(document)
        if page_count > request.limits.container_members:
            raise PdfParseError("PDF page count exceeds container_members limit")

        for page_index in range(page_count):
            _check_deadline(started, request)
            page_number = page_index + 1
            page = document.get_page(page_index)
            try:
                has_image = any(
                    pdfium_c.FPDFPageObj_GetType(obj.raw) == pdfium_c.FPDF_PAGEOBJ_IMAGE
                    for obj in page.get_objects()
                )
                textpage = page.get_textpage()
                try:
                    text = textpage.get_text_bounded(errors="strict")
                    encoded = text.encode("utf-8")
                    work_bytes = _consume(
                        len(encoded),
                        used=work_bytes,
                        limit=request.limits.decompressed_bytes,
                        label="decompressed_bytes",
                    )
                    links = _web_links(textpage, page_number)
                    link_bytes = sum(len(link.target.encode("utf-8")) for link in links)
                    work_bytes = _consume(
                        link_bytes,
                        used=work_bytes,
                        limit=request.limits.decompressed_bytes,
                        label="decompressed_bytes",
                    )
                    if text:
                        output_bytes = _consume(
                            len(encoded) + link_bytes,
                            used=output_bytes,
                            limit=request.limits.output_bytes,
                            label="output_bytes",
                        )
                        blocks.append(
                            TextBlock(
                                order=len(blocks),
                                role=BlockRole.TEXT,
                                text=text,
                                location=PageLocation(page_number),
                                links=links,
                            )
                        )
                finally:
                    textpage.close()

                if not text and has_image:
                    limitations.append(
                        _limitation(
                            LimitationKind.SCANNED,
                            "image-only-page",
                            "Page has image content but no extractable text; "
                            "OCR was not run.",
                            page_number=page_number,
                            feature="image-content",
                        )
                    )
                elif not text:
                    limitations.append(
                        _limitation(
                            LimitationKind.MISSING,
                            "empty-page",
                            "Page contains no PDFium-extractable text or image object.",
                            page_number=page_number,
                            feature="page-content",
                        )
                    )
                elif has_image:
                    limitations.append(
                        _limitation(
                            LimitationKind.PARTIAL,
                            "image-content-unextracted",
                            "Page text was extracted, but image meaning was "
                            "not extracted.",
                            page_number=page_number,
                            feature="image-content",
                        )
                    )
            finally:
                page.close()

        limitations.extend(
            (
                _limitation(
                    LimitationKind.PARTIAL,
                    "reading-order-unverified",
                    "PDFium text order is observed extraction order, not a "
                    "claim of semantic reading order.",
                    feature="reading-order",
                ),
                _limitation(
                    LimitationKind.PARTIAL,
                    "layout-unrepresented",
                    "Geometric layout and multi-column relationships are not "
                    "represented by this text profile.",
                    feature="layout",
                ),
                _limitation(
                    LimitationKind.PARTIAL,
                    "table-structure-unavailable",
                    "Table structure is not inferred from positioned PDF text.",
                    feature="tables",
                ),
            )
        )
        if b"/Type /Sig" in content or b"/FT /Sig" in content:
            limitations.append(
                _limitation(
                    LimitationKind.UNSUPPORTED,
                    "digital-signature-unverified",
                    "Digital signature presence is not cryptographically "
                    "verified by the text parser.",
                    feature="digital-signature",
                )
            )
        _check_deadline(started, request)
        return ParserOutput(
            provenance=ParserProvenance.from_request(request),
            blocks=tuple(blocks),
            limitations=tuple(limitations),
        )
    except pdfium.PdfiumError as exc:
        raise PdfParseError("PDFium extraction failed") from exc
    finally:
        document.close()
