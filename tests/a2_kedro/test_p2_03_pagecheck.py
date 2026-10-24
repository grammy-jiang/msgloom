"""P2-03 page count check: spacing, escapes, object streams and bounds."""

from __future__ import annotations

import struct
import time
import zlib

import pypdfium2 as pdfium
import pytest

from msgloom.a2_kedro.parsers import pdf_pagecheck
from msgloom.a2_kedro.parsers.pdf import PdfLimit, parse_pdf
from msgloom.a2_kedro.parsers.pdf_pagecheck import PageCountVerdict, check_page_count
from msgloom.contracts import TerminalStatus
from tests.a2_kedro.helpers import check
from tests.a2_kedro.test_p2_03 import build_pdf

COMPLETE = TerminalStatus.COMPLETE
INCOMPLETE = TerminalStatus.INCOMPLETE
OK = PageCountVerdict.OK
MISMATCH = PageCountVerdict.MISMATCH
UNVERIFIED = PageCountVerdict.UNVERIFIED


def build_objstm_pdf(
    texts: list[bytes],
    *,
    count: int | None = None,
    leaf: bytes = b"/Type /Page",
    compress: bool = True,
    stm_filter: bytes | None = None,
    stm_extra: bytes = b"",
    payload: bytes | None = None,
) -> bytes:
    """
    Build a PDF 1.5 file whose page tree and page leaves sit in an ObjStm.

    The catalog, the page content streams, the object stream and the xref
    stream are plain objects. ``count`` overrides the ``/Count`` claim,
    ``leaf`` the leaf type token. ``stm_filter`` overrides the ``/Filter``
    entry and ``payload`` the object stream data (default: the real data).
    """
    n = len(texts)
    size = 6 + 2 * n
    kids = b" ".join(b"%d 0 R" % (6 + i) for i in range(n))
    inner: list[tuple[int, bytes]] = [
        (2, b"<< /Type /Pages /Kids [" + kids + b"] /Count %d >>" % (count or n)),
        (3, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"),
    ]
    for i in range(n):
        inner.append(
            (
                6 + i,
                b"<< "
                + leaf
                + b" /Parent 2 0 R /MediaBox [0 0 200 200] /Contents %d 0 R "
                b"/Resources << /Font << /F1 3 0 R >> >> >>" % (6 + n + i),
            )
        )
    offsets: list[bytes] = []
    pos = 0
    bodies = b""
    for num, body in inner:
        offsets.append(b"%d %d" % (num, pos))
        bodies += body + b"\n"
        pos += len(body) + 1
    header = b" ".join(offsets) + b"\n"
    data = header + bodies
    stm_data = data if payload is None else payload
    if compress and payload is None:
        stm_data = zlib.compress(data)
    flt = stm_filter if stm_filter is not None else b"/Filter /FlateDecode"
    if not compress and stm_filter is None:
        flt = b""

    out = bytearray(b"%PDF-1.5\n")
    where: dict[int, int] = {}

    def add(num: int, body: bytes) -> None:
        where[num] = len(out)
        out.extend(b"%d 0 obj\n" % num + body + b"\nendobj\n")

    add(1, b"<< /Type /Catalog /Pages 2 0 R >>")
    for i, text in enumerate(texts):
        content = b"BT /F1 12 Tf 20 100 Td (" + text + b") Tj ET"
        add(
            6 + n + i,
            b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
        )
    add(
        4,
        b"<< /Type /ObjStm /N %d /First %d %s %s /Length %d >>\nstream\n"
        % (len(inner), len(header), flt, stm_extra, len(stm_data))
        + stm_data
        + b"\nendstream",
    )
    xref_at = len(out)
    rows = bytearray()
    index_of = {num: k for k, (num, _) in enumerate(inner)}
    for num in range(size):
        if num in index_of:
            rows += struct.pack(">BIH", 2, 4, index_of[num])
        elif num in where or num == 5:
            rows += struct.pack(">BIH", 1, xref_at if num == 5 else where[num], 0)
        else:
            rows += struct.pack(">BIH", 0, 0, 0)
    out.extend(
        b"5 0 obj\n<< /Type /XRef /Size %d /W [1 4 2] /Root 1 0 R /Length %d >>\n"
        b"stream\n" % (size, len(rows)) + bytes(rows) + b"\nendstream\nendobj\n"
    )
    out.extend(b"startxref\n%d\n%%%%EOF\n" % xref_at)
    return bytes(out)


def test_objstm_builder_opens_in_pdfium_with_claimed_count() -> None:
    data = build_objstm_pdf([b"A", b"B", b"C"])
    document = pdfium.PdfDocument(data)
    try:
        check(len(document) == 3, "pdfium reads three pages from the object stream")
        text = document[0].get_textpage().get_text_range()
    finally:
        document.close()
    check("A" in text, "page text is read")


def test_honest_objstm_file_is_complete() -> None:
    data = build_objstm_pdf([b"A", b"B", b"C"])
    check(b"/Type /Page " not in data, "leaves are hidden from the raw scan")
    result = parse_pdf(data)
    check(result.status is COMPLETE, "honest object stream file is complete")
    check(result.claimed_pages == 3 and len(result.pages) == 3, "three pages")


@pytest.mark.parametrize("claim", [1, 2])
def test_hidden_objstm_leaves_are_a_mismatch(claim: int) -> None:
    data = build_objstm_pdf([b"A", b"B", b"C"], count=claim)
    document = pdfium.PdfDocument(data)
    try:
        check(len(document) == claim, "pdfium trusts the claim")
    finally:
        document.close()
    result = parse_pdf(data)
    check(result.status is INCOMPLETE, "hidden leaves are never complete")
    check(PdfLimit.PAGE_COUNT_MISMATCH.value in result.codes, "mismatch")


def test_unfiltered_objstm_is_seen_by_the_raw_scan() -> None:
    data = build_objstm_pdf([b"A", b"B"], count=1, compress=False)
    check(parse_pdf(data).status is INCOMPLETE, "plain object stream leaves count")
    check(check_page_count(data, 1) is MISMATCH, "mismatch")
    honest = build_objstm_pdf([b"A", b"B"], compress=False)
    check(check_page_count(honest, 2) is OK, "honest plain object stream")


def test_garbage_flate_objstm_is_unverified() -> None:
    data = build_objstm_pdf([b"A"], payload=b"not zlib data at all")
    check(check_page_count(data, 1) is UNVERIFIED, "undecodable stream")


def test_unreferenced_garbage_objstm_makes_a_good_file_incomplete() -> None:
    good = build_objstm_pdf([b"A", b"B"])
    junk = (
        b"9 0 obj\n<< /Type /ObjStm /N 1 /First 4 /Filter /FlateDecode >>\n"
        b"stream\nnot zlib\nendstream\nendobj\n"
    )
    result = parse_pdf(good + junk)
    check(result.claimed_pages == 2, "pdfium still opens the file")
    check(result.status is INCOMPLETE, "never complete")
    check(PdfLimit.PAGE_COUNT_UNVERIFIED.value in result.codes, "unverified")


def test_truncated_flate_objstm_is_unverified() -> None:
    packed = zlib.compress(b"x" * 5000)
    data = build_objstm_pdf([b"A"], payload=packed[:-8])
    check(check_page_count(data, 1) is UNVERIFIED, "cut stream")


@pytest.mark.parametrize(
    ("flt", "extra"),
    [
        (b"/Filter /LZWDecode", b""),
        (b"/Filter [/ASCIIHexDecode /FlateDecode]", b""),
        (b"/Filter /FlateDecode", b"/DecodeParms << /Predictor 12 >>"),
        (b"/Filter 9 0 R", b""),
    ],
)
def test_unsupported_objstm_filter_is_unverified(flt: bytes, extra: bytes) -> None:
    data = build_objstm_pdf([b"A"], stm_filter=flt, stm_extra=extra)
    check(check_page_count(data, 1) is UNVERIFIED, "filter cannot be checked")


def test_overlarge_inflate_is_unverified(monkeypatch: pytest.MonkeyPatch) -> None:
    padding = b"%" + b" " * 70_000 + b"\n"
    data = build_objstm_pdf([b"A"], payload=zlib.compress(padding * 4))
    check(check_page_count(data, 1) is OK, "payload without leaves is fine")
    monkeypatch.setattr(pdf_pagecheck, "MAX_OBJSTM_OUTPUT", 100_000)
    check(check_page_count(data, 1) is UNVERIFIED, "output cap is a limitation")


def test_inflate_bomb_stops_at_the_cap() -> None:
    bomb = zlib.compress(b"\x00" * (pdf_pagecheck.MAX_OBJSTM_OUTPUT * 4))
    data = build_objstm_pdf([b"A"], payload=bomb)
    started = time.perf_counter()
    verdict = check_page_count(data, 1)
    check(verdict is UNVERIFIED, "bomb is a limitation")
    check(time.perf_counter() - started < 5.0, "bomb is cut early")
    check(parse_pdf(data).status is not COMPLETE, "never complete")


def test_too_many_object_streams_is_unverified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    one = build_objstm_pdf([b"A"])
    body = one[one.index(b"4 0 obj") : one.index(b"5 0 obj")]
    data = one + body * 3
    monkeypatch.setattr(pdf_pagecheck, "MAX_OBJSTM_COUNT", 2)
    check(check_page_count(data, 9) is UNVERIFIED, "stream count cap")


def test_input_cap_is_unverified(monkeypatch: pytest.MonkeyPatch) -> None:
    data = build_objstm_pdf([b"A"])
    check(check_page_count(data, 1) is OK, "honest file")
    monkeypatch.setattr(pdf_pagecheck, "MAX_OBJSTM_INPUT", 10)
    check(check_page_count(data, 1) is UNVERIFIED, "input cap")


def test_objstm_without_stream_keyword_is_unverified() -> None:
    check(
        check_page_count(b"<< /Type /ObjStm >> no data", 1) is UNVERIFIED, "no stream"
    )


@pytest.mark.parametrize(
    "leaf",
    [
        b"/Type /Page",
        b"/Type/Page",
        b"/Type" + b" " * 1000 + b"/Page",
        b"/Type\r\n\t\x00 /Page",
        b"/Subtype /Page",
        b"/T#79pe /Page",
        b"/Type /P#61ge",
        b"/Type /P#61g#65",
        b"/Typ#65 /P#41GE".replace(b"#41GE", b"#61ge"),
        b"/S#75btype /Page",
    ],
)
def test_leaf_forms_are_counted(leaf: bytes) -> None:
    data = build_pdf([b"A", b"B"], count=1).replace(b"/Type /Page ", leaf + b" ")
    check(check_page_count(data, 1) is MISMATCH, "two leaves above a claim of one")
    check(check_page_count(data, 2) is OK, "two leaves match a claim of two")


def test_leaf_forms_in_objstm_are_counted() -> None:
    for leaf in (
        b"/Type" + b" " * 500 + b"/Page",
        b"/T#79pe /P#61ge",
        b"/Subtype /Page",
    ):
        data = build_objstm_pdf([b"A", b"B"], count=1, leaf=leaf)
        check(parse_pdf(data).status is INCOMPLETE, "hidden leaf form is flagged")
        check(check_page_count(data, 1) is MISMATCH, "mismatch")


@pytest.mark.parametrize(
    "raw",
    [
        b"/Type /Pages",
        b"/Type /P#61ges",
        b"/Type /Page#20x",
        b"/Type /PageLabels",
        b"/Typex /Page",
        b"/Subtype /Pages",
        b"/Type % comment\n/Page",
    ],
)
def test_non_leaf_names_are_not_counted(raw: bytes) -> None:
    check(check_page_count(raw, 0) is OK, "not a leaf")


def test_known_undetected_variants_stay_documented() -> None:
    no_type = build_pdf([b"A", b"B"], count=1).replace(b"/Type /Page ", b"")
    check(check_page_count(no_type, 1) is OK, "a leaf without /Type is not found")


def test_whitespace_run_is_linear() -> None:
    run = b"/Type" + b" " * 1_000_000 + b"/Page"
    started = time.perf_counter()
    check(check_page_count(run, 0) is MISMATCH, "a long gap still matches")
    spaced = (b"/Type" + b" " * 100_000) * 10 + b"/Pag"
    check(check_page_count(spaced, 0) is OK, "no leaf in repeated gaps")
    check(time.perf_counter() - started < 3.0, "whitespace scan is linear")


def test_hash_noise_is_linear() -> None:
    noise = b"/T#79pe" * 300_000 + b"/#" * 300_000
    started = time.perf_counter()
    check(check_page_count(noise, 0) is OK, "no leaf")
    check(time.perf_counter() - started < 3.0, "escape scan is linear")
