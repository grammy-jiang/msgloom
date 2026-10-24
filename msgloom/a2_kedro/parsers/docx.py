"""
Safe DOCX parser for saved component bytes (P2-04).

The parser reads ``word/document.xml`` of the saved zip package with
:mod:`zipfile` and :mod:`defusedxml`, so body order is exact. It returns
a frozen :class:`DocxResult`. It never raises for document content. A
non-bytes argument raises :exc:`DocxInputError` with a fixed message.

Status: ``COMPLETE`` means every body paragraph and table cell was read
and nothing was skipped. The result refuses ``COMPLETE`` with a limitation
or unsupported item. ``INCOMPLETE`` means content was skipped or a bound
was hit; blocks read before the bound stay. ``FAILED`` means no usable
document (the first nine :class:`DocxLimit` members). It holds no block.

Blocks: each ``w:p`` and ``w:tbl`` child of ``w:body`` takes the next body
index; ``w:sdt`` and ``w:customXml`` are transparent. A table cell is one
block that joins its direct paragraphs with a newline. Nested tables follow
their cell. IDs depend on structure only: ``b{i}``, ``b{i}/r{row}c{col}``
and ``b{i}/r{row}c{col}/{k}/r{row}c{col}``.

Tracked changes: the parser reads the final view. Inserted text is read.
Deleted text, rows (``w:trPr/w:del``) and cells (``w:tcPr/w:cellDel``)
are skipped and recorded as ``tracked_deletion``. Inline ``w:sym`` and
``w:ptab`` and unknown table children are recorded as ``unknown_block``.
Helpers live in ``docx_rows``; enums and records in ``docx_model``. Skipped
content is recorded as :class:`UnsupportedItem`. Hyperlink targets and
field codes are not read and not recorded. Bounds keep work linear. XML is
parsed with ``forbid_dtd``, so entities never expand. ``repr`` shows
counts only. See ``docs/notes/a2-v2-parser-p2-04.md`` (PROVISIONAL).
"""

from __future__ import annotations

import io
import re
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from xml.etree.ElementTree import Element, ParseError

from defusedxml import ElementTree as safe_et
from defusedxml.common import DefusedXmlException

from msgloom.a2_kedro.contracts.codec import sha256_hex
from msgloom.a2_kedro.contracts.parse import LimitHit, ParserReceipt
from msgloom.a2_kedro.parsers.docx_model import (
    Block,
    DocxInputError,
    DocxLimit,
    UnsupportedItem,
    UnsupportedKind,
)
from msgloom.a2_kedro.parsers.docx_rows import (
    cell_deleted,
    grid_span,
    is_marker,
    row_deleted,
)
from msgloom.a2_kedro.parsers.docx_rows import qname as _qname
from msgloom.contracts import Limitation, TerminalStatus

WORKER = "msgloom.a2_kedro.parsers.docx"
DOCUMENT_MEMBER = "word/document.xml"

#: Provisional bounds. They are parser decisions, not production limits.
MIB = 1024 * 1024
MAX_INPUT_BYTES, MAX_MEMBER_BYTES, MAX_TOTAL_BYTES = 32 * MIB, 16 * MIB, 64 * MIB
MAX_MEMBERS, MAX_XML_DEPTH, MAX_XML_ELEMENTS = 1000, 128, 1_000_000
MAX_PARAGRAPHS, MAX_TEXT_CHARS, MAX_TABLE_DEPTH = 100_000, 5_000_000, 4
MAX_UNSUPPORTED_ITEMS = 1000

_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


_FAILED = frozenset(list(DocxLimit)[:9])  # the first nine members
_LIMIT_HIT: dict[DocxLimit, LimitHit] = {
    DocxLimit.MEMBER_LIMIT: "parts",
    DocxLimit.UNSUPPORTED_CONTENT: "parts",
    DocxLimit.UNSUPPORTED_OVERFLOW: "parts",
    DocxLimit.PARAGRAPH_LIMIT: "cells",
}
_DETAIL = "The DOCX result is not complete. See the limitation code."


