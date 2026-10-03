"""Additive acquisition ledger tables; current state is only a freshness index."""

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AcquisitionLedgerMetadata(Base):
    """One identity retained by catalog backups and reopen."""

    __tablename__ = "acquisition_ledger_metadata"
    singleton: Mapped[int] = mapped_column(Integer, primary_key=True)
    schema_version: Mapped[int] = mapped_column(Integer)
    catalog_identity: Mapped[str] = mapped_column(String, unique=True)


class AcquisitionFact(Base):
    """Immutable bounded provenance, independent of mutable provider tables."""

    __tablename__ = "acquisition_facts"
    fact_id: Mapped[str] = mapped_column(String, primary_key=True)
    staging_key: Mapped[str] = mapped_column(String, unique=True)
    effective_key: Mapped[str] = mapped_column(String, index=True)
    source_id: Mapped[str] = mapped_column(String)
    stream: Mapped[str] = mapped_column(String)
    run_id: Mapped[str] = mapped_column(String)
    source_state_key: Mapped[str | None] = mapped_column(String)
    storage_relation: Mapped[str] = mapped_column(String)
    payload: Mapped[str] = mapped_column(Text)
    __table_args__ = (Index("ix_handoff_run", "source_id", "stream", "run_id"),)


class AcquisitionEffectiveState(Base):
    """Mutable equivalence/freshness pointer, never historical replay truth."""

    __tablename__ = "acquisition_effective_states"
    effective_key: Mapped[str] = mapped_column(String, primary_key=True)
    fact_id: Mapped[str] = mapped_column(ForeignKey("acquisition_facts.fact_id"))
    source_state_key: Mapped[str] = mapped_column(String)


class AcquisitionReleaseGroup(Base):
    """One atomic completion decision, including valid zero-entry decisions."""

    __tablename__ = "acquisition_release_groups"
    release_group_id: Mapped[str] = mapped_column(String, primary_key=True)
    source_id: Mapped[str] = mapped_column(String)
    stream: Mapped[str] = mapped_column(String)
    group_digest: Mapped[str] = mapped_column(String)
    input_digest: Mapped[str] = mapped_column(String)
    payload: Mapped[str] = mapped_column(Text)


class AcquisitionReleaseEntry(Base):
    """Globally sequenced admission unit; sequence is not provider chronology."""

    __tablename__ = "acquisition_release_entries"
    release_entry_seq: Mapped[int] = mapped_column(Integer, primary_key=True)
    release_group_id: Mapped[str] = mapped_column(
        ForeignKey("acquisition_release_groups.release_group_id")
    )
    source_id: Mapped[str] = mapped_column(String)
    stream: Mapped[str] = mapped_column(String)
    entry_digest: Mapped[str] = mapped_column(String)
    payload: Mapped[str] = mapped_column(Text)
    __table_args__ = (
        Index("ix_handoff_feed", "source_id", "stream", "release_entry_seq"),
        {"sqlite_autoincrement": True},
    )


class AcquisitionReleaseEntryFact(Base):
    """Ordered immutable members of one bounded entry."""

    __tablename__ = "acquisition_release_entry_facts"
    release_entry_seq: Mapped[int] = mapped_column(
        ForeignKey("acquisition_release_entries.release_entry_seq"), primary_key=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    fact_id: Mapped[str] = mapped_column(
        ForeignKey("acquisition_facts.fact_id"), index=True
    )
    role: Mapped[str] = mapped_column(String)


class AcquisitionRunOutcome(Base):
    """Append-only attempt outcomes; never a universal release gate."""

    __tablename__ = "acquisition_run_outcomes"
    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    attempt_id: Mapped[str] = mapped_column(String, primary_key=True)
    source_id: Mapped[str] = mapped_column(String)
    spider_name: Mapped[str] = mapped_column(String)
    execution_outcome: Mapped[str] = mapped_column(String)
    close_outcome: Mapped[str] = mapped_column(String)
    coverage_outcome: Mapped[str] = mapped_column(String)
