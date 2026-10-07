"""SQLAlchemy models owned only by provider-neutral Phase 1 persistence."""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Phase1Base(DeclarativeBase):
    """Declarative metadata for the neutral application tables only."""


class SchemaMetadataRecord(Phase1Base):
    """Record the exact neutral schema version for explicit migrations."""

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
    semantic_data_ref: Mapped[str | None] = mapped_column(Text)
    exposed_output_ref: Mapped[str | None] = mapped_column(Text)
    exposed_diagnostics: Mapped[str] = mapped_column(Text, nullable=False)
    limitations: Mapped[str] = mapped_column(Text, nullable=False)
    failures: Mapped[str] = mapped_column(Text, nullable=False)


class SemanticDataRecord(Phase1Base):
    """Persist immutable semantic data; raw evidence is never stored."""

    __tablename__ = "phase1_semantic_data"

    data_id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    schema_version: Mapped[str] = mapped_column(String, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_count: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)


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
    """Retain attempt history when stale work is superseded or finished."""

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


class ReconciliationRecord(Phase1Base):
    """Retain one immutable external-effect reconciliation decision."""

    __tablename__ = "phase1_reconciliations"

    reconciliation_id: Mapped[str] = mapped_column(String, primary_key=True)
    claim_token: Mapped[str] = mapped_column(String, nullable=False, index=True)
    claim_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    claim_kind: Mapped[str] = mapped_column(String, nullable=False)
    execution_id: Mapped[str] = mapped_column(String, nullable=False)
    attempt_id: Mapped[str] = mapped_column(String, nullable=False)
    decision: Mapped[str] = mapped_column(String, nullable=False)
    evidence_refs: Mapped[str] = mapped_column(Text, nullable=False)
    resolved_at: Mapped[str] = mapped_column(String, nullable=False)


class PreparationIntakeCursorRecord(Phase1Base):
    """
    Keep one current anchor for each stable catalog/source/stream/consumer.
    """

    __tablename__ = "phase1_preparation_intake_cursors"
    __table_args__ = (CheckConstraint("last_release_entry_seq > 0"),)

    catalog_identity: Mapped[str] = mapped_column(String, primary_key=True)
    source_id: Mapped[str] = mapped_column(String, primary_key=True)
    stream: Mapped[str] = mapped_column(String, primary_key=True)
    consumer_id: Mapped[str] = mapped_column(String, primary_key=True)
    last_release_entry_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    last_release_entry_digest: Mapped[str] = mapped_column(String(64), nullable=False)


class PreparationIntakeWorksetRecord(Phase1Base):
    """Index immutable worksets independently of cursor admission progress."""

    __tablename__ = "phase1_preparation_intake_worksets"
    __table_args__ = (
        UniqueConstraint("scope_key", "cutoff_release_entry_seq"),
        Index(
            "phase1_intake_pending", "scope_key", "state", "cutoff_release_entry_seq"
        ),
        CheckConstraint("state IN ('pending', 'terminal')"),
    )

    result_id: Mapped[str] = mapped_column(String, primary_key=True)
    scope_key: Mapped[str] = mapped_column(String, nullable=False)
    cutoff_release_entry_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    cutoff_release_entry_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String, nullable=False)
    terminal_status: Mapped[str | None] = mapped_column(String)
    result_refs: Mapped[str] = mapped_column(Text, nullable=False)
    terminal_claim_token: Mapped[str | None] = mapped_column(String)
    terminal_execution_id: Mapped[str | None] = mapped_column(String)
    terminal_attempt_id: Mapped[str | None] = mapped_column(String)


class PreparationIntakeHeldEntryRecord(Phase1Base):
    """Provide bounded operator lookups without decoding every old workset."""

    __tablename__ = "phase1_preparation_intake_held_entries"
    __table_args__ = (
        UniqueConstraint("scope_key", "release_entry_seq"),
        Index("phase1_intake_held", "scope_key", "release_entry_seq"),
    )

    result_id: Mapped[str] = mapped_column(String, primary_key=True)
    release_entry_seq: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope_key: Mapped[str] = mapped_column(String, nullable=False)
    entry_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=False)


class PreparationPlanProofRecord(Phase1Base):
    """Bind publication to frozen plan ownership and explicit acceptance."""

    __tablename__ = "phase1_preparation_plan_proofs"
    __table_args__ = (
        CheckConstraint(
            "accepted_status IS NULL AND accepted_result_refs IS NULL OR "
            "accepted_status IS NOT NULL AND "
            "accepted_status IN ('complete', 'incomplete') "
            "AND accepted_result_refs IS NOT NULL"
        ),
    )

    claim_token: Mapped[str] = mapped_column(String, primary_key=True)
    claim_key: Mapped[str] = mapped_column(String, nullable=False)
    claim_kind: Mapped[str] = mapped_column(String, nullable=False)
    execution_id: Mapped[str] = mapped_column(String, nullable=False)
    attempt_id: Mapped[str] = mapped_column(String, nullable=False)
    required_inputs: Mapped[str] = mapped_column(Text, nullable=False)
    configuration_version: Mapped[str] = mapped_column(String, nullable=False)
    code_version: Mapped[str] = mapped_column(String, nullable=False)
    accepted_status: Mapped[str | None] = mapped_column(String)
    accepted_result_refs: Mapped[str | None] = mapped_column(Text)


class PreparationResultBindingRecord(Phase1Base):
    """Retain the exact publishing plan for each immutable result identity."""

    __tablename__ = "phase1_preparation_result_bindings"
    __table_args__ = (Index("phase1_preparation_bindings_by_token", "claim_token"),)

    result_id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    schema_version: Mapped[str] = mapped_column(String, nullable=False)
    claim_token: Mapped[str] = mapped_column(String, nullable=False)
