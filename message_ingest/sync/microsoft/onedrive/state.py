"""Materialize a completed OneDrive full-resync attempt atomically."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from message_ingest.catalog.models.microsoft.onedrive import (
    OneDriveDeltaResyncAttempt,
    OneDriveDeltaResyncObservation,
    OneDriveItemRecord,
)
from message_ingest.items.microsoft.onedrive import OneDriveItem

_ITEM_GRAPH_FIELDS = {
    "name": "name",
    "size": "size",
    "created_date_time": "createdDateTime",
    "last_modified_date_time": "lastModifiedDateTime",
    "web_url": "webUrl",
    "e_tag": "eTag",
    "c_tag": "cTag",
    "parent_reference": "parentReference",
    "file": "file",
    "folder": "folder",
    "deleted": "deleted",
    "package": "package",
    "remote_item": "remoteItem",
    "file_system_info": "fileSystemInfo",
    "special_folder": "specialFolder",
}


def apply_onedrive_resync_state(
    session: Session,
    *,
    source_id: str,
    run_id: str,
    reset_attempt: int,
    base_revision: int,
    terminal_observed_at: str,
    terminal_evidence_id: str,
) -> tuple[int, int]:
    """Apply staged sightings and authoritative absence inside promotion."""
    attempt = session.get(
        OneDriveDeltaResyncAttempt, (source_id, run_id, reset_attempt)
    )
    if attempt is None or attempt.base_revision != base_revision:
        raise ValueError("OneDrive resync attempt does not match checkpoint base")
    observations = session.scalars(
        select(OneDriveDeltaResyncObservation)
        .filter_by(
            source_id=source_id,
            run_id=run_id,
            reset_attempt=reset_attempt,
            base_revision=base_revision,
        )
        .order_by(
            OneDriveDeltaResyncObservation.page_number,
            OneDriveDeltaResyncObservation.entry_index,
            OneDriveDeltaResyncObservation.observation_id,
        )
    ).all()
    seen: set[str] = set()
    applied = 0
    for observation in observations:
        seen.add(observation.item_id)
        item = OneDriveItem.from_graph(
            observation.raw,
            observed_at=observation.observed_at,
            evidence_id=observation.evidence_id,
            run_id=run_id,
        )
        record = session.get(OneDriveItemRecord, (source_id, item.id))
        if record is not None and _capture_time(item.observed_at) < _capture_time(
            record.latest_observed_at
        ):
            continue
        values = _item_values(source_id, item)
        if record is None:
            session.add(OneDriveItemRecord(**values))
            applied += 1
            continue
        if item.deleted is not None:
            for name, graph_name in _ITEM_GRAPH_FIELDS.items():
                if graph_name not in item.raw:
                    values.pop(name)
        for name, value in values.items():
            setattr(record, name, value)
        applied += 1

    absent = 0
    started_at = _capture_time(attempt.started_at)
    for record in session.scalars(
        select(OneDriveItemRecord).filter_by(source_id=source_id, is_deleted=False)
    ):
        if record.item_id in seen:
            continue
        # A newer concurrent metadata observation is outside this reset's
        # authority. Equal timestamps follow normal processing-order semantics.
        if _capture_time(record.latest_observed_at) > started_at:
            continue
        record.is_deleted = True
        record.latest_observed_at = terminal_observed_at
        record.latest_evidence_id = terminal_evidence_id
        record.latest_run_id = run_id
        absent += 1
    return applied, absent


def _item_values(source_id: str, item: OneDriveItem) -> dict[str, object]:
    """Project one sanitized provider observation into current-state columns."""
    values: dict[str, object] = {
        "source_id": source_id,
        "item_id": item.id,
        "is_deleted": item.deleted is not None,
        "latest_observed_at": item.observed_at,
        "latest_evidence_id": item.evidence_id,
        "latest_run_id": item.run_id,
        "raw": item.raw,
    }
    for name in _ITEM_GRAPH_FIELDS:
        values[name] = getattr(item, name)
    return values


def _capture_time(value: str) -> datetime:
    """Parse one timezone-aware persisted capture time."""
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("OneDrive observed_at must include a timezone offset")
    return parsed


__all__ = ["apply_onedrive_resync_state"]
