"""
Version 2 Workset finalizer: receipt proof plus legacy terminal row, one lock.

CANDIDATE/RESEARCH (C0-14b). Nothing here runs against a real database.
Tests use disposable files under ``tmp_path``. See
``docs/notes/a2-v2-db-finalize.md`` for the decisions and open questions.

:func:`finalize_a2_intake_workset_v2` ends a pending ``intake_worksets`` row
for a receipt that covers the frozen Workset. It does not change
``intake_completion.py``, the v1 finalizer or any A1 file. The v1 finalizer
already refuses a terminal row whose values differ from its own, so a row
finished here cannot be finished again by v1.

Steps (``BEGIN IMMEDIATE`` on a caller-owned autocommit connection):

1. Pure checks, no lock: the receipt covers the frozen Workset
   (:meth:`CompletionReceipt.validate_against`) and the publisher proof
   names the Workset PREPARE claim key.
2. Exact schema 5, no legacy recovery hold, the Workset stage result is
   present, and the row matches the Workset scope and cutoff.
3. The row is ``pending`` and the proof is the live claim. A terminal row
   with identical values is an idempotent replay. A terminal row with other
   values raises :exc:`A2FinalizeConflict` and nothing changes.
4. Metadata recheck: each receipt result must be an accepted-stage record
   whose digest the coverage proof binds (``build_receipt_proof``). Then,
   for every accepted stage, the saved ``StageResult`` row must exist and
   rebuild the record (kind, version, writer execution and attempt, status,
   limitations digest, stage metadata SHA, lineage, canonical SHA, length and
   semantic data id). The accepted-stage columns must equal the record. The
   publishing claim row (``writer_claim_seq``) must equal the record writer.
   That claim must have an ``inserted`` row in the stage attempt history.
   The stage may come from an earlier attempt. Only ``phase1_a2_*`` tables,
   ``phase1_stage_results``, the row and one metadata key are read. The
   function never reads ``phase1_semantic_data``, a payload or a body.
5. ``UPDATE`` the row (state, status, refs, claim digest, execution and
   attempt), read the row back, write the receipt proof file, ``COMMIT``.

Atomicity and its limit: SQLite cannot roll back a file. The proof file is
write-once and written after the ``UPDATE`` and the read-back, and before
``COMMIT``. A failure
before ``COMMIT`` rolls back SQL, so the row stays pending. A file written
before a failed ``COMMIT`` stays as an orphan. An orphan is harmless: it is
the exact proof of the same receipt, a retry replays it, and a different
receipt for that Workset raises :exc:`A2ReceiptConflict` and leaves the row
pending. A terminal row therefore implies a proof file, never the reverse.

Privacy: errors carry fixed reason codes and field names, never a value,
path, id, digest, claim value or pydantic text. ``repr`` of the request and
outcome hides all data.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Literal, cast

from sqlalchemy.engine import RowMapping

from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.a2_kedro.contracts.identity import AttemptProof, stage_metadata
from msgloom.a2_kedro.contracts.receipt import CompletionReceipt
from msgloom.contracts import ResultRef
from msgloom.persistence.a2_acceptance_models import AcceptedStage
from msgloom.persistence.a2_receipt_errors import A2ReceiptConflict, A2ReceiptError
from msgloom.persistence.a2_receipt_store import ReceiptStore, build_receipt_proof
from msgloom.persistence.a2_schema import require_schema5
from msgloom.persistence.a2_store import get_accepted
from msgloom.persistence.a2_txn import rollback_quietly
from msgloom.persistence.codecs import encode_result_refs
from msgloom.persistence.intake_records import INTAKE_KIND, INTAKE_SCHEMA_VERSION
from msgloom.persistence.records import result_from_row
from msgloom.persistence.schema_store import LEGACY_TERMINAL_PREFIX
from msgloom.preparation_pipeline.intake_models import (
    PreparationIntakeWorkset,
    workset_claim_key,
)

FinalizeOutcome = Literal["finalized", "replayed"]

_ROW = (
    "SELECT state, scope_key, cutoff_release_entry_seq, "
    "cutoff_release_entry_digest, terminal_status, result_refs, "
    "terminal_claim_token, terminal_execution_id, terminal_attempt_id "
    "FROM phase1_preparation_intake_worksets WHERE result_id = ?"
)
_UPDATE = (
    "UPDATE phase1_preparation_intake_worksets SET state = 'terminal', "
    "terminal_status = ?, result_refs = ?, terminal_claim_token = ?, "
    "terminal_execution_id = ?, terminal_attempt_id = ? "
    "WHERE result_id = ? AND state = 'pending'"
)
_RESULT_COLUMNS = (
    "result_id, kind, schema_version, execution_id, attempt_id, status, "
    "acceptable, input_refs, source_versions, prepared_versions, "
    "topic_versions, configuration_version, code_version, rule_version, "
    "prompt_version, model_identifier, working_context_version, "
    "semantic_data_ref, exposed_output_ref, exposed_diagnostics, "
    "limitations, failures"
)
_RESULT = f"SELECT {_RESULT_COLUMNS} FROM phase1_stage_results WHERE result_id = ?"
_STAGE_ROW = (
    "SELECT canonical_sha256, canonical_byte_count, semantic_data_id, "
    "stage_metadata_sha256, lineage_digest, limitations_digest, "
    "writer_claim_seq FROM phase1_a2_accepted_stages WHERE logical_key = ?"
)
_CLAIM_ROW = (
    "SELECT claim_key, execution_id, attempt_id, claim_token_sha256 "
    "FROM phase1_a2_claims WHERE claim_seq = ?"
)
_HISTORY_ROW = (
    "SELECT 1 FROM phase1_a2_stage_attempts "
    "WHERE logical_key = ? AND claim_seq = ? AND outcome = 'inserted'"
)
_TERMINAL_FIELDS = (
    "terminal_status",
    "result_refs",
    "terminal_claim_token",
    "terminal_execution_id",
    "terminal_attempt_id",
)


class A2FinalizeError(A2ReceiptError):
    """A finalize was refused. ``reason`` is a fixed code, never data."""


class A2FinalizeConflict(A2ReceiptConflict):
    """The row is terminal with other values. ``fields`` names columns."""


@dataclass(frozen=True, slots=True, repr=False)
class FinalizeRequest:
    """
    Everything one finalize needs.

    ``workset`` is the frozen Workset the caller loaded before the lock. The
    lock binds it to the row by scope and cutoff only. ``proof`` is the
    publisher proof of the live Workset PREPARE claim.
    """

    workset: PreparationIntakeWorkset
    workset_ref: ResultRef
    receipt: CompletionReceipt
    proof: AttemptProof

    def __repr__(self) -> str:
        return "FinalizeRequest(<redacted>)"


@dataclass(frozen=True, slots=True, repr=False)
class FinalizeResult:
    """``finalized`` when SQL changed, ``replayed`` for an identical replay."""

    outcome: FinalizeOutcome

    def __repr__(self) -> str:
        return f"FinalizeResult({self.outcome})"


def _terminal_values(request: FinalizeRequest) -> tuple[str, str, str, str, str]:
    """Return the five terminal column values this request would write."""
    receipt = request.receipt
    refs = tuple(root.result for root in receipt.roots)
    if receipt.transition_batch is not None:
        refs += (receipt.transition_batch.result,)
    proof = request.proof
    return (
        receipt.status.value,
        encode_result_refs(refs),
        proof.claim_token_sha256,
        proof.execution_id,
        proof.attempt_id,
    )


def _check_pure(request: FinalizeRequest) -> tuple[str, str, str, str, str]:
    """Run every check that needs no database. Return the terminal values."""
    ref = request.workset_ref
    if (ref.kind, ref.schema_version) != (INTAKE_KIND, INTAKE_SCHEMA_VERSION):
        raise A2FinalizeError("workset-ref-invalid")
    try:
        request.receipt.validate_against(request.workset, ref)
    except A2ContractError:
        raise A2FinalizeError("receipt-not-covering-workset") from None
    try:
        claim_key = workset_claim_key(ref.result_id)
    except ValueError:
        raise A2FinalizeError("workset-ref-invalid") from None
    if request.proof.claim_key != claim_key:
        raise A2FinalizeError("claim-key-mismatch")
    return _terminal_values(request)


@contextmanager
def _immediate(db: sqlite3.Connection) -> Iterator[None]:
    """Run the body in ``BEGIN IMMEDIATE``; roll back on any failure."""
    if db.in_transaction:
        raise A2FinalizeError("open-transaction")
    try:
        db.execute("BEGIN IMMEDIATE")
    except sqlite3.Error:
        raise A2FinalizeError("lock-failed") from None
    try:
        yield
    except sqlite3.Error:
        rollback_quietly(db)
        raise A2FinalizeError("database-error") from None
    except BaseException:
        rollback_quietly(db)
        raise
    try:
        db.execute("COMMIT")
    except sqlite3.Error:
        rollback_quietly(db)
        raise A2FinalizeError("commit-failed") from None
    except BaseException:
        rollback_quietly(db)
        raise


def _require_live_claim(db: sqlite3.Connection, proof: AttemptProof) -> None:
    """Raise unless ``proof`` is the live claim for its key."""
    row = db.execute(
        "SELECT execution_id, attempt_id, claim_token_sha256 "
        "FROM phase1_a2_claims WHERE claim_key = ? AND state = 'live'",
        (proof.claim_key,),
    ).fetchone()
    if row is None:
        raise A2FinalizeError("claim-not-live")
    held = (proof.execution_id, proof.attempt_id, proof.claim_token_sha256)
    if tuple(row) != held:
        raise A2FinalizeError("claim-foreign")


def _require_workset_row(
    db: sqlite3.Connection, request: FinalizeRequest
) -> tuple[object, ...]:
    """Return the legacy row after the metadata-only identity checks."""
    result_id = request.workset_ref.result_id
    meta = db.execute(
        'SELECT 1 FROM phase1_schema_metadata WHERE "key" = ?',
        (LEGACY_TERMINAL_PREFIX + result_id,),
    ).fetchone()
    if meta is not None:
        raise A2FinalizeError("legacy-recovery-hold")
    saved = db.execute(
        "SELECT kind, schema_version FROM phase1_stage_results WHERE result_id = ?",
        (result_id,),
    ).fetchone()
    if saved is None or tuple(saved) != (INTAKE_KIND, INTAKE_SCHEMA_VERSION):
        raise A2FinalizeError("workset-result-missing")
    row = db.execute(_ROW, (result_id,)).fetchone()
    if row is None:
        raise A2FinalizeError("workset-not-admitted")
    workset = request.workset
    if row[1] != workset.scope.claim_key():
        raise A2FinalizeError("workset-scope-mismatch")
    cutoff = workset.cutoff
    if (row[2], row[3]) != (
        cutoff.last_release_entry_seq,
        cutoff.last_release_entry_digest or "",
    ):
        raise A2FinalizeError("workset-cutoff-mismatch")
    return tuple(row)


def _accepted_records(
    db: sqlite3.Connection, receipt: CompletionReceipt
) -> dict[str, AcceptedStage]:
    """Load the accepted-stage metadata records the receipt names."""
    refs = [root.result for root in receipt.roots]
    if receipt.transition_batch is not None:
        refs.append(receipt.transition_batch.result)
    found: dict[str, AcceptedStage] = {}
    for ref in refs:
        if (record := get_accepted(db, ref.result_id)) is not None:
            found[ref.result_id] = record
    return found


def _verify_saved_result(db: sqlite3.Connection, record: AcceptedStage) -> None:
    """Rebuild the record's metadata from the saved ``StageResult`` row."""
    row = db.execute(_RESULT, (record.logical_key,)).fetchone()
    if row is None:
        raise A2FinalizeError("stage-result-missing")
    names = tuple(part.strip() for part in _RESULT_COLUMNS.split(","))
    try:
        result = result_from_row(cast("RowMapping", dict(zip(names, row, strict=True))))
        meta = stage_metadata(result)
    except (ValueError, TypeError, KeyError):
        raise A2FinalizeError("stage-result-corrupt") from None
    ref = record.output
    if (result.kind, result.schema_version) != (ref.kind, ref.schema_version):
        raise A2FinalizeError("stage-result-mismatch")
    writer = (result.execution.value, result.attempt.value)
    if writer != (record.writer.execution_id, record.writer.attempt_id):
        raise A2FinalizeError("stage-result-writer-mismatch")
    saved = (
        meta.semantic_sha256,
        meta.semantic_byte_count,
        meta.semantic_data_id,
        meta.digest(),
        meta.lineage_digest,
        meta.status,
        meta.limitations_digest,
    )
    held = (
        record.canonical_sha256,
        record.canonical_byte_count,
        record.semantic_data_id,
        record.stage_metadata_sha256,
        record.lineage_digest,
        record.status,
        record.limitations_digest,
    )
    if saved != held:
        raise A2FinalizeError("stage-result-mismatch")


