"""Additive Teams coverage history and sticky-uncertainty projection."""

from sqlalchemy import JSON, Boolean, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ...base import Base


class TeamsCoverageObservation(Base):
    """One visibility, retention, subscription, or delivery-gap fact."""

    __tablename__ = "teams_coverage_observations"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "scope_key_sha256",
            "evidence_id",
            name="uq_teams_coverage_evidence",
        ),
    )

    observation_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    scope_kind: Mapped[str] = mapped_column(String(64), index=True)
    scope_key: Mapped[list[str]] = mapped_column(JSON)
    scope_key_sha256: Mapped[str] = mapped_column(String(64), index=True)
    fact_kind: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(80), index=True)
    history_incomplete: Mapped[bool] = mapped_column(Boolean)
    visible_scope: Mapped[dict[str, object] | None] = mapped_column(JSON)
    retention_limitations: Mapped[list[str]] = mapped_column(JSON)
    subscription_id: Mapped[str | None] = mapped_column(Text)
    subscription_valid_from: Mapped[str | None] = mapped_column(String(40))
    subscription_valid_until: Mapped[str | None] = mapped_column(String(40))
    gap_kind: Mapped[str | None] = mapped_column(String(80))
    details: Mapped[dict[str, object]] = mapped_column(JSON)
    observed_at: Mapped[str] = mapped_column(String(40), index=True)
    evidence_id: Mapped[str] = mapped_column(String(32), index=True)
    run_id: Mapped[str] = mapped_column(String(32), index=True)
    evidence_run_id: Mapped[str | None] = mapped_column(String(32), index=True)


class TeamsCoverageCurrent(Base):
    """Latest coverage fact with irreversible known-history uncertainty."""

    __tablename__ = "teams_coverage_current"

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    scope_key_sha256: Mapped[str] = mapped_column(String(64), primary_key=True)
    scope_kind: Mapped[str] = mapped_column(String(64), index=True)
    scope_key: Mapped[list[str]] = mapped_column(JSON)
    observation_id: Mapped[int] = mapped_column(Integer)
    history_incomplete: Mapped[bool] = mapped_column(Boolean)
    latest_fact_kind: Mapped[str] = mapped_column(String(64))
    latest_status: Mapped[str] = mapped_column(String(80))
    latest_observed_at: Mapped[str] = mapped_column(String(40), index=True)
    latest_evidence_id: Mapped[str] = mapped_column(String(32), index=True)
    latest_run_id: Mapped[str] = mapped_column(String(32), index=True)
    latest_evidence_run_id: Mapped[str | None] = mapped_column(String(32), index=True)
    visible_scope: Mapped[dict[str, object] | None] = mapped_column(JSON)
    retention_limitations: Mapped[list[str]] = mapped_column(JSON)
    subscription_id: Mapped[str | None] = mapped_column(Text)
    subscription_valid_from: Mapped[str | None] = mapped_column(String(40))
    subscription_valid_until: Mapped[str | None] = mapped_column(String(40))
    gap_kind: Mapped[str | None] = mapped_column(String(80))
    details: Mapped[dict[str, object]] = mapped_column(JSON)


__all__ = ["TeamsCoverageCurrent", "TeamsCoverageObservation"]
