"""
Guarded A2 acceptance writer for the schema 5 ``phase1_a2_*`` tables.

CANDIDATE/RESEARCH (C0-12b). Nothing here runs against a real database.
Tests use disposable files under ``tmp_path``.

:func:`accept_result` is the one writer of ``phase1_a2_accepted_stages``.
It runs these steps inside one ``BEGIN IMMEDIATE`` transaction:

1. Require an exact schema 5 file (:func:`require_schema5`).
2. Check that the publisher proof is the live claim for its claim key.
3. Check each required input (the upstream refs of the frozen plan). Each
   one must be an accepted stage of the same kind and version.
4. Append the accepted stage, or verify it equals the stored one.
5. Check the live claim again, then ``COMMIT``.

Receipt binding: a :class:`PublisherReceipt` holds the raw ``StageResult``
as the publisher saved it, and the :class:`AttemptProof` of the publisher.
The proof must name the execution and attempt that the result names. The
result must match the frozen plan (:class:`StageIdentity`). The stored
record keeps the proof as its ``writer`` and the live ``claim_seq`` as
``writer_claim_seq``. The schema has no column for the raw result, so the
result itself is not stored (see ``docs/notes/a2-v2-db-store.md``).

Single unique key: ``logical_key`` is the primary key. An identical replay,
also by another live claim, returns the stored row. A different body under
the same key records a ``conflict`` attempt, commits it, and raises
:exc:`AcceptanceConflict`. The stored row never changes.

Failure handling: any exception inside the transaction, including a failed
``COMMIT`` and a ``BaseException``, rolls back on a best-effort basis
(:func:`msgloom.persistence.a2_txn.rollback_quietly`). Refusals raise
:exc:`A2AcceptError` with a short reason code. Messages never contain a
path, a key, a claim token, a row value or SQL text.

The caller owns the connection. It must be in autocommit mode with no open
transaction, for example from
:func:`msgloom.persistence.a2_schema.connect_existing`.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Literal

from msgloom.a2_kedro.contracts.codec import (
    A2ContractError,
    decode_canonical_json,
    sha256_hex,
)
from msgloom.a2_kedro.contracts.identity import AttemptProof, StageIdentity
from msgloom.contracts import StageResult
from msgloom.persistence.a2_acceptance_models import (
    MAX_RECORD_BYTES,
    AcceptanceConflict,
    AcceptedStage,
    accepted_stage_from_result,
    decide_append_or_verify,
)
from msgloom.persistence.a2_schema import require_schema5
from msgloom.persistence.a2_txn import rollback_quietly

AcceptOutcome = Literal["inserted", "replayed"]


class A2AcceptError(A2ContractError):
    """A publication was refused. ``reason`` is a short code, never data."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True, slots=True)
class PublisherReceipt:
    """
    The raw publication of one stage.

    ``result`` is the ``StageResult`` exactly as the publisher saved it.
    ``proof`` is the publisher's attempt proof for its live claim.
    """

    result: StageResult
    proof: AttemptProof


@dataclass(frozen=True, slots=True)
class Accepted:
    """Outcome of :func:`accept_result` and the verified stored record."""

    outcome: AcceptOutcome
    record: AcceptedStage


def _bind(identity: StageIdentity, receipt: PublisherReceipt) -> AcceptedStage:
    """Check the receipt against the plan and build the proposed record."""
    result, proof = receipt.result, receipt.proof
    if (result.execution.value, result.attempt.value) != (
        proof.execution_id,
        proof.attempt_id,
    ):
        raise A2AcceptError("receipt-binding-mismatch")
    try:
        return accepted_stage_from_result(identity, result, proof)
    except ValueError:
        # Pydantic and contract errors may quote values; drop them.
        raise A2AcceptError("plan-mismatch") from None


@contextmanager
def _immediate(db: sqlite3.Connection) -> Iterator[None]:
    """Run the body in ``BEGIN IMMEDIATE``; roll back on any failure."""
    if db.in_transaction:
        raise A2AcceptError("open-transaction")
    try:
        db.execute("BEGIN IMMEDIATE")
    except sqlite3.Error:
        raise A2AcceptError("lock-failed") from None
    try:
        yield
    except sqlite3.Error:
        rollback_quietly(db)
        raise A2AcceptError("database-error") from None
    except BaseException:
        rollback_quietly(db)
        raise
    try:
        db.execute("COMMIT")
    except sqlite3.Error:
        rollback_quietly(db)
        raise A2AcceptError("commit-failed") from None
    except BaseException:
        rollback_quietly(db)
        raise


def _live_claim(db: sqlite3.Connection, proof: AttemptProof) -> int:
    """Return the ``claim_seq`` when ``proof`` is the live claim."""
    row = db.execute(
        "SELECT claim_seq, execution_id, attempt_id, claim_token_sha256 "
        "FROM phase1_a2_claims WHERE claim_key = ? AND state = 'live'",
        (proof.claim_key,),
    ).fetchone()
    if row is None:
        raise A2AcceptError("claim-not-live")
    held = (proof.execution_id, proof.attempt_id, proof.claim_token_sha256)
    if tuple(row[1:]) != held:
        raise A2AcceptError("claim-foreign")
    return row[0]


