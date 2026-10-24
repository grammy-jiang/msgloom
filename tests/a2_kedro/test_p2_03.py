"""P2-03 PDF parser: pages, text, scanned, encrypted, damaged and limits."""

from __future__ import annotations

import hashlib
import struct
from typing import Final

import pytest

from msgloom.a2_kedro.contracts.parse import ParsedParts
from msgloom.a2_kedro.parsers import pdf
from msgloom.a2_kedro.parsers.pdf import (
    PageState,
    PdfInputError,
    PdfParseResult,
    parse_pdf,
    source_block_id,
)
from msgloom.contracts import Limitation, TerminalStatus
from tests.a2_kedro.helpers import check

SECRET = "alice.private@example.invalid"
COMPLETE = TerminalStatus.COMPLETE
INCOMPLETE = TerminalStatus.INCOMPLETE
FAILED = TerminalStatus.FAILED

#: Marker for a page that holds only an image (a scanned page).
IMAGE: Final = object()
_PAD = bytes.fromhex("28BF4E5E4E758A4164004E56FFFA01082E2E00B6D0683E802F0CA9FE6453697A")
_OWNER = b"O" * 32
_FILE_ID = b"0123456789abcdef"


def _rc4(key: bytes, data: bytes) -> bytes:
    state = list(range(256))
    j = 0
    for i in range(256):
        j = (j + state[i] + key[i % len(key)]) % 256
        state[i], state[j] = state[j], state[i]
    out = bytearray()
    i = j = 0
    for byte in data:
        i = (i + 1) % 256
        j = (j + state[i]) % 256
        state[i], state[j] = state[j], state[i]
        out.append(byte ^ state[(state[i] + state[j]) % 256])
    return bytes(out)


def _content(page: object) -> bytes:
    if page is IMAGE:
        return b"q 100 0 0 100 10 10 cm BI /W 1 /H 1 /CS /G /BPC 8 ID \x80 EI Q"
    if isinstance(page, bytes) and page:
        return b"BT /F1 12 Tf 20 100 Td (" + page + b") Tj ET"
    return b""


