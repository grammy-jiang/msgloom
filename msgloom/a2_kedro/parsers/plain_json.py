"""
Pure-Python parser for saved JSON and plain-text bodies (P2-02).

The parser reads the exact saved bytes of one component and returns a
frozen :class:`ParseResult`. It uses only the standard library. It never
raises for bad body content. A bad body yields an explicit outcome and
closed, content-free :class:`Limitation` codes.

Outcomes: ``COMPLETE`` (no limitation), ``INCOMPLETE`` (at least one
limitation: truncated or invalid JSON, paging marker, bound hit, invalid
UTF-8, NUL bytes) and ``MISSING`` (zero bytes, only a UTF-8 BOM or only
white space). An empty body is never ``COMPLETE``. Any limitation makes
the result ``INCOMPLETE``, as :class:`ParserReceipt` needs
``limit_hit == "none"`` for ``complete``.

Plain text: the parser splits bytes, never decoded text, so every offset
is a source byte offset. ``CRLF``, ``LF`` and ``CR`` end a line. They are
ASCII and never occur inside a UTF-8 multi-byte sequence, so the split is
safe for invalid UTF-8. A UTF-8 BOM is skipped but still counts in
offsets. A block is a run of non-blank lines. Text is decoded on request
with replacement characters (:meth:`ByteSpan.text`).

JSON: ``json.loads`` with a duplicate-key hook, hooks that reject ``NaN``
and ``Infinity`` and a digit bound on integers. A scan bounds nesting
depth before the decoder runs. The result lists each string, empty string
and ``null`` leaf with its JSON Pointer (RFC 6901). ``null``, an empty
string and a missing key are three outcomes (:class:`FieldState`). A byte
position is not available for JSON; the pointer is the position. A body
that fails at its end is ``TRUNCATED_JSON``. A non-empty root
``@odata.nextLink`` or ``"truncated": true`` is ``PAGING_MARKER``.

PII: ``repr`` of every result type shows no text, key or value.
Limitation codes and error messages are fixed text.

Determinism: the same bytes give an equal result.

CANDIDATE/RESEARCH, PROVISIONAL: bounds and limitation names are not
frozen. See ``docs/notes/a2-v2-parser-p2-02.md``.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal

from msgloom.a2_kedro.contracts.codec import A2ContractError, sha256_hex
from msgloom.a2_kedro.contracts.parse import ParserReceipt

WORKER = "msgloom.a2_kedro.parsers.plain_json"

#: Provisional bounds. They are parser decisions, not production limits.
MAX_BODY_BYTES = 8 * 1024 * 1024
MAX_JSON_DEPTH = 64
MAX_INT_DIGITS = 64
MAX_JSON_FIELDS = 10_000
MAX_LINES = 200_000

#: Root keys that mark a page of a larger response.
PAGING_KEYS: tuple[str, ...] = ("@odata.nextLink", "nextPageToken")
TRUNCATED_KEY = "truncated"

_UTF8_BOM = b"\xef\xbb\xbf"
_WIDE_BOMS = (b"\xff\xfe", b"\xfe\xff", b"\x00\x00\xfe\xff")
_EOL = re.compile(rb"\r\n|\n|\r")
_NESTING = re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*(?:"|\Z)|[\[\]{}]', re.DOTALL)
_INDEX = re.compile(r"0|[1-9][0-9]*")


class PlainJsonInputError(A2ContractError):
    """Raised for caller misuse. The message is fixed and has no content."""


class Outcome(StrEnum):
    """Closed result of one parse."""

    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    MISSING = "missing"


class Limitation(StrEnum):
    """Closed, content-free reasons that a result is not complete."""

    EMPTY_BODY = "empty_body"
    SIZE_LIMIT = "size_limit"
    UNSUPPORTED_ENCODING = "unsupported_encoding"
    INVALID_UTF8 = "invalid_utf8"
    NUL_BYTES = "nul_bytes"
    LINE_LIMIT = "line_limit"
    TRUNCATED_JSON = "truncated_json"
    INVALID_JSON = "invalid_json"
    DEPTH_LIMIT = "depth_limit"
    DUPLICATE_KEY = "duplicate_key"
    NON_FINITE_NUMBER = "non_finite_number"
    HUGE_INTEGER = "huge_integer"
    LONE_SURROGATE = "lone_surrogate"
    FIELD_LIMIT = "field_limit"
    PAGING_MARKER = "paging_marker"


class FieldState(StrEnum):
    """Outcome of one JSON field: three different states and two more."""

    TEXT = "text"
    EMPTY = "empty"
    NULL = "null"
    MISSING = "missing"
    OTHER = "other"


LineEnding = Literal["lf", "crlf", "cr", "none"]
_ENDINGS: dict[bytes, LineEnding] = {b"\n": "lf", b"\r\n": "crlf", b"\r": "cr"}


@dataclass(frozen=True, slots=True)
class ByteSpan:
    """A byte window ``[offset, offset + length)`` of the source bytes."""

    offset: int
    length: int

    def slice(self, source: bytes) -> bytes:
        """Return the exact source bytes of this span."""
        return source[self.offset : self.offset + self.length]

    def text(self, source: bytes) -> str:
        """Return the span decoded as UTF-8 with replacement characters."""
        return self.slice(source).decode("utf-8", "replace")

    def __repr__(self) -> str:
        return f"ByteSpan({self.offset}, {self.length})"


@dataclass(frozen=True, slots=True)
class TextLine:
    """One line: its content span (no terminator) and its terminator."""

    index: int
    span: ByteSpan
    ending: LineEnding


@dataclass(frozen=True, slots=True)
class TextBlock:
    """A paragraph block. The span ends at the last content byte."""

    index: int
    span: ByteSpan
    first_line: int
    line_count: int


@dataclass(frozen=True, slots=True)
class JsonField:
    """A text, empty-string or null leaf. ``repr`` hides pointer and value."""

    pointer: str = field(repr=False)
    state: FieldState
    value: str | None = field(repr=False)


@dataclass(frozen=True, slots=True)
class FieldLookup:
    """Answer of :meth:`ParseResult.lookup`. ``repr`` hides the value."""

    state: FieldState
    value: str | None = field(repr=False)


@dataclass(frozen=True, slots=True)
class ParseResult:
    """
    Result of one parse of one saved body.

    ``lines`` and ``blocks`` fill for plain text. ``fields`` fills for
    JSON. ``limitations`` is unique and in declaration order of
    :class:`Limitation`. ``repr`` carries counts only.
    """

    format: Literal["json", "plain_text"]
    outcome: Outcome
    limitations: tuple[Limitation, ...]
    input_bytes: int
    input_sha256: str
    bom: bool = False
    lines: tuple[TextLine, ...] = field(default=(), repr=False)
    blocks: tuple[TextBlock, ...] = field(default=(), repr=False)
    fields: tuple[JsonField, ...] = field(default=(), repr=False)
    parsed: bool = field(default=False, repr=False)
    document: Any = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        return (
            f"ParseResult({self.format}, {self.outcome.value}, "
            f"limitations={len(self.limitations)}, bytes={self.input_bytes}, "
            f"lines={len(self.lines)}, blocks={len(self.blocks)}, "
            f"fields={len(self.fields)})"
        )

    def lookup(self, pointer: str) -> FieldLookup:
        """
        Return the state of the JSON Pointer ``pointer``.

        Raise :exc:`PlainJsonInputError` when the pointer is malformed or
        when no JSON document was parsed. A missing key is answered only
        when a document exists, so ``MISSING`` is never a guess.
        """
        if self.format != "json" or not self.parsed:
            raise PlainJsonInputError("no parsed JSON document")
        if pointer and not pointer.startswith("/"):
            raise PlainJsonInputError("malformed JSON pointer")
        node: Any = self.document
        for raw in pointer.split("/")[1:] if pointer else ():
            token = raw.replace("~1", "/").replace("~0", "~")
            if isinstance(node, dict) and token in node:
                node = node[token]
            elif isinstance(node, list) and _INDEX.fullmatch(token):
                if int(token) >= len(node):
                    return FieldLookup(FieldState.MISSING, None)
                node = node[int(token)]
            else:
                return FieldLookup(FieldState.MISSING, None)
        return _classify(node)

    def to_receipt(self, worker_version: str) -> ParserReceipt | None:
        """
        Return the parser receipt, or ``None`` for a ``MISSING`` body.

        ``limit_hit`` has no value for malformed input, so every
        limitation maps to ``"bytes"``. :attr:`limitations` keeps the reason.
        """
        if self.outcome is Outcome.MISSING:
            return None
        complete = self.outcome is Outcome.COMPLETE
        return ParserReceipt(
            worker=WORKER,
            worker_version=worker_version,
            outcome="complete" if complete else "partial",
            limit_hit="none" if complete else "bytes",
            input_bytes=self.input_bytes,
            part_count=1,
        )


def _classify(node: Any) -> FieldLookup:
    if node is None:
        return FieldLookup(FieldState.NULL, None)
    if isinstance(node, str):
        return FieldLookup(FieldState.TEXT if node else FieldState.EMPTY, node)
    return FieldLookup(FieldState.OTHER, None)


def _as_bytes(data: object) -> bytes:
    if isinstance(data, (bytes, bytearray, memoryview)):
        return bytes(data)
    raise PlainJsonInputError("body must be bytes")


def _finish(
    fmt: Literal["json", "plain_text"],
    raw: bytes,
    found: set[Limitation],
    **parts: Any,
) -> ParseResult:
    if Limitation.EMPTY_BODY in found:
        outcome = Outcome.MISSING
    else:
        outcome = Outcome.INCOMPLETE if found else Outcome.COMPLETE
    return ParseResult(
        format=fmt,
        outcome=outcome,
        limitations=tuple(item for item in Limitation if item in found),
        input_bytes=len(raw),
        input_sha256=sha256_hex(raw),
        bom=raw.startswith(_UTF8_BOM),
        **parts,
    )


def _payload_start(raw: bytes, found: set[Limitation]) -> int | None:
    """Return the first payload byte, or ``None`` when parsing must stop."""
    if len(raw) > MAX_BODY_BYTES:
        found.add(Limitation.SIZE_LIMIT)
        return None
    if raw.startswith(_WIDE_BOMS):
        found.add(Limitation.UNSUPPORTED_ENCODING)
        return None
    start = len(_UTF8_BOM) if raw.startswith(_UTF8_BOM) else 0
    if not raw[start:].strip():
        found.add(Limitation.EMPTY_BODY)
        return None
    return start


def parse_plain_text(data: bytes) -> ParseResult:
    """Split saved plain-text bytes into lines and paragraph blocks."""
    raw = _as_bytes(data)
    found: set[Limitation] = set()
    start = _payload_start(raw, found)
    if start is None:
        return _finish("plain_text", raw, found)
    if b"\x00" in raw:
        found.add(Limitation.NUL_BYTES)
    try:
        raw[start:].decode("utf-8")
    except UnicodeDecodeError:
        found.add(Limitation.INVALID_UTF8)
    lines, overflow = _split_lines(raw, start)
    if overflow:
        found.add(Limitation.LINE_LIMIT)
    return _finish("plain_text", raw, found, lines=lines, blocks=_blocks(raw, lines))


def _split_lines(raw: bytes, start: int) -> tuple[tuple[TextLine, ...], bool]:
    lines: list[TextLine] = []
    pos = start
    for match in _EOL.finditer(raw, start):
        if len(lines) >= MAX_LINES:
            return tuple(lines), True
        span = ByteSpan(pos, match.start() - pos)
        lines.append(TextLine(len(lines), span, _ENDINGS[match.group()]))
        pos = match.end()
    if pos < len(raw):
        if len(lines) >= MAX_LINES:
            return tuple(lines), True
        lines.append(TextLine(len(lines), ByteSpan(pos, len(raw) - pos), "none"))
    return tuple(lines), False


def _blocks(raw: bytes, lines: tuple[TextLine, ...]) -> tuple[TextBlock, ...]:
    blocks: list[TextBlock] = []
    first = -1
    for line in lines:
        if line.span.slice(raw).strip():
            first = line.index if first < 0 else first
            continue
        if first >= 0:
            blocks.append(_block(lines, len(blocks), first, line.index - 1))
            first = -1
    if first >= 0:
        blocks.append(_block(lines, len(blocks), first, len(lines) - 1))
    return tuple(blocks)


def _block(lines: tuple[TextLine, ...], index: int, first: int, last: int) -> TextBlock:
    start = lines[first].span.offset
    end = lines[last].span.offset + lines[last].span.length
    return TextBlock(index, ByteSpan(start, end - start), first, last - first + 1)


#: Placeholder for an integer with too many digits.
_HUGE = object()


class _State:
    """Per-call flags set by the decoder hooks."""

    def __init__(self) -> None:
        self.duplicate = False
        self.huge = False
        self.non_finite = False

    def pairs(self, pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                self.duplicate = True
            result[key] = value
        return result

    def integer(self, text: str) -> Any:
        if len(text) > MAX_INT_DIGITS:
            self.huge = True
            return _HUGE
        return int(text)

    def real(self, text: str) -> float:
        value = float(text)
        if not math.isfinite(value):
            self.non_finite = True
        return value

    def constant(self, _name: str) -> float:
        self.non_finite = True
        return math.nan


def _too_deep(text: str) -> bool:
    depth = 0
    for match in _NESTING.finditer(text):
        token = match.group()
        if token in "[{":
            depth += 1
            if depth > MAX_JSON_DEPTH:
                return True
        elif token in "]}":
            depth = max(depth - 1, 0)
    return False


def parse_json(data: bytes) -> ParseResult:
    """
    Parse saved JSON bytes into text-bearing fields with JSON Pointers.

    Fields are listed in document order. A body that is not one complete,
    valid JSON value yields no fields and no document.
    """
    raw = _as_bytes(data)
    found: set[Limitation] = set()
    start = _payload_start(raw, found)
    if start is None:
        return _finish("json", raw, found)
    try:
        text = raw[start:].decode("utf-8")
    except UnicodeDecodeError:
        found.add(Limitation.INVALID_UTF8)
        return _finish("json", raw, found)
    if _too_deep(text):
        found.add(Limitation.DEPTH_LIMIT)
        return _finish("json", raw, found)
    state = _State()
    try:
        document = json.loads(
            text,
            object_pairs_hook=state.pairs,
            parse_int=state.integer,
            parse_float=state.real,
            parse_constant=state.constant,
        )
    except json.JSONDecodeError as error:
        cut = error.pos >= len(text.rstrip()) or error.msg.startswith("Unterminated")
        found.add(Limitation.TRUNCATED_JSON if cut else Limitation.INVALID_JSON)
        return _finish("json", raw, found)
    except RecursionError:
        found.add(Limitation.DEPTH_LIMIT)
        return _finish("json", raw, found)
    if state.duplicate:
        found.add(Limitation.DUPLICATE_KEY)
    if state.non_finite:
        found.add(Limitation.NON_FINITE_NUMBER)
    if state.duplicate or state.non_finite:
        return _finish("json", raw, found)
    if state.huge:
        found.add(Limitation.HUGE_INTEGER)
    if _has_paging_marker(document):
        found.add(Limitation.PAGING_MARKER)
    fields, overflow, surrogate = _collect_fields(document)
    if overflow:
        found.add(Limitation.FIELD_LIMIT)
    if surrogate:
        found.add(Limitation.LONE_SURROGATE)
    return _finish("json", raw, found, fields=fields, parsed=True, document=document)


def _has_paging_marker(document: Any) -> bool:
    if not isinstance(document, dict):
        return False
    marks = (document.get(key) for key in PAGING_KEYS)
    return document.get(TRUNCATED_KEY) is True or any(
        isinstance(mark, str) and mark for mark in marks
    )


def _escape(key: str) -> str:
    return key.replace("~", "~0").replace("/", "~1")


def _collect_fields(document: Any) -> tuple[tuple[JsonField, ...], bool, bool]:
    fields: list[JsonField] = []
    surrogate = False
    stack: list[tuple[str, Any]] = [("", document)]
    while stack:
        pointer, node = stack.pop()
        if isinstance(node, dict):
            stack.extend(
                (f"{pointer}/{_escape(key)}", node[key]) for key in reversed(list(node))
            )
            continue
        if isinstance(node, list):
            stack.extend(
                (f"{pointer}/{index}", node[index])
                for index in range(len(node) - 1, -1, -1)
            )
            continue
        if node is not None and not isinstance(node, str):
            continue
        if len(fields) >= MAX_JSON_FIELDS:
            return tuple(fields), True, surrogate
        value = node
        if value is not None and not value.isascii():
            clean = value.encode("utf-8", "replace").decode("utf-8")
            surrogate = surrogate or clean != value
            value = clean
        fields.append(JsonField(pointer, _classify(value).state, value))
    return tuple(fields), False, surrogate
