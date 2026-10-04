"""Teams reference-resolution and hosted-content observation models."""

from sqlalchemy import JSON, Boolean, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ...base import Base


class TeamsReferenceResolutionObservation(Base):
    """One explicit resolution state for an exact observed attachment."""

    __tablename__ = "teams_reference_resolution_observations"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "trigger_scope_sha256",
            "trigger_evidence_id",
            "attachment_ordinal",
            "evidence_id",
            name="uq_teams_reference_resolution_evidence",
        ),
    )

    observation_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    trigger_scope_sha256: Mapped[str] = mapped_column(String(64), index=True)
    trigger_evidence_id: Mapped[str] = mapped_column(String(32), index=True)
    trigger_observed_at: Mapped[str] = mapped_column(String(40))
    attachment_ordinal: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(24), index=True)
    observed_at: Mapped[str] = mapped_column(String(40), index=True)
    evidence_id: Mapped[str] = mapped_column(String(32), index=True)
    run_id: Mapped[str] = mapped_column(String(32), index=True)
    evidence_run_id: Mapped[str | None] = mapped_column(String(32), index=True)
    details: Mapped[dict[str, object]] = mapped_column(JSON)


class TeamsReferenceResolutionCurrent(Base):
    """Latest strictly newer resolution state for one observed attachment."""

    __tablename__ = "teams_reference_resolution_current"

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    trigger_scope_sha256: Mapped[str] = mapped_column(String(64), primary_key=True)
    trigger_evidence_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    attachment_ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    observation_id: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(24), index=True)
    latest_observed_at: Mapped[str] = mapped_column(String(40), index=True)
    latest_evidence_id: Mapped[str] = mapped_column(String(32), index=True)
    latest_run_id: Mapped[str] = mapped_column(String(32), index=True)
    latest_evidence_run_id: Mapped[str | None] = mapped_column(String(32), index=True)
    details: Mapped[dict[str, object]] = mapped_column(JSON)


class TeamsHostedContentObservation(Base):
    """One hosted metadata, bytes, or failure response tied to its trigger."""

    __tablename__ = "teams_hosted_content_observations"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "trigger_scope_sha256",
            "trigger_evidence_id",
            "hosted_content_id",
            "observation_kind",
            "evidence_id",
            name="uq_teams_hosted_content_evidence",
        ),
    )

    observation_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    trigger_scope_sha256: Mapped[str] = mapped_column(String(64), index=True)
    trigger_evidence_id: Mapped[str] = mapped_column(String(32), index=True)
    trigger_observed_at: Mapped[str] = mapped_column(String(40))
    hosted_content_id: Mapped[str] = mapped_column(Text, index=True)
    observation_kind: Mapped[str] = mapped_column(String(16), index=True)
    provider_version_bound: Mapped[bool] = mapped_column(Boolean, default=False)
    observed_at: Mapped[str] = mapped_column(String(40), index=True)
    evidence_id: Mapped[str] = mapped_column(String(32), index=True)
    run_id: Mapped[str] = mapped_column(String(32), index=True)
    evidence_run_id: Mapped[str | None] = mapped_column(String(32), index=True)
    content_type: Mapped[object | None] = mapped_column(JSON)
    content_sha256: Mapped[str | None] = mapped_column(String(64))
    content_bytes: Mapped[int | None] = mapped_column(Integer)
    failure_kind: Mapped[str | None] = mapped_column(String(80))
    status_code: Mapped[int | None] = mapped_column(Integer)
    raw: Mapped[dict[str, object] | None] = mapped_column(JSON)
    details: Mapped[dict[str, object]] = mapped_column(JSON)


__all__ = [
    "TeamsHostedContentObservation",
    "TeamsReferenceResolutionCurrent",
    "TeamsReferenceResolutionObservation",
]
