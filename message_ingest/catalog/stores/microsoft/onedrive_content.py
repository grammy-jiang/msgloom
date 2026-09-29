"""Query OneDrive metadata versions and explicit-content freshness."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select

from message_ingest.catalog.models.microsoft.onedrive import (
    OneDriveContentCapture,
    OneDriveContentRecord,
    OneDriveItemRecord,
)

type ContentFreshness = Literal["current", "stale", "unknown", "missing"]


@dataclass(frozen=True, slots=True)
class OneDriveItemVersion:
    """Metadata facts known when an explicit content request is planned."""

    e_tag: str | None
    c_tag: str | None
    observed_at: str
    evidence_id: str | None
    is_deleted: bool


@dataclass(frozen=True, slots=True)
class OneDriveContentFreshness:
    """Detached proof state for the latest stored explicit content."""

    status: ContentFreshness
    content_evidence_id: str | None
    current_e_tag: str | None
    planned_e_tag: str | None
    response_e_tag: str | None


def load_item_versions(catalog, *, source_id: str, item_ids: tuple[str, ...]):
    """Load one planning snapshot without keeping an ORM session alive."""
    with catalog.Session() as session:
        rows = session.scalars(
            select(OneDriveItemRecord).where(
                OneDriveItemRecord.source_id == source_id,
                OneDriveItemRecord.item_id.in_(item_ids),
            )
        ).all()
        return {
            row.item_id: OneDriveItemVersion(
                e_tag=row.e_tag,
                c_tag=row.c_tag,
                observed_at=row.latest_observed_at,
                evidence_id=row.latest_evidence_id,
                is_deleted=row.is_deleted,
            )
            for row in rows
        }


def content_freshness(catalog, *, source_id: str, item_id: str):
    """Return current only when planning, response, and current eTags agree."""
    with catalog.Session() as session:
        current = session.get(OneDriveItemRecord, (source_id, item_id))
        content = session.get(OneDriveContentRecord, (source_id, item_id))
        if content is None:
            return OneDriveContentFreshness("missing", None, None, None, None)
        capture = (
            session.get(OneDriveContentCapture, (source_id, content.latest_evidence_id))
            if content.latest_evidence_id
            else None
        )
        if current is None or capture is None:
            return OneDriveContentFreshness(
                "unknown",
                content.latest_evidence_id,
                current.e_tag if current is not None else None,
                capture.planned_e_tag if capture is not None else None,
                capture.response_e_tag if capture is not None else None,
            )
        if current.is_deleted:
            status: ContentFreshness = "stale"
        elif not current.e_tag or not capture.planned_e_tag:
            status = "unknown"
        elif current.e_tag != capture.planned_e_tag:
            status = "stale"
        elif not capture.response_e_tag:
            status = "unknown"
        elif capture.response_e_tag != capture.planned_e_tag:
            status = "stale"
        else:
            status = "current"
        return OneDriveContentFreshness(
            status,
            content.latest_evidence_id,
            current.e_tag,
            capture.planned_e_tag,
            capture.response_e_tag,
        )


__all__ = [
    "ContentFreshness",
    "OneDriveContentFreshness",
    "OneDriveItemVersion",
    "content_freshness",
    "load_item_versions",
]
