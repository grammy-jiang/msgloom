"""SQLAlchemy schema for evidence, Outlook entities, and delta checkpoints."""

from __future__ import annotations

from sqlalchemy import JSON, Boolean, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Shared metadata for schema creation; keep model changes migration-aware.
    """


class SourceBinding(Base):
    """Stable logical source bound to one hashed external provider account."""

    __tablename__ = "source_bindings"

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    key_scheme: Mapped[str] = mapped_column(String(96))
    account_key_sha256: Mapped[str] = mapped_column(String(64), index=True)
    binding_method: Mapped[str] = mapped_column(String(32))
    bound_at: Mapped[str] = mapped_column(String(40))


class RawHttpEvidence(Base):
    """
    One captured exchange, with credential-free headers and digest-named
    payload files.
    """

    __tablename__ = "raw_http_evidence"

    evidence_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    run_id: Mapped[str | None] = mapped_column(String(32), index=True)
    purpose: Mapped[str | None] = mapped_column(String(80), index=True)
    observed_at: Mapped[str] = mapped_column(String(40), index=True)
    origin: Mapped[str] = mapped_column(String(24), index=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64), index=True)

    request_url: Mapped[str] = mapped_column(Text)
    request_method: Mapped[str] = mapped_column(String(16))
    request_headers: Mapped[dict[str, list[str]]] = mapped_column(JSON)
    request_body_sha256: Mapped[str] = mapped_column(String(64), index=True)
    request_body_path: Mapped[str] = mapped_column(Text)
    request_body_bytes: Mapped[int] = mapped_column(Integer)

    response_url: Mapped[str | None] = mapped_column(Text)
    response_status: Mapped[int | None] = mapped_column(Integer)
    response_headers: Mapped[dict[str, list[str]]] = mapped_column(JSON)
    response_body_sha256: Mapped[str] = mapped_column(String(64), index=True)
    response_body_path: Mapped[str] = mapped_column(Text)
    response_body_bytes: Mapped[int] = mapped_column(Integer)
    response_flags: Mapped[list[str]] = mapped_column(JSON)
    error_type: Mapped[str | None] = mapped_column(String(160))
    error_message: Mapped[str | None] = mapped_column(Text)


class MessageRecord(Base):
    """
    Latest known message projection, keyed by source and provider message ID.
    """

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
    """
    Historical observation; evidence identity lets the store detect cache
    replay.
    """

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
    """
    Latest status of one profile surface, including terminal
    unavailable/unsupported results.
    """

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


class AttachmentRecord(Base):
    """Latest attachment metadata within its owning message and source."""

    __tablename__ = "attachments"
    __table_args__ = (UniqueConstraint("source_id", "message_id", "attachment_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    message_id: Mapped[str] = mapped_column(Text, index=True)
    attachment_id: Mapped[str] = mapped_column(Text)
    attachment_type: Mapped[str | None] = mapped_column(String(80), index=True)
    name: Mapped[str | None] = mapped_column(Text)
    content_type: Mapped[str | None] = mapped_column(String(255))
    size: Mapped[int | None] = mapped_column(Integer)
    is_inline: Mapped[bool | None] = mapped_column(Boolean)
    latest_observed_at: Mapped[str] = mapped_column(String(40))
    latest_evidence_id: Mapped[str | None] = mapped_column(String(32))


class MailFolderRecord(Base):
    """Latest observed folder metadata, including hidden folders."""

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
    """Committed provider cursor safe for the next independent delta run."""

    __tablename__ = "delta_checkpoints"
    __table_args__ = (UniqueConstraint("source_id", "folder_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    folder_id: Mapped[str] = mapped_column(Text)
    delta_link: Mapped[str] = mapped_column(Text)
    committed_at: Mapped[str] = mapped_column(String(40))
    run_id: Mapped[str] = mapped_column(String(32), index=True)


class DeltaCheckpointCandidate(Base):
    """
    Uncommitted final-page cursor for one run/folder, retained for validation.
    """

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
