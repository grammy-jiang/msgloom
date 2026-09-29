"""Small deterministic mappings from Graph JSON into shared source contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from msgloom.contracts import Limitation
from msgloom.preparation.contracts import DocumentLocation, SavedByteReference
from msgloom.preparation.records import (
    PreparedParty,
    PreparedRecipient,
    RecipientRole,
)
from msgloom.sources.models import (
    CollectedBody,
    ContentKind,
    SourceEvidenceError,
    SourceMetadata,
    SourceReferenceError,
)

_JSON_LOCATION = DocumentLocation(part="graph-json")


def source_time(value: object, fallback: str) -> datetime:
    """Parse an aware provider time, falling back to the aware observation."""
    text = value if isinstance(value, str) and value else fallback
    try:
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            parsed = datetime.fromisoformat(fallback)
    except ValueError:
        raise SourceReferenceError("saved source timestamp is invalid") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SourceReferenceError("A1 observation time is not timezone-aware")
    return parsed


def graph_object(payload: object, provider_id: str) -> dict[str, Any]:
    """Select one exact provider object from an object or collection page."""
    if isinstance(payload, dict) and payload.get("id") == provider_id:
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("value"), list):
        matches = [
            item
            for item in payload["value"]
            if isinstance(item, dict) and item.get("id") == provider_id
        ]
        if len(matches) == 1:
            return matches[0]
    raise SourceEvidenceError("saved Graph evidence does not contain selected item")


def party(value: object) -> PreparedParty | None:
    """Map one Graph recipient/sender object without provider SDK types."""
    if not isinstance(value, dict):
        return None
    address = value.get("emailAddress")
    if isinstance(address, dict):
        identity = address.get("address")
        name = address.get("name")
    else:
        identity = value.get("address")
        name = value.get("name")
    if not isinstance(identity, str) or not identity.strip():
        return None
    return PreparedParty(
        identity=identity,
        display_name=name if isinstance(name, str) and name else None,
    )


def recipients(raw: dict[str, Any]) -> tuple[PreparedRecipient, ...]:
    """Retain exact To/Cc/Bcc roles from one Outlook representation."""
    values: list[PreparedRecipient] = []
    for field, role in (
        ("toRecipients", RecipientRole.TO),
        ("ccRecipients", RecipientRole.CC),
        ("bccRecipients", RecipientRole.BCC),
    ):
        candidates = raw.get(field)
        if not isinstance(candidates, list):
            continue
        for candidate in candidates:
            if (mapped := party(candidate)) is not None:
                values.append(PreparedRecipient(party=mapped, role=role))
    return tuple(values)


def content_kind(
    content_type: str | None, *, mime_default: bool = False
) -> ContentKind:
    """Preserve declared representation without claiming parsed cleanliness."""
    normalized = (content_type or "").lower().split(";", 1)[0].strip()
    if normalized in {"text/plain", "text"}:
        return ContentKind.PLAIN
    if normalized in {"text/html", "html"}:
        return ContentKind.HTML
    if normalized in {"application/json", "json"}:
        return ContentKind.JSON
    if normalized in {"message/rfc822", "mime"} or mime_default:
        return ContentKind.MIME
    return ContentKind.BINARY


def metadata(name: str, value: object) -> SourceMetadata | None:
    """Retain one non-empty scalar provider fact as data."""
    if isinstance(value, str) and value.strip():
        return SourceMetadata(name=name, value=value)
    return None


def body_descriptor(
    value: object,
    saved: SavedByteReference | None,
) -> CollectedBody | None:
    """Retain raw body text and its declared kind; do not parse HTML here."""
    if not isinstance(value, dict):
        return None
    content = value.get("content")
    content_type = value.get("contentType")
    if not isinstance(content, str):
        return None
    declared = content_type if isinstance(content_type, str) else None
    kind = content_kind(declared)
    limitations: tuple[Limitation, ...] = ()
    if kind is ContentKind.BINARY:
        limitations = (
            Limitation(
                "unsupported-body-content-kind",
                "Body content type is not a supported text representation.",
            ),
        )
    return CollectedBody(
        kind=kind,
        content=content,
        saved_bytes=saved,
        location=_JSON_LOCATION,
        limitations=limitations,
    )
