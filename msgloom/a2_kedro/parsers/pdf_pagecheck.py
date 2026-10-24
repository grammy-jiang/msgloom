"""
Cross-check of the PDF page count claim against raw page leaves (P2-03).

pdfium trusts the ``/Count`` of the page tree and cannot load a page past
it. :func:`check_page_count` scans the saved bytes for page leaf objects and
compares their number with the claim. It is a heuristic with a closed result
(:class:`PageCountVerdict`). It never raises for file content.

Detected leaf forms, in the raw bytes and in inflated object streams:

* ``/Type /Page`` with any amount of PDF white space between the two names
  (including none).
* ``/Subtype /Page``. This form is not valid PDF, but a hostile file can use
  it, so it counts as a leaf.
* ``#xx`` hex escapes in the key and in the value, for example
  ``/T#79pe /P#61ge``. The patterns match the escape directly. The scan does
  not rewrite the bytes.

Not detected:

* Leaf objects with no ``/Type`` or ``/Subtype`` entry. pdfium accepts them
  as pages, but no token marks them.
* A comment (``%``) between the key and the value.
* Leaves in an object stream that is not marked by ``/Type /ObjStm`` in its
  dictionary.
* Leaves in an object stream with a predictor, another filter, a damaged
  Flate stream or an indirect ``/Filter``. These cases give
  :attr:`PageCountVerdict.UNVERIFIED`, never ``OK``.

Object streams (``/ObjStm``, PDF 1.5 and later) are inflated with hard
bounds: at most ``MAX_OBJSTM_COUNT`` streams, ``MAX_OBJSTM_INPUT`` bytes of
compressed input and ``MAX_OBJSTM_OUTPUT`` bytes of inflated output over all
streams. A cap hit gives ``UNVERIFIED``. The scan can flag a file with old
page revisions (incremental update) or the token in stream data. Those cases
are flagged, never hidden.

Cost: every pattern is a single pass over its input and has no nested
repetition, so the work is linear. A white space run of any length is read
once. Counting stops when the leaves exceed the claim.
"""

from __future__ import annotations

import re
import zlib
from enum import StrEnum

#: Provisional bounds for object stream inflation.
MAX_OBJSTM_COUNT = 256
MAX_OBJSTM_INPUT = 16 * 1024 * 1024
MAX_OBJSTM_OUTPUT = 8 * 1024 * 1024

_CHUNK = 64 * 1024
_DICT_WINDOW = 4096
_WS = rb"[\x00\t\n\f\r ]"
_DELIMS = rb"\x00\t\n\f\r /<>\[\]()%{}"


class PageCountVerdict(StrEnum):
    """Result of the page count cross-check."""

    OK = "ok"
    MISMATCH = "mismatch"
    UNVERIFIED = "unverified"


def _name(word: str) -> bytes:
    """Return a pattern for ``word`` where each letter may be ``#xx``."""
    parts = (rb"(?:%s|#(?i:%02x))" % (c.encode(), ord(c)) for c in word)
    return b"".join(parts)


_LEAF = re.compile(
    rb"/(?:%s|%s)%s*/%s(?=[%s]|\Z)"
    % (_name("Subtype"), _name("Type"), _WS, _name("Page"), _DELIMS)
)
_OBJSTM = re.compile(
    rb"/%s%s*/%s(?=[%s]|\Z)" % (_name("Type"), _WS, _name("ObjStm"), _DELIMS)
)
_FILTER = re.compile(rb"/Filter%s*(\[[^\]]*\]|/[^%s]+)" % (_WS, _DELIMS))
_FILTER_NAME = re.compile(rb"/[^%s]+" % _DELIMS)
_FLATE = ([b"/FlateDecode"], [b"/Fl"])


def _count_leaves(buf: bytes, limit: int) -> int:
    """Count leaves in ``buf``. Stop at ``limit + 1``."""
    if b"#" not in buf and buf.count(b"/Page") <= limit:
        return 0
    leaves = 0
    for _ in _LEAF.finditer(buf):
        leaves += 1
        if leaves > limit:
            break
    return leaves


def _stream_span(raw: bytes, found: re.Match[bytes]) -> tuple[bytes, int, int] | None:
    """Return the dictionary, data start and data end of the stream."""
    low = max(0, found.start() - _DICT_WINDOW)
    keyword = raw.find(b"stream", found.end(), found.end() + _DICT_WINDOW)
    if keyword < 0:
        return None
    begin = max(low, raw.rfind(b"obj", low, found.start()))
    start = keyword + 6
    if raw.startswith(b"\r\n", start):
        start += 2
    elif raw[start : start + 1] in (b"\n", b"\r"):
        start += 1
    end = raw.find(b"endstream", start)
    if end < 0:
        return None
    return raw[begin:keyword], start, end


def _is_flate(dictionary: bytes) -> bool | None:
    """Return ``None`` for no filter, else whether it is plain Flate."""
    if b"/Filter" not in dictionary:
        return None
    if b"Predictor" in dictionary:
        return False
    match = _FILTER.search(dictionary)
    if match is None:
        return False
    return _FILTER_NAME.findall(match.group(1)) in _FLATE


def _inflate(data: memoryview, room: int) -> bytes | None:
    """Inflate ``data`` to at most ``room`` bytes. Return ``None`` on failure."""
    inflater = zlib.decompressobj()
    out = bytearray()
    try:
        for at in range(0, len(data), _CHUNK):
            out += inflater.decompress(data[at : at + _CHUNK], room - len(out) + 1)
            if len(out) > room:
                return None
            if inflater.eof:
                break
    except zlib.error:
        return None
    return bytes(out) if inflater.eof else None


def check_page_count(raw: bytes, claimed: int) -> PageCountVerdict:
    """
    Compare the page leaves in ``raw`` with the ``claimed`` page count.

    Return ``MISMATCH`` when there are more leaves than ``claimed``. Return
    ``UNVERIFIED`` when an object stream cannot be checked within bounds and
    no mismatch was found. Return ``OK`` otherwise.
    """
    if _count_leaves(raw, claimed) > claimed:
        return PageCountVerdict.MISMATCH
    if b"ObjStm" not in raw and b"#" not in raw:
        return PageCountVerdict.OK
    view = memoryview(raw)
    seen: set[int] = set()
    leaves = 0
    in_budget = MAX_OBJSTM_INPUT
    out_budget = MAX_OBJSTM_OUTPUT
    for number, found in enumerate(_OBJSTM.finditer(raw)):
        span = None if number >= MAX_OBJSTM_COUNT else _stream_span(raw, found)
        if span is None:
            return PageCountVerdict.UNVERIFIED
        dictionary, start, end = span
        flate = _is_flate(dictionary)
        if flate is None or start in seen:
            continue
        seen.add(start)
        in_budget -= end - start
        inflated = _inflate(view[start:end], out_budget) if flate else None
        if in_budget < 0 or inflated is None:
            return PageCountVerdict.UNVERIFIED
        out_budget -= len(inflated)
        leaves += _count_leaves(inflated, claimed - leaves)
        if leaves > claimed:
            return PageCountVerdict.MISMATCH
    return PageCountVerdict.OK
