"""
PDF parser for saved PDF bytes: page count, per-page text and limits (P2-03).

The parser reads the exact saved bytes of one component with ``pypdfium2``
and returns a frozen :class:`PdfParseResult`. It never raises for bad PDF
content. A bad PDF yields a :class:`~msgloom.contracts.TerminalStatus` and
closed :class:`~msgloom.contracts.Limitation` records with fixed text.

Core rule: an empty read is never ``COMPLETE``. ``COMPLETE`` needs no
limitation and at least one page with a text layer.

Status rules:

* ``FAILED``: no readable page. Empty input, not a PDF, unreadable or
  truncated file, password needed, zero pages, every page unreadable.
* ``INCOMPLETE``: some result exists, or the input was not processed. Any
  limitation that is not a failure: scanned (image-only) page, unreadable
  page, page or text limit, encrypted file opened with the empty
  password, missing end marker, a PDF with no text at all, or a file over
  the byte limit (the file is not opened).
* ``COMPLETE``: no limitation and at least one page with text.

Encryption: the parser calls pdfium with no password. It never tries or
guesses a password. A file that needs a password is ``FAILED`` with
``encrypted`` and ``password_required``. A file that pdfium opens with
the empty password (owner-password-only encryption) is ``INCOMPLETE`` with
``encrypted``. The text is returned, but the result is never ``COMPLETE``.

Pages: page indices are zero based. :func:`source_block_id` gives the
stable source block ID of a page from its index only. The ID does not
change when a later page is cut off by a limit. A page with no text is
``NO_TEXT_LAYER`` when it holds page objects (image-only or scanned) and
``BLANK`` when it holds none. A blank page is not a limitation by itself.
The page count in a PDF is a claim of the file. pdfium may report a count
that the file cannot support. The parser reads at most ``MAX_PAGES``
pages, counts pages that fail to load as ``UNREADABLE`` and reports the
claim in :attr:`PdfParseResult.claimed_pages`. pdfium trusts a ``/Count``
above zero and cannot load a page past it. The parser therefore cross-checks
the claim with
:func:`~msgloom.a2_kedro.parsers.pdf_pagecheck.check_page_count`, a
heuristic scan for page leaf objects. More leaves than the claim gives
``PAGE_COUNT_MISMATCH``. A scan that cannot finish (object stream that is
damaged, too large, over the stream limit, with a predictor or with a
filter other than Flate) gives ``PAGE_COUNT_UNVERIFIED``. Neither result is
``COMPLETE``. The scan finds ``/Type /Page`` with any white space between
the names, the ``/Subtype /Page`` form and ``#xx`` name escapes, in the raw
bytes and in Flate object streams. It does not find leaves with no
``/Type`` entry, a comment between key and value, or leaves in an object
stream that has no ``/Type /ObjStm``. A result without a mismatch
limitation is therefore not proof that the page count is right. The scan
can flag a file with old page revisions or with the token in stream data.
See ``pdf_pagecheck.py`` for the exact rules.

A page text that pdfium returns with undecodable UTF-16 (a lone
surrogate) is read with replacement characters and gives
``TEXT_UNDECODABLE``. The text is not cut silently.

Bounds: ``MAX_PDF_BYTES`` (input), ``MAX_PAGES`` (pages read) and
``MAX_TEXT_CHARS`` (text characters over all pages). A page limit or a
text limit gives a partial, deterministic result. The text limit cuts a
page at the limit and reads no later page. Work is linear in the bounded
input. The page count scan uses fixed regular expressions without nested
repetition.

PII: ``repr`` of every result type shows counts and states only. Limitation
details and error messages are fixed text. Page text is available only
through :attr:`PdfPage.text`.

Not covered: pdfium runs in process. The parser sets no time or memory
limit against decompression bombs or hostile content streams. Run it in
a worker process with an operating-system limit. pdfium is not thread
safe; call the parser from one thread at a time.

CANDIDATE/RESEARCH, PROVISIONAL: bounds and limitation names are not
frozen. See ``docs/notes/a2-v2-parser-p2-03.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_raw

from msgloom.a2_kedro.contracts.codec import A2ContractError, sha256_hex
from msgloom.a2_kedro.contracts.parse import (
    MAX_PAGES as CONTRACT_MAX_PAGES,
)
from msgloom.a2_kedro.contracts.parse import (
    ByteLink,
    LimitHit,
    PageRecord,
    ParsedParts,
    ParserReceipt,
    Part,
    PartRole,
)
from msgloom.a2_kedro.parsers.pdf_pagecheck import (
    PageCountVerdict,
    check_page_count,
)
from msgloom.contracts import Limitation, TerminalStatus

WORKER = "msgloom.a2_kedro.parsers.pdf"

#: Provisional bounds. They are parser decisions, not production limits.
MAX_PDF_BYTES = 32 * 1024 * 1024
MAX_PAGES = 500
MAX_TEXT_CHARS = 2_000_000

_HEADER_WINDOW = 1024
_TAIL_WINDOW = 4096
_ENCRYPTED_LOCKED = frozenset(
    {pdfium_raw.FPDF_ERR_PASSWORD, pdfium_raw.FPDF_ERR_SECURITY}
)


class PdfInputError(A2ContractError):
    """Raised for caller misuse. The message is fixed and has no content."""


class PdfLimit(StrEnum):
    """Closed, content-free reasons that a result is not complete."""

    EMPTY_INPUT = "empty_input"
    SIZE_LIMIT = "size_limit"
    NOT_PDF = "not_pdf"
    TRUNCATED_PDF = "truncated_pdf"
    INVALID_PDF = "invalid_pdf"
    ENCRYPTED = "encrypted"
    PASSWORD_REQUIRED = "password_required"
    NO_PAGES = "no_pages"
    PAGE_LIMIT = "page_limit"
    TEXT_LIMIT = "text_limit"
    PAGE_UNREADABLE = "page_unreadable"
    NO_TEXT_LAYER = "no_text_layer"
    NO_TEXT = "no_text"
    PAGE_COUNT_MISMATCH = "page_count_mismatch"
    PAGE_COUNT_UNVERIFIED = "page_count_unverified"
    TEXT_UNDECODABLE = "text_undecodable"


_DETAIL: dict[PdfLimit, str] = {
    PdfLimit.EMPTY_INPUT: "the input has no bytes",
    PdfLimit.SIZE_LIMIT: "the input is larger than the byte limit",
    PdfLimit.NOT_PDF: "the input has no PDF header",
    PdfLimit.TRUNCATED_PDF: "the PDF end marker is missing",
    PdfLimit.INVALID_PDF: "the PDF cannot be read",
    PdfLimit.ENCRYPTED: "the PDF is encrypted",
    PdfLimit.PASSWORD_REQUIRED: "the PDF needs a password that is not available",
    PdfLimit.NO_PAGES: "the PDF has no pages",
    PdfLimit.PAGE_LIMIT: "pages after the page limit are not read",
    PdfLimit.TEXT_LIMIT: "text after the text limit is not read",
    PdfLimit.PAGE_UNREADABLE: "at least one page cannot be read",
    PdfLimit.NO_TEXT_LAYER: "at least one page has content but no text layer",
    PdfLimit.NO_TEXT: "the PDF has no text",
    PdfLimit.PAGE_COUNT_MISMATCH: "the PDF may have more pages than it claims",
    PdfLimit.PAGE_COUNT_UNVERIFIED: "the page count could not be fully checked",
    PdfLimit.TEXT_UNDECODABLE: "text of at least one page was not decodable",
}


class PageState(StrEnum):
    """State of one page that was read."""

    TEXT = "text"
    NO_TEXT_LAYER = "no_text_layer"
    BLANK = "blank"
    UNREADABLE = "unreadable"


def source_block_id(page_index: int) -> str:
    """Return the stable source block ID of a page from its index."""
    if not 0 <= page_index < CONTRACT_MAX_PAGES:
        raise PdfInputError("page index is out of range")
    return f"page-{page_index:04d}"


@dataclass(frozen=True, slots=True)
class PdfPage:
    """
    One page that was read. ``repr`` hides the text.

    ``width`` and ``height`` are the page size in points, rounded to two
    decimals. They are ``0.0`` for an unreadable page. This is the only
    layout data; the parser gives no text coordinates.
    """

    index: int
    state: PageState
    text: str = field(default="", repr=False)
    width: float = 0.0
    height: float = 0.0

    @property
    def block_id(self) -> str:
        """Return the stable source block ID of this page."""
        return source_block_id(self.index)

    @property
    def char_count(self) -> int:
        """Return the number of text characters of this page."""
        return len(self.text)


@dataclass(frozen=True, slots=True)
class PdfParseResult:
    """
    Result of one parse of one saved PDF.

    ``pages`` lists the pages that were read, in index order, without gaps.
    ``claimed_pages`` is the page count that pdfium reports (``0`` when the
    file did not open). ``limitations`` is unique and in declaration order
    of :class:`PdfLimit`. ``repr`` carries counts only.
    """

    status: TerminalStatus
    limitations: tuple[Limitation, ...]
    input_bytes: int
    input_sha256: str
    claimed_pages: int = 0
    pages: tuple[PdfPage, ...] = field(default=(), repr=False)

    def __repr__(self) -> str:
        return (
            f"PdfParseResult({self.status.value}, "
            f"limitations={len(self.limitations)}, bytes={self.input_bytes}, "
            f"claimed_pages={self.claimed_pages}, pages={len(self.pages)})"
        )

    @property
    def codes(self) -> tuple[str, ...]:
        """Return the limitation codes in declaration order."""
        return tuple(item.code for item in self.limitations)

    @property
    def text_chars(self) -> int:
        """Return the number of text characters over all pages."""
        return sum(page.char_count for page in self.pages)

    def to_receipt(self, worker_version: str) -> ParserReceipt | None:
        """
        Return the parser receipt, or ``None`` when no page was read.

        ``limit_hit`` is ``"pages"`` for a page limit and ``"bytes"`` for
        every other limitation. The closed ``LimitHit`` has no value for
        scanned, encrypted or damaged input. :attr:`limitations` keeps the
        reason.
        """
        if self.status is TerminalStatus.FAILED or not self.pages:
            return None
        complete = self.status is TerminalStatus.COMPLETE
        hit: LimitHit = "none"
        if not complete:
            hit = "pages" if PdfLimit.PAGE_LIMIT in self.codes else "bytes"
        return ParserReceipt(
            worker=WORKER,
            worker_version=worker_version,
            outcome="complete" if complete else "partial",
            limit_hit=hit,
            input_bytes=self.input_bytes,
            part_count=1,
        )

    def to_parsed_parts(
        self,
        component_id: str,
        worker_version: str,
        *,
        part_id: str = "pdf-0",
        role: PartRole = "attachment",
    ) -> ParsedParts | None:
        """
        Return a ``ParsedParts`` record, or ``None`` when no page was read.

        The part links the whole component. ``page_count`` is the number
        of pages that were read. A page that failed to load has no page
        record. The record holds sizes only, never text.
        """
        receipt = self.to_receipt(worker_version)
        if receipt is None:
            return None
        link = ByteLink(
            component_id=component_id,
            component_sha256=self.input_sha256,
            component_size=self.input_bytes,
            offset=0,
            length=self.input_bytes,
        )
        part = Part(
            part_id=part_id,
            role=role,
            declared_format="pdf",
            detected_format="pdf",
            link=link,
            page_count=len(self.pages),
        )
        records = tuple(
            PageRecord(part_id=part_id, page_index=p.index, char_count=p.char_count)
            for p in self.pages
            if p.state is not PageState.UNREADABLE
        )
        return ParsedParts(parts=(part,), pages=records, receipt=receipt)


def _as_bytes(data: object) -> bytes:
    if isinstance(data, (bytes, bytearray, memoryview)):
        return bytes(data)
    raise PdfInputError("input must be bytes")


def _finish(
    raw: bytes,
    found: set[PdfLimit],
    pages: tuple[PdfPage, ...] = (),
    claimed: int = 0,
) -> PdfParseResult:
    usable = any(page.state is not PageState.UNREADABLE for page in pages)
    if not any(page.state is PageState.TEXT for page in pages) and (pages or not found):
        found.add(PdfLimit.NO_TEXT)
    if usable or found == {PdfLimit.SIZE_LIMIT}:
        status = TerminalStatus.INCOMPLETE if found else TerminalStatus.COMPLETE
    else:
        status = TerminalStatus.FAILED
    return PdfParseResult(
        status=status,
        limitations=tuple(
            Limitation(item.value, _DETAIL[item]) for item in PdfLimit if item in found
        ),
        input_bytes=len(raw),
        input_sha256=sha256_hex(raw),
        claimed_pages=claimed,
        pages=pages,
    )


def _clean(text: str) -> str:
    """Return ``text`` with ``\\n`` line ends and no lone surrogates."""
    unified = text.replace("\r\n", "\n").replace("\r", "\n")
    return unified.encode("utf-8", "replace").decode()


def _page_text(textpage: pdfium.PdfTextPage, count: int) -> tuple[str, bool]:
    """Return the cleaned text and whether it needed replacement characters."""
    if not count:
        return "", False
    try:
        return _clean(textpage.get_text_range(0, count, errors="strict")), False
    except UnicodeDecodeError:
        return _clean(textpage.get_text_range(0, count, errors="replace")), True


def _read_page(
    document: pdfium.PdfDocument, index: int, budget: int
) -> tuple[PdfPage, bool, bool]:
    """
    Read one page and return the page and two flags.

    The second item is ``True`` when the text limit cut the page text. The
    third item is ``True`` when the text was not decodable and holds
    replacement characters.

    ``budget`` is the number of text characters left.
    """
    try:
        page = document[index]
    except Exception:  # noqa: BLE001 - pdfium text must not leak via errors
        return PdfPage(index, PageState.UNREADABLE), False, False
    try:
        width, height = (round(side, 2) for side in page.get_size())
        textpage = page.get_textpage()
        try:
            total = textpage.count_chars()
            count = min(total, budget)
            text, lossy = _page_text(textpage, count)
        finally:
            textpage.close()
        if text.strip():
            shown = PdfPage(index, PageState.TEXT, text, width, height)
            return shown, total > budget, lossy
        objects = pdfium_raw.FPDFPage_CountObjects(page.raw)
        state = PageState.NO_TEXT_LAYER if objects else PageState.BLANK
        return PdfPage(index, state, "", width, height), total > budget, lossy
    except Exception:  # noqa: BLE001 - pdfium text must not leak via errors
        return PdfPage(index, PageState.UNREADABLE), False, False
    finally:
        page.close()


_PAGE_LIMITS = {
    PageState.UNREADABLE: PdfLimit.PAGE_UNREADABLE,
    PageState.NO_TEXT_LAYER: PdfLimit.NO_TEXT_LAYER,
}


def _read_pages(
    document: pdfium.PdfDocument, claimed: int, found: set[PdfLimit]
) -> tuple[PdfPage, ...]:
    if claimed == 0:
        found.add(PdfLimit.NO_PAGES)
    wanted = min(claimed, MAX_PAGES)
    pages: list[PdfPage] = []
    used = 0
    for index in range(wanted):
        if used >= MAX_TEXT_CHARS:
            found.add(PdfLimit.TEXT_LIMIT)
            break
        page, cut, lossy = _read_page(document, index, MAX_TEXT_CHARS - used)
        pages.append(page)
        used += page.char_count
        if cut:
            found.add(PdfLimit.TEXT_LIMIT)
        if lossy:
            found.add(PdfLimit.TEXT_UNDECODABLE)
        if page.state in _PAGE_LIMITS:
            found.add(_PAGE_LIMITS[page.state])
    if claimed > MAX_PAGES:
        found.add(PdfLimit.PAGE_LIMIT)
    return tuple(pages)


def parse_pdf(data: bytes | bytearray | memoryview) -> PdfParseResult:
    """
    Parse saved PDF bytes into per-page text and closed limitations.

    Raise :exc:`PdfInputError` only when ``data`` is not bytes-like.
    """
    raw = _as_bytes(data)
    found: set[PdfLimit] = set()
    if not raw:
        found.add(PdfLimit.EMPTY_INPUT)
        return _finish(raw, found)
    if len(raw) > MAX_PDF_BYTES:
        found.add(PdfLimit.SIZE_LIMIT)
        return _finish(raw, found)
    if raw.find(b"%PDF-", 0, _HEADER_WINDOW) < 0:
        found.add(PdfLimit.NOT_PDF)
        return _finish(raw, found)
    if raw.rfind(b"%%EOF", max(0, len(raw) - _TAIL_WINDOW)) < 0:
        found.add(PdfLimit.TRUNCATED_PDF)
    try:
        document = pdfium.PdfDocument(raw)
    except pdfium.PdfiumError as error:
        if error.err_code in _ENCRYPTED_LOCKED:
            found.update({PdfLimit.ENCRYPTED, PdfLimit.PASSWORD_REQUIRED})
        else:
            found.add(PdfLimit.INVALID_PDF)
        return _finish(raw, found)
    except Exception:  # noqa: BLE001 - pdfium text must not leak via errors
        found.add(PdfLimit.INVALID_PDF)
        return _finish(raw, found)
    try:
        try:
            encrypted = pdfium_raw.FPDF_GetSecurityHandlerRevision(document.raw) != -1
            claimed = len(document)
        except Exception:  # noqa: BLE001 - pdfium text must not leak via errors
            found.add(PdfLimit.INVALID_PDF)
            return _finish(raw, found)
        if encrypted:
            found.add(PdfLimit.ENCRYPTED)
        pages = _read_pages(document, claimed, found)
    finally:
        document.close()
    if claimed <= MAX_PAGES:
        verdict = check_page_count(raw, claimed)
        if verdict is PageCountVerdict.MISMATCH:
            found.add(PdfLimit.PAGE_COUNT_MISMATCH)
        elif verdict is PageCountVerdict.UNVERIFIED:
            found.add(PdfLimit.PAGE_COUNT_UNVERIFIED)
    return _finish(raw, found, pages, claimed)
