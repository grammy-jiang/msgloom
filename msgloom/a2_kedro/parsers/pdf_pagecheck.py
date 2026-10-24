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

* the place is ambiguous: no stream start within 8 KiB after the word, no
  ``N G obj`` header in the 8 KiB before it (also when the window cut the
  header off), no ``endobj`` before that header in a cut window, a ``%`` in
  the header line, unbalanced ``(`` and ``)`` between the header and the
  stream start, or a second ``>>`` plus ``stream`` opener before the first
  ``endstream``. The header is the last ``N G obj`` before the word;
* ``endstream`` is missing;
* the text has more than one ``/Filter`` key, a filter other than one plain
  ``FlateDecode`` (single name or one-item array, no comment), or a
  ``Predictor``, ``DecodeParms`` or ``Crypt`` word (also as ``/Pred#69ctor``);
* the text has no ``/Filter`` but the stream is not a real object stream: the
  dictionary needs exactly one integer ``/N`` and ``/First`` (``/First`` at
  most 64 KiB) and the first ``/First`` bytes of data need exactly ``N``
  pairs of integers with strictly increasing offsets. Data that passes is
  plain bytes, and the raw scan counts its leaves;
* the Flate data is damaged or cut, or a cap is hit.

Still not detected: a filter (or any other key) that sits before the header
or outside the 8 KiB window, with a dictionary that is well formed in every
check above, for example a string or comment trick that this scan does not
recognize (a ``%`` in the header line and unbalanced parentheses are the only
ones checked). A filtered stream that is not Flate is never read, so the scan
only refuses it when the filter is in the window.

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
from collections import deque
from enum import StrEnum
from itertools import islice, pairwise

#: Provisional bounds for object stream inflation.
MAX_OBJSTM_COUNT = 256
MAX_OBJSTM_INPUT = 16 * 1024 * 1024
MAX_OBJSTM_OUTPUT = 8 * 1024 * 1024
MAX_ESCAPES = 1 << 16

_CHUNK = 64 * 1024
_DICT_WINDOW = 8192
_MAX_FIRST = 64 * 1024
_MAX_DIGITS = 18
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
_STRING_TOKEN = re.compile(rb"\\.|[()]", re.DOTALL)
_KEY_N = re.compile(rb"/N%s+(\d+)(?=[%s]|\Z)" % (_WS, _DELIMS))
_KEY_FIRST = re.compile(rb"/First%s+(\d+)(?=[%s]|\Z)" % (_WS, _DELIMS))
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


def _strings_balanced(text: bytes) -> bool:
    """Return ``True`` when the ``(`` and ``)`` in ``text`` pair up."""
    depth = 0
    for token in _STRING_TOKEN.finditer(text):
        mark = token[0]
        if mark == b"(":
            depth += 1
        elif mark == b")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _locate(raw: bytes, start: int) -> tuple[int, int, int] | None:
    """
    Return ``(low, header, data)`` for the ``ObjStm`` word at ``start``.

    ``header`` is the start of the last ``N G obj`` before the word and
    ``data`` the end of the first stream opener. Return ``None`` when the
    place is ambiguous: no opener or header, no ``endobj`` before the header
    in a cut window, a ``%`` in the header line, unbalanced parentheses
    between header and opener, or more than one opener before the first ``endstream``.
    """
    end = start + _DICT_WINDOW
    low = max(0, start - _DICT_WINDOW)
    opener = _OPENER.search(raw, start, end)
    headers = deque(_HEADER.finditer(raw, low, start), maxlen=1)
    if opener is None or not headers:
        return None
    header = headers[0]
    at = header.start()
    line = max(raw.rfind(b"\n", low, at), raw.rfind(b"\r", low, at)) + 1
    if low > 0 and b"endobj" not in raw[low:at]:
        return None
    if b"%" in raw[max(line, low) : at]:
        return None
    if not _strings_balanced(raw[at : opener.start()]):
        return None
    stop = raw.find(b"endstream", opener.end(), end)
    if len(list(islice(_OPENER.finditer(raw, at, stop if stop > 0 else end), 2))) > 1:
        return None
    return low, at, opener.end()


def _is_objstm_header(raw: bytes, at: int, data: int) -> bool:
    """Return ``True`` when the stream at ``data`` has a real ObjStm header."""
    text = _ESCAPE.sub(_unhex, raw[at:data])
    counts = _KEY_N.findall(text)
    firsts = _KEY_FIRST.findall(text)
    if len(counts) != 1 or len(firsts) != 1:
        return False
    count, first = int(counts[0]), int(firsts[0])
    if len(counts[0]) > _MAX_DIGITS or len(firsts[0]) > _MAX_DIGITS:
        return False
    if count < 1 or first > _MAX_FIRST or count > first:
        return False
    tokens = raw[data : data + first].split()
    if len(tokens) != 2 * count or not all(
        t.isdigit() and len(t) <= _MAX_DIGITS for t in tokens
    ):
        return False
    offsets = [int(t) for t in tokens[1::2]]
    return all(a < b for a, b in pairwise(offsets))


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
        place = _locate(raw, word.start()) if streams <= MAX_OBJSTM_COUNT else None
        if place is None:
            return PageCountVerdict.UNVERIFIED
        low, header, covered = place
        decoded = _unescape(raw[low:covered], escapes)
        if decoded is None:
            return PageCountVerdict.UNVERIFIED
        text, escapes = decoded
        flate = _classify(text)
        if flate is None:
            return PageCountVerdict.UNVERIFIED
        if not flate and not _is_objstm_header(raw, header, covered):
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
