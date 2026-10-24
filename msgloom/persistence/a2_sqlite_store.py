"""
Isolated SQLite append-or-verify store for A2 C0 research.

CANDIDATE/RESEARCH, not production-ready. The store opens its own
``sqlite3`` connection to a brand-new file, creates the ``a2c0_*`` tables
from :mod:`msgloom.persistence.a2_sqlite_ddl` and refuses to touch any file
that exists without our marker. It does not import ``Phase1Store``, any
schema store or async store, so it cannot alter a real msgloom database.

Ownership: one instance owns one connection and is not thread-safe. Use one
instance per thread. Writers serialize through ``BEGIN IMMEDIATE``.

Ordering: compare and insert share one immediate transaction, so two
legitimate writers racing on one key produce one accepted row. Conflict
attempts are committed before the conflict is raised, so the attempt row
survives while the original accepted row stays unchanged.

Failure handling: any exception inside a transaction, including a failed
``COMMIT`` and a ``BaseException``, rolls it back on a best-effort basis
(:func:`msgloom.persistence.a2_txn.rollback_quietly`). A secondary rollback
error never masks the original exception. A replay by the same execution and attempt is idempotent.

Not covered here (future guarded hooks, see the C0 v2 note): live claim
checks, ``required_inputs`` plan checks, stored semantic-data byte checks,
workset terminal updates and the async facade.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Literal, Self

from msgloom.a2_kedro.contracts.codec import (
    A2ContractError,
    canonical_model_bytes,
    decode_canonical_json,
    sha256_hex,
)
from msgloom.a2_kedro.contracts.identity import AttemptProof
from msgloom.a2_kedro.contracts.receipt import CompletionReceipt
from msgloom.persistence.a2_acceptance_models import (
    MAX_RECORD_BYTES,
    AcceptanceConflict,
    AcceptedStage,
    decide_append_or_verify,
)
from msgloom.persistence.a2_sqlite_ddl import MARKER, STATEMENTS
from msgloom.persistence.a2_txn import rollback_quietly

MAX_RECEIPT_BYTES = 1024 * 1024
BUSY_TIMEOUT_SECONDS = 10.0


class A2StoreError(A2ContractError):
    """The research store refused an unsafe open or a failed proof."""


class A2ResearchStore:
    """CANDIDATE/RESEARCH append-or-verify store on a scratch SQLite file."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._db = connection

    @classmethod
    def create(cls, path: Path) -> A2ResearchStore:
        """Create a new store file. Refuse an existing path of any kind."""
        if path.exists():
            raise A2StoreError("refusing to initialize an existing path")
        if not path.parent.is_dir():
            raise A2StoreError("store directory does not exist")
        connection = cls._connect(path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            for statement in STATEMENTS:
                connection.execute(statement)
            connection.execute(
                "INSERT INTO a2c0_meta (key, value) VALUES ('marker', ?)", (MARKER,)
            )
            connection.execute("COMMIT")
        except BaseException:
            rollback_quietly(connection)
            connection.close()
            path.unlink(missing_ok=True)
            raise
        return cls(connection)

    @classmethod
    def open_existing(cls, path: Path) -> A2ResearchStore:
        """Open a file only when it carries this store's marker."""
        if not path.is_file():
            raise A2StoreError("store file does not exist")
        connection = cls._connect(path)
        try:
            row = connection.execute(
                "SELECT value FROM a2c0_meta WHERE key = 'marker'"
            ).fetchone()
        except sqlite3.DatabaseError as error:
            connection.close()
            raise A2StoreError("file is not an A2 research store") from error
        if row is None or row[0] != MARKER:
            connection.close()
            raise A2StoreError("file is not an A2 research store")
        return cls(connection)

    @staticmethod
    def _connect(path: Path) -> sqlite3.Connection:
        connection = sqlite3.connect(
            path, timeout=BUSY_TIMEOUT_SECONDS, isolation_level=None
        )
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def close(self) -> None:
        """Close the connection."""
        self._db.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    @contextmanager
    def _immediate(self) -> Iterator[None]:
        self._db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self._db.execute("COMMIT")
        except BaseException:
            rollback_quietly(self._db)
            raise

    def _load(self, logical_key: str) -> AcceptedStage | None:
        row = self._db.execute(
            "SELECT record_sha256, record_json FROM a2c0_accepted_stage "
            "WHERE logical_key = ?",
            (logical_key,),
        ).fetchone()
        if row is None:
            return None
        data = row[1].encode()
        if sha256_hex(data) != row[0]:
            raise A2StoreError("stored accepted record fails its digest")
        decode_canonical_json(data, max_bytes=MAX_RECORD_BYTES)
        record = AcceptedStage.model_validate_json(data)
        if record.logical_key != logical_key:
            raise A2StoreError("stored accepted record has a foreign key")
        return record

    def _attempt(
        self,
        key: str,
        proof: AttemptProof,
        outcome: str,
        fields: tuple[str, ...] = (),
    ) -> None:
        self._db.execute(
            "INSERT OR IGNORE INTO a2c0_stage_attempt (logical_key, execution_id, "
            "attempt_id, claim_key, claim_token_sha256, outcome, conflict_fields) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                key,
                proof.execution_id,
                proof.attempt_id,
                proof.claim_key,
                proof.claim_token_sha256,
                outcome,
                ",".join(fields) or None,
            ),
        )

    def accept_stage(
        self, proposed: AcceptedStage, attempt: AttemptProof
    ) -> Literal["inserted", "replayed"]:
        """
        Append the stage or verify it equals the stored one.

        CANDIDATE/RESEARCH writer. It does not check a live claim, a plan or
        stored semantic bytes. Raises :exc:`AcceptanceConflict` after
        recording the conflicting attempt; the stored row never changes.
        """
        key = proposed.logical_key
        conflict: AcceptanceConflict | None = None
        outcome: Literal["inserted", "replayed"] = "replayed"
        with self._immediate():
            try:
                action = decide_append_or_verify(self._load(key), proposed)
            except AcceptanceConflict as error:
                conflict = error
                self._attempt(key, attempt, "conflict", error.fields)
            else:
                if action == "insert":
                    outcome = "inserted"
                    self._db.execute(
                        "INSERT INTO a2c0_accepted_stage (logical_key, result_id, "
                        "kind, schema_version, status, record_sha256, record_json) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            key,
                            proposed.output.result_id,
                            proposed.output.kind,
                            proposed.output.schema_version,
                            proposed.status.value,
                            proposed.record_sha256(),
                            proposed.record_bytes().decode(),
                        ),
                    )
                self._attempt(key, attempt, outcome)
        if conflict is not None:
            raise conflict
        return outcome

    def get_accepted(self, logical_key: str) -> AcceptedStage | None:
        """
        Return the verified stored record for ``logical_key``, if any.

        CANDIDATE/RESEARCH: proof-dependent, not production-ready.
        """
        return self._load(logical_key)

    def count_accepted(self) -> int:
        """Return the number of accepted stage rows."""
        return self._db.execute("SELECT count(*) FROM a2c0_accepted_stage").fetchone()[
            0
        ]

    def attempts(self, logical_key: str) -> tuple[tuple[str, str, str], ...]:
        """Return ``(execution_id, attempt_id, outcome)`` in insert order."""
        rows = self._db.execute(
            "SELECT execution_id, attempt_id, outcome FROM a2c0_stage_attempt "
            "WHERE logical_key = ? ORDER BY attempt_seq",
            (logical_key,),
        ).fetchall()
        return tuple((a, b, c) for a, b, c in rows)

    def _require_proofs(self, receipt: CompletionReceipt) -> None:
        """CANDIDATE/RESEARCH: check each root against an accepted proof."""
        results = [(root.result, root.status) for root in receipt.roots]
        if receipt.transition_batch is not None:
            batch = receipt.transition_batch
            results.append((batch.result, batch.status))
        for ref, status in results:
            record = self._load(ref.result_id)
            if record is None:
                raise A2StoreError("receipt names a result with no accepted proof")
            if record.output != ref or record.status is not status:
                raise A2StoreError("receipt disagrees with the accepted proof")

    def append_receipt(
        self, receipt: CompletionReceipt
    ) -> Literal["inserted", "replayed"]:
        """
        Append the receipt after verifying every accepted-stage proof.

        CANDIDATE/RESEARCH finalizer step. It writes only the research
        receipt table and never updates a workset or its pending state.
        A different receipt under the same workset and policy fails closed.
        """
        data = canonical_model_bytes(receipt, max_bytes=MAX_RECEIPT_BYTES)
        digest = sha256_hex(data)
        workset_id = receipt.workset.result_id
        with self._immediate():
            self._require_proofs(receipt)
            row = self._db.execute(
                "SELECT receipt_sha256 FROM a2c0_receipt "
                "WHERE workset_id = ? AND policy_version = ?",
                (workset_id, receipt.policy_version),
            ).fetchone()
            if row is not None:
                if row[0] != digest:
                    raise A2StoreError("conflicting receipt for the same workset")
                return "replayed"
            self._db.execute(
                "INSERT INTO a2c0_receipt (workset_id, policy_version, status, "
                "receipt_sha256, receipt_json) VALUES (?, ?, ?, ?, ?)",
                (
                    workset_id,
                    receipt.policy_version,
                    receipt.status.value,
                    digest,
                    data.decode(),
                ),
            )
        return "inserted"
