"""Deterministic MIME assembly from immutable rendered report parts."""

from __future__ import annotations

import base64
from email.utils import parseaddr
from hashlib import sha256

from msgloom.reporting import ReportPart, SavedReport


def validate_owner_address(value: str) -> str:
    """Require one newline-free mailbox and reject recipient injection."""
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("owner destination must be non-empty canonical text")
    if any(char in value for char in ("\r", "\n", ",", ";")):
        raise ValueError("owner destination cannot contain extra recipients")
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
    seed = (
        f"{report.report_ref.identity}:{report.report_ref.version}:"
        f"{report.policy_ref.identity}:{part.part_number}"
    ).encode()
    digest = sha256(seed).hexdigest()
    boundary = f"msgloom-{digest[:40]}"
    message_id = f"<{digest}@msgloom.invalid>"
    subject = (
        f"Msgloom report {report.report_ref.identity} "
        f"part {part.part_number}/{len(report.parts)}"
    )
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
    plain = base64.b64encode(part.plain_text.encode("utf-8")).decode("ascii")
    html = base64.b64encode(part.html.encode("utf-8")).decode("ascii")
    body = [
        f"--{boundary}",
        'Content-Type: text/plain; charset="utf-8"',
        "Content-Transfer-Encoding: base64",
        "",
        plain,
        f"--{boundary}",
        'Content-Type: text/html; charset="utf-8"',
        "Content-Transfer-Encoding: base64",
        "",
        html,
        f"--{boundary}--",
        "",
    ]
    return "\r\n".join(headers + body).encode("ascii")
