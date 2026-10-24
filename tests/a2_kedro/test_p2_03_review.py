"""P2-03 review fixes: page count cross-check, lossy text, pdfium errors."""

from __future__ import annotations

import pypdfium2 as pdfium
import pytest

from msgloom.a2_kedro.parsers import pdf
from msgloom.a2_kedro.parsers.pdf import PdfLimit, parse_pdf
from msgloom.contracts import TerminalStatus
from tests.a2_kedro.helpers import check
from tests.a2_kedro.test_p2_03 import build_pdf

INCOMPLETE = TerminalStatus.INCOMPLETE
FAILED = TerminalStatus.FAILED


@pytest.mark.parametrize("claim", [1, 2])
def test_count_below_real_pages_is_reported_not_complete(claim: int) -> None:
    result = parse_pdf(build_pdf([b"A", b"B", b"C"], count=claim))
    check(result.status is INCOMPLETE, "dropped pages are never complete")
    check("page_count_mismatch" in result.codes, "page_count_mismatch")
    check(result.claimed_pages == claim, "the claim is reported")
    check(len(result.pages) == claim, "only the claimed pages are read")
    check(result.to_receipt("1") is not None, "partial result has a receipt")


def test_honest_count_has_no_mismatch() -> None:
    result = parse_pdf(build_pdf([b"A", b"B", b"C"]))
    check(result.status is TerminalStatus.COMPLETE, "honest count is complete")
    check(PdfLimit.PAGE_COUNT_MISMATCH.value not in result.codes, "no mismatch")


@pytest.mark.parametrize(
    "token", [b"/Type /Page", b"/Type/Page", b"/Type\n/Page\n", b"/Type  /Page>>"]
)
def test_leaf_token_spacing_is_detected(token: bytes) -> None:
    base = build_pdf([b"A", b"B"], count=1)
    data = base.replace(b"/Type /Page ", token + b" ")
    check(pdf._has_more_leaves(data, 1), "two leaves above a claim of one")
    check(not pdf._has_more_leaves(data, 2), "two leaves match a claim of two")


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"/Page",
        b"/Type /Pages /Type /Pages /Type /Pages",
        b"/Type /PageLabels /Type /PageX /Type /Page1",
        b"/Page /Page /Page /Page",
        b"     /Page /Page",
    ],
)
def test_non_leaf_names_do_not_count(raw: bytes) -> None:
    check(not pdf._has_more_leaves(raw, 0), "not a page leaf")


def test_mismatch_scan_survives_hostile_repeats() -> None:
    data = b"/Type /Page" * 100_000
    check(pdf._has_more_leaves(data, 5), "early exit on many leaves")
    noise = b"/Page " * 200_000
    check(not pdf._has_more_leaves(noise, 0), "bare names are not leaves")


def test_undecodable_page_text_is_flagged_not_dropped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = pdfium.PdfTextPage.get_text_range

    def fake(
        self: pdfium.PdfTextPage,
        index: int = 0,
        count: int = -1,
        errors: str = "ignore",
    ) -> str:
        if errors == "strict":
            raise UnicodeDecodeError("utf-16-le", b"\x00\xd8", 0, 2, "lone surrogate")
        return original(self, index, count, errors)

    monkeypatch.setattr(pdfium.PdfTextPage, "get_text_range", fake)
    result = parse_pdf(build_pdf([b"Hello"]))
    check(result.status is INCOMPLETE, "lossy text is never complete")
    check(result.codes == ("text_undecodable",), "text_undecodable")
    check(result.pages[0].text == "Hello", "text is kept")


def test_decodable_text_uses_strict_decoding(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []
    original = pdfium.PdfTextPage.get_text_range

    def spy(
        self: pdfium.PdfTextPage,
        index: int = 0,
        count: int = -1,
        errors: str = "ignore",
    ) -> str:
        seen.append(errors)
        return original(self, index, count, errors)

    monkeypatch.setattr(pdfium.PdfTextPage, "get_text_range", spy)
    result = parse_pdf(build_pdf([b"Hello"]))
    check(seen == ["strict"], "strict decoding first")
    check(result.status is TerminalStatus.COMPLETE, "clean text is complete")


SECRET = "alice.private@example.invalid"


def _boom(*_args: object, **_kwargs: object) -> int:
    raise RuntimeError(SECRET)


def test_security_revision_error_becomes_invalid_pdf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pdf.pdfium_raw, "FPDF_GetSecurityHandlerRevision", _boom)
    result = parse_pdf(build_pdf([b"Hello"]))
    check(result.status is FAILED and result.codes == ("invalid_pdf",), "invalid_pdf")
    check(SECRET not in repr(result) + repr(result.limitations), "message hidden")


def test_page_count_error_becomes_invalid_pdf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pdfium.PdfDocument, "__len__", _boom)
    result = parse_pdf(build_pdf([b"Hello"]))
    check(result.status is FAILED and result.codes == ("invalid_pdf",), "invalid_pdf")
    check(SECRET not in repr(result) + repr(result.limitations), "message hidden")
