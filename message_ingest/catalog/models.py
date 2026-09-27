"""SQLAlchemy schema for evidence and resource-specific observations."""

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


class CalendarRecord(Base):
    """Latest known metadata for one calendar visible to the source."""

    __tablename__ = "calendars"
    __table_args__ = (UniqueConstraint("source_id", "calendar_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    calendar_id: Mapped[str] = mapped_column(Text, index=True)
    name: Mapped[str | None] = mapped_column(Text)
    change_key: Mapped[str | None] = mapped_column(Text)
    is_default_calendar: Mapped[bool | None] = mapped_column(Boolean)
    can_edit: Mapped[bool | None] = mapped_column(Boolean)
    can_share: Mapped[bool | None] = mapped_column(Boolean)
    can_view_private_items: Mapped[bool | None] = mapped_column(Boolean)
    latest_observed_at: Mapped[str] = mapped_column(String(40), index=True)
    latest_evidence_id: Mapped[str | None] = mapped_column(String(32), index=True)
    raw: Mapped[dict[str, object]] = mapped_column(JSON)


class CalendarEventRecord(Base):
    """Latest known semantic state for one immutable Calendar event ID."""

    __tablename__ = "calendar_events"
    __table_args__ = (UniqueConstraint("source_id", "event_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    event_id: Mapped[str] = mapped_column(Text, index=True)
    calendar_id: Mapped[str] = mapped_column(Text, index=True)
    change_key: Mapped[str | None] = mapped_column(Text)
    subject: Mapped[str | None] = mapped_column(Text)
    start: Mapped[dict[str, object] | None] = mapped_column(JSON)
    end: Mapped[dict[str, object] | None] = mapped_column(JSON)
    event_type: Mapped[str | None] = mapped_column(String(40))
    series_master_id: Mapped[str | None] = mapped_column(Text, index=True)
    is_all_day: Mapped[bool | None] = mapped_column(Boolean)
    is_cancelled: Mapped[bool | None] = mapped_column(Boolean)
    is_removed: Mapped[bool] = mapped_column(Boolean, default=False)
    latest_observed_at: Mapped[str] = mapped_column(String(40), index=True)
    latest_evidence_id: Mapped[str | None] = mapped_column(String(32), index=True)
    raw: Mapped[dict[str, object]] = mapped_column(JSON)


class CalendarEventObservation(Base):
    """Immutable observed Calendar event linked to raw provider evidence."""

    __tablename__ = "calendar_event_observations"
    __table_args__ = (
        UniqueConstraint("source_id", "event_id", "evidence_id"),
    )

    observation_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    event_id: Mapped[str] = mapped_column(Text, index=True)
    run_id: Mapped[str | None] = mapped_column(String(32), index=True)
    evidence_id: Mapped[str | None] = mapped_column(String(32), index=True)
    observed_at: Mapped[str] = mapped_column(String(40), index=True)
    subject: Mapped[str | None] = mapped_column(Text)
    start: Mapped[dict[str, object] | None] = mapped_column(JSON)
    end: Mapped[dict[str, object] | None] = mapped_column(JSON)
    event_type: Mapped[str | None] = mapped_column(String(40))
    raw: Mapped[dict[str, object]] = mapped_column(JSON)


class CalendarDeltaCheckpoint(Base):
    """Committed delta cursor for one fixed default-calendar time window."""

    __tablename__ = "calendar_delta_checkpoints"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "calendar_scope",
            "start_datetime",
            "end_datetime",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    calendar_scope: Mapped[str] = mapped_column(String(80), index=True)
    start_datetime: Mapped[str] = mapped_column(String(40), index=True)
    end_datetime: Mapped[str] = mapped_column(String(40), index=True)
    delta_link: Mapped[str] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(Integer)
    run_id: Mapped[str] = mapped_column(String(32), index=True)
    attempt: Mapped[int] = mapped_column(Integer)
    committed_at: Mapped[str] = mapped_column(String(40))


class CalendarDeltaCheckpointCandidate(Base):
    """Uncommitted terminal cursor for one Calendar delta attempt."""

    __tablename__ = "calendar_delta_checkpoint_candidates"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "calendar_scope",
            "start_datetime",
            "end_datetime",
            "run_id",
            "attempt",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    calendar_scope: Mapped[str] = mapped_column(String(80), index=True)
    start_datetime: Mapped[str] = mapped_column(String(40), index=True)
    end_datetime: Mapped[str] = mapped_column(String(40), index=True)
    run_id: Mapped[str] = mapped_column(String(32), index=True)
    attempt: Mapped[int] = mapped_column(Integer)
    base_revision: Mapped[int | None] = mapped_column(Integer)
    delta_link: Mapped[str] = mapped_column(Text)
    evidence_id: Mapped[str] = mapped_column(String(32), index=True)
    observed_at: Mapped[str] = mapped_column(String(40))
    committed_at: Mapped[str | None] = mapped_column(String(40))


class CalendarDeltaObservation(Base):
    """One scoped event entry observed during a Calendar delta attempt."""

    __tablename__ = "calendar_delta_observations"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "calendar_scope",
            "start_datetime",
            "end_datetime",
            "evidence_id",
            "entry_index",
        ),
    )

    observation_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    calendar_scope: Mapped[str] = mapped_column(String(80), index=True)
    start_datetime: Mapped[str] = mapped_column(String(40), index=True)
    end_datetime: Mapped[str] = mapped_column(String(40), index=True)
    run_id: Mapped[str] = mapped_column(String(32), index=True)
    attempt: Mapped[int] = mapped_column(Integer)
    page_number: Mapped[int] = mapped_column(Integer)
    entry_index: Mapped[int] = mapped_column(Integer)
    event_id: Mapped[str] = mapped_column(Text, index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    removed_reason: Mapped[str | None] = mapped_column(String(80))
    evidence_id: Mapped[str] = mapped_column(String(32), index=True)
    observed_at: Mapped[str] = mapped_column(String(40), index=True)
    raw: Mapped[dict[str, object]] = mapped_column(JSON)


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
