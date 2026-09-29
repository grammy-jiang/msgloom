"""Typed SQLAlchemy table and row conversion helpers for Phase 1 persistence."""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy import Table
from sqlalchemy.engine import RowMapping

from msgloom.contracts import (
    AttemptIdentity,
    ExecutionIdentity,
    ExternalEffectState,
    OperationOutcome,
    PhaseCapability,
    StageResult,
    TerminalStatus,
)
from msgloom.persistence.codecs import (
    decode_diagnostics,
    decode_failures,
    decode_limitations,
    decode_result_refs,
    decode_semantic_data_ref,
    decode_version_ref,
    decode_version_refs,
    encode_diagnostics,
    encode_failures,
    encode_limitations,
    encode_result_refs,
    encode_semantic_data_ref,
    encode_version_ref,
    encode_version_refs,
)
from msgloom.persistence.models import (
    ClaimAttemptRecord,
    OperationOutcomeRecord,
    ReconciliationRecord,
    SchemaMetadataRecord,
    SemanticDataRecord,
    StageResultRecord,
    WorkClaimRecord,
)

# SQLAlchemy's declarative typing exposes __table__ as FromClause even though
# mapped declarative classes own concrete Table instances at runtime. Keep the
# narrow casts here rather than suppressing Core insert/update/delete checking.
CLAIM_ATTEMPTS = cast(Table, ClaimAttemptRecord.__table__)
OPERATION_OUTCOMES = cast(Table, OperationOutcomeRecord.__table__)
RECONCILIATIONS = cast(Table, ReconciliationRecord.__table__)
SCHEMA_METADATA = cast(Table, SchemaMetadataRecord.__table__)
SEMANTIC_DATA = cast(Table, SemanticDataRecord.__table__)
STAGE_RESULTS = cast(Table, StageResultRecord.__table__)
WORK_CLAIMS = cast(Table, WorkClaimRecord.__table__)


def result_values(result: StageResult) -> dict[str, Any]:
    """Return the storage values for one immutable stage result."""
    return {
        "result_id": result.result_id,
        "kind": result.kind,
        "schema_version": result.schema_version,
        "execution_id": result.execution.value,
        "attempt_id": result.attempt.value,
        "status": result.status.value,
        "acceptable": result.acceptable,
        "input_refs": encode_result_refs(result.input_refs),
        "source_versions": encode_version_refs(result.source_versions),
        "prepared_versions": encode_version_refs(result.prepared_versions),
        "topic_versions": encode_version_refs(result.topic_versions),
        "configuration_version": result.configuration_version,
        "code_version": result.code_version,
        "rule_version": result.rule_version,
        "prompt_version": result.prompt_version,
        "model_identifier": result.model_identifier,
        "working_context_version": encode_version_ref(result.working_context_version),
        "semantic_data_ref": encode_semantic_data_ref(result.semantic_data_ref),
        "exposed_output_ref": encode_version_ref(result.exposed_output_ref),
        "exposed_diagnostics": encode_diagnostics(result.exposed_diagnostics),
        "limitations": encode_limitations(result.limitations),
        "failures": encode_failures(result.failures),
    }


def result_from_row(row: RowMapping) -> StageResult:
    """Decode one stage-result row into the provider-neutral contract."""
    return StageResult(
        result_id=row["result_id"],
        kind=row["kind"],
        schema_version=row["schema_version"],
        execution=ExecutionIdentity(row["execution_id"]),
        attempt=AttemptIdentity(row["attempt_id"]),
        input_refs=decode_result_refs(row["input_refs"]),
        source_versions=decode_version_refs(row["source_versions"]),
        prepared_versions=decode_version_refs(row["prepared_versions"]),
        topic_versions=decode_version_refs(row["topic_versions"]),
        configuration_version=row["configuration_version"],
        code_version=row["code_version"],
        rule_version=row["rule_version"],
        prompt_version=row["prompt_version"],
        model_identifier=row["model_identifier"],
        working_context_version=decode_version_ref(row["working_context_version"]),
        semantic_data_ref=decode_semantic_data_ref(row["semantic_data_ref"]),
        exposed_output_ref=decode_version_ref(row["exposed_output_ref"]),
        exposed_diagnostics=decode_diagnostics(row["exposed_diagnostics"]),
        limitations=decode_limitations(row["limitations"]),
        failures=decode_failures(row["failures"]),
        status=TerminalStatus(row["status"]),
        acceptable=bool(row["acceptable"]),
    )


def outcome_values(outcome: OperationOutcome) -> dict[str, str]:
    """Return the storage values for one immutable operation outcome."""
    return {
        "execution_id": outcome.execution.value,
        "capability": outcome.capability.value,
        "status": outcome.status.value,
        "result_refs": encode_result_refs(outcome.result_refs),
        "limitations": encode_limitations(outcome.limitations),
        "failures": encode_failures(outcome.failures),
        "external_effect": outcome.external_effect.value,
    }


def outcome_from_row(row: RowMapping) -> OperationOutcome:
    """Decode one operation-outcome row into the provider-neutral contract."""
    return OperationOutcome(
        execution=ExecutionIdentity(row["execution_id"]),
        capability=PhaseCapability(row["capability"]),
        status=TerminalStatus(row["status"]),
        result_refs=decode_result_refs(row["result_refs"]),
        limitations=decode_limitations(row["limitations"]),
        failures=decode_failures(row["failures"]),
        external_effect=ExternalEffectState(row["external_effect"]),
    )
