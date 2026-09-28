"""Outlook Calendar catalog models."""

from __future__ import annotations

from sqlalchemy import JSON, Boolean, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ...base import Base


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


class CalendarEventSighting(Base):
    """One crawl-run sighting without implying a new semantic event version."""

    __tablename__ = "calendar_event_sightings"

    sighting_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    event_id: Mapped[str] = mapped_column(Text, index=True)
    calendar_id: Mapped[str] = mapped_column(Text, index=True)
    run_id: Mapped[str | None] = mapped_column(String(32), index=True)
    observation_kind: Mapped[str] = mapped_column(String(40), index=True)
    evidence_id: Mapped[str | None] = mapped_column(String(32), index=True)
    observed_at: Mapped[str] = mapped_column(String(40), index=True)


class CalendarEventObservation(Base):
    """Immutable observed Calendar event linked to raw provider evidence."""

    __tablename__ = "calendar_event_observations"
    __table_args__ = (UniqueConstraint("source_id", "event_id", "evidence_id"),)

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


class CalendarEventSurface(Base):
    """Latest versioned full-acquisition status for one event surface."""

    __tablename__ = "calendar_event_surfaces"
    __table_args__ = (UniqueConstraint("source_id", "event_id", "surface"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    event_id: Mapped[str] = mapped_column(Text, index=True)
    surface: Mapped[str] = mapped_column(String(96), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    evidence_id: Mapped[str | None] = mapped_column(String(32), index=True)
    observed_at: Mapped[str] = mapped_column(String(40), index=True)
    profile_version: Mapped[str | None] = mapped_column(String(40), index=True)
    resource_version: Mapped[str | None] = mapped_column(Text, index=True)


class CalendarEventAttachmentRecord(Base):
    """Latest known attachment metadata for one Calendar event."""

    __tablename__ = "calendar_event_attachments"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "event_id",
            "attachment_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    event_id: Mapped[str] = mapped_column(Text, index=True)
    attachment_id: Mapped[str] = mapped_column(Text, index=True)
    calendar_id: Mapped[str] = mapped_column(Text, index=True)
    attachment_type: Mapped[str | None] = mapped_column(String(96), index=True)
    name: Mapped[str | None] = mapped_column(Text)
    content_type: Mapped[str | None] = mapped_column(String(255))
    size: Mapped[int | None] = mapped_column(Integer)
    is_inline: Mapped[bool | None] = mapped_column(Boolean)
    content_bytes_present: Mapped[bool] = mapped_column(Boolean, default=False)
    content_status: Mapped[str] = mapped_column(String(32), index=True)
    content_observed_at: Mapped[str | None] = mapped_column(String(40), index=True)
    content_evidence_id: Mapped[str | None] = mapped_column(String(32), index=True)
    latest_observed_at: Mapped[str] = mapped_column(String(40), index=True)
    latest_evidence_id: Mapped[str | None] = mapped_column(String(32), index=True)
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


class CalendarDeltaEventState(Base):
    """Committed membership state for one fixed Calendar delta window."""

    __tablename__ = "calendar_delta_event_states"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "calendar_scope",
            "start_datetime",
            "end_datetime",
            "event_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    calendar_scope: Mapped[str] = mapped_column(String(80), index=True)
    start_datetime: Mapped[str] = mapped_column(String(40), index=True)
    end_datetime: Mapped[str] = mapped_column(String(40), index=True)
    event_id: Mapped[str] = mapped_column(Text, index=True)
    is_present: Mapped[bool] = mapped_column(Boolean, index=True)
    last_kind: Mapped[str] = mapped_column(String(32), index=True)
    removed_reason: Mapped[str | None] = mapped_column(String(80))
    latest_run_id: Mapped[str] = mapped_column(String(32), index=True)
    latest_attempt: Mapped[int] = mapped_column(Integer)
    latest_revision: Mapped[int] = mapped_column(Integer, index=True)
    latest_observed_at: Mapped[str] = mapped_column(String(40), index=True)
    latest_evidence_id: Mapped[str] = mapped_column(String(32), index=True)
    raw: Mapped[dict[str, object]] = mapped_column(JSON)


__all__ = [
    "CalendarDeltaCheckpoint",
    "CalendarDeltaCheckpointCandidate",
    "CalendarDeltaEventState",
    "CalendarDeltaObservation",
    "CalendarEventAttachmentRecord",
    "CalendarEventObservation",
    "CalendarEventRecord",
    "CalendarEventSighting",
    "CalendarEventSurface",
    "CalendarRecord",
]
