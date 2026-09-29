"""Deterministic MIME assembly from immutable rendered report parts."""

from __future__ import annotations

import base64
import json
from email.header import Header
from email.utils import parseaddr
from hashlib import sha256
from textwrap import wrap

from msgloom.reporting import ReportPart, SavedReport


def validate_owner_address(value: str) -> str:
    """Require one ASCII newline-free mailbox and reject recipient injection."""
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("owner destination must be non-empty canonical text")
    if any(char in value for char in ("\r", "\n", ",", ";")):
        raise ValueError("owner destination cannot contain extra recipients")
    try:
        value.encode("ascii")
    except UnicodeEncodeError:
        raise ValueError("owner destination must be an ASCII mailbox") from None
    name, address = parseaddr(value)
    if name or address != value or "@" not in address:
        raise ValueError("owner destination must be one bare email address")
    local, domain = address.rsplit("@", 1)
    if not local or not domain or "." not in domain:
        raise ValueError("owner destination is not a complete mailbox")
    return address


def build_mime(report: SavedReport, part: ReportPart, destination: str) -> bytes:
    """Build deterministic multipart alternative bytes for one saved part."""
    owner = validate_owner_address(destination)
    # Canonical JSON keeps distinct references distinct; colon joining let
    # "a:b"/"c" and "a"/"b:c" share one Message-ID, which mail clients may
    # treat as a duplicate and hide.
    seed = json.dumps(
        [
            report.report_ref.identity,
            report.report_ref.version,
            report.policy_ref.identity,
            report.policy_ref.version,
            part.part_number,
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = sha256(seed).hexdigest()
    boundary = f"msgloom-{digest[:40]}"
    message_id = f"<{digest}@msgloom.invalid>"
    identity = _header_value(report.report_ref.identity)
    subject_text = (
        f"Msgloom report {identity} part {part.part_number}/{len(report.parts)}"
    )
    subject = Header(
        subject_text,
        charset="utf-8",
        header_name="Subject",
        maxlinelen=78,
    ).encode(linesep="\r\n")
    headers = [
        f"From: {owner}",
        f"To: {owner}",
        f"Subject: {subject}",
        f"Message-ID: {message_id}",
        f"Date: {report.due_at.strftime('%a, %d %b %Y %H:%M:%S %z')}",
        "MIME-Version: 1.0",
        f'Content-Type: multipart/alternative; boundary="{boundary}"',
        "",
    ]
    body = [
        f"--{boundary}",
        'Content-Type: text/plain; charset="utf-8"',
        "Content-Transfer-Encoding: base64",
        "",
        *_base64_lines(part.plain_text),
        f"--{boundary}",
        'Content-Type: text/html; charset="utf-8"',
        "Content-Transfer-Encoding: base64",
        "",
        *_base64_lines(part.html),
        f"--{boundary}--",
        "",
    ]
    return "\r\n".join(headers + body).encode("ascii")


def _header_value(value: str) -> str:
    """Reject header injection while retaining Unicode for RFC 2047 encoding."""
    if "\r" in value or "\n" in value:
        raise ValueError("report identity cannot contain header newlines")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("report identity cannot contain header controls")
    return value


def _base64_lines(value: str) -> list[str]:
    """Return RFC 2045 base64 lines no longer than 76 characters."""
    encoded = base64.b64encode(value.encode("utf-8")).decode("ascii")
    return wrap(encoded, width=76) or [""]