def _verify_publication(db: sqlite3.Connection, record: AcceptedStage) -> None:
    """Check the stored columns, the publishing claim and the attempt history."""
    row = db.execute(_STAGE_ROW, (record.logical_key,)).fetchone()
    if row is None:
        raise A2FinalizeError("accepted-result-missing")
    columns = (
        record.canonical_sha256,
        record.canonical_byte_count,
        record.semantic_data_id,
        record.stage_metadata_sha256,
        record.lineage_digest,
        record.limitations_digest,
    )
    if tuple(row[:6]) != columns:
        raise A2FinalizeError("accepted-columns-mismatch")
    claim = db.execute(_CLAIM_ROW, (row[6],)).fetchone()
    if claim is None:
        raise A2FinalizeError("publish-claim-missing")
    writer = record.writer
    held = (
        writer.claim_key,
        writer.execution_id,
        writer.attempt_id,
        writer.claim_token_sha256,
    )
    if tuple(claim) != held:
        raise A2FinalizeError("publish-claim-mismatch")
    if db.execute(_HISTORY_ROW, (record.logical_key, row[6])).fetchone() is None:
        raise A2FinalizeError("publish-attempt-missing")


def _verify_durable(db: sqlite3.Connection, accepted: dict[str, AcceptedStage]) -> None:
    """
    Verify every accepted stage from database metadata (no payload read).

    Stages may come from earlier attempts. Each one must carry its own
    original publication proof, so no same-attempt rule applies.
    """
    for record in accepted.values():
        _verify_publication(db, record)
        _verify_saved_result(db, record)