def build_pdf(
    pages: list[object],
    *,
    count: int | None = None,
    password: bytes | None = None,
    trailer: bool = True,
) -> bytes:
    """
    Build a tiny PDF. A page is text bytes, ``b""`` (blank) or ``IMAGE``.

    ``password`` encrypts with RC4 40-bit (revision 2) and that user
    password. ``count`` overrides the ``/Count`` claim of the page tree.
    """
    n = len(pages)
    key = b""
    if password is not None:
        padded = (password + _PAD)[:32]
        seed = padded + _OWNER + struct.pack("<i", -4) + _FILE_ID
        key = hashlib.md5(seed).digest()[:5]
    kids = b" ".join(b"%d 0 R" % (4 + 2 * i) for i in range(n))
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids ["
        + kids
        + b"] /Count %d >>" % (n if count is None else count),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for i, page in enumerate(pages):
        num = 5 + 2 * i
        objs.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
            b"/Contents %d 0 R /Resources << /Font << /F1 3 0 R >> >> >>" % num
        )
        body = _content(page)
        if password is not None:
            obj_key = hashlib.md5(key + struct.pack("<I", num)[:3] + b"\0\0").digest()[
                :10
            ]
            body = _rc4(obj_key, body)
        objs.append(b"<< /Length %d >>\nstream\n" % len(body) + body + b"\nendstream")
    extra = b""
    if password is not None:
        u_entry = _rc4(key, _PAD)
        objs.append(
            b"<< /Filter /Standard /V 1 /R 2 /P -4 /O <"
            + _OWNER.hex().encode()
            + b"> /U <"
            + u_entry.hex().encode()
            + b"> >>"
        )
        file_id = _FILE_ID.hex().encode()
        extra = b" /Encrypt %d 0 R /ID [<%s> <%s>]" % (len(objs), file_id, file_id)
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, obj in enumerate(objs, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + obj + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R%s >>\n" % (len(objs) + 1, extra)
    if trailer:
        out += b"startxref\n%d\n%%%%EOF\n" % xref
    return bytes(out)


def codes(result: PdfParseResult) -> tuple[str, ...]:
    return result.codes


def texts(result: PdfParseResult) -> list[str]:
    return [page.text for page in result.pages]


# --- positive ------------------------------------------------------------


def test_text_pdf_is_complete_with_per_page_text_and_stable_block_ids() -> None:
    data = build_pdf([b"Hello", b"World"])
    result = parse_pdf(data)
    check(result.status is COMPLETE, "text PDF is complete")
    check(result.limitations == (), "no limitation")
    check(result.claimed_pages == 2 and len(result.pages) == 2, "two pages")
    check(texts(result) == ["Hello", "World"], "per-page text")
    check([p.block_id for p in result.pages] == ["page-0000", "page-0001"], "block IDs")
    check(result.input_bytes == len(data), "input size")
    check(result.input_sha256 == hashlib.sha256(data).hexdigest(), "input digest")
    check([(p.width, p.height) for p in result.pages] == [(200.0, 200.0)] * 2, "size")
    check(parse_pdf(data) == result, "same bytes give an equal result")
    check(parse_pdf(bytearray(data)) == result, "bytearray gives the same result")
    check(parse_pdf(memoryview(data)) == result, "memoryview gives the same result")


def test_blank_page_between_text_pages_does_not_block_complete() -> None:
    result = parse_pdf(build_pdf([b"One", b"", b"Three"]))
    check(result.status is COMPLETE, "a blank page alone is no limitation")
    check([p.state for p in result.pages][1] is PageState.BLANK, "blank state")
    check(result.pages[1].char_count == 0, "blank page has no characters")


def test_block_ids_depend_on_page_index_only(monkeypatch: pytest.MonkeyPatch) -> None:
    data = build_pdf([b"A1", b"B2", b"C3", b"D4"])
    full = parse_pdf(data)
    monkeypatch.setattr(pdf, "MAX_PAGES", 2)
    cut = parse_pdf(data)
    check(
        [p.block_id for p in cut.pages] == [p.block_id for p in full.pages[:2]],
        "stable",
    )
    check(source_block_id(7) == "page-0007", "index 7")
    for bad in (-1, 4096):
        with pytest.raises(PdfInputError):
            source_block_id(bad)


def test_receipt_and_parsed_parts_for_complete_result() -> None:
    data = build_pdf([b"Hello", b"", b"World"])
    result = parse_pdf(data)
    receipt = result.to_receipt("1")
    check(receipt is not None and receipt.outcome == "complete", "complete receipt")
    check(receipt is not None and receipt.limit_hit == "none", "no limit hit")
    parts = result.to_parsed_parts("comp-1", "1")
    check(isinstance(parts, ParsedParts), "parsed parts built")
    if parts is None:
        pytest.fail("parsed parts missing")
    check(parts.parts[0].page_count == 3, "page count")
    check([p.char_count for p in parts.pages] == [5, 0, 5], "page sizes only")
    check(parts.parts[0].link.component_sha256 == result.input_sha256, "link digest")
    check(ParsedParts.decode(parts.encode()) == parts, "canonical round trip")
    check(SECRET.encode() not in parts.encode(), "no content in the record")


# --- scanned, blank and encrypted ----------------------------------------


def test_image_only_pdf_is_incomplete_never_complete_empty() -> None:
    result = parse_pdf(build_pdf([IMAGE, IMAGE]))
    check(result.status is INCOMPLETE, "scanned PDF is incomplete")
    check(codes(result) == ("no_text_layer", "no_text"), "scanned limitations")
    check(
        [p.state for p in result.pages] == [PageState.NO_TEXT_LAYER] * 2, "page states"
    )
    check(result.text_chars == 0, "no text")


def test_mixed_text_and_scanned_pages_keep_text_and_report_limit() -> None:
    result = parse_pdf(build_pdf([b"Typed", IMAGE]))
    check(result.status is INCOMPLETE, "mixed PDF is incomplete")
    check(codes(result) == ("no_text_layer",), "one limitation")
    check(texts(result) == ["Typed", ""], "text of the typed page is kept")
    receipt = result.to_receipt("1")
    check(receipt is not None and receipt.outcome == "partial", "partial receipt")


def test_all_blank_pdf_is_incomplete_with_no_text() -> None:
    result = parse_pdf(build_pdf([b"", b""]))
    check(result.status is INCOMPLETE, "an all-blank PDF is not complete")
    check(codes(result) == ("no_text",), "no_text limitation")


def test_pdf_without_pages_is_not_complete() -> None:
    result = parse_pdf(build_pdf([]))
    check(result.status is FAILED, "zero pages fail")
    check(
        set(codes(result)) & {"no_pages", "invalid_pdf"} != set(), "limitation present"
    )
    check(result.to_receipt("1") is None, "no receipt")


def test_encrypted_with_empty_password_is_incomplete_with_limitation() -> None:
    result = parse_pdf(build_pdf([b"Open"], password=b""))
    check(result.status is INCOMPLETE, "encrypted PDF is not complete")
    check("encrypted" in codes(result), "encrypted limitation")
    check("password_required" not in codes(result), "no password needed")
    check(texts(result) == ["Open"], "text is readable with the empty password")


def test_encrypted_needing_a_password_fails_without_text() -> None:
    data = build_pdf([SECRET.encode()], password=b"hunter2")
    result = parse_pdf(data)
    check(result.status is FAILED, "locked PDF fails")
    check(codes(result) == ("encrypted", "password_required"), "locked limitations")
    check(result.pages == () and result.claimed_pages == 0, "no page is read")
    check(result.to_receipt("1") is None, "no receipt")
    check(result.to_parsed_parts("c", "1") is None, "no parsed parts")
    check(parse_pdf(data) == result, "deterministic")


# --- damaged input -------------------------------------------------------


def test_empty_read_is_never_complete() -> None:
    for data in (b"", bytearray(), memoryview(b"")):
        result = parse_pdf(data)
        check(result.status is FAILED, "empty input fails")
        check(codes(result) == ("empty_input",), "empty_input limitation")
        check(result.to_receipt("1") is None, "no receipt")


@pytest.mark.parametrize(
    ("data", "want"),
    [
        (b"GIF89a" + b"\x00" * 64, ("not_pdf",)),
        (b"%PDF-1.4\n" + bytes(range(256)), ("truncated_pdf", "invalid_pdf")),
        (b"%PDF-1.7\n%%EOF\n", ("invalid_pdf",)),
        (b"\x00" * 5000, ("not_pdf",)),
        (b"%PDF-", ("truncated_pdf", "invalid_pdf")),
    ],
)
def test_garbage_bytes_fail_with_fixed_limitations(
    data: bytes, want: tuple[str, ...]
) -> None:
    result = parse_pdf(data)
    check(result.status is FAILED, "garbage fails")
    check(codes(result) == want, f"limitations {codes(result)}")
    check(result.pages == (), "no pages")


def test_truncated_pdf_fails_and_never_completes() -> None:
    data = build_pdf([b"Hello", b"World"])
    result = parse_pdf(data[:300])
    check(result.status is FAILED, "cut file fails")
    check("truncated_pdf" in codes(result), "truncated limitation")
    check("invalid_pdf" in codes(result), "invalid limitation")


def test_recoverable_truncation_keeps_text_but_is_incomplete() -> None:
    data = build_pdf([b"Hello", b"World"], trailer=False)
    result = parse_pdf(data)
    check(result.status is INCOMPLETE, "recovered file is incomplete")
    check(codes(result) == ("truncated_pdf",), "truncated limitation")
    check(texts(result) == ["Hello", "World"], "recovered text")


def test_every_cut_without_end_marker_is_not_complete() -> None:
    data = build_pdf([b"Hello", b"World"])
    for cut in range(0, len(data) - len(b"%%EOF\n") + 1, 5):
        result = parse_pdf(data[:cut])
        check(result.status is not COMPLETE, f"cut at {cut} was complete")


# --- limits --------------------------------------------------------------


def test_byte_limit_stops_before_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    data = build_pdf([b"Hello"])
    monkeypatch.setattr(pdf, "MAX_PDF_BYTES", len(data) - 1)
    result = parse_pdf(data)
    check(result.status is INCOMPLETE, "oversized input is incomplete")
    check(codes(result) == ("size_limit",), "size_limit only")
    check(result.pages == (), "no page is read")
    check(result.to_receipt("1") is None, "no receipt without a page")
    monkeypatch.setattr(pdf, "MAX_PDF_BYTES", len(data))
    check(parse_pdf(data).status is COMPLETE, "exact limit is accepted")


def test_page_limit_gives_partial_pages_and_pages_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pdf, "MAX_PAGES", 2)
    result = parse_pdf(build_pdf([b"P0", b"P1", b"P2", b"P3"]))
    check(result.status is INCOMPLETE, "page limit is incomplete")
    check(codes(result) == ("page_limit",), "page_limit")
    check(texts(result) == ["P0", "P1"] and result.claimed_pages == 4, "partial pages")
    receipt = result.to_receipt("1")
    check(receipt is not None and receipt.limit_hit == "pages", "pages limit hit")
    check(result.to_parsed_parts("c", "1") is not None, "parsed parts are valid")


