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
* A comment (``%``) between the key and the value of a leaf.
* Leaves in an object stream whose dictionary has no ``ObjStm`` token.

Object streams (PDF 1.5 and later) are found by the word ``ObjStm`` (also as
``Obj#53tm``), not by an exact ``/Type /ObjStm`` key pair. This also covers a
comment between ``/Type`` and ``/ObjStm``. For each word the scan takes the
bytes of the 8 KiB before it up to the next ``>>`` plus ``stream`` plus
CRLF or LF. It does not try to find the exact start of the dictionary,
because a name such as ``/xobj``, a string such as ``(stream)`` or a
``N G obj`` token inside the dictionary can fool such a search. The ``#xx``
escapes of that text are decoded, then the text is checked. The result is
``UNVERIFIED``, never ``OK``, when:

* no stream start follows the word within 8 KiB, the text before the word
  has no ``endobj`` and no ``N G obj`` header, or ``endstream`` is missing;
* the text has more than one ``/Filter`` key, a filter other than one plain
  ``FlateDecode`` (single name or one-item array, no comment), or a
  ``Predictor``, ``DecodeParms`` or ``Crypt`` word (also as ``/Pred#69ctor``);
* the text has no ``/Filter`` but the stream data does not start with two
  integers, so it is not a plain object stream;
* the Flate data is damaged or cut, or a cap is hit.

The 8 KiB text can include the end of the previous object. A ``/Filter``,
``Predictor`` or second ``ObjStm`` word in that part gives a false
``UNVERIFIED``. That is accepted. A hidden page that returns ``OK`` is not.

Caps: at most ``MAX_OBJSTM_COUNT`` streams, ``MAX_OBJSTM_INPUT`` bytes of
compressed input, ``MAX_OBJSTM_OUTPUT`` bytes of inflated output and
``MAX_ESCAPES`` decoded ``#xx`` escapes over all streams. A cap hit gives
``UNVERIFIED``. The scan can flag a file with old page revisions
(incremental update) or the token in stream data. Those cases are flagged,
never hidden.

Cost: every pattern is a single pass over its input and has no nested
repetition, so the work is linear. Each ``ObjStm`` word reads at most 16 KiB
and at most ``MAX_OBJSTM_COUNT`` words are read. Counting stops when the
leaves exceed the claim.
"""

from __future__ import annotations

import re
import zlib
from enum import StrEnum
from itertools import islice

#: Provisional bounds for object stream inflation.
MAX_OBJSTM_COUNT = 256
MAX_OBJSTM_INPUT = 16 * 1024 * 1024
MAX_OBJSTM_OUTPUT = 8 * 1024 * 1024
MAX_ESCAPES = 1 << 16

_CHUNK = 64 * 1024
_DICT_WINDOW = 8192
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
_OBJSTM_WORD = re.compile(_name("ObjStm"))
_OPENER = re.compile(rb">>%s*stream(?:\r\n|\n)" % _WS)
_HEADER = re.compile(
    rb"(?<![^\x00\t\n\f\r ])\d+%s+\d+%s+obj(?=[%s]|\Z)" % (_WS, _WS, _DELIMS)
)
_PLAIN = re.compile(rb"%s*\d+%s+\d+" % (_WS, _WS))
_ESCAPE = re.compile(rb"#([0-9A-Fa-f]{2})")
_FILTER_KEY = re.compile(rb"/Filter(?=[%s]|\Z)" % _DELIMS)
_FLATE = re.compile(
    rb"/Filter%s*(?:/Fl(?:ateDecode)?|\[%s*/Fl(?:ateDecode)?%s*\])(?=[%s]|\Z)"
    % (_WS, _WS, _WS, _DELIMS)
)
_FORBIDDEN = re.compile(rb"Predictor|DecodeParms|Crypt")


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


def _unhex(found: re.Match[bytes]) -> bytes:
    """Return the byte of one ``#xx`` escape."""
    return bytes([int(found[1], 16)])


def _unescape(text: bytes, budget: int) -> tuple[bytes, int] | None:
    """Decode ``#xx`` escapes. Return text and escapes left, or ``None``."""
    out, used = _ESCAPE.subn(_unhex, text, count=budget or 1)
    if used >= (budget or 1):
        return None
    return out, budget - used


def _classify(text: bytes) -> bool | None:
    """Return ``True`` for plain Flate, ``False`` for no filter, else ``None``."""
    keys = list(islice(_FILTER_KEY.finditer(text), 2))
    if not keys:
        return False
    if len(keys) > 1 or _FORBIDDEN.search(text) or _FLATE.search(text) is None:
        return None
    return True


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
    leaves = 0
    streams = 0
    covered = 0
    escapes = MAX_ESCAPES
    in_budget = MAX_OBJSTM_INPUT
    out_budget = MAX_OBJSTM_OUTPUT
    for word in _OBJSTM_WORD.finditer(raw):
        if word.start() < covered:
            continue
        streams += 1
        opener = _OPENER.search(raw, word.start(), word.start() + _DICT_WINDOW)
        if opener is None or streams > MAX_OBJSTM_COUNT:
            return PageCountVerdict.UNVERIFIED
        covered = opener.end()
        low = max(0, word.start() - _DICT_WINDOW)
        region = raw[low:covered]
        if low > 0 and b"endobj" not in region or _HEADER.search(region) is None:
            return PageCountVerdict.UNVERIFIED
        decoded = _unescape(region, escapes)
        if decoded is None:
            return PageCountVerdict.UNVERIFIED
        text, escapes = decoded
        flate = _classify(text)
        if flate is None or (not flate and _PLAIN.match(raw, covered) is None):
            return PageCountVerdict.UNVERIFIED
        if not flate:
            continue
        end = raw.find(b"endstream", covered)
        if end < 0:
            return PageCountVerdict.UNVERIFIED
        in_budget -= end - covered
        inflated = _inflate(view[covered:end], out_budget)
        if in_budget < 0 or inflated is None:
            return PageCountVerdict.UNVERIFIED
        out_budget -= len(inflated)
        leaves += _count_leaves(inflated, claimed - leaves)
        if leaves > claimed:
            return PageCountVerdict.MISMATCH
    return PageCountVerdict.OK
