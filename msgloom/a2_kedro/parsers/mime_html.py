"""
Pure-Python MIME and HTML parser for saved raw message bytes (P2-01).

:func:`parse_mime` turns the bytes of one saved component into a
:class:`~msgloom.a2_kedro.parsers.MimeParseResult`: ordered
:class:`~msgloom.a2_kedro.parsers.MimePart` records and, when a part is
representable, a ``ParsedParts`` record that reuses the C0-04 wire models.

Traceability: the stdlib ``email`` package reports no byte offsets. This
module scans the structure itself and uses ``email`` only to read header
blocks. Every part keeps a byte window, so ``data[part.start:part.end]``
is its exact source. The root path is ``1``; children are ``1.1``,
``1.2`` and so on in source order. A ``message/rfc822`` part holds its
inner message as ``.1``. A path is the ``part_id`` of the wire record.

Limitations: an unknown charset, an undecodable byte, bad base64 or
quoted-printable, an unknown transfer encoding, a malformed or truncated
multipart, an empty, oversize or unrepresentable part, and an oversize
input each create a ``Limitation``. Its detail is a part path, never
content. The part stays in the result. Any limitation makes the status
INCOMPLETE. A message with no usable text body gets
``body_status="missing"`` and the ``body_absent`` limitation.

Bounds: the ``MAX_*`` constants cap work and memory. A part over its cap is
listed with its window and is not decoded.

Text: HTML goes through :class:`html.parser.HTMLParser`. Script, style,
template and title content is dropped. Attributes are never read, so
nothing is fetched. ``text_map`` maps text ranges to character ranges of
the decoded part body. The part window is the exact byte link. A line that
starts with ``>`` and an HTML ``blockquote`` become ``QuotedRegion``
records; text is never removed.

Failure handling: ``parse_mime`` never raises for message content. It
raises :exc:`A2ContractError`, with a fixed message, for a wrong argument
type. Same bytes and component ID give an equal result.

CANDIDATE/RESEARCH, PROVISIONAL: limits and limitation codes are not
frozen. See ``docs/notes/a2-v2-parser-p2-01.md``.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from email.message import Message
from email.parser import BytesHeaderParser
from html.parser import HTMLParser
from typing import Literal, NamedTuple

from msgloom.a2_kedro.contracts.codec import A2ContractError, sha256_hex
from msgloom.a2_kedro.contracts.extract import ComponentStatus
from msgloom.a2_kedro.contracts.parse import (
    MAX_PARTS,
    ByteLink,
    ParsedParts,
    ParserReceipt,
    Part,
    PartFormat,
    PartRole,
)
from msgloom.a2_kedro.parsers import (
    MAX_MAP_ITEMS,
    MimeParseResult,
    MimePart,
    QuotedRegion,
    TextSpan,
    decode_text,
    decode_transfer,
    marker_regions,
    split_multipart,
)
from msgloom.contracts import Limitation, TerminalStatus

WORKER = "msgloom.a2-mime-html"
WORKER_VERSION = "1"

#: Provisional bounds.
MAX_INPUT_BYTES = 64 * 1024 * 1024
MAX_PART_BYTES = 8 * 1024 * 1024
MAX_HEADER_BYTES = 64 * 1024
MAX_DEPTH = 16

_FORMATS: dict[str, PartFormat] = {
    "text/plain": "plain_text",
    "text/html": "html",
    "text/csv": "csv",
    "message/rfc822": "rfc822",
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
}
_BODY_TYPES = frozenset({"text/plain", "text/html"})
_SKIPPED = frozenset({"script", "style", "template", "title"})
_BLOCKS = frozenset(
    ("p", "div", "br", "li", "ul", "ol", "tr", "table", "blockquote", "pre", "hr")
    + ("section", "article", "header", "footer", "h1", "h2", "h3", "h4", "h5", "h6")
)
_HEADER_END = re.compile(rb"\r?\n\r?\n")
_SPACE = re.compile(r"\s+")


class _Reducer(HTMLParser):
    """Reduce HTML to text and record where each text piece came from."""

    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=False)
        self._source = source
        self._line, self._line_at = 1, 0
        self._pieces: list[str] = []
        self._size = 0
        self._tail = ""
        self._skip: str | None = None
        self._skip_depth = 0
        self._open: list[int] | None = None
        self._spans: list[list[int]] = []
        self._quotes: list[int] = []
        self.regions: list[QuotedRegion] = []
        self.truncated = False
        self.unclosed = False

    def _event(self) -> int:
        line, col = self.getpos()
        while self._line < line:
            self._line_at = self._source.index("\n", self._line_at) + 1
            self._line += 1
        pos = self._line_at + col
        if self._open is not None:
            self._open[3] = pos
            self._open = None
        return pos

    def _put(self, text: str, pos: int) -> None:
        if not text:
            return
        entry = [self._size, self._size + len(text), pos, len(self._source)]
        self._pieces.append(text)
        self._size += len(text)
        self._tail = text[-1]
        if len(self._spans) >= MAX_MAP_ITEMS:
            self.truncated = True
            return
        self._spans.append(entry)
        self._open = entry

    def _break(self, pos: int) -> None:
        if self._tail not in ("", "\n"):
            self._put("\n", pos)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        pos = self._event()
        if self._skip is None and tag in _SKIPPED:
            self._skip, self._skip_depth = tag, 1
        elif tag == self._skip:
            self._skip_depth += 1
        if tag in _BLOCKS and self._skip is None:
            self._break(pos)
        if tag == "blockquote":
            self._quotes.append(self._size)

    def handle_endtag(self, tag: str) -> None:
        pos = self._event()
        if tag == self._skip:
            self._skip_depth -= 1
            if self._skip_depth == 0:
                self._skip = None
            return
        if tag in _BLOCKS and self._skip is None:
            self._break(pos)
        if tag == "blockquote" and self._quotes:
            self._close_quote()

    def _close_quote(self) -> None:
        depth = len(self._quotes)
        begin = self._quotes.pop()
        if len(self.regions) < MAX_MAP_ITEMS:
            self.regions.append(QuotedRegion(begin, self._size, depth, "blockquote"))
        else:
            self.truncated = True

    def handle_data(self, data: str) -> None:
        pos = self._event()
        if self._skip is not None:
            return
        text = _SPACE.sub(" ", data)
        if self._tail in ("", " ", "\n"):
            text = text.lstrip(" ")
        self._put(text, pos)

    def handle_entityref(self, name: str) -> None:
        self.handle_data(html.unescape(f"&{name};"))

    def handle_charref(self, name: str) -> None:
        self.handle_data(html.unescape(f"&#{name};"))

    def finish(self) -> tuple[str, tuple[TextSpan, ...], tuple[QuotedRegion, ...]]:
        """Close the parser and return text, text map and quote regions."""
        self.close()
        self._event()
        self.unclosed = self._skip is not None
        while self._quotes:
            self._close_quote()
        spans = tuple(TextSpan(*entry) for entry in self._spans)
        return "".join(self._pieces), spans, tuple(self.regions)


@dataclass(slots=True)
class _Scan:
    """Mutable state of one parse run."""

    data: bytes
    parts: list[MimePart] = field(default_factory=list)
    limits: set[tuple[str, str]] = field(default_factory=set)
    limit_hit: Literal["none", "bytes", "parts"] = "none"
    body_seen: bool = False


def _split_head(data: bytes, start: int, end: int) -> tuple[int, int]:
    """Return ``(header_end, body_start)`` of the entity in ``data``."""
    if data.startswith((b"\r\n", b"\n"), start, end):
        return start, start + (2 if data.startswith(b"\r\n", start) else 1)
    if match := _HEADER_END.search(data, start, end):
        return match.start(), match.end()
    return end, end


def _role(
    scan: _Scan,
    kind: str,
    ptype: str,
    forced: PartRole | None,
    info: tuple[str | None, bool, bool],
) -> PartRole:
    if forced is not None:
        return forced
    disposition, named, has_cid = info
    if disposition == "attachment":
        return "attachment"
    if kind.startswith("multipart/"):
        return "body"
    if kind == "message/rfc822":
        return "embedded"
    if kind in _BODY_TYPES and not named:
        first, scan.body_seen = not scan.body_seen, True
        return "body" if first or ptype != "multipart/alternative" else "alternate"
    if kind.startswith("text/") and not named:
        return "attachment"
    if ptype == "multipart/related" or has_cid:
        return "embedded"
    return "attachment"


def _leaf(
    scan: _Scan, begin: int, end: int, kind: str, msg: Message, flags: set[str]
) -> str | None:
    """Check the transfer encoding; return decoded text for body types."""
    if end - begin > MAX_PART_BYTES:
        flags.add("part_too_large")
        scan.limit_hit = "bytes"
        return None
    encoding = str(msg.get("content-transfer-encoding", "")).strip().lower()
    raw = decode_transfer(scan.data[begin:end], encoding, flags)
    if kind not in _BODY_TYPES:
        return None
    return decode_text(raw, msg.get_content_charset(), flags)


def _reduce(
    kind: str, text: str, flags: set[str]
) -> tuple[str, tuple[TextSpan, ...], tuple[QuotedRegion, ...]]:
    """Return ``(text, text_map, quoted)`` for a decoded body."""
    mapping: tuple[TextSpan, ...]
    regions: list[QuotedRegion] = []
    if kind == "text/html":
        reducer = _Reducer(text)
        try:
            reducer.feed(text)
            text, mapping, found = reducer.finish()
        except Exception:  # noqa: BLE001 - HTMLParser must not end the run
            flags.add("html_parse_error")
            return "", (), ()
        regions.extend(found)
        if reducer.truncated:
            flags.add("map_truncated")
        if reducer.unclosed:
            flags.add("html_parse_error")  # skipped element never closed
    else:
        mapping = (TextSpan(0, len(text), 0, len(text)),) if text else ()
    found_marks, cut = marker_regions(text)
    if cut:
        flags.add("map_truncated")
    regions.extend(found_marks)
    regions.sort(key=lambda r: (r.start, -r.end, r.kind))
    return text, mapping, tuple(regions)


class _Site(NamedTuple):
    """Where an entity sits: path, parent, depth and inherited context."""

    path: str
    parent: str | None
    depth: int
    dtype: str
    forced: PartRole | None
    ptype: str


def _format(kind: str) -> PartFormat | None:
    if kind.startswith(("multipart/", "image/")):
        return "rfc822" if kind.startswith("multipart/") else "image"
    return _FORMATS.get(kind)


def _entity(scan: _Scan, start: int, end: int, site: _Site) -> None:
    """Scan one entity, append its part, then recurse into children."""
    path = site.path
    if len(scan.parts) >= MAX_PARTS:
        scan.limit_hit = "parts"
        scan.limits.add(("part_limit", path))
        return
    flags: set[str] = set()
    head_end, body = _split_head(scan.data, start, end)
    if head_end - start > MAX_HEADER_BYTES:
        flags.add("header_too_large")
    header = scan.data[start : min(head_end, start + MAX_HEADER_BYTES)]
    msg = BytesHeaderParser().parsebytes(header)
    msg.set_default_type(site.dtype)
    kind = msg.get_content_type()
    disposition = msg.get_content_disposition()
    info = (disposition, bool(msg.get_filename()), msg["content-id"] is not None)
    role = _role(scan, kind, site.ptype, site.forced, info)
    if end <= start:
        flags.add("part_empty")
    deep = site.depth >= MAX_DEPTH
    container = kind.startswith("multipart/") and not deep
    inner = kind == "message/rfc822" and not deep and body < end
    if (
        deep
        and kind in ("message/rfc822", "multipart/mixed")
        or (deep and kind.startswith("multipart/"))
    ):
        flags.add("depth_limit")
        scan.limit_hit = "parts"
    children: list[tuple[int, int]] = []
    if container:
        raw = msg.get_boundary()
        problems = ("multipart_malformed",)
        if raw:
            wire = raw.encode("utf-8", "surrogateescape")
            children, problems = split_multipart(scan.data, body, end, wire)
        flags.update(problems)
    text, mapping, quoted = None, (), ()
    leaf = None if container or inner or end <= body else (body, end)
    if leaf and (text := _leaf(scan, *leaf, kind, msg, flags)) is not None:
        text, mapping, quoted = _reduce(kind, text, flags)
    fmt = _format(kind)
    if fmt is None:
        flags.add("attachment_unsupported" if role != "body" else "part_unsupported")
    scan.parts.append(
        MimePart(path, site.parent, kind, msg.get_content_charset(), disposition, role,
                 fmt, start, end, body, tuple(sorted(flags)), text, mapping, quoted)
    )  # fmt: skip
    scan.limits.update((code, path) for code in flags)
    child_forced = site.forced
    if role == "attachment" or (role == "embedded" and kind == "message/rfc822"):
        child_forced = site.forced or role
    ctype = "message/rfc822" if kind == "multipart/digest" else "text/plain"
    depth = site.depth + 1
    if inner:
        _entity(
            scan,
            body,
            end,
            _Site(f"{path}.1", path, depth, "text/plain", child_forced, kind),
        )
    for number, (low, high) in enumerate(children, 1):
        _entity(
            scan,
            low,
            high,
            _Site(f"{path}.{number}", path, depth, ctype, child_forced, kind),
        )


def _body_status(parts: list[MimePart]) -> ComponentStatus:
    cands = [
        p
        for p in parts
        if p.role in ("body", "alternate") and p.content_type in _BODY_TYPES
    ]
    if any(p.text is not None and p.text.strip() for p in cands):
        return "present"
    big = any("part_too_large" in p.flags for p in cands)
    return "partial" if big else "missing"


def _wire(scan: _Scan, size: int, digest: str, component_id: str) -> ParsedParts | None:
    """Build the C0-04 record from representable parts; ``None`` if none."""
    wired = [p for p in scan.parts if p.format is not None and p.end > p.start]
    if not wired:
        return None
    paths = {p.path for p in wired}
    parts = tuple(
        Part(
            part_id=p.path,
            role=p.role,
            declared_format=p.format,
            detected_format=p.format,
            link=ByteLink(
                component_id=component_id,
                component_sha256=digest,
                component_size=size,
                offset=p.start,
                length=p.end - p.start,
            ),
            parent_part_id=p.parent if p.parent in paths else None,
        )
        for p in wired
        if p.format is not None
    )
    receipt = ParserReceipt(
        worker=WORKER,
        worker_version=WORKER_VERSION,
        # C0-04 ties outcome to limit_hit; content defects stay limitations.
        outcome="complete" if scan.limit_hit == "none" else "partial",
        limit_hit=scan.limit_hit,
        input_bytes=size,
        part_count=len(parts),
    )
    return ParsedParts(parts=parts, receipt=receipt)


def parse_mime(data: bytes, *, component_id: str = "primary") -> MimeParseResult:
    """
    Parse saved raw message bytes into ordered parts with byte windows.

    ``component_id`` names the saved component in every byte link. The
    function does not raise for any content of ``data``. A zero-byte input
    or a message without a usable body gets ``body_status="missing"`` and
    the ``body_absent`` limitation. See the module docstring for the rest.
    """
    if not isinstance(data, bytes | bytearray | memoryview):
        raise A2ContractError("input must be bytes")
    if not isinstance(component_id, str) or not component_id:
        raise A2ContractError("component id must be non-empty text")
    raw = bytes(data)
    scan = _Scan(raw)
    digest, size = sha256_hex(raw), len(raw)
    if size == 0:
        scan.limits.add(("input_empty", "1"))
    elif size > MAX_INPUT_BYTES:
        scan.limit_hit = "bytes"
        scan.limits.add(("input_too_large", "1"))
        scan.parts.append(
            MimePart(
                "1", None, "message/rfc822", None, None, "body", "rfc822", 0, size, size
            )
        )
    else:
        try:
            _entity(scan, 0, size, _Site("1", None, 0, "text/plain", None, ""))
        except Exception:  # noqa: BLE001 - content must not end the run
            scan.limits.add(("parser_error", "1"))
    body = "partial" if size > MAX_INPUT_BYTES else _body_status(scan.parts)
    if body == "missing":
        scan.limits.add(("body_absent", "1"))
    try:
        parsed = _wire(scan, size, digest, component_id)
    except ValueError:
        scan.limits.add(("contract_rejected", "1"))
        parsed = None
    limits = tuple(Limitation(code, detail) for code, detail in sorted(scan.limits))
    status = TerminalStatus.INCOMPLETE if limits else TerminalStatus.COMPLETE
    return MimeParseResult(
        status, body, limits, tuple(scan.parts), parsed, size, digest
    )