def test_text_limit_cuts_text_and_stops_reading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pdf, "MAX_TEXT_CHARS", 7)
    result = parse_pdf(build_pdf([b"Hello", b"World", b"Third"]))
    check(result.status is INCOMPLETE, "text limit is incomplete")
    check(codes(result) == ("text_limit",), "text_limit")
    check(texts(result) == ["Hello", "Wo"], "cut at the character limit")
    check(result.text_chars == 7, "exactly the limit")
    receipt = result.to_receipt("1")
    check(receipt is not None and receipt.limit_hit == "bytes", "bytes limit hit")


def test_text_exactly_at_the_limit_is_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pdf, "MAX_TEXT_CHARS", 10)
    result = parse_pdf(build_pdf([b"Hello", b"World"]))
    check(result.status is COMPLETE, "text equal to the limit is not cut")


@pytest.mark.parametrize("claim", [3, 100_000, 2_000_000_000])
def test_inflated_page_count_claim_is_bounded(claim: int) -> None:
    result = parse_pdf(build_pdf([b"Only"], count=claim))
    check(
        result.status is not COMPLETE or result.claimed_pages == 1,
        "claim is not trusted",
    )
    check(len(result.pages) <= pdf.MAX_PAGES, "page reads are bounded")
    check(result.pages[0].text == "Only", "the real page is read")
    if result.claimed_pages > 1:
        check(result.status is INCOMPLETE, "unreadable pages make it incomplete")
        check("page_unreadable" in codes(result), "page_unreadable limitation")
    parts = result.to_parsed_parts("c", "1")
    check(
        parts is not None and len(parts.pages) == 1, "only the real page has a record"
    )


