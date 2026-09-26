from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Integer, String, Text, UniqueConstraint, create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class RawHttpEvidence(Base):
    __tablename__ = "raw_http_evidence"

    evidence_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    run_id: Mapped[str | None] = mapped_column(String(32), index=True)
    purpose: Mapped[str | None] = mapped_column(String(80), index=True)
    request_url: Mapped[str] = mapped_column(Text)
    request_method: Mapped[str] = mapped_column(String(16))
    response_status: Mapped[int] = mapped_column(Integer)
    response_headers: Mapped[dict[str, list[str]]] = mapped_column(JSON)
    body_sha256: Mapped[str] = mapped_column(String(64), index=True)
    body_path: Mapped[str] = mapped_column(Text)
    body_bytes: Mapped[int] = mapped_column(Integer)
    observed_at: Mapped[str] = mapped_column(String(40), index=True)
    origin: Mapped[str] = mapped_column(String(24), index=True)


class MessageRecord(Base):
    __tablename__ = "messages"
    __table_args__ = (UniqueConstraint("source_id", "message_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    message_id: Mapped[str] = mapped_column(Text)
    subject: Mapped[str | None] = mapped_column(Text)
    internet_message_id: Mapped[str | None] = mapped_column(Text)
    conversation_id: Mapped[str | None] = mapped_column(Text)
    parent_folder_id: Mapped[str | None] = mapped_column(Text, index=True)
    received_date_time: Mapped[str | None] = mapped_column(String(40))
    last_modified_date_time: Mapped[str | None] = mapped_column(String(40))
    is_read: Mapped[bool | None] = mapped_column(Boolean)
    has_attachments: Mapped[bool | None] = mapped_column(Boolean)
    is_removed: Mapped[bool] = mapped_column(Boolean, default=False)
    latest_observed_at: Mapped[str] = mapped_column(String(40), index=True)
    latest_evidence_id: Mapped[str | None] = mapped_column(String(32), index=True)


class MessageObservation(Base):
    __tablename__ = "message_observations"

    observation_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    message_id: Mapped[str] = mapped_column(Text, index=True)
    run_id: Mapped[str | None] = mapped_column(String(32), index=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    evidence_id: Mapped[str | None] = mapped_column(String(32), index=True)
    observed_at: Mapped[str] = mapped_column(String(40), index=True)
    parent_folder_id: Mapped[str | None] = mapped_column(Text)
    last_modified_date_time: Mapped[str | None] = mapped_column(String(40))
    removed_reason: Mapped[str | None] = mapped_column(String(80))


class MessageSurface(Base):
    __tablename__ = "message_surfaces"
    __table_args__ = (UniqueConstraint("source_id", "message_id", "surface"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    message_id: Mapped[str] = mapped_column(Text, index=True)
    surface: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    evidence_id: Mapped[str | None] = mapped_column(String(32), index=True)
    observed_at: Mapped[str] = mapped_column(String(40))
    profile_version: Mapped[str | None] = mapped_column(String(40))


class MailFolderRecord(Base):
    __tablename__ = "mail_folders"
    __table_args__ = (UniqueConstraint("source_id", "folder_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    folder_id: Mapped[str] = mapped_column(Text)
    display_name: Mapped[str | None] = mapped_column(Text)
    parent_folder_id: Mapped[str | None] = mapped_column(Text, index=True)
    child_folder_count: Mapped[int | None] = mapped_column(Integer)
    total_item_count: Mapped[int | None] = mapped_column(Integer)
    unread_item_count: Mapped[int | None] = mapped_column(Integer)
    is_hidden: Mapped[bool | None] = mapped_column(Boolean)
    latest_observed_at: Mapped[str] = mapped_column(String(40))
    latest_evidence_id: Mapped[str | None] = mapped_column(String(32))


class DeltaCheckpoint(Base):
    __tablename__ = "delta_checkpoints"
    __table_args__ = (UniqueConstraint("source_id", "folder_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    folder_id: Mapped[str] = mapped_column(Text)
    delta_link: Mapped[str] = mapped_column(Text)
    committed_at: Mapped[str] = mapped_column(String(40))
    run_id: Mapped[str] = mapped_column(String(32), index=True)


class DeltaCheckpointCandidate(Base):
    __tablename__ = "delta_checkpoint_candidates"
    __table_args__ = (UniqueConstraint("run_id", "source_id", "folder_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(32), index=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    folder_id: Mapped[str] = mapped_column(Text)
    delta_link: Mapped[str] = mapped_column(Text)
    evidence_id: Mapped[str | None] = mapped_column(String(32))
    observed_at: Mapped[str] = mapped_column(String(40))
    committed_at: Mapped[str | None] = mapped_column(String(40))


class Catalog:
    """Small SQLAlchemy-backed local catalog/state store."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        url = make_url(database_url)
        if url.get_backend_name() != "sqlite":
            raise ValueError("The current local catalog implementation requires SQLite")
        database = url.database
        if database and database != ":memory:":
            path = Path(database)
            path.parent.mkdir(parents=True, exist_ok=True)
            os.chmod(path.parent, 0o700)

        self.engine = create_engine(
            database_url,
            connect_args={"autocommit": False, "timeout": 30.0},
            pool_size=1,
            max_overflow=0,
            pool_timeout=30.0,
        )
        self.Session: sessionmaker[Session] = sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
        )
        Base.metadata.create_all(self.engine)
        if database and database != ":memory:":
            os.chmod(Path(database), 0o600)

    def close(self) -> None:
        self.engine.dispose()

    def record_raw_http_evidence(
        self,
        *,
        source_id: str,
        run_id: str | None,
        purpose: str | None,
        request_url: str,
        request_method: str,
        response_status: int,
        response_headers: dict[str, list[str]],
        body_sha256: str,
        body_path: str,
        body_bytes: int,
        observed_at: str,
        origin: str,
    ) -> str:
        evidence_id = uuid4().hex
        with self.Session.begin() as session:
            session.add(
                RawHttpEvidence(
                    evidence_id=evidence_id,
                    source_id=source_id,
                    run_id=run_id,
                    purpose=purpose,
                    request_url=request_url,
                    request_method=request_method,
                    response_status=response_status,
                    response_headers=response_headers,
                    body_sha256=body_sha256,
                    body_path=body_path,
                    body_bytes=body_bytes,
                    observed_at=observed_at,
                    origin=origin,
                )
            )
        return evidence_id

    def find_raw_http_evidence(
        self, *, source_id: str, request_url: str, body_sha256: str
    ) -> str | None:
        with self.Session() as session:
            stmt = (
                select(RawHttpEvidence.evidence_id)
                .where(
                    RawHttpEvidence.source_id == source_id,
                    RawHttpEvidence.request_url == request_url,
                    RawHttpEvidence.body_sha256 == body_sha256,
                )
                .order_by(RawHttpEvidence.observed_at.desc())
                .limit(1)
            )
            return session.scalar(stmt)

    def record_message(
        self,
        *,
        source_id: str,
        run_id: str | None,
        message: dict[str, Any],
        kind: str,
        evidence_id: str | None,
        observed_at: str,
        removed_reason: str | None = None,
    ) -> None:
        message_id = message["id"]
        with self.Session.begin() as session:
            record = session.scalar(
                select(MessageRecord).where(
                    MessageRecord.source_id == source_id,
                    MessageRecord.message_id == message_id,
                )
            )
            if record is None:
                record = MessageRecord(
                    source_id=source_id,
                    message_id=message_id,
                    latest_observed_at=observed_at,
                    is_removed=removed_reason is not None,
                )
                session.add(record)

            record.subject = message.get("subject", record.subject)
            record.internet_message_id = message.get(
                "internetMessageId", record.internet_message_id
            )
            record.conversation_id = message.get("conversationId", record.conversation_id)
            record.parent_folder_id = message.get("parentFolderId", record.parent_folder_id)
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
            record.is_removed = removed_reason is not None
            record.latest_observed_at = observed_at
            record.latest_evidence_id = evidence_id

            session.add(
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
                    removed_reason=removed_reason,
                )
            )

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
        with self.Session.begin() as session:
            record = session.scalar(
                select(MessageSurface).where(
                    MessageSurface.source_id == source_id,
                    MessageSurface.message_id == message_id,
                    MessageSurface.surface == surface,
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
            else:
                record.status = status
                record.evidence_id = evidence_id
                record.observed_at = observed_at
                record.profile_version = profile_version

    def upsert_folder(
        self,
        *,
        source_id: str,
        folder: dict[str, Any],
        evidence_id: str | None,
        observed_at: str,
    ) -> None:
        folder_id = folder["id"]
        with self.Session.begin() as session:
            record = session.scalar(
                select(MailFolderRecord).where(
                    MailFolderRecord.source_id == source_id,
                    MailFolderRecord.folder_id == folder_id,
                )
            )
            if record is None:
                record = MailFolderRecord(
                    source_id=source_id,
                    folder_id=folder_id,
                    latest_observed_at=observed_at,
                )
                session.add(record)
            record.display_name = folder.get("displayName")
            record.parent_folder_id = folder.get("parentFolderId")
            record.child_folder_count = folder.get("childFolderCount")
            record.total_item_count = folder.get("totalItemCount")
            record.unread_item_count = folder.get("unreadItemCount")
            record.is_hidden = folder.get("isHidden")
            record.latest_observed_at = observed_at
            record.latest_evidence_id = evidence_id

    def get_delta_link(self, *, source_id: str, folder_id: str) -> str | None:
        with self.Session() as session:
            return session.scalar(
                select(DeltaCheckpoint.delta_link).where(
                    DeltaCheckpoint.source_id == source_id,
                    DeltaCheckpoint.folder_id == folder_id,
                )
            )

    def get_delta_links(self, *, source_id: str) -> dict[str, str]:
        with self.Session() as session:
            rows = session.execute(
                select(DeltaCheckpoint.folder_id, DeltaCheckpoint.delta_link).where(
                    DeltaCheckpoint.source_id == source_id
                )
            ).all()
            return {folder_id: delta_link for folder_id, delta_link in rows}

    def write_delta_candidate(
        self,
        *,
        run_id: str,
        source_id: str,
        folder_id: str,
        delta_link: str,
        evidence_id: str | None,
        observed_at: str,
    ) -> None:
        with self.Session.begin() as session:
            record = session.scalar(
                select(DeltaCheckpointCandidate).where(
                    DeltaCheckpointCandidate.run_id == run_id,
                    DeltaCheckpointCandidate.source_id == source_id,
                    DeltaCheckpointCandidate.folder_id == folder_id,
                )
            )
            if record is None:
                record = DeltaCheckpointCandidate(
                    run_id=run_id,
                    source_id=source_id,
                    folder_id=folder_id,
                    delta_link=delta_link,
                    evidence_id=evidence_id,
                    observed_at=observed_at,
                )
                session.add(record)
            else:
                record.delta_link = delta_link
                record.evidence_id = evidence_id
                record.observed_at = observed_at

    def load_delta_candidates(
        self, *, run_id: str, source_id: str
    ) -> dict[str, DeltaCheckpointCandidate]:
        with self.Session() as session:
            rows = session.scalars(
                select(DeltaCheckpointCandidate).where(
                    DeltaCheckpointCandidate.run_id == run_id,
                    DeltaCheckpointCandidate.source_id == source_id,
                )
            ).all()
            return {row.folder_id: row for row in rows}

    def commit_delta_candidates(
        self, *, run_id: str, source_id: str, committed_at: str
    ) -> int:
        with self.Session.begin() as session:
            candidates = session.scalars(
                select(DeltaCheckpointCandidate).where(
                    DeltaCheckpointCandidate.run_id == run_id,
                    DeltaCheckpointCandidate.source_id == source_id,
                )
            ).all()
            for candidate in candidates:
                checkpoint = session.scalar(
                    select(DeltaCheckpoint).where(
                        DeltaCheckpoint.source_id == source_id,
                        DeltaCheckpoint.folder_id == candidate.folder_id,
                    )
                )
                if checkpoint is None:
                    checkpoint = DeltaCheckpoint(
                        source_id=source_id,
                        folder_id=candidate.folder_id,
                        delta_link=candidate.delta_link,
                        committed_at=committed_at,
                        run_id=run_id,
                    )
                    session.add(checkpoint)
                else:
                    checkpoint.delta_link = candidate.delta_link
                    checkpoint.committed_at = committed_at
                    checkpoint.run_id = run_id
                candidate.committed_at = committed_at
            return len(candidates)
