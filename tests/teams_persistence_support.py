"""Shared fixtures for dedicated Teams persistence tests."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.store import Catalog
from message_ingest.items.acquisition import RawHttpEvidenceItem
from message_ingest.items.microsoft.teams.message import TeamsMessageItem

SOURCE = "teams-source"
RUN = "run-current"
OBSERVED = "2026-10-04T00:00:00+00:00"


def open_catalog(tmp_path: Path, name: str = "catalog.sqlite3") -> Catalog:
    """Open a catalog after dedicated Teams models have registered metadata."""
    return Catalog(f"sqlite:///{tmp_path / name}")


def record_evidence(
    catalog: Catalog,
    evidence_id: str,
    *,
    source_id: str = SOURCE,
    observed_at: str = OBSERVED,
    run_id: str | None = RUN,
    body: bytes = b"{}",
) -> None:
    """Insert one protected raw-evidence row for semantic store tests."""
    digest = hashlib.sha256(body).hexdigest()
    catalog.evidence.record(
        RawHttpEvidence(
            evidence_id=evidence_id,
            source_id=source_id,
            run_id=run_id,
            purpose="teams-test",
            observed_at=observed_at,
            origin="network",
            request_fingerprint=f"fp-{evidence_id}",
            request_url="https://graph.microsoft.test/v1.0/test",
            request_method="GET",
            request_headers={},
            request_body_sha256=hashlib.sha256(b"").hexdigest(),
            request_body_path="/protected/request.bin",
            request_body_bytes=0,
            response_url="https://graph.microsoft.test/v1.0/test",
            response_status=200,
            response_headers={"content-type": ["application/json"]},
            response_body_sha256=digest,
            response_body_path="/protected/response.bin",
            response_body_bytes=len(body),
            response_flags=[],
            error_type=None,
            error_message=None,
        )
    )


def raw_item(
    evidence_id: str,
    *,
    source_run: str = RUN,
    observed_at: str = OBSERVED,
    origin: str = "network",
    body: bytes = b'{"id":"message"}',
) -> RawHttpEvidenceItem:
    """Build one raw item suitable for the real evidence pipeline."""
    return RawHttpEvidenceItem(
        evidence_id=evidence_id,
        run_id=source_run,
        purpose="teams-test",
        observed_at=observed_at,
        origin=origin,
        request_fingerprint="teams-shared-fingerprint",
        request_url="https://graph.microsoft.test/v1.0/test",
        request_method="GET",
        request_headers={},
        request_body=b"",
        response_url="https://graph.microsoft.test/v1.0/test",
        response_status=200,
        response_headers={"content-type": ["application/json"]},
        response_body=body,
        response_flags=[],
    )


def chat_message(
    *,
    chat_id: str = "chat-a",
    message_id: str = "opaque-message",
    evidence_id: str = "evidence-1",
    observed_at: str = OBSERVED,
    run_id: str = RUN,
    source_id: str = SOURCE,
    etag: str = "etag-a",
    body: str = "first",
    deleted_date_time: str | None = None,
    attachments: list[dict[str, Any]] | None = None,
) -> TeamsMessageItem:
    """Build one pre-parsed application message item."""
    raw: dict[str, Any] = {
        "id": message_id,
        "etag": etag,
        "createdDateTime": "2026-10-01T00:00:00Z",
        "lastModifiedDateTime": observed_at,
        "body": {"contentType": "html", "content": body},
    }
    if deleted_date_time is not None:
        raw["deletedDateTime"] = deleted_date_time
    if attachments is not None:
        raw["attachments"] = attachments
    return TeamsMessageItem.from_chat_graph(
        raw,
        chat_id=chat_id,
        source_id=source_id,
        observed_at=observed_at,
        evidence_id=evidence_id,
        run_id=run_id,
    )


__all__ = [
    "OBSERVED",
    "RUN",
    "SOURCE",
    "chat_message",
    "open_catalog",
    "raw_item",
    "record_evidence",
]
