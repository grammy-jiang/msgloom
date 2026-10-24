"""
Attachment inventory for saved raw message bytes (P2-06).

:func:`inventory_attachments` reads the :class:`MimeParseResult` that
:func:`~msgloom.a2_kedro.parsers.mime_html.parse_mime` made from ``data``.
It returns an :class:`AttachmentInventory`: one :class:`AttachmentRecord`
per attachment-like part, in source order, plus a ``Limitation`` for each
part or structure that it cannot represent. The function is pure. It never
parses attachment content, so nothing is fetched or executed.

Attachment-like: a part that is not a ``multipart/*`` container and that
is one of the following. The first matching rule gives the role.

- ``embedded_message``: media type ``message/rfc822`` or ``message/global``.
- ``calendar``: media type ``text/calendar`` or ``application/ics``.
- ``attachment``: disposition ``attachment``; or a declared filename and
  no disposition; or a non-text part with no Content-ID, outside a
  ``multipart/related``; or a ``text/*`` part other than plain or HTML.
- ``inline``: disposition ``inline`` with a filename, a Content-ID or a
  non-text type; or a non-text part with a Content-ID or inside a
  ``multipart/related``.

A ``text/plain`` or ``text/html`` part with no filename and no
``attachment`` disposition is a message body, not an attachment. The roles
come from the headers of each part, not from the P2-01 role. P2-01 marks
every part inside an embedded message as ``embedded``, which hides a nested
attachment.

Traceability: ``start`` and ``end`` are the half-open window of the whole
part (headers and body) in ``data``, so ``data[start:end]`` is its exact
source. ``size`` and ``sha256`` describe the decoded payload: the body
after the transfer encoding is removed. ``parent`` is the P2-01 parent
path. ``message_path`` is the path of the nearest enclosing
``message/rfc822`` part, or ``None`` at top level.

Status: ``ok`` (payload decoded, size and hash set), ``empty`` (no
payload), ``undecodable`` (corrupt or unknown transfer encoding) and
``oversize`` (over ``MAX_ATTACHMENT_BYTES``). A record that is not ``ok``
has ``size`` and ``sha256`` of ``None`` and a matching limitation.

Limitations: the detail is always a part path, never a filename or any
content. Codes: ``attachment_empty``, ``attachment_undecodable``,
``attachment_too_large``, ``attachment_depth_limit`` (nesting over
``MAX_DEPTH`` or a P2-01 ``depth_limit`` part), ``attachment_limit`` (more
than ``MAX_ATTACHMENTS`` parts), ``attachment_count_mismatch`` (declared
count differs from the count found), ``attachment_error``,
``structure_incomplete`` (P2-01 could not scan the whole structure) and
``source_mismatch`` (``data`` is not the input of ``result``). Any
limitation makes the status INCOMPLETE. An attachment-only message with no
body is COMPLETE: P2-01 reports the missing body, not this module.

Filename: the declared name is only a label. It is decoded, cut to its
last path segment, stripped of control, format and unassigned characters
(each becomes ``_``), stripped of edge dots and spaces, and cut to
``MAX_FILENAME_CHARS``. It is never used as a path. A changed name gets the
``filename_sanitized`` flag. Names that match after case folding get the
``filename_duplicate`` flag on every record; no record is merged.

Failure handling: the function never raises for message content. It
raises :exc:`A2ContractError`, with a fixed message, for a wrong argument
type. Same arguments give an equal result.

CANDIDATE/RESEARCH, PROVISIONAL: limits, roles and codes are not frozen.
See ``docs/notes/a2-v2-parser-p2-06.md``.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace
from email.header import decode_header, make_header
from email.message import Message
from email.parser import BytesHeaderParser
from typing import Literal

from msgloom.a2_kedro.contracts.codec import A2ContractError, sha256_hex
from msgloom.a2_kedro.parsers import (
    MimeParseResult,
    MimePart,
    decode_transfer,
)
from msgloom.a2_kedro.parsers.mime_html import MAX_HEADER_BYTES
from msgloom.contracts import Limitation, TerminalStatus

#: Provisional bounds.
MAX_ATTACHMENTS = 128
MAX_ATTACHMENT_BYTES = 8 * 1024 * 1024
MAX_DEPTH = 8
MAX_FILENAME_CHARS = 128
MAX_MEDIA_TYPE_CHARS = 127

AttachmentRole = Literal["attachment", "inline", "embedded_message", "calendar"]
AttachmentStatus = Literal["ok", "empty", "undecodable", "oversize"]

_MEDIA_TYPE = re.compile(r"[a-z0-9][a-z0-9!#$&^_.+-]*/[a-z0-9][a-z0-9!#$&^_.+-]*")
_SEGMENTS = re.compile(r"[\\/]+")
_DROPPED = frozenset({"Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp"})
_CALENDAR = frozenset({"text/calendar", "application/ics"})
_BODY_TYPES = frozenset({"text/plain", "text/html"})
_BAD_ENCODING = frozenset({"base64_corrupt", "qp_corrupt", "cte_unknown"})
# Structure problems of P2-01 that can hide an attachment from the scan.
_STRUCTURE = frozenset(
    {
        "input_too_large",
        "parser_error",
        "part_limit",
        "header_too_large",
        "multipart_malformed",
        "multipart_truncated",
    }
)


@dataclass(frozen=True, slots=True)
class AttachmentRecord:
    """One attachment-like part; ``filename`` is sanitized and a label only."""

    path: str
    parent: str | None
    message_path: str | None
    role: AttachmentRole
    media_type: str
    filename: str | None
    has_content_id: bool
    start: int
    end: int
    size: int | None
    sha256: str | None
    status: AttachmentStatus
    flags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AttachmentInventory:
    """
    Outcome of :func:`inventory_attachments`.

    ``seen`` counts every attachment-like part found. It equals
    ``len(records)`` plus the parts that have a limitation and no record.
    """

    status: TerminalStatus
    limitations: tuple[Limitation, ...]
    records: tuple[AttachmentRecord, ...]
    seen: int
    input_size: int
    input_sha256: str


def sanitize_filename(raw: str) -> str | None:
    """Return a safe display label for ``raw``, or ``None`` if nothing is left."""
    segments = [item for item in _SEGMENTS.split(raw) if item]
    if not segments:
        return None
    name = "".join(
        "_" if unicodedata.category(char) in _DROPPED else char for char in segments[-1]
    )
    name = name.strip(" .")[:MAX_FILENAME_CHARS].strip(" .")
    return name or None


def _filename(msg: Message, flags: set[str]) -> str | None:
    """Return the sanitized declared filename; add a flag for a defect."""
    try:
        raw = msg.get_filename()
        if not isinstance(raw, str) or not raw:
            return None
        if "=?" in raw:
            raw = str(make_header(decode_header(raw)))
    except Exception:  # noqa: BLE001 - a bad header must not end the run
        flags.add("filename_unreadable")
        return None
    name = sanitize_filename(raw)
    if name != raw:
        flags.add("filename_sanitized")
    return name


def _role(
    kind: str, disposition: str | None, named: bool, has_cid: bool, ptype: str
) -> AttachmentRole | None:
    """Return the role of a part, or ``None`` if it is not attachment-like."""
    if kind.startswith("multipart/"):
        return None
    if kind in _EMBEDDED:
        return "embedded_message"
    if kind in _CALENDAR:
        return "calendar"
    if disposition == "attachment":
        return "attachment"
    text = kind.startswith("text/")
    if disposition == "inline":
        return "inline" if named or has_cid or not text else None
    if named:
        return "attachment"
    if kind in _BODY_TYPES:
        return None
    if text:
        return "attachment"
    return "inline" if has_cid or ptype == "multipart/related" else "attachment"


def _payload(
    data: bytes, part: MimePart, msg: Message
) -> tuple[AttachmentStatus, int | None, str | None]:
    """Decode the payload; return ``(status, size, sha256)``."""
    too_big = part.end - part.body_start > MAX_ATTACHMENT_BYTES
    if too_big or "part_too_large" in part.flags:
        return "oversize", None, None
    flags: set[str] = set()
    encoding = str(msg.get("content-transfer-encoding", "")).strip().lower()
    body = decode_transfer(data[part.body_start : part.end], encoding, flags)
    if flags & _BAD_ENCODING:
        return "undecodable", None, None
    if not body:
        return "empty", None, None
    return "ok", len(body), sha256_hex(body)


def _media_type(kind: str, flags: set[str]) -> str:
    if len(kind) <= MAX_MEDIA_TYPE_CHARS and _MEDIA_TYPE.fullmatch(kind):
        return kind
    flags.add("media_type_invalid")
    return "application/octet-stream"


def _message_path(part: MimePart, by_path: dict[str, MimePart]) -> str | None:
    """Return the path of the nearest ``message/rfc822`` ancestor."""
    seen: set[str] = set()
    current = part.parent
    while current is not None and current not in seen:
        seen.add(current)
        ancestor = by_path.get(current)
        if ancestor is None:
            return None
        if ancestor.content_type in _EMBEDDED:
            return ancestor.path
        current = ancestor.parent
    return None


_EMBEDDED = frozenset({"message/rfc822", "message/global"})
_STATUS_CODE = {
    "empty": "attachment_empty",
    "undecodable": "attachment_undecodable",
    "oversize": "attachment_too_large",
}


def _inspect(
    data: bytes, part: MimePart, by_path: dict[str, MimePart]
) -> tuple[AttachmentRecord | None, str | None, bool]:
    """
    Classify one part.

    Return ``(record, limitation_code, attachment_like)``. A part that is
    not attachment-like returns ``(None, None, False)`` unless P2-01 could
    not expand it (``depth_limit``).
    """
    header = data[part.start : min(part.body_start, part.start + MAX_HEADER_BYTES)]
    msg = BytesHeaderParser().parsebytes(header)
    parent = by_path.get(part.parent or "")
    flags: set[str] = set()
    name = _filename(msg, flags)
    has_cid = msg["content-id"] is not None
    role = _role(
        part.content_type,
        part.disposition,
        name is not None,
        has_cid,
        parent.content_type if parent else "",
    )
    # A part over our bound is reported only if it is attachment-like; its
    # children are in ``result.parts`` and are judged on their own. A part
    # that P2-01 did not expand may hide children, so it is always reported.
    too_deep = role is not None and part.path.count(".") + 1 > MAX_DEPTH
    if too_deep or "depth_limit" in part.flags:
        return None, "attachment_depth_limit", role is not None
    if role is None:
        return None, None, False
    status, size, digest = _payload(data, part, msg)
    record = AttachmentRecord(
        path=part.path,
        parent=part.parent,
        message_path=_message_path(part, by_path),
        role=role,
        media_type=_media_type(part.content_type, flags),
        filename=name,
        has_content_id=has_cid,
        start=part.start,
        end=part.end,
        size=size,
        sha256=digest,
        status=status,
        flags=tuple(sorted(flags)),
    )
    return record, _STATUS_CODE.get(status), True


def _mark_duplicates(
    records: list[AttachmentRecord],
) -> tuple[AttachmentRecord, ...]:
    counts: dict[str, int] = {}
    for record in records:
        if record.filename is not None:
            key = record.filename.casefold()
            counts[key] = counts.get(key, 0) + 1
    return tuple(
        replace(record, flags=(*record.flags, "filename_duplicate"))
        if record.filename is not None and counts[record.filename.casefold()] > 1
        else record
        for record in records
    )


def _claims_attachments(data: bytes, root: MimePart) -> bool:
    """Return true when the root header says the message has attachments."""
    header = data[root.start : min(root.body_start, root.start + MAX_HEADER_BYTES)]
    value = BytesHeaderParser().parsebytes(header).get("x-ms-has-attach")
    return str(value).strip().lower() == "yes" if value is not None else False


def _check_arguments(result: object, data: object, declared_count: object) -> bytes:
    if not isinstance(result, MimeParseResult):
        raise A2ContractError("result must be a MimeParseResult")
    if not isinstance(data, bytes | bytearray | memoryview):
        raise A2ContractError("input must be bytes")
    if declared_count is not None and (
        not isinstance(declared_count, int)
        or isinstance(declared_count, bool)
        or declared_count < 0
    ):
        raise A2ContractError("declared count must be a non-negative integer")
    return bytes(data)


def _identity_encoded(data: bytes, part: MimePart) -> bool:
    """Return whether the part body is stored without a transfer encoding."""
    header = data[part.start : min(part.body_start, part.start + MAX_HEADER_BYTES)]
    value = BytesHeaderParser().parsebytes(header)["content-transfer-encoding"]
    return str(value or "7bit").strip().lower() in {"7bit", "8bit", "binary"}


def inventory_attachments(
    result: MimeParseResult,
    data: bytes,
    *,
    declared_count: int | None = None,
) -> AttachmentInventory:
    """
    Return the attachment inventory of ``data`` using its P2-01 ``result``.

    ``declared_count`` is an optional claim from the provider metadata. It
    counts every attachment-like part, including inline and embedded
    messages. A count that differs from ``seen`` creates the
    ``attachment_count_mismatch`` limitation. The ``X-MS-Has-Attach: yes``
    header of the root part with no part found does the same.
    """
    raw = _check_arguments(result, data, declared_count)
    size, digest = len(raw), sha256_hex(raw)
    limits: set[tuple[str, str]] = set()
    records: list[AttachmentRecord] = []
    seen = 0
    if size != result.input_size or digest != result.input_sha256:
        limits.add(("source_mismatch", "1"))
    else:
        by_path = {part.path: part for part in result.parts}
        for item in result.limitations:
            if item.code in _STRUCTURE:
                limits.add(("structure_incomplete", item.detail))
        for part in result.parts:
            try:
                record, code, like = _inspect(raw, part, by_path)
            except Exception:  # noqa: BLE001 - content must not end the run
                record, code, like = None, "attachment_error", True
            seen += like
            if record is not None and len(records) >= MAX_ATTACHMENTS:
                record, code = None, "attachment_limit"
            if record is not None:
                records.append(record)
            if code is not None:
                limits.add((code, part.path))
        # P2-01 expands only an identity-encoded embedded message as child
        # ``.1``. Any other message part may hide attachments, so the gap
        # is reported and never dropped.
        parents = {part.parent for part in result.parts}
        for part in result.parts:
            if part.content_type in _EMBEDDED and (
                part.path not in parents or not _identity_encoded(raw, part)
            ):
                limits.add(("attachment_nested_unexpanded", part.path))
        root = result.parts[0] if result.parts else None
        claimed = root is not None and not seen and _claims_attachments(raw, root)
        if claimed or (declared_count is not None and declared_count != seen):
            limits.add(("attachment_count_mismatch", "1"))
    found = tuple(Limitation(code, detail) for code, detail in sorted(limits))
    status = TerminalStatus.INCOMPLETE if found else TerminalStatus.COMPLETE
    return AttachmentInventory(
        status, found, _mark_duplicates(records), seen, size, digest
    )
