"""Bounded, immutable Mail capture/association value helpers."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session


def bounded_json(value: object, limit: int = 8192) -> str:
    """Bound local structured metadata independently of shared wire fields."""
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if len(text.encode()) > limit:
        raise ValueError("Oversized Mail binding metadata")
    return text


def identifier(value: str, limit: int = 2048) -> str:
    """Reject absent, oversized or non-string association identities."""
    if not isinstance(value, str) or not value or len(value.encode()) > limit:
        raise ValueError("Invalid Mail binding identifier")
    return value


def append_row(session: Session, model, key, values: dict[str, Any]):
    """Accept exact repeats; reject conflicting identities before insertion."""
    existing = session.get(model, key)
    if existing is not None:
        if any(getattr(existing, name) != value for name, value in values.items()):
            raise ValueError("Conflicting immutable Mail binding")
        return existing
    row = model(**values)
    session.add(row)
    session.flush()
    return row


def projection(attachment: dict[str, Any]) -> dict[str, Any]:
    """Retain only the existing attachment metadata representation."""
    if not isinstance(attachment, dict):
        raise TypeError("Invalid attachment metadata")
    for field in ("@odata.type", "name", "contentType"):
        value = attachment.get(field)
        if value is not None and (
            not isinstance(value, str) or len(value.encode()) > 4096
        ):
            raise ValueError("Invalid attachment text metadata")
    size, inline = attachment.get("size"), attachment.get("isInline")
    if size is not None and (type(size) is not int or not 0 <= size < 2**63):
        raise ValueError("Invalid attachment size")
    if inline is not None and type(inline) is not bool:
        raise ValueError("Invalid attachment inline flag")
    return {
        "attachment_id": identifier(attachment["id"]),
        "attachment_type": attachment.get("@odata.type"),
        "name": attachment.get("name"),
        "content_type": attachment.get("contentType"),
        "size": attachment.get("size"),
        "is_inline": attachment.get("isInline"),
    }
