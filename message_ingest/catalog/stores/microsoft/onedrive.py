"""Current OneDrive state and evidence-backed delta cursor promotion."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal, cast

from sqlalchemy import CursorResult, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.models.microsoft.onedrive import (
    OneDriveContentRecord,
    OneDriveDeltaCheckpoint,
    OneDriveDeltaCheckpointCandidate,
    OneDriveDriveRecord,
    OneDriveItemRecord,
    OneDriveRecord,
)
from message_ingest.items.microsoft.onedrive import (
    OneDriveContentItem,
    OneDriveDeltaCheckpointCandidateItem,
    OneDriveDriveItem,
    OneDriveItem,
)

if TYPE_CHECKING:
    from message_ingest.catalog import Catalog

type Outcome = Literal["created", "changed", "unchanged", "stale"]
type Observation = OneDriveDriveItem | OneDriveItem | OneDriveContentItem

# Tombstones preserve only omitted fields. Presence checks use Graph names;
# values still come from the provider projection, including null/falsey values.
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


class OneDriveStore:
    """Persist source-scoped state without inferring absent-item deletion."""

    def __init__(self, catalog: Catalog, *, source_id: str) -> None:
        self.catalog = catalog
        self.source_id = source_id

    def persist_drive(self, item: OneDriveDriveItem) -> Outcome:
        """Replace drive metadata only with an equal or later observation."""
        return self._upsert(OneDriveDriveRecord, item, {"drive_id": item.id})

    def persist_item(self, item: OneDriveItem) -> Outcome:
        """Keep omitted metadata across tombstones, including empty facets."""
        return self._upsert(
            OneDriveItemRecord,
            item,
            {"item_id": item.id, "is_deleted": item.deleted is not None},
        )

    def persist_content(self, item: OneDriveContentItem) -> Outcome:
        """Store the latest explicit digest and size without body bytes."""
        return self._upsert(OneDriveContentRecord, item, {})

    def _upsert(
        self,
        model: type[OneDriveRecord],
        item: Observation,
        overrides: dict[str, object],
    ) -> Outcome:
        """
        Commit one observation with timezone-aware capture ordering.

        Equal capture times use processing order. The caller serializes writes
        with the shared catalog lock. No discovery absence removes state.
        """
        observed = self._capture_time(item.observed_at)
        provenance = {
            "source_id": self.source_id,
            "latest_observed_at": item.observed_at,
            "latest_evidence_id": item.evidence_id,
            "latest_run_id": item.run_id,
        }
        values = {
            column.name: (
                overrides[column.name]
                if column.name in overrides
                else getattr(item, column.name)
            )
            for column in model.__table__.columns
            if column.name not in provenance
        }
        values.update(provenance)
        identity = {
            column.name: values[column.name] for column in model.__mapper__.primary_key
        }
        with self.catalog.Session() as session, session.begin():
            record = session.get(model, identity)
            if record is None:
                session.add(model(**values))
                return "created"
            if observed < self._capture_time(record.latest_observed_at):
                return "stale"
            if isinstance(item, OneDriveItem) and item.deleted is not None:
                for name, graph_name in _ITEM_GRAPH_FIELDS.items():
                    if graph_name not in item.raw:
                        values.pop(name)
            changed = any(
                getattr(record, name) != value
                for name, value in values.items()
                if name not in provenance
            )
            for name, value in values.items():
                setattr(record, name, value)
            return "changed" if changed else "unchanged"

    def persist_candidate(self, item: OneDriveDeltaCheckpointCandidateItem) -> Outcome:
        """Stage one terminal cursor after committing its evidence."""
        self._capture_time(item.observed_at)
        for name in ("run_id", "evidence_id", "delta_link"):
            value = getattr(item, name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"OneDrive candidate requires a non-empty {name}")
        if item.base_revision is not None and (
            isinstance(item.base_revision, bool)
            or not isinstance(item.base_revision, int)
            or item.base_revision < 1
        ):
            raise ValueError("OneDrive base_revision must be positive or None")
        values = {
            "source_id": self.source_id,
            "run_id": item.run_id,
            "base_revision": item.base_revision,
            "delta_link": item.delta_link,
            "evidence_id": item.evidence_id,
            "observed_at": item.observed_at,
        }
        with self.catalog.Session() as session, session.begin():
            self._require_evidence(session, item.evidence_id, item.run_id)
            record = session.get(
                OneDriveDeltaCheckpointCandidate, (self.source_id, item.run_id)
            )
            if record is None:
                session.add(OneDriveDeltaCheckpointCandidate(**values))
                return "created"
            if any(getattr(record, name) != value for name, value in values.items()):
                raise ValueError(
                    "OneDrive run already has a different terminal candidate"
                )
            return "unchanged"

    def load_checkpoint(self) -> OneDriveDeltaCheckpoint | None:
        """Return only a committed cursor; pending candidates never resume."""
        with self.catalog.Session() as session:
            return session.get(OneDriveDeltaCheckpoint, self.source_id)

    def promote_checkpoint(
        self, *, run_id: str, base_revision: int | None
    ) -> OneDriveDeltaCheckpoint:
        """
        Advance a cursor only from the run's exact starting revision.

        The Scrapy lifecycle caller must first prove terminal traversal and a
        clean run after item work drains. This transaction verifies committed
        evidence and uses an atomic revision comparison to reject stale runs.
        SQLite write conflicts also fail closed; the prior cursor survives.
        """
        with self.catalog.Session() as session, session.begin():
            candidate = session.get(
                OneDriveDeltaCheckpointCandidate, (self.source_id, run_id)
            )
            if candidate is None:
                raise ValueError("OneDrive terminal checkpoint candidate is missing")
            if candidate.base_revision != base_revision:
                raise ValueError("OneDrive candidate base revision does not match")
            self._require_evidence(session, candidate.evidence_id, run_id)
            values = {
                "source_id": self.source_id,
                "delta_link": candidate.delta_link,
                "revision": 1 if base_revision is None else base_revision + 1,
                "observed_at": candidate.observed_at,
                "evidence_id": candidate.evidence_id,
                "run_id": run_id,
            }
            if base_revision is None:
                statement = (
                    insert(OneDriveDeltaCheckpoint)
                    .values(**values)
                    .on_conflict_do_nothing(index_elements=["source_id"])
                )
            else:
                statement = (
                    update(OneDriveDeltaCheckpoint)
                    .where(
                        OneDriveDeltaCheckpoint.source_id == self.source_id,
                        OneDriveDeltaCheckpoint.revision == base_revision,
                    )
                    .values(**values)
                )
            result = cast(CursorResult, session.execute(statement))
            if result.rowcount != 1:
                raise ValueError(
                    "OneDrive checkpoint revision changed before promotion"
                )
            return OneDriveDeltaCheckpoint(**values)

    def _require_evidence(
        self, session: Session, evidence_id: str | None, run_id: str | None
    ) -> None:
        """Reject missing or unrelated evidence before cursor persistence."""
        evidence = session.get(RawHttpEvidence, evidence_id)
        if (
            evidence is None
            or evidence.source_id != self.source_id
            or evidence.run_id != run_id
        ):
            raise ValueError(
                "OneDrive candidate requires this run's committed evidence"
            )

    @staticmethod
    def _capture_time(value: str) -> datetime:
        """Parse an observation instant without lexical timestamp ordering."""
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("OneDrive observed_at must include a timezone offset")
        return parsed


__all__ = ["OneDriveStore"]
