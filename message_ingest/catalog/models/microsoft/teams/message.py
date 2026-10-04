"""Additive Teams message history, current projection, and deletion models."""

from typing import Any

from sqlalchemy import JSON, Boolean, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ...base import Base


class TeamsMessageObservation(Base):
    """One immutable provider message capture under a durable scoped identity."""

    __tablename__ = "teams_message_observations"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "scope_key_sha256",
            "evidence_id",
            name="uq_teams_message_observation_evidence",
        ),
    )

    observation_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    scope_key: Mapped[list[str]] = mapped_column(JSON)
    scope_key_sha256: Mapped[str] = mapped_column(String(64), index=True)
    location: Mapped[str] = mapped_column(String(32), index=True)
    message_id: Mapped[str] = mapped_column(Text, index=True)
    chat_id: Mapped[str | None] = mapped_column(Text)
    team_id: Mapped[str | None] = mapped_column(Text)
    channel_id: Mapped[str | None] = mapped_column(Text)
    root_message_id: Mapped[str | None] = mapped_column(Text)
    provider_etag: Mapped[object | None] = mapped_column(JSON)
    deleted_date_time: Mapped[object | None] = mapped_column(JSON)
    observed_at: Mapped[str] = mapped_column(String(40), index=True)
    evidence_id: Mapped[str] = mapped_column(String(32), index=True)
    run_id: Mapped[str] = mapped_column(String(32), index=True)
    evidence_run_id: Mapped[str | None] = mapped_column(String(32), index=True)
    raw: Mapped[dict[str, Any]] = mapped_column(JSON)


class TeamsMessageCurrent(Base):
    """Latest strictly newer message projection; equal-time captures do not win."""

    __tablename__ = "teams_message_current"

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    scope_key_sha256: Mapped[str] = mapped_column(String(64), primary_key=True)
    scope_key: Mapped[list[str]] = mapped_column(JSON)
    location: Mapped[str] = mapped_column(String(32), index=True)
    message_id: Mapped[str] = mapped_column(Text, index=True)
    chat_id: Mapped[str | None] = mapped_column(Text)
    team_id: Mapped[str | None] = mapped_column(Text)
    channel_id: Mapped[str | None] = mapped_column(Text)
    root_message_id: Mapped[str | None] = mapped_column(Text)
    message_observation_id: Mapped[int | None] = mapped_column(Integer, index=True)
    provider_etag: Mapped[object | None] = mapped_column(JSON)
    deleted_date_time: Mapped[object | None] = mapped_column(JSON)
    is_deleted: Mapped[bool] = mapped_column(Boolean)
    latest_observed_at: Mapped[str] = mapped_column(String(40), index=True)
    latest_evidence_id: Mapped[str] = mapped_column(String(32), index=True)
    latest_run_id: Mapped[str] = mapped_column(String(32), index=True)
    latest_evidence_run_id: Mapped[str | None] = mapped_column(String(32), index=True)
    raw: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class TeamsMessageDeletionObservation(Base):
    """One explicit direct or notification-backed message deletion fact."""

    __tablename__ = "teams_message_deletions"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "scope_key_sha256",
            "evidence_id",
            name="uq_teams_message_deletion_evidence",
        ),
    )

    deletion_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    scope_key: Mapped[list[str]] = mapped_column(JSON)
    scope_key_sha256: Mapped[str] = mapped_column(String(64), index=True)
    deletion_kind: Mapped[str] = mapped_column(String(24), index=True)
    declared_deleted_at: Mapped[object | None] = mapped_column(JSON)
    observed_at: Mapped[str] = mapped_column(String(40), index=True)
    evidence_id: Mapped[str] = mapped_column(String(32), index=True)
    run_id: Mapped[str] = mapped_column(String(32), index=True)
    evidence_run_id: Mapped[str | None] = mapped_column(String(32), index=True)
    readback_state: Mapped[str] = mapped_column(String(24))
    readback_observed_at: Mapped[str | None] = mapped_column(String(40))
    readback_evidence_id: Mapped[str | None] = mapped_column(String(32), index=True)
    readback_evidence_run_id: Mapped[str | None] = mapped_column(String(32), index=True)


class TeamsMessageAttachmentObservation(Base):
    """Embedded attachment metadata at its exact message observation ordinal."""

    __tablename__ = "teams_message_attachments"

    message_observation_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    scope_key_sha256: Mapped[str] = mapped_column(String(64), index=True)
    attachment_id: Mapped[str | None] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(48), index=True)
    content_type: Mapped[object | None] = mapped_column(JSON)
    raw: Mapped[dict[str, Any]] = mapped_column(JSON)


__all__ = [
    "TeamsMessageAttachmentObservation",
    "TeamsMessageCurrent",
    "TeamsMessageDeletionObservation",
    "TeamsMessageObservation",
]