# --- misuse and privacy --------------------------------------------------


@pytest.mark.parametrize("bad", ["%PDF-1.4", None, 12, [b"x"]])
def test_non_bytes_input_raises_fixed_error(bad: object) -> None:
    with pytest.raises(PdfInputError) as raised:
        parse_pdf(bad)  # type: ignore[arg-type]
    check(str(raised.value) == "input must be bytes", "fixed message")


def test_results_and_limitations_hide_content() -> None:
    results = [
        parse_pdf(build_pdf([SECRET.encode(), IMAGE])),
        parse_pdf(build_pdf([SECRET.encode()], password=b"x")),
        parse_pdf(b"%PDF-1.4\n" + SECRET.encode() * 3),
        parse_pdf(build_pdf([SECRET.encode()])[:200]),
    ]
    for result in results:
        shown = repr(result) + repr(result.pages) + repr(result.limitations)
        check(SECRET not in shown, "repr must not show text")
        check(SECRET not in str(result.codes), "codes must not show text")
        for item in result.limitations:
            check(isinstance(item, Limitation), "contract Limitation")
            check(
                SECRET not in item.detail
                and item.code in pdf.PdfLimit._value2member_map_,
                "closed",
            )
    check(SECRET in results[0].pages[0].text, "text is available on request")
