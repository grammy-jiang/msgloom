"""Focused durable delivery record helpers."""

from __future__ import annotations

import json
from hashlib import sha256

from msgloom.contracts import (
    AttemptIdentity,
    ClaimToken,
    ExecutionIdentity,
    ExternalEffectState,
    ResultRef,
    StageResult,
    TerminalStatus,
    VersionRef,
)
from msgloom.persistence import Phase1Persistence

from .models import SubmissionAttempt, SubmissionHistory, SubmissionReceipt


async def persist_history_records(
    persistence: Phase1Persistence,
    *,
    execution: ExecutionIdentity,
    attempt: AttemptIdentity,
    code_version: str,
    report_ref: VersionRef,
    policy_ref: VersionRef,
    assessments: tuple[VersionRef, ...],
    receipt_ref: ResultRef,
    receipt: SubmissionReceipt,
    claim: ClaimToken,
) -> tuple[ResultRef, ...]:
    """Persist idempotent singular history from one exact durable receipt."""
    _require_receipt_binding(
        receipt,
        report_ref=report_ref,
        policy_ref=policy_ref,
        assessments=assessments,
        receipt_ref=receipt_ref,
    )
    receipt_version = VersionRef(
        "report-receipt", receipt_ref.result_id, receipt_ref.schema_version
    )
    refs: list[ResultRef] = []
    for assessment in assessments:
        history = SubmissionHistory(
            report_ref=report_ref,
            policy_ref=policy_ref,
            assessment_ref=assessment,
            receipt_ref=receipt_version,
            effect=receipt.effect,
            reported_at=receipt.recorded_at,
        )
        result_id = history_result_id(
            report_ref, policy_ref, receipt.part_number, assessment
        )
        existing = await persistence.get_result(result_id)
        if existing is not None:
            if (
                existing.kind != "report_submission"
                or existing.schema_version != "1"
                or not existing.acceptable
                or existing.input_refs != (receipt_ref,)
                or existing.topic_versions != (assessment,)
                or existing.configuration_version != policy_ref.version
                or existing.exposed_output_ref != report_ref
                or existing.semantic_data_ref is None
            ):
                raise ValueError("existing report history lineage mismatches")
            saved = await persistence.load_semantic_data(existing.semantic_data_ref)
            if saved != history:
                raise ValueError("existing report history semantics mismatches")
            refs.append(ResultRef(result_id, "report_submission", "1"))
            continue
        data_ref = persistence.semantic_reference(
            f"data-{result_id}", "report_submission", "1", history
        )
        result = StageResult(
            result_id=result_id,
            kind="report_submission",
            schema_version="1",
            execution=execution,
            attempt=attempt,
            input_refs=(receipt_ref,),
            source_versions=(),
            prepared_versions=(),
            topic_versions=(assessment,),
            configuration_version=policy_ref.version,
            code_version=code_version,
            status=TerminalStatus.COMPLETE,
            acceptable=True,
            semantic_data_ref=data_ref,
            exposed_output_ref=report_ref,
        )
        await persistence.append_result_with_data(
            result, history, require_new=False, claim=claim
        )
        refs.append(ResultRef(result_id, "report_submission", "1"))
    return tuple(refs)


async def load_attempt(
    persistence: Phase1Persistence, ref: ResultRef
) -> SubmissionAttempt:
    """Load and integrity-check exact persisted replay bytes."""
    _result, value = await load_attempt_record(persistence, ref)
    return value


async def load_attempt_record(
    persistence: Phase1Persistence, ref: ResultRef
) -> tuple[StageResult, SubmissionAttempt]:
    """Load one exact attempt together with immutable stage lineage."""
    result = await persistence.get_result(ref.result_id)
    if (
        result is None
        or ResultRef(result.result_id, result.kind, result.schema_version) != ref
        or result.semantic_data_ref is None
    ):
        raise ValueError("replay attempt evidence is missing")
    value = await persistence.load_semantic_data(result.semantic_data_ref)
    if not isinstance(value, SubmissionAttempt):
        raise TypeError("replay evidence is not a submission attempt")
    if sha256(value.send_bytes).hexdigest() != value.send_sha256:
        raise ValueError("replay bytes failed integrity validation")
    if (
        result.status is not TerminalStatus.INCOMPLETE
        or not result.acceptable
        or len(result.input_refs) != 1
        or result.input_refs[0].kind != "report"
        or result.input_refs[0].schema_version != "1"
        or result.topic_versions != value.assessment_refs
        or result.configuration_version != value.policy_ref.version
        or result.exposed_output_ref != value.report_ref
    ):
        raise ValueError("submission attempt stage lineage mismatches")
    return result, value