@dataclass(frozen=True, slots=True)
class DocxResult:
    """Result of one parse. ``limitations`` follow :class:`DocxLimit` order."""

    status: TerminalStatus
    limitations: tuple[DocxLimit, ...]
    input_bytes: int
    input_sha256: str
    blocks: tuple[Block, ...] = field(default=(), repr=False)
    unsupported: tuple[UnsupportedItem, ...] = field(default=(), repr=False)

    def __post_init__(self) -> None:
        clean = not self.limitations and not self.unsupported
        if (self.status is TerminalStatus.COMPLETE) != clean:
            raise DocxInputError("status conflicts with limitations")

    def __repr__(self) -> str:
        counts = (len(self.limitations), len(self.blocks), len(self.unsupported))
        return f"DocxResult({self.status.value}, limits/blocks/unsupported={counts})"

    def to_contract_limitations(self) -> tuple[Limitation, ...]:
        """Return fixed-text limitations; one per unsupported kind."""
        kinds = {item.kind for item in self.unsupported}
        codes = [f"unsupported_{k}" for k in UnsupportedKind if k in kinds]
        codes += [
            str(c) for c in self.limitations if c != DocxLimit.UNSUPPORTED_CONTENT
        ]
        return tuple(Limitation(code, _DETAIL) for code in codes)

    def to_receipt(self, worker_version: str) -> ParserReceipt | None:
        """
        Return the parser receipt, or ``None`` for a ``FAILED`` result.

        ``limit_hit`` maps the first limitation (member and unsupported
        limits to ``parts``, paragraphs to ``cells``, else ``bytes``).
        """
        if self.status is TerminalStatus.FAILED:
            return None
        done = self.status is TerminalStatus.COMPLETE
        hit: LimitHit = "none" if done else _LIMIT_HIT.get(self.limitations[0], "bytes")
        return ParserReceipt(
            worker=WORKER,
            worker_version=worker_version,
            outcome="complete" if done else "partial",
            limit_hit=hit,
            input_bytes=self.input_bytes,
            part_count=1,
        )


_TEXT = {"w:tab": "\t", "w:br": "\n", "w:cr": "\n", "w:noBreakHyphen": "-"}
_DROPPED = {
    "w:del": UnsupportedKind.TRACKED_DELETION,
    "w:moveFrom": UnsupportedKind.TRACKED_DELETION,
    "w:commentReference": UnsupportedKind.COMMENT,
    "w:footnoteReference": UnsupportedKind.FOOTNOTE,
    "w:endnoteReference": UnsupportedKind.ENDNOTE,
    "w:altChunk": UnsupportedKind.ALT_CHUNK,
    "w:control": UnsupportedKind.FORM_CONTROL,
    "m:oMath": UnsupportedKind.EQUATION,
    "m:oMathPara": UnsupportedKind.EQUATION,
    "w:sym": UnsupportedKind.UNKNOWN_BLOCK,
    "w:ptab": UnsupportedKind.UNKNOWN_BLOCK,
}
_OPAQUE = frozenset({"w:drawing", "w:pict", "w:object", "mc:AlternateContent"})
_PROPERTIES = frozenset({"w:pPr", "w:rPr", "w:instrText", "w:delText", "w:sdtPr"})
_SCAN = {
    "x:blip": UnsupportedKind.IMAGE,
    "x:imagedata": UnsupportedKind.IMAGE,
    "x:OLEObject": UnsupportedKind.OLE_OBJECT,
    "w:object": UnsupportedKind.OLE_OBJECT,
    "w:control": UnsupportedKind.FORM_CONTROL,
    "w:txbxContent": UnsupportedKind.TEXTBOX,
    "x:textbox": UnsupportedKind.TEXTBOX,
    "x:chart": UnsupportedKind.CHART,
    "x:relIds": UnsupportedKind.DIAGRAM,
}