def _require_inputs(db: sqlite3.Connection, identity: StageIdentity) -> None:
    """Each upstream ref must be an accepted stage of the same kind."""
    for ref in identity.upstream:
        row = db.execute(
            "SELECT kind, schema_version FROM phase1_a2_accepted_stages "
            "WHERE logical_key = ?",
            (ref.result_id,),
        ).fetchone()
        if row is None:
            raise A2AcceptError("required-input-missing")
        if tuple(row) != (ref.kind, ref.schema_version):
            raise A2AcceptError("required-input-mismatch")


def _load(db: sqlite3.Connection, logical_key: str) -> AcceptedStage | None:
    """Return the verified stored record for ``logical_key``, if any."""
    row = db.execute(
        "SELECT record_sha256, record_json, kind, schema_version, status "
        "FROM phase1_a2_accepted_stages WHERE logical_key = ?",
        (logical_key,),
    ).fetchone()
    if row is None:
        return None
    try:
        data = row[1].encode()
        if sha256_hex(data) != row[0]:
            raise A2AcceptError("stored-record-corrupt")
        decode_canonical_json(data, max_bytes=MAX_RECORD_BYTES)
        record = AcceptedStage.model_validate_json(data)
    except ValueError:
        raise A2AcceptError("stored-record-corrupt") from None
    columns = (record.output.kind, record.output.schema_version, record.status.value)
    if record.logical_key != logical_key or tuple(row[2:]) != columns:
        raise A2AcceptError("stored-record-corrupt")
    return record


def _attempt(
    db: sqlite3.Connection,
    key: str,
    claim_seq: int,
    outcome: str,
    fields: tuple[str, ...] = (),
) -> None:
    db.execute(
        "INSERT OR IGNORE INTO phase1_a2_stage_attempts "
        "(logical_key, claim_seq, outcome, conflict_fields) VALUES (?, ?, ?, ?)",
        (key, claim_seq, outcome, ",".join(fields) or None),
    )


def _insert(db: sqlite3.Connection, record: AcceptedStage, claim_seq: int) -> None:
    try:
        db.execute(
            "INSERT INTO phase1_a2_accepted_stages (logical_key, kind, "
            "schema_version, status, canonical_sha256, canonical_byte_count, "
            "semantic_data_id, stage_metadata_sha256, lineage_digest, "
            "limitations_digest, writer_claim_seq, record_sha256, record_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record.logical_key,
                record.output.kind,
                record.output.schema_version,
                record.status.value,
                record.canonical_sha256,
                record.canonical_byte_count,
                record.semantic_data_id,
                record.stage_metadata_sha256,
                record.lineage_digest,
                record.limitations_digest,
                claim_seq,
                record.record_sha256(),
                record.record_bytes().decode(),
            ),
        )
    except sqlite3.IntegrityError:
        raise A2AcceptError("insert-rejected") from None


def accept_result(
    db: sqlite3.Connection, identity: StageIdentity, receipt: PublisherReceipt
) -> Accepted:
    """
    Accept the published stage once, in one ``BEGIN IMMEDIATE`` transaction.

    CANDIDATE/RESEARCH writer. Returns ``inserted`` for a new row and
    ``replayed`` with the stored record for an identical replay. Raises
    :exc:`A2AcceptError` for a bad receipt binding, a plan mismatch, a
    claim that is not live or not the publisher's, a missing required
    input or a corrupt stored row. Raises :exc:`AcceptanceConflict` after
    it commits the conflict attempt, when the key holds a different body.
    """
    proposed = _bind(identity, receipt)
    conflict: AcceptanceConflict | None = None
    result = Accepted("replayed", proposed)
    with _immediate(db):
        require_schema5(db)
        claim_seq = _live_claim(db, receipt.proof)
        _require_inputs(db, identity)
        key = proposed.logical_key
        known = _load(db, key)
        try:
            decide_append_or_verify(known, proposed)
        except AcceptanceConflict as error:
            conflict = error
            _attempt(db, key, claim_seq, "conflict", error.fields)
        else:
            if known is None:
                _insert(db, proposed, claim_seq)
                result = Accepted("inserted", proposed)
            else:
                result = Accepted("replayed", known)
            _attempt(db, key, claim_seq, result.outcome)
        if _live_claim(db, receipt.proof) != claim_seq:
            raise A2AcceptError("claim-changed")
    if conflict is not None:
        raise conflict
    return result


def get_accepted(db: sqlite3.Connection, logical_key: str) -> AcceptedStage | None:
    """Return the verified stored record for ``logical_key``, if any."""
    return _load(db, logical_key)