async def load_receipt_record(
    persistence: Phase1Persistence,
    ref: ResultRef,
    *,
    acceptable_only: bool = True,
) -> tuple[StageResult, SubmissionReceipt]:
    """Load one exact definite receipt and its immutable stage lineage."""
    result = await persistence.get_result(ref.result_id)
    if (
        result is None
        or ResultRef(result.result_id, result.kind, result.schema_version) != ref
        or result.kind != "report_submission"
        or result.schema_version != "1"
        or (acceptable_only and not result.acceptable)
        or result.semantic_data_ref is None
    ):
        raise ValueError("definite receipt evidence is missing")
    value = await persistence.load_semantic_data(result.semantic_data_ref)
    if not isinstance(value, SubmissionReceipt):
        raise TypeError("definite receipt evidence is not a receipt")
    return result, value


def require_replay_binding(
    attempt: SubmissionAttempt,
    *,
    report_ref: VersionRef,
    policy_ref: VersionRef,
    part_number: int,
    assessments: tuple[VersionRef, ...],
    owner_identity: str,
    destination_identity: str,
) -> None:
    """Require replay evidence to bind the exact owner, report, and part."""
    if (
        attempt.report_ref != report_ref
        or attempt.policy_ref != policy_ref
        or attempt.part_number != part_number
        or attempt.owner_identity != owner_identity
        or attempt.destination_identity != destination_identity
        or attempt.assessment_refs != assessments
    ):
        raise ValueError("replay attempt does not match exact report part")


def require_receipt_lineage(
    receipt_result: StageResult,
    receipt: SubmissionReceipt,
    *,
    report_ref: VersionRef,
    policy_ref: VersionRef,
    part_number: int,
    assessments: tuple[VersionRef, ...],
) -> None:
    """Require accepted receipt semantics and stage lineage to agree."""
    receipt_ref = ResultRef(
        receipt_result.result_id,
        receipt_result.kind,
        receipt_result.schema_version,
    )
    _require_receipt_binding(
        receipt,
        report_ref=report_ref,
        policy_ref=policy_ref,
        assessments=assessments,
        receipt_ref=receipt_ref,
    )
    accepted = receipt.effect in {
        ExternalEffectState.ACCEPTED,
        ExternalEffectState.CONFIRMED,
    }
    expected_status = TerminalStatus.COMPLETE if accepted else TerminalStatus.FAILED
    if (
        receipt.part_number != part_number
        or receipt_result.status is not expected_status
        or receipt_result.acceptable is not accepted
        or len(receipt_result.input_refs) != 2
        or receipt_result.input_refs[0].kind != "report"
        or receipt_result.input_refs[0].schema_version != "1"
        or receipt_result.input_refs[1] != receipt.attempt_ref
        or receipt_result.topic_versions != assessments
        or receipt_result.configuration_version != policy_ref.version
        or receipt_result.exposed_output_ref != report_ref
    ):
        raise ValueError("accepted receipt stage lineage mismatches")


def history_recovery_claim_key(receipt_ref: ResultRef) -> str:
    """Return one stable recovery scope for receipt-backed history."""
    payload = json.dumps(
        [
            "report-history-recovery",
            receipt_ref.result_id,
            receipt_ref.kind,
            receipt_ref.schema_version,
        ],
        separators=(",", ":"),
    ).encode()
    return f"report-history-recovery:{sha256(payload).hexdigest()}"


def history_result_id(
    report_ref: VersionRef,
    policy_ref: VersionRef,
    part_number: int,
    assessment: VersionRef,
) -> str:
    """Return a stable singular identity independent of retry result names."""
    payload = json.dumps(
        [
            report_ref.kind,
            report_ref.identity,
            report_ref.version,
            policy_ref.kind,
            policy_ref.identity,
            policy_ref.version,
            part_number,
            assessment.kind,
            assessment.identity,
            assessment.version,
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"report-history-{sha256(payload).hexdigest()[:32]}"


def _require_receipt_binding(
    receipt: SubmissionReceipt,
    *,
    report_ref: VersionRef,
    policy_ref: VersionRef,
    assessments: tuple[VersionRef, ...],
    receipt_ref: ResultRef,
) -> None:
    if (
        receipt.report_ref != report_ref
        or receipt.policy_ref != policy_ref
        or receipt.assessment_refs != assessments
        or receipt_ref.kind != "report_submission"
        or receipt_ref.schema_version != "1"
    ):
        raise ValueError("accepted receipt does not match report history")
