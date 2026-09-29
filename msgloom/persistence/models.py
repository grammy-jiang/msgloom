"""SQLAlchemy models owned only by provider-neutral Phase 1 persistence."""

from __future__ import annotations

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Phase1Base(DeclarativeBase):
    """Declarative metadata for the neutral application tables only."""


class SchemaMetadataRecord(Phase1Base):
    """Record the exact neutral schema version; migrations are never implicit."""

    __tablename__ = "phase1_schema_metadata"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String, nullable=False)


class StageResultRecord(Phase1Base):
    """Persist one immutable terminal stage result."""

    __tablename__ = "phase1_stage_results"

    result_id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String, nullable=False, index=True)
    schema_version: Mapped[str] = mapped_column(String, nullable=False)
    execution_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    attempt_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    acceptable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    input_refs: Mapped[str] = mapped_column(Text, nullable=False)
    source_versions: Mapped[str] = mapped_column(Text, nullable=False)
    prepared_versions: Mapped[str] = mapped_column(Text, nullable=False)
    topic_versions: Mapped[str] = mapped_column(Text, nullable=False)
    configuration_version: Mapped[str] = mapped_column(String, nullable=False)
    code_version: Mapped[str] = mapped_column(String, nullable=False)
    rule_version: Mapped[str | None] = mapped_column(String)
    prompt_version: Mapped[str | None] = mapped_column(String)
    model_identifier: Mapped[str | None] = mapped_column(String)
    working_context_version: Mapped[str | None] = mapped_column(Text)
    exposed_output_ref: Mapped[str | None] = mapped_column(Text)
    exposed_diagnostics: Mapped[str] = mapped_column(Text, nullable=False)
    limitations: Mapped[str] = mapped_column(Text, nullable=False)
    failures: Mapped[str] = mapped_column(Text, nullable=False)


class OperationOutcomeRecord(Phase1Base):
    """Persist one immutable terminal outcome per execution identity."""

    __tablename__ = "phase1_operation_outcomes"

    execution_id: Mapped[str] = mapped_column(String, primary_key=True)
    capability: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    result_refs: Mapped[str] = mapped_column(Text, nullable=False)
    limitations: Mapped[str] = mapped_column(Text, nullable=False)
    failures: Mapped[str] = mapped_column(Text, nullable=False)
    external_effect: Mapped[str] = mapped_column(String, nullable=False)


class WorkClaimRecord(Phase1Base):
    """Hold the one current durable owner for a work scope."""

    __tablename__ = "phase1_work_claims"

    claim_key: Mapped[str] = mapped_column(String, primary_key=True)
    claim_token: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    claim_kind: Mapped[str] = mapped_column(String, nullable=False)
    execution_id: Mapped[str] = mapped_column(String, nullable=False)
    attempt_id: Mapped[str] = mapped_column(String, nullable=False)
    required_inputs: Mapped[str] = mapped_column(Text, nullable=False)
    claimed_at: Mapped[str] = mapped_column(String, nullable=False)
    expires_at: Mapped[str] = mapped_column(String, nullable=False)
    external_effect: Mapped[str] = mapped_column(String, nullable=False)


class ClaimAttemptRecord(Phase1Base):
    """Retain claim attempt history when stale work is superseded or finished."""

    __tablename__ = "phase1_claim_attempts"

    claim_token: Mapped[str] = mapped_column(String, primary_key=True)
    claim_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    claim_kind: Mapped[str] = mapped_column(String, nullable=False)
    execution_id: Mapped[str] = mapped_column(String, nullable=False)
    attempt_id: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[str] = mapped_column(String, nullable=False)
    finished_at: Mapped[str | None] = mapped_column(String)
    terminal_status: Mapped[str | None] = mapped_column(String)
    external_effect: Mapped[str] = mapped_column(String, nullable=False)