def finalize_a2_intake_workset_v2(
    db: sqlite3.Connection, store: ReceiptStore, request: FinalizeRequest
) -> FinalizeResult:
    """
    Finish one pending Workset in one transaction (see the module notes).

    Returns ``finalized`` when the row changed and ``replayed`` for an
    identical replay. Raises :exc:`A2FinalizeError` (fixed reason) for a
    missing, wrong-scope, held, uncovered or foreign-claim request, or an
    accepted stage whose saved result, publishing claim or attempt history
    does not verify, :exc:`A2FinalizeConflict` for a terminal row with other
    values, and :exc:`A2ReceiptError` or :exc:`A2ReceiptConflict` from the
    proof file. After any failure the row is unchanged.
    """
    values = _check_pure(request)
    result_id = request.workset_ref.result_id
    outcome: FinalizeOutcome = "finalized"
    with _immediate(db):
        require_schema5(db)
        row = _require_workset_row(db, request)
        pending = row[0] == "pending"
        if pending:
            _require_live_claim(db, request.proof)
        elif row[0] == "terminal" and row[4:] == values:
            outcome = "replayed"
        else:
            fields = tuple(
                name
                for name, old, new in zip(
                    _TERMINAL_FIELDS, row[4:], values, strict=True
                )
                if old != new
            )
            raise A2FinalizeConflict("terminal-conflict", fields)
        accepted = _accepted_records(db, request.receipt)
        proof = build_receipt_proof(request.receipt, accepted)
        _verify_durable(db, accepted)
        if pending:
            cursor = db.execute(_UPDATE, (*values, result_id))
            if cursor.rowcount != 1:
                raise A2FinalizeError("workset-not-pending")
            stored = db.execute(_ROW, (result_id,)).fetchone()
            if stored is None or tuple(stored[4:]) != values:
                raise A2FinalizeError("readback-mismatch")
        store.put_receipt_proof(proof, request.receipt, accepted)
    return FinalizeResult(outcome)
