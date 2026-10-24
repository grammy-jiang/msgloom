"""P2-03 page count check: hostile object stream dictionaries (re-review 2)."""

from __future__ import annotations

import time

import pypdfium2 as pdfium
import pytest

from msgloom.a2_kedro.parsers import pdf_pagecheck
from msgloom.a2_kedro.parsers.pdf import PdfLimit, parse_pdf
from msgloom.a2_kedro.parsers.pdf_pagecheck import PageCountVerdict, check_page_count
from msgloom.contracts import TerminalStatus
from tests.a2_kedro.helpers import check
from tests.a2_kedro.test_p2_03_pagecheck import build_objstm_pdf

OK = PageCountVerdict.OK
FLATE = b"/Filter /FlateDecode"

#: name -> (filter entry, extra entry, expected verdict). Hidden: 3 leaves.
VARIANTS = {
    "name_with_obj_before_filter": (b"/xobj 1 " + FLATE, b"", None),
    "name_with_stream_before_filter": (b"/Xstream 1 " + FLATE, b"", None),
    "string_with_stream_before_filter": (b"(stream) " + FLATE, b"", None),
    "fake_opener_string_after_filter": (FLATE + b" /S (>>\nstream\n)", b"", None),
    "fake_header_after_filter": (FLATE + b" /S 1 0 obj", b"", None),
    "escaped_filter_key": (b"/Fil#74er /FlateDecode", b"", None),
    "escaped_filter_value": (b"/Filter /Flate#44ecode", b"", None),
    "escaped_predictor": (
        FLATE,
        b"/DecodeParms << /Pred#69ctor 12 >>",
        PageCountVerdict.UNVERIFIED,
    ),
    "escaped_decodeparms": (
        FLATE,
        b"/Decode#50arms << /Columns 5 >>",
        PageCountVerdict.UNVERIFIED,
    ),
    "comment_in_filter": (
        b"/Filter %c\n/FlateDecode",
        b"",
        PageCountVerdict.UNVERIFIED,
    ),
    "two_filters": (FLATE + b" /Filter /FlateDecode", b"", PageCountVerdict.UNVERIFIED),
    "crypt_filter": (FLATE, b"/Crypt#20 1", PageCountVerdict.UNVERIFIED),
}


def hidden(**kwargs: object) -> bytes:
    return build_objstm_pdf([b"A", b"B", b"C"], count=1, **kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize("name", sorted(VARIANTS))
def test_hostile_dictionary_is_never_ok(name: str) -> None:
    flt, extra, expected = VARIANTS[name]
    data = hidden(stm_filter=flt, stm_extra=extra)
    verdict = check_page_count(data, 1)
    check(verdict is not OK, f"{name} must not pass: {verdict}")
    if expected is not None:
        check(verdict is expected, f"{name} gives {expected}, got {verdict}")
    result = parse_pdf(data)
    check(result.status is not TerminalStatus.COMPLETE, "never complete")


def test_hostile_dictionary_with_valid_file_is_incomplete() -> None:
    data = hidden(stm_filter=b"/xobj 1 " + FLATE)
    document = pdfium.PdfDocument(data)
    try:
        check(len(document) == 1, "pdfium trusts the claim")
    finally:
        document.close()
    result = parse_pdf(data)
    check(result.status is TerminalStatus.INCOMPLETE, "incomplete")
    check(PdfLimit.PAGE_COUNT_MISMATCH.value in result.codes, "mismatch")


@pytest.mark.parametrize(
    "mark",
    [b"/Type %comment\n/ObjStm", b"/Type %c\r/ObjStm", b"/T#79pe /Obj#53tm"],
)
def test_comment_and_escape_in_objstm_type_are_not_ok(mark: bytes) -> None:
    data = hidden().replace(b"/Type /ObjStm", mark)
    check(mark in data, "the marker was replaced")
    check(check_page_count(data, 1) is not OK, "ObjStm is found")
    check(parse_pdf(data).status is not TerminalStatus.COMPLETE, "never complete")


def test_unmarked_plain_stream_data_after_objstm_word_is_unverified() -> None:
    data = (
        b"3 0 obj\n<< /Type /ObjStm /N 1 /First 4 >>\nstream\n\x78\x9c junk\nendstream"
    )
    check(check_page_count(data, 1) is PageCountVerdict.UNVERIFIED, "not plain")


def test_honest_objstm_stays_complete() -> None:
    data = build_objstm_pdf([b"A", b"B", b"C"])
    check(check_page_count(data, 3) is OK, "verdict ok")
    check(parse_pdf(data).status is TerminalStatus.COMPLETE, "complete")
    plain = build_objstm_pdf([b"A", b"B"], compress=False)
    check(check_page_count(plain, 2) is OK, "plain object stream")
    escaped = build_objstm_pdf([b"A"], stm_filter=b"/Fil#74er /Flate#44ecode")
    check(check_page_count(escaped, 1) is OK, "escaped but honest Flate")


def test_many_mentions_are_cut_early_and_fast() -> None:
    started = time.perf_counter()
    noise = b"/Type /ObjStm " * 2_000_000
    check(check_page_count(noise, 0) is PageCountVerdict.UNVERIFIED, "no stream")
    escapes = (b"/Obj#53tm " + b"#41" * 100 + b" >>\nstream\n") * 200_000
    check(check_page_count(escapes, 0) is PageCountVerdict.UNVERIFIED, "caps")
    check(time.perf_counter() - started < 3.0, "scan is bounded")


def test_escape_budget_is_a_limitation(monkeypatch: pytest.MonkeyPatch) -> None:
    data = build_objstm_pdf([b"A"], stm_filter=b"/Fil#74er /FlateDecode")
    check(check_page_count(data, 1) is OK, "one escape fits")
    monkeypatch.setattr(pdf_pagecheck, "MAX_ESCAPES", 1)
    check(check_page_count(data, 1) is PageCountVerdict.UNVERIFIED, "budget hit")