class _Run:
    def __init__(self) -> None:
        self.found: set[DocxLimit] = set()
        self.items: list[UnsupportedItem] = []
        self.paragraphs = 0
        self.chars = 0
        self.stop = False

    def drop(self, kind: UnsupportedKind, block_id: str | None) -> None:
        self.found.add(DocxLimit.UNSUPPORTED_CONTENT)
        if len(self.items) < MAX_UNSUPPORTED_ITEMS:
            self.items.append(UnsupportedItem(kind, block_id))
        else:
            self.found.add(DocxLimit.UNSUPPORTED_OVERFLOW)

    def drop_opaque(self, element: Element, block_id: str | None) -> None:
        kinds = {
            _SCAN[n] for n in (_qname(e.tag) for e in element.iter()) if n in _SCAN
        }
        for kind in kinds or {UnsupportedKind.DRAWING}:
            self.drop(kind, block_id)


def _paragraph_text(para: Element, run: _Run, block_id: str) -> str:
    parts: list[str] = []
    stack = [iter(para)]
    while stack:
        if (node := next(stack[-1], None)) is None:
            stack.pop()
            continue
        name = _qname(node.tag)
        if name == "w:t":
            parts.append(node.text or "")
        elif name in _TEXT:
            parts.append(_TEXT[name])
        elif name in _DROPPED:
            run.drop(_DROPPED[name], block_id)
        elif name in _OPAQUE:
            run.drop_opaque(node, block_id)
        elif name not in _PROPERTIES:
            stack.append(iter(node))
    return "".join(parts)


def _flatten(parent: Element) -> Iterator[Element]:
    """Yield children in order; ``w:sdt`` and ``w:customXml`` are transparent."""
    stack = [iter(parent)]
    while stack:
        if (node := next(stack[-1], None)) is None:
            stack.pop()
            continue
        name = _qname(node.tag)
        if name == "w:sdt":
            stack.extend(iter(c) for c in node if _qname(c.tag) == "w:sdtContent")
        elif name == "w:customXml":
            stack.append(iter(node))
        else:
            yield node


def _walk(
    container: Element, prefix: str, depth: int, run: _Run
) -> tuple[list[Block], list[str]]:
    """Return body blocks (body only) and direct paragraph texts (cell)."""
    body = prefix == ""
    blocks: list[Block] = []
    texts: list[str] = []
    index = 0
    for node in _flatten(container):
        if run.stop:
            break
        name = _qname(node.tag)
        child = f"b{index}" if body else f"{prefix}/{index}"
        if name == "w:p":
            index += 1
            run.paragraphs += 1
            if run.paragraphs > MAX_PARAGRAPHS:
                run.found.add(DocxLimit.PARAGRAPH_LIMIT)
                run.stop = True
                break
            text = _paragraph_text(node, run, child)
            room = max(MAX_TEXT_CHARS - run.chars, 0)
            if len(text) > room:
                run.found.add(DocxLimit.TEXT_LIMIT)
                run.stop = True
            text = text[:room]
            run.chars += len(text)
            if body:
                blocks.append(Block(child, "paragraph", index - 1, text))
            else:
                texts.append(text)
        elif name == "w:tbl":
            index += 1
            blocks.extend(_table(node, child, depth + 1, run))
        elif name in _DROPPED:
            run.drop(_DROPPED[name], prefix or None)
        elif name in _OPAQUE:
            run.drop_opaque(node, prefix or None)
        elif not is_marker(name):
            run.drop(UnsupportedKind.UNKNOWN_BLOCK, prefix or None)
    return blocks, texts


