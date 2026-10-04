"""Generic additive Teams topology observations and current projections."""

from sqlalchemy import JSON, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ...base import Base


class TeamsTopologyObservation(Base):
    """One immutable chat/team/channel/member/pin topology observation."""

    __tablename__ = "teams_topology_observations"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "scope_key_sha256",
            "evidence_id",
            name="uq_teams_topology_observation_evidence",
        ),
    )

    observation_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    resource_kind: Mapped[str] = mapped_column(String(48), index=True)
    scope_key: Mapped[list[str | None]] = mapped_column(JSON)
    scope_key_sha256: Mapped[str] = mapped_column(String(64), index=True)
    observed_at: Mapped[str] = mapped_column(String(40), index=True)
    evidence_id: Mapped[str] = mapped_column(String(32), index=True)
    run_id: Mapped[str] = mapped_column(String(32), index=True)
    evidence_run_id: Mapped[str | None] = mapped_column(String(32), index=True)
    raw: Mapped[dict[str, object] | None] = mapped_column(JSON)
    context: Mapped[dict[str, object]] = mapped_column(JSON)


class TeamsTopologyCurrent(Base):
    """Latest strictly newer topology representation for one durable scope."""

    __tablename__ = "teams_topology_current"

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    scope_key_sha256: Mapped[str] = mapped_column(String(64), primary_key=True)
    resource_kind: Mapped[str] = mapped_column(String(48), index=True)
    scope_key: Mapped[list[str | None]] = mapped_column(JSON)
    observation_id: Mapped[int] = mapped_column(Integer, index=True)
    latest_observed_at: Mapped[str] = mapped_column(String(40), index=True)
    latest_evidence_id: Mapped[str] = mapped_column(String(32), index=True)
    latest_run_id: Mapped[str] = mapped_column(String(32), index=True)
    latest_evidence_run_id: Mapped[str | None] = mapped_column(String(32), index=True)
    raw: Mapped[dict[str, object] | None] = mapped_column(JSON)
    context: Mapped[dict[str, object]] = mapped_column(JSON)


__all__ = ["TeamsTopologyCurrent", "TeamsTopologyObservation"]
