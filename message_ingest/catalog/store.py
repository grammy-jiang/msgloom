"""Transactional persistence and queries for the local Outlook catalog."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from message_ingest.catalog.models import (
    AttachmentRecord,
    MailFolderRecord,
    MessageObservation,
    MessageRecord,
    MessageSurface,
    RawHttpEvidence,
)
from message_ingest.catalog.schema import initialize_schema


class Catalog:
    """
    Own the SQLite engine and transactional evidence/entity operations.

    Callers offload blocking operations to worker threads and serialize writes
    with the crawler's lock. Each method owns a short session/transaction;
    returned values must remain usable after that session closes. Checkpoint
    promotion lives in the source-scoped
    :class:`~message_ingest.sync.microsoft.outlook.email.checkpoints.OutlookDeltaCheckpointStore`.
    """

    def __init__(self, database_url: str) -> None:
        """
        Create the SQLite schema and restrict local file permissions.

        Schema creation takes SQLite's writer lock before inspecting tables,
        so independent catalogs can safely add missing tables at startup.
        The one-connection pool serializes access within this catalog.
        ``expire_on_commit=False`` keeps returned ORM values readable after a
        session closes; do not return lazy relations.
        """
        self.database_url = database_url
        url = make_url(database_url)
        if url.get_backend_name() != "sqlite":
            raise ValueError("The current local catalog implementation requires SQLite")
        database = url.database
        in_memory = not database or database == ":memory:"
        if database and not in_memory:
            path = Path(database)
            path.parent.mkdir(parents=True, exist_ok=True)
            os.chmod(path.parent, 0o700)

        schema_image = initialize_schema(database_url, in_memory=in_memory)
        self.engine = create_engine(
            database_url,
            connect_args={
                "autocommit": False,
                "timeout": 30.0,
                **({"check_same_thread": False} if in_memory else {}),
            },
            **({"poolclass": QueuePool} if in_memory else {}),
            pool_size=1,
            max_overflow=0,
            pool_timeout=30.0,
        )
        if schema_image is not None:
            # Retain one private database across checkouts and worker threads.
            # Only the schema image crosses from startup to runtime; no driver
            # connection or transaction state is reused.
            try:
                with self.engine.connect() as connection:
                    driver = cast(
                        sqlite3.Connection, connection.connection.driver_connection
                    )
                    driver.deserialize(schema_image)
            except BaseException:
                self.engine.dispose()
                raise
        self.Session: sessionmaker[Session] = sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
        )
        if database and not in_memory:
            os.chmod(Path(database), 0o600)

    def close(self) -> None:
        """Dispose the engine after outstanding pipeline work finishes."""
        self.engine.dispose()

    def record_raw_http_evidence(self, evidence: RawHttpEvidence) -> str:
        """
        Insert an HTTP capture once, retaining the original row on replay.
        """
        with self.Session() as session, session.begin():
            existing = session.get(RawHttpEvidence, evidence.evidence_id)
            if existing is not None:
                return existing.evidence_id
            session.add(evidence)
        return evidence.evidence_id

    def find_raw_http_evidence(
        self,
        *,
        source_id: str,
        request_fingerprint: str,
        response_body_sha256: str,
    ) -> tuple[str, str] | None:
        """
        Find the latest matching response capture for cache aliasing.

        Transport failures cannot serve as cached response evidence.
        """
        with self.Session() as session:
            stmt = (
                select(RawHttpEvidence.evidence_id, RawHttpEvidence.observed_at)
                .where(
                    RawHttpEvidence.source_id == source_id,
                    RawHttpEvidence.request_fingerprint == request_fingerprint,
                    RawHttpEvidence.response_body_sha256 == response_body_sha256,
                    RawHttpEvidence.response_status.is_not(None),
                )
                .order_by(RawHttpEvidence.observed_at.desc())
                .limit(1)
            )
            row = session.execute(stmt).first()
            if row is None:
                return None
            return row.evidence_id, row.observed_at

    def has_raw_http_evidence(self, evidence_id: str) -> bool:
        """Return whether *evidence_id* references a committed capture."""
        with self.Session() as session:
            return session.get(RawHttpEvidence, evidence_id) is not None

    def record_message(
        self,
        *,
        source_id: str,
        run_id: str | None,
        message: dict[str, Any],
        kind: str,
        evidence_id: str | None,
        observed_at: str,
    ) -> bool:
        """
        Record a message and its observation in one transaction.

        Older captures cannot overwrite current state. Missing fields leave
        existing values intact because discovery and full-detail responses
        select different fields. The return value reports whether a new
        observation was added, not whether current state changed. Even a replay
        may refresh the current projection before deduplication.
        """
        message_id = message["id"]
        with self.Session() as session, session.begin():
            record = session.scalar(
                select(MessageRecord).filter_by(
                    source_id=source_id,
                    message_id=message_id,
                )
            )
            if record is None:
                record = MessageRecord(
                    source_id=source_id,
                    message_id=message_id,
                    latest_observed_at=observed_at,
                    is_removed=False,
                )
                session.add(record)

            if datetime.fromisoformat(observed_at) >= datetime.fromisoformat(
                record.latest_observed_at
            ):
                record.subject = message.get("subject", record.subject)
                record.internet_message_id = message.get(
                    "internetMessageId", record.internet_message_id
                )
                record.conversation_id = message.get(
                    "conversationId", record.conversation_id
                )
                record.parent_folder_id = message.get(
                    "parentFolderId", record.parent_folder_id
                )
                record.received_date_time = message.get(
                    "receivedDateTime", record.received_date_time
                )
                record.last_modified_date_time = message.get(
                    "lastModifiedDateTime", record.last_modified_date_time
                )
                if "isRead" in message:
                    record.is_read = message.get("isRead")
                if "hasAttachments" in message:
                    record.has_attachments = message.get("hasAttachments")
                # A concrete message representation confirms that the message
                # exists. Folder-level @removed events are recorded separately.
                record.is_removed = False
                record.latest_observed_at = observed_at
                record.latest_evidence_id = evidence_id

            return self._add_observation(
                session,
                MessageObservation(
                    observation_id=uuid4().hex,
                    source_id=source_id,
                    message_id=message_id,
                    run_id=run_id,
                    kind=kind,
                    evidence_id=evidence_id,
                    observed_at=observed_at,
                    parent_folder_id=message.get("parentFolderId"),
                    last_modified_date_time=message.get("lastModifiedDateTime"),
                    removed_reason=None,
                ),
            )

    def record_folder_removal(
        self,
        *,
        source_id: str,
        run_id: str | None,
        message_id: str,
        folder_id: str,
        removed_reason: str | None,
        evidence_id: str | None,
        observed_at: str,
    ) -> bool:
        """Record removal from one folder without inferring global deletion."""
        with self.Session() as session, session.begin():
            return self._add_observation(
                session,
                MessageObservation(
                    observation_id=uuid4().hex,
                    source_id=source_id,
                    message_id=message_id,
                    run_id=run_id,
                    kind="folder_removed",
                    evidence_id=evidence_id,
                    observed_at=observed_at,
                    parent_folder_id=folder_id,
                    last_modified_date_time=None,
                    removed_reason=removed_reason,
                ),
            )

    @staticmethod
    def _add_observation(session: Session, observation: MessageObservation) -> bool:
        """
        Deduplicate the same source/message/kind/evidence, independent of run
        ID.

        Without an evidence ID there is no reliable replay key, so each
        observation is retained. Folder-removal observations use the same rule
        as message observations.
        """
        if observation.evidence_id is not None:
            existing = session.scalar(
                select(MessageObservation).filter_by(
                    source_id=observation.source_id,
                    message_id=observation.message_id,
                    kind=observation.kind,
                    evidence_id=observation.evidence_id,
                )
            )
            if existing is not None:
                return False
        session.add(observation)
        return True

    def set_message_surface(
        self,
        *,
        source_id: str,
        message_id: str,
        surface: str,
        status: str,
        evidence_id: str | None,
        observed_at: str,
        profile_version: str | None = None,
    ) -> None:
        """
        Upsert one profile surface without letting older evidence replace its
        latest status.
        """
        with self.Session() as session, session.begin():
            record = session.scalar(
                select(MessageSurface).filter_by(
                    source_id=source_id,
                    message_id=message_id,
                    surface=surface,
                )
            )
            if record is None:
                record = MessageSurface(
                    source_id=source_id,
                    message_id=message_id,
                    surface=surface,
                    status=status,
                    evidence_id=evidence_id,
                    observed_at=observed_at,
                    profile_version=profile_version,
                )
                session.add(record)
                return
            if datetime.fromisoformat(observed_at) < datetime.fromisoformat(
                record.observed_at
            ):
                return
            record.status = status
            record.evidence_id = evidence_id
            record.observed_at = observed_at
            record.profile_version = profile_version

    def upsert_attachment(
        self,
        *,
        source_id: str,
        message_id: str,
        attachment: dict[str, Any],
        evidence_id: str | None,
        observed_at: str,
    ) -> None:
        """Keep the newest metadata for one source/message/attachment key."""
        attachment_id = attachment["id"]
        with self.Session() as session, session.begin():
            record = session.scalar(
                select(AttachmentRecord).filter_by(
                    source_id=source_id,
                    message_id=message_id,
                    attachment_id=attachment_id,
                )
            )
            if record is None:
                record = AttachmentRecord(
                    source_id=source_id,
                    message_id=message_id,
                    attachment_id=attachment_id,
                    latest_observed_at=observed_at,
                )
                session.add(record)
            if datetime.fromisoformat(observed_at) < datetime.fromisoformat(
                record.latest_observed_at
            ):
                return
            record.attachment_type = attachment.get("@odata.type")
            record.name = attachment.get("name")
            record.content_type = attachment.get("contentType")
            record.size = attachment.get("size")
            record.is_inline = attachment.get("isInline")
            record.latest_observed_at = observed_at
            record.latest_evidence_id = evidence_id

    def get_message_state(
        self, *, source_id: str, message_id: str
    ) -> dict[str, Any] | None:
        """
        Return detached message state, or ``None`` for an unknown message.
        """
        with self.Session() as session:
            row = session.scalar(
                select(MessageRecord).filter_by(
                    source_id=source_id,
                    message_id=message_id,
                )
            )
            if row is None:
                return None
            return {
                "message_id": row.message_id,
                "has_attachments": row.has_attachments,
                "is_removed": row.is_removed,
                "latest_observed_at": row.latest_observed_at,
                "latest_evidence_id": row.latest_evidence_id,
            }

    def get_message_surfaces(
        self, *, source_id: str, message_id: str
    ) -> dict[str, dict[str, Any]]:
        """
        Return detached surface statuses and profile versions for enrichment
        planning.
        """
        with self.Session() as session:
            rows = session.scalars(
                select(MessageSurface).filter_by(
                    source_id=source_id,
                    message_id=message_id,
                )
            ).all()
            return {
                row.surface: {
                    "status": row.status,
                    "evidence_id": row.evidence_id,
                    "observed_at": row.observed_at,
                    "profile_version": row.profile_version,
                }
                for row in rows
            }

    def get_attachments(
        self, *, source_id: str, message_id: str
    ) -> list[dict[str, Any]]:
        """
        Return detached attachment metadata and evidence needed to plan child
        surfaces.
        """
        with self.Session() as session:
            rows = session.scalars(
                select(AttachmentRecord).filter_by(
                    source_id=source_id,
                    message_id=message_id,
                )
            ).all()
            return [
                {
                    "attachment_id": row.attachment_id,
                    "attachment_type": row.attachment_type,
                    "name": row.name,
                    "content_type": row.content_type,
                    "size": row.size,
                    "is_inline": row.is_inline,
                    "latest_observed_at": row.latest_observed_at,
                    "latest_evidence_id": row.latest_evidence_id,
                }
                for row in rows
            ]

    def upsert_folder(
        self,
        *,
        source_id: str,
        folder: dict[str, Any],
        evidence_id: str | None,
        observed_at: str,
    ) -> None:
        """
        Keep the latest observed folder metadata; discovery does not infer
        deletion.
        """
        folder_id = folder["id"]
        with self.Session() as session, session.begin():
            record = session.scalar(
                select(MailFolderRecord).filter_by(
                    source_id=source_id,
                    folder_id=folder_id,
                )
            )
            if record is None:
                record = MailFolderRecord(
                    source_id=source_id,
                    folder_id=folder_id,
                    latest_observed_at=observed_at,
                )
                session.add(record)
            if datetime.fromisoformat(observed_at) < datetime.fromisoformat(
                record.latest_observed_at
            ):
                return
            record.display_name = folder.get("displayName")
            record.parent_folder_id = folder.get("parentFolderId")
            record.child_folder_count = folder.get("childFolderCount")
            record.total_item_count = folder.get("totalItemCount")
            record.unread_item_count = folder.get("unreadItemCount")
            record.is_hidden = folder.get("isHidden")
            record.latest_observed_at = observed_at
            record.latest_evidence_id = evidence_id