def _table(table: Element, table_id: str, depth: int, run: _Run) -> list[Block]:
    """
    Return the cell blocks of one table.

    A row marked deleted (``w:trPr/w:del``) and a cell marked deleted
    (``w:tcPr/w:cellDel``) are skipped and recorded as ``tracked_deletion``.
    A skipped row or cell still takes its row or column index, so IDs
    depend on structure only. Unknown children are recorded, not lost.
    """
    if depth > MAX_TABLE_DEPTH:
        run.found.add(DocxLimit.TABLE_DEPTH_LIMIT)
        return []
    blocks: list[Block] = []
    row = 0
    for tr in _flatten(table):
        if _qname(tr.tag) != "w:tr":
            if not is_marker(_qname(tr.tag)):
                run.drop(UnsupportedKind.UNKNOWN_BLOCK, table_id)
            continue
        if row_deleted(tr):
            run.drop(UnsupportedKind.TRACKED_DELETION, f"{table_id}/r{row}")
            row += 1
            continue
        col = 0
        for cell in _flatten(tr):
            name = _qname(cell.tag)
            if name != "w:tc":
                if not is_marker(name):
                    run.drop(UnsupportedKind.UNKNOWN_BLOCK, f"{table_id}/r{row}")
                continue
            if run.stop:
                continue
            cell_id = f"{table_id}/r{row}c{col}"
            span, malformed = grid_span(cell)
            if malformed:
                run.found.add(DocxLimit.MALFORMED_TABLE)
            if cell_deleted(cell):
                run.drop(UnsupportedKind.TRACKED_DELETION, cell_id)
                col += span
                continue
            nested, texts = _walk(cell, cell_id, depth, run)
            top = int(cell_id.split("/")[0][1:])
            blocks.append(Block(cell_id, "table_cell", top, "\n".join(texts), row, col))
            blocks.extend(nested)
            col += span
        row += 1
    return blocks


_PARSE_ERRORS = (ParseError, UnicodeError, LookupError)
_XML_ERRORS = (DefusedXmlException, *_PARSE_ERRORS)


def _events(data: bytes, found: set[DocxLimit]) -> Iterator[tuple[str, Element]]:
    """Yield XML events. Stop at a bound and record it in ``found``."""
    depth = count = 0
    source = io.BytesIO(data)
    for event, node in safe_et.iterparse(source, ("start", "end"), forbid_dtd=True):
        depth += 1 if event == "start" else -1
        count += event == "start"
        if depth > MAX_XML_DEPTH or count > MAX_XML_ELEMENTS:
            found.add(DocxLimit.XML_LIMIT)
            return
        yield event, node


def _load_tree(data: bytes, run: _Run) -> Element | None:
    root: Element | None = None
    try:
        for _event, node in _events(data, run.found):
            root = node if root is None else root
    except DefusedXmlException:  # distinct from _PARSE_ERRORS: forbidden, not invalid
        run.found.add(DocxLimit.XML_FORBIDDEN)
    except _PARSE_ERRORS:
        run.found.add(DocxLimit.INVALID_XML)
    return None if DocxLimit.XML_LIMIT in run.found else root


def _has_content(data: bytes, comments: bool) -> bool:
    """Stream-scan a member; unknown or unparsable content counts as content."""
    found: set[DocxLimit] = set()
    try:
        for event, node in _events(data, found):
            name = _qname(node.tag)
            if event == "start":
                continue
            if (comments and name == "w:comment") or (
                name == "w:t" and (node.text or "").strip()
            ):
                return True
            node.clear()
    except _XML_ERRORS:
        return True
    return bool(found)


#: (member name pattern, kind, probe mode). Probe: None = always counts,
#: "text" = counts when it holds text, "comments" = counts with a comment.
_PACKAGE_RULES: tuple[tuple[re.Pattern[str], UnsupportedKind, str | None], ...] = (
    (re.compile(r"word/media/.+"), UnsupportedKind.IMAGE, None),
    (re.compile(r"word/embeddings/.+"), UnsupportedKind.OLE_OBJECT, None),
    (re.compile(r"word/charts/.+"), UnsupportedKind.CHART, None),
    (re.compile(r"word/diagrams/.+"), UnsupportedKind.DIAGRAM, None),
    (re.compile(r"word/activeX/.+"), UnsupportedKind.FORM_CONTROL, None),
    (re.compile(r"word/vbaProject\.bin"), UnsupportedKind.MACRO, None),
    (re.compile(r"word/comments\.xml"), UnsupportedKind.COMMENT, "comments"),
    (re.compile(r"word/header[0-9]*\.xml"), UnsupportedKind.HEADER, "text"),
    (re.compile(r"word/footer[0-9]*\.xml"), UnsupportedKind.FOOTER, "text"),
    (re.compile(r"word/footnotes\.xml"), UnsupportedKind.FOOTNOTE, "text"),
    (re.compile(r"word/endnotes\.xml"), UnsupportedKind.ENDNOTE, "text"),
)


