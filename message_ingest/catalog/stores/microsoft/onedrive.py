"""Current OneDrive state, staged resync, content linkage, and checkpoints."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal, cast

from sqlalchemy import CursorResult, select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.models.microsoft.onedrive import (
    OneDriveContentCapture,
    OneDriveContentRecord,
    OneDriveDeltaCheckpoint,
    OneDriveDeltaCheckpointCandidate,
    OneDriveDeltaResyncAttempt,
    OneDriveDeltaResyncObservation,
    OneDriveDriveRecord,
    OneDriveItemRecord,
    OneDriveRecord,
)
from message_ingest.catalog.stores.microsoft.onedrive_content import (
    content_freshness,
    load_item_versions,
)
from message_ingest.items.microsoft.onedrive import (
    OneDriveContentItem,
    OneDriveDeltaCheckpointCandidateItem,
    OneDriveDeltaResyncAttemptItem,
    OneDriveDeltaResyncObservationItem,
    OneDriveDriveItem,
    OneDriveItem,
)
from message_ingest.sync.microsoft.onedrive import apply_onedrive_resync_state

if TYPE_CHECKING:
    from message_ingest.catalog import Catalog

type Outcome = Literal["created", "changed", "unchanged", "stale"]
type Observation = OneDriveDriveItem | OneDriveItem | OneDriveContentItem

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
    """Persist source-scoped state without treating partial reset as current."""

    def __init__(self, catalog: Catalog, *, source_id: str) -> None:
        self.catalog = catalog
        self.source_id = source_id

    def persist_drive(self, item: OneDriveDriveItem) -> Outcome:
        """Replace drive metadata only with an equal or later observation."""
        return self._upsert(OneDriveDriveRecord, item, {"drive_id": item.id})

    def persist_item(self, item: OneDriveItem) -> Outcome:
        """Keep omitted metadata across provider tombstones."""
        return self._upsert(
            OneDriveItemRecord,
            item,
            {"item_id": item.id, "is_deleted": item.deleted is not None},
        )

    def persist_content(self, item: OneDriveContentItem) -> Outcome:
        """Update latest content and append its metadata-version association."""
        self._capture_time(item.observed_at)
        if not isinstance(item.evidence_id, str) or not item.evidence_id:
            raise ValueError("OneDrive content requires linked evidence")
        with self.catalog.writer_session() as session:
            outcome = self._upsert_session(session, OneDriveContentRecord, item, {})
            self._append_content_capture(session, item)
            return outcome

    def load_item_versions(self, item_ids: tuple[str, ...]):
        """Return metadata facts known before explicit content requests."""
        return load_item_versions(
            self.catalog, source_id=self.source_id, item_ids=item_ids
        )

    def content_freshness(self, item_id: str):
        """Prove whether the latest explicit content matches current metadata."""
        return content_freshness(
            self.catalog, source_id=self.source_id, item_id=item_id
        )

    def persist_resync_attempt(self, item: OneDriveDeltaResyncAttemptItem) -> Outcome:
        """Stage one durable reset start without changing current state."""
        if item.reset_attempt != 1 or not isinstance(item.base_revision, int):
            raise ValueError("OneDrive resync requires reset attempt 1 and a base")
        self._capture_time(item.started_at)
        if not isinstance(item.run_id, str) or not item.run_id:
            raise ValueError("OneDrive resync requires a run_id")
        if (
            not isinstance(item.trigger_evidence_id, str)
            or not item.trigger_evidence_id
        ):
            raise ValueError("OneDrive resync requires trigger evidence")
        values = {
            "source_id": self.source_id,
            "run_id": item.run_id,
            "reset_attempt": item.reset_attempt,
            "base_revision": item.base_revision,
            "started_at": item.started_at,
            "trigger_evidence_id": item.trigger_evidence_id,
        }
        with self.catalog.writer_session() as session:
            self._require_evidence(session, item.trigger_evidence_id, item.run_id)
            record = session.get(
                OneDriveDeltaResyncAttempt,
                (self.source_id, item.run_id, item.reset_attempt),
            )
            if record is None:
                session.add(OneDriveDeltaResyncAttempt(**values))
                return "created"
            if any(getattr(record, name) != value for name, value in values.items()):
                raise ValueError("OneDrive run already has a different resync attempt")
            return "unchanged"

    def persist_resync_observation(
        self, item: OneDriveDeltaResyncObservationItem
    ) -> Outcome:
        """Append one ordered reset sighting without touching current metadata."""
        self._validate_resync_observation(item)
        values = {
            "source_id": self.source_id,
            "run_id": item.run_id,
            "reset_attempt": item.reset_attempt,
            "base_revision": item.base_revision,
            "item_id": item.id,
            "page_number": item.page_number,
            "entry_index": item.entry_index,
            "observed_at": item.observed_at,
            "evidence_id": item.evidence_id,
            "raw": item.raw,
        }
        with self.catalog.writer_session() as session:
            self._require_evidence(session, item.evidence_id, item.run_id)
            record = session.scalar(
                select(OneDriveDeltaResyncObservation).filter_by(
                    source_id=self.source_id,
                    run_id=item.run_id,
                    reset_attempt=item.reset_attempt,
                    page_number=item.page_number,
                    entry_index=item.entry_index,
                )
            )
            if record is None:
                session.add(OneDriveDeltaResyncObservation(**values))
                return "created"
            if any(getattr(record, name) != value for name, value in values.items()):
                raise ValueError("OneDrive resync position changed during replay")
            return "unchanged"

    def _upsert(
        self,
        model: type[OneDriveRecord],
        item: Observation,
        overrides: dict[str, object],
    ) -> Outcome:
        """Commit one current observation in its own transaction."""
        self._capture_time(item.observed_at)
        with self.catalog.writer_session() as session:
            return self._upsert_session(session, model, item, overrides)

    def _upsert_session(
        self,
        session: Session,
        model: type[OneDriveRecord],
        item: Observation,
        overrides: dict[str, object],
    ) -> Outcome:
        """Apply latest-capture semantics inside the caller's transaction."""
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

    def _append_content_capture(
        self, session: Session, item: OneDriveContentItem
    ) -> None:
        """Insert one immutable capture/version association idempotently."""
        values = {
            "source_id": self.source_id,
            "evidence_id": item.evidence_id,
            "item_id": item.item_id,
            "content_sha256": item.content_sha256,
            "content_bytes": item.content_bytes,
            "planned_metadata_observed_at": item.planned_metadata_observed_at,
            "planned_metadata_evidence_id": item.planned_metadata_evidence_id,
            "planned_e_tag": item.planned_e_tag,
            "planned_c_tag": item.planned_c_tag,
            "response_e_tag": item.response_e_tag,
            "observed_at": item.observed_at,
            "run_id": item.run_id,
        }
        record = session.get(OneDriveContentCapture, (self.source_id, item.evidence_id))
        if record is None:
            session.add(OneDriveContentCapture(**values))
            return
        if any(getattr(record, name) != value for name, value in values.items()):
            raise ValueError("OneDrive content capture evidence cannot be rewritten")

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
        with self.catalog.writer_session() as session:
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

    def load_candidate(
        self, *, run_id: str, base_revision: int | None
    ) -> OneDriveDeltaCheckpointCandidate | None:
        """Load only the exact terminal candidate expected by this run."""
        with self.catalog.Session() as session:
            candidate = session.get(
                OneDriveDeltaCheckpointCandidate, (self.source_id, run_id)
            )
            if candidate is None or candidate.base_revision != base_revision:
                return None
            session.expunge(candidate)
            return candidate

    def load_checkpoint(self) -> OneDriveDeltaCheckpoint | None:
        """Return only a committed cursor; pending candidates never resume."""
        with self.catalog.Session() as session:
            checkpoint = session.get(OneDriveDeltaCheckpoint, self.source_id)
            if checkpoint is not None:
                session.expunge(checkpoint)
            return checkpoint

    def promote_checkpoint(
        self,
        *,
        run_id: str,
        base_revision: int | None,
        reset_attempt: int | None = None,
    ) -> OneDriveDeltaCheckpoint:
        """Atomically materialize a winning reset, then advance its exact cursor."""
        with self.catalog.writer_session() as session:
            candidate = session.get(
                OneDriveDeltaCheckpointCandidate, (self.source_id, run_id)
            )
            if candidate is None:
                raise ValueError("OneDrive terminal checkpoint candidate is missing")
            if candidate.base_revision != base_revision:
                raise ValueError("OneDrive candidate base revision does not match")
            self._require_evidence(session, candidate.evidence_id, run_id)
            revision = 1 if base_revision is None else base_revision + 1
            current = session.get(OneDriveDeltaCheckpoint, self.source_id)
            if (
                current is not None
                and current.revision == revision
                and current.run_id == run_id
                and current.delta_link == candidate.delta_link
            ):
                session.expunge(current)
                return current
            values = {
                "source_id": self.source_id,
                "delta_link": candidate.delta_link,
                "revision": revision,
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
            if reset_attempt is not None:
                if base_revision is None:
                    raise ValueError("OneDrive resync requires an existing checkpoint")
                apply_onedrive_resync_state(
                    session,
                    source_id=self.source_id,
                    run_id=run_id,
                    reset_attempt=reset_attempt,
                    base_revision=base_revision,
                    terminal_observed_at=candidate.observed_at,
                    terminal_evidence_id=candidate.evidence_id,
                )
            return OneDriveDeltaCheckpoint(**values)

    def _validate_resync_observation(
        self, item: OneDriveDeltaResyncObservationItem
    ) -> None:
        """Reject malformed reset ordering/provenance before persistence."""
        self._capture_time(item.observed_at)
        if item.reset_attempt != 1 or item.page_number < 1 or item.entry_index < 0:
            raise ValueError("OneDrive resync observation has invalid ordering")
        if not isinstance(item.base_revision, int) or item.base_revision < 1:
            raise ValueError("OneDrive resync observation requires a base revision")
        for name in ("run_id", "evidence_id"):
            value = getattr(item, name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"OneDrive resync observation requires {name}")

    def _require_evidence(
        self, session: Session, evidence_id: str | None, run_id: str | None
    ) -> None:
        """Reject missing or unrelated evidence before durable state changes."""
        evidence = session.get(RawHttpEvidence, evidence_id)
        if (
            evidence is None
            or evidence.source_id != self.source_id
            or evidence.run_id != run_id
        ):
            raise ValueError(
                "OneDrive durable state requires this run's committed evidence"
            )

    @staticmethod
    def _capture_time(value: str) -> datetime:
        """Parse an observation instant without lexical timestamp ordering."""
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("OneDrive observed_at must include a timezone offset")
        return parsed


__all__ = ["OneDriveStore"]
