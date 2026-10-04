"""Shared Teams persistence validation and durable scoped-key helpers."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from sqlalchemy.orm import Session

from message_ingest.catalog.models.acquisition import RawHttpEvidence

Outcome = str


def require_source(actual: str, expected: str) -> None:
    """Reject application items routed to a different logical source store."""
    if actual != expected:
        raise ValueError("Teams item source does not match the catalog store source")


def parse_instant(value: str) -> datetime:
    """Parse a timezone-aware observation instant for chronological comparison."""
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Teams observed_at must be an ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Teams observed_at must include a timezone offset")
    return parsed


def scope_digest(parts: tuple[str | None, ...]) -> tuple[list[str | None], str]:
    """Encode typed tuple boundaries canonically instead of delimiter joining."""
    values = list(parts)
    encoded = json.dumps(
        values,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    return values, hashlib.sha256(encoded).hexdigest()


def require_evidence(
    session: Session,
    *,
    source_id: str,
    evidence_id: str | None,
    observed_at: str,
) -> RawHttpEvidence:
    """
    Resolve committed canonical evidence without requiring the current run ID.

    A cache replay can canonicalize to a capture from an earlier crawl. Source
    and canonical capture time must match, while semantic and evidence run IDs
    are intentionally retained independently.
    """
    parse_instant(observed_at)
    if not isinstance(evidence_id, str) or not evidence_id:
        raise ValueError("Teams durable state requires committed evidence")
    evidence = session.get(RawHttpEvidence, evidence_id)
    if evidence is None:
        raise ValueError("Teams durable state requires committed evidence")
    if evidence.source_id != source_id:
        raise ValueError("Teams evidence source does not match semantic source")
    if evidence.observed_at != observed_at:
        raise ValueError("Teams evidence capture time does not match semantic time")
    return evidence


def compare_observed(incoming: str, current: str) -> int:
    """Return negative, zero, or positive chronological capture ordering."""
    left = parse_instant(incoming)
    right = parse_instant(current)
    return (left > right) - (left < right)


__all__ = [
    "Outcome",
    "compare_observed",
    "parse_instant",
    "require_evidence",
    "require_source",
    "scope_digest",
]