def _read(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> bytes:
    with archive.open(info) as handle:
        return handle.read(MAX_MEMBER_BYTES + 1)


def _scan_package(archive: zipfile.ZipFile, run: _Run) -> None:
    seen: set[UnsupportedKind] = set()
    skip = DocxLimit.TOTAL_SIZE_LIMIT in run.found
    for info in archive.infolist()[:MAX_MEMBERS]:
        rule = next((r for r in _PACKAGE_RULES if r[0].fullmatch(info.filename)), None)
        if rule is None or rule[1] in seen:
            continue
        _, kind, probe = rule
        if probe and (skip or info.file_size > MAX_MEMBER_BYTES):
            run.found.add(DocxLimit.MEMBER_SIZE_LIMIT)
        elif probe and not _has_content(_read(archive, info), probe == "comments"):
            continue
        seen.add(kind)
        run.drop(kind, None)


def _parse_package(raw: bytes, run: _Run) -> list[Block]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile:
        run.found.add(DocxLimit.NOT_A_ZIP)
        return []
    infos = archive.infolist()
    if len({i.filename for i in infos}) != len(infos):
        run.found.add(DocxLimit.DUPLICATE_MEMBER)
    if any(i.flag_bits & 0x1 for i in infos):
        run.found.add(DocxLimit.ENCRYPTED_MEMBER)
    if len(infos) > MAX_MEMBERS:
        run.found.add(DocxLimit.MEMBER_LIMIT)
    if sum(i.file_size for i in infos) > MAX_TOTAL_BYTES:
        run.found.add(DocxLimit.TOTAL_SIZE_LIMIT)
    doc = next((i for i in infos if i.filename == DOCUMENT_MEMBER), None)
    if doc is None:
        run.found.add(DocxLimit.NOT_DOCX)
    if doc is None or run.found & _FAILED:
        return []
    if doc.file_size > MAX_MEMBER_BYTES:
        run.found.add(DocxLimit.MEMBER_SIZE_LIMIT)
        return []
    data = _read(archive, doc)
    root = _load_tree(data, run)
    if root is None:
        return []
    body = next((c for c in root if _qname(c.tag) == "w:body"), None)
    if _qname(root.tag) != "w:document" or body is None:
        run.found.add(DocxLimit.NOT_DOCX)
        return []
    blocks, _ = _walk(body, "", 0, run)
    _scan_package(archive, run)
    return blocks


def _finish(raw: bytes, run: _Run, blocks: list[Block]) -> DocxResult:
    found = run.found
    if not blocks and not found:
        found.add(DocxLimit.EMPTY_DOCUMENT)
    failed = bool(found & _FAILED)
    status = TerminalStatus.INCOMPLETE if found else TerminalStatus.COMPLETE
    return DocxResult(
        status=TerminalStatus.FAILED if failed else status,
        limitations=tuple(item for item in DocxLimit if item in found),
        input_bytes=len(raw),
        input_sha256=sha256_hex(raw),
        blocks=() if failed else tuple(blocks),
        unsupported=() if failed else tuple(run.items),
    )


def parse_docx(data: bytes) -> DocxResult:
    """Parse saved DOCX bytes into ordered blocks and unsupported items."""
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise DocxInputError("component must be bytes")
    raw = bytes(data)
    run = _Run()
    blocks: list[Block] = []
    if not raw:
        run.found.add(DocxLimit.EMPTY_INPUT)
    elif raw.startswith(_OLE_MAGIC):
        run.found.add(DocxLimit.ENCRYPTED_OR_OLE)
    elif len(raw) > MAX_INPUT_BYTES:
        run.found.add(DocxLimit.SIZE_LIMIT)
    else:
        try:
            blocks = _parse_package(raw, run)
        except Exception:  # noqa: BLE001 - any failure maps to a fixed code
            run.found.add(DocxLimit.CORRUPT_PACKAGE)
    return _finish(raw, run, blocks)
