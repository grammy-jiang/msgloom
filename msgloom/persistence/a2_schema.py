"""
Exact constrained A2 v2 DDL and the guarded schema 4 to 5 migration.

CANDIDATE/RESEARCH (C0-11b). See ``docs/notes/a2-v2-db-schema-migration.md``
for the plan this module implements. Nothing here runs against a real
database. Tests use disposable files under ``tmp_path``.

Ownership: this module owns the ``phase1_a2_*`` tables, the schema 5 marker
and the pinned digest of the schema 4 DDL. It never imports or edits the A1
schema store. The pinned digest is a constant, and a test rebuilds it from
the live A1 models so drift fails loudly.

No implicit creation: :func:`classify_schema` and :func:`require_schema5`
only read. :func:`migrate_schema4_to_v5` is the only writer. It needs a
:class:`MigrationGate`, one connection with no open transaction, and it runs
inside one ``BEGIN IMMEDIATE`` transaction. Any failure, including a
``BaseException``, rolls back to the unchanged schema 4 file.

Failure handling: every refusal raises :exc:`A2SchemaError` with a short
reason code. Messages never contain a path, a key, a row value or SQL text
from the file under inspection.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from msgloom.a2_kedro.contracts.codec import MAX_TEXT_BYTES
from msgloom.a2_kedro.contracts.identity import AttemptProof
from msgloom.a2_kedro.contracts.schema_ids import ACCEPTED_KEY_PREFIX, STAGE_SCHEMAS
from msgloom.persistence.a2_acceptance_models import (
    MAX_PAYLOAD_BYTES,
    MAX_RECORD_BYTES,
)
from msgloom.persistence.a2_txn import rollback_quietly
from msgloom.persistence.errors import IncompatibleSchemaError

SCHEMA4_VERSION = "4"
SCHEMA5_VERSION = "5"
PROOF_REVISION = "1"
A2_REVISION = "1"
#: Versioned producer marker written with the schema 5 activation.
PRODUCER_MARKER = "a2-kedro-v2-schema@1"
BUSY_TIMEOUT_SECONDS = 10.0

#: Digest of the whitespace-collapsed schema 4 DDL (12 tables, indexes).
SCHEMA4_DIGEST = "e7bbda8e66251a36e9fea82fd6ae1ce68539e45f8b0561f4fc541b58490d8657"
SCHEMA4_TABLES = frozenset(
    {
        "phase1_schema_metadata",
        "phase1_stage_results",
        "phase1_semantic_data",
        "phase1_operation_outcomes",
        "phase1_work_claims",
        "phase1_claim_attempts",
        "phase1_reconciliations",
        "phase1_preparation_intake_cursors",
        "phase1_preparation_intake_worksets",
        "phase1_preparation_intake_held_entries",
        "phase1_preparation_plan_proofs",
        "phase1_preparation_result_bindings",
    }
)
_LEGACY_PREFIX = "preparation_proof_legacy_terminal:"
_A2_KEYS = {"a2_schema_revision": A2_REVISION, "a2_producer_marker": PRODUCER_MARKER}
_V4_KEYS = {"schema_version", "preparation_proof_revision"}
_HEX64_RE = re.compile(r"[0-9a-f]{64}")
_FOLD = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")


class A2SchemaError(IncompatibleSchemaError):
    """A schema is unknown, partial, older or refused. ``reason`` is a code."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class SchemaState(StrEnum):
    """Recognized, fully verified schema states."""

    SCHEMA4 = "schema4"
    SCHEMA5 = "schema5"


def hex64_check(col: str) -> str:
    """Return the SQL CHECK text for a lowercase 64-character hex column."""
    return f"typeof({col}) = 'text' AND length({col}) = 64 AND {col} NOT GLOB '*[^0-9a-f]*'"


def _text(col: str) -> str:
    return (
        f"typeof({col}) = 'text' "
        f"AND length(CAST({col} AS BLOB)) BETWEEN 1 AND {MAX_TEXT_BYTES}"
    )


_PAIRS = ", ".join(f"'{k}@{v}'" for k, v in sorted(STAGE_SCHEMAS.items()))
_KEY_LEN = len(ACCEPTED_KEY_PREFIX) + 64
_KEY = (
    f"typeof(logical_key) = 'text' AND length(logical_key) = {_KEY_LEN} "
    f"AND substr(logical_key, 1, {len(ACCEPTED_KEY_PREFIX)}) = "
    f"'{ACCEPTED_KEY_PREFIX}' AND substr(logical_key, "
    f"{len(ACCEPTED_KEY_PREFIX) + 1}) NOT GLOB '*[^0-9a-f]*'"
)


def _norm(sql: str) -> str:
    return " ".join(sql.split())


#: ``(type, name, sql)`` in creation order. Parents come before children.
A2_OBJECTS: tuple[tuple[str, str, str], ...] = tuple(
    (kind, name, _norm(sql))
    for kind, name, sql in (
        (
            "table",
            "phase1_a2_claims",
            f"""CREATE TABLE phase1_a2_claims (
                claim_seq INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_key TEXT NOT NULL CHECK ({_text("claim_key")}),
                execution_id TEXT NOT NULL CHECK ({_text("execution_id")}),
                attempt_id TEXT NOT NULL CHECK ({_text("attempt_id")}),
                claim_token_sha256 TEXT NOT NULL
                    CHECK ({hex64_check("claim_token_sha256")}),
                state TEXT NOT NULL DEFAULT 'live'
                    CHECK (state IN ('live', 'released')),
                UNIQUE (claim_key, execution_id, attempt_id)
            )""",
        ),
        (
            "index",
            "phase1_a2_claims_live",
            (
                "CREATE UNIQUE INDEX phase1_a2_claims_live "
                "ON phase1_a2_claims (claim_key) WHERE state = 'live'"
            ),
        ),
        (
            "table",
            "phase1_a2_accepted_stages",
            f"""CREATE TABLE phase1_a2_accepted_stages (
                logical_key TEXT PRIMARY KEY CHECK ({_KEY}),
                kind TEXT NOT NULL CHECK ({_text("kind")}),
                schema_version TEXT NOT NULL CHECK ({_text("schema_version")}),
                status TEXT NOT NULL CHECK (status IN ('complete', 'incomplete')),
                canonical_sha256 TEXT NOT NULL CHECK ({hex64_check("canonical_sha256")}),
                canonical_byte_count INTEGER NOT NULL
                    CHECK (typeof(canonical_byte_count) = 'integer'
                    AND canonical_byte_count BETWEEN 1 AND {MAX_PAYLOAD_BYTES}),
                semantic_data_id TEXT NOT NULL CHECK ({_text("semantic_data_id")}),
                stage_metadata_sha256 TEXT NOT NULL
                    CHECK ({hex64_check("stage_metadata_sha256")}),
                lineage_digest TEXT NOT NULL CHECK ({hex64_check("lineage_digest")}),
                limitations_digest TEXT NOT NULL
                    CHECK ({hex64_check("limitations_digest")}),
                writer_claim_seq INTEGER NOT NULL
                    REFERENCES phase1_a2_claims (claim_seq),
                record_sha256 TEXT NOT NULL CHECK ({hex64_check("record_sha256")}),
                record_json TEXT NOT NULL CHECK (typeof(record_json) = 'text'
                    AND length(CAST(record_json AS BLOB))
                    BETWEEN 1 AND {MAX_RECORD_BYTES}),
                CHECK (kind || '@' || schema_version IN ({_PAIRS}))
            )""",
        ),
        (
            "index",
            "phase1_a2_accepted_by_claim",
            (
                "CREATE INDEX phase1_a2_accepted_by_claim "
                "ON phase1_a2_accepted_stages (writer_claim_seq)"
            ),
        ),
        (
            "table",
            "phase1_a2_stage_attempts",
            """CREATE TABLE phase1_a2_stage_attempts (
                attempt_seq INTEGER PRIMARY KEY AUTOINCREMENT,
                logical_key TEXT NOT NULL
                    REFERENCES phase1_a2_accepted_stages (logical_key),
                claim_seq INTEGER NOT NULL REFERENCES phase1_a2_claims (claim_seq),
                outcome TEXT NOT NULL
                    CHECK (outcome IN ('inserted', 'replayed', 'conflict')),
                conflict_fields TEXT CHECK (conflict_fields IS NULL OR
                    (typeof(conflict_fields) = 'text'
                    AND length(CAST(conflict_fields AS BLOB)) BETWEEN 1 AND 512)),
                CHECK ((outcome = 'conflict') = (conflict_fields IS NOT NULL)),
                UNIQUE (logical_key, claim_seq, outcome)
            )""",
        ),
        (
            "index",
            "phase1_a2_attempts_by_claim",
            (
                "CREATE INDEX phase1_a2_attempts_by_claim "
                "ON phase1_a2_stage_attempts (claim_seq)"
            ),
        ),
    )
)
A2_TABLES = frozenset(name for kind, name, _ in A2_OBJECTS if kind == "table")


def _fold(name: str) -> str:
    return name.translate(_FOLD)


def _sql_digest(rows: list[tuple[str, str]]) -> str:
    """Digest sorted ``(name, sql)`` pairs the way the pinned value does."""
    text = "\n".join(_norm(sql) for _, sql in sorted(rows))
    return hashlib.sha256(text.encode()).hexdigest()


def _schema_rows(connection: sqlite3.Connection) -> list[tuple[str, str, str, str]]:
    try:
        return connection.execute(
            "SELECT type, name, tbl_name, sql FROM main.sqlite_schema "
            "WHERE name <> 'sqlite_sequence' ORDER BY name"
        ).fetchall()
    except sqlite3.DatabaseError:
        raise A2SchemaError("file-is-not-a-database") from None


def _metadata(connection: sqlite3.Connection) -> dict[str, str]:
    try:
        rows = connection.execute(
            'SELECT "key", value FROM phase1_schema_metadata'
        ).fetchall()
    except sqlite3.DatabaseError:
        raise A2SchemaError("metadata-unreadable") from None
    if any(not isinstance(key, str) or not isinstance(val, str) for key, val in rows):
        raise A2SchemaError("metadata-not-text")
    return dict(rows)


def _check_keys(meta: dict[str, str], allowed: set[str]) -> None:
    for key in meta:
        if key not in allowed and not key.startswith(_LEGACY_PREFIX):
            raise A2SchemaError("unknown-metadata-key")


def classify_schema(connection: sqlite3.Connection) -> SchemaState:
    """
    Return the verified state of the main database. Read only.

    Accepts exactly schema 4 (pinned digest, versions ``4`` and ``1``) or
    exactly schema 5 (schema 4 plus the exact A2 objects and marker). Any
    older, partial, foreign or altered shape raises :exc:`A2SchemaError`.
    """
    rows = _schema_rows(connection)
    if any(kind in ("view", "trigger") for kind, *_ in rows):
        raise A2SchemaError("view-or-trigger-present")
    tables = {name for kind, name, *_ in rows if kind == "table"}
    owned = {name for name in tables if _fold(name).startswith("phase1_")}
    if not owned:
        raise A2SchemaError("no-neutral-schema")
    if {_fold(n) for n in owned if _fold(n).startswith("phase1_a2_")} - A2_TABLES:
        raise A2SchemaError("unreviewed-a2-table")
    if owned == SCHEMA4_TABLES:
        state = SchemaState.SCHEMA4
    elif owned == SCHEMA4_TABLES | A2_TABLES:
        state = SchemaState.SCHEMA5
    else:
        raise A2SchemaError("unreviewed-table-set")
    v4 = [(n, s) for _, n, t, s in rows if t in SCHEMA4_TABLES and s is not None]
    if _sql_digest(v4) != SCHEMA4_DIGEST:
        raise A2SchemaError("schema4-definition-mismatch")
    meta = _metadata(connection)
    if state is SchemaState.SCHEMA4:
        _check_keys(meta, _V4_KEYS)
        if (meta.get("schema_version"), meta.get("preparation_proof_revision")) != (
            SCHEMA4_VERSION,
            PROOF_REVISION,
        ):
            raise A2SchemaError("unreviewed-version-pair")
        return state
    found = {
        (kind, name, _norm(sql))
        for kind, name, table, sql in rows
        if table in A2_TABLES and sql is not None
    }
    if found != set(A2_OBJECTS):
        raise A2SchemaError("a2-definition-mismatch")
    _check_keys(meta, _V4_KEYS | set(_A2_KEYS))
    expected = {
        "schema_version": SCHEMA5_VERSION,
        "preparation_proof_revision": PROOF_REVISION,
        **_A2_KEYS,
    }
    if {k: v for k, v in meta.items() if k in expected} != expected:
        raise A2SchemaError("unreviewed-version-pair")
    return state


def require_schema5(connection: sqlite3.Connection) -> None:
    """Raise unless the file is exactly schema 5. Never writes or creates."""
    if classify_schema(connection) is not SchemaState.SCHEMA5:
        raise A2SchemaError("migration-required")


def connect_existing(path: Path) -> sqlite3.Connection:
    """
    Open an existing file read-write without ever creating it.

    The returned connection is in autocommit mode with foreign keys on.
    """
    if not path.is_file():
        raise A2SchemaError("database-file-missing")
    try:
        connection = sqlite3.connect(
            f"{path.resolve().as_uri()}?mode=rw",
            uri=True,
            timeout=BUSY_TIMEOUT_SECONDS,
            isolation_level=None,
        )
        connection.execute("PRAGMA foreign_keys = ON")
    except sqlite3.Error:
        raise A2SchemaError("database-open-failed") from None
    return connection


@dataclass(frozen=True)
class MigrationGate:
    """
    Explicit operator confirmation for the one-way migration.

    ``backup_sha256`` is the digest of the verified backup the operator
    took. ``schema4_digest`` is the pinned digest the operator read from
    the read-only verification step. The function does not read the backup.
    """

    backup_sha256: str
    schema4_digest: str


def _check_gate(gate: MigrationGate) -> None:
    if not isinstance(gate, MigrationGate):
        raise A2SchemaError("operator-gate-required")
    if not _HEX64_RE.fullmatch(gate.backup_sha256):
        raise A2SchemaError("operator-gate-backup-digest")
    if gate.schema4_digest != SCHEMA4_DIGEST:
        raise A2SchemaError("operator-gate-schema-digest")


def _activate(connection: sqlite3.Connection) -> None:
    connection.execute(
        'UPDATE phase1_schema_metadata SET value = ? WHERE "key" = ?',
        (SCHEMA5_VERSION, "schema_version"),
    )
    connection.executemany(
        'INSERT INTO phase1_schema_metadata ("key", value) VALUES (?, ?)',
        sorted(_A2_KEYS.items()),
    )


def migrate_schema4_to_v5(connection: sqlite3.Connection, gate: MigrationGate) -> None:
    """
    Atomically add the A2 tables and activate schema 5.

    Requires a valid :class:`MigrationGate`, an autocommit connection with
    no open transaction and an exact schema 4 file. The state is verified
    again inside the write lock and once more before ``COMMIT``. On any
    failure, including a failed ``COMMIT`` or a ``BaseException``, the
    transaction rolls back on a best-effort basis and the file stays
    schema 4. A secondary rollback error never masks the original one.
    """
    _check_gate(gate)
    if connection.in_transaction:
        raise A2SchemaError("open-transaction")
    try:
        connection.execute("BEGIN IMMEDIATE")
    except sqlite3.Error:
        raise A2SchemaError("migration-lock-failed") from None
    try:
        if classify_schema(connection) is not SchemaState.SCHEMA4:
            raise A2SchemaError("not-schema4")
        for _, _, sql in A2_OBJECTS:
            connection.execute(sql)
        _activate(connection)
        if classify_schema(connection) is not SchemaState.SCHEMA5:
            raise A2SchemaError("post-migration-check")
        connection.execute("COMMIT")
    except sqlite3.Error:
        rollback_quietly(connection)
        raise A2SchemaError("migration-failed") from None
    except BaseException:
        rollback_quietly(connection)
        raise


def acquire_claim(connection: sqlite3.Connection, proof: AttemptProof) -> int | None:
    """
    Record ``proof`` as the live claim for its key. Return ``claim_seq``.

    Exactly one connection wins a race on one ``claim_key``: the partial
    unique index admits one ``live`` row. A loser gets ``None``. The row
    stores only the SHA-256 of the claim token.
    """
    try:
        cursor = connection.execute(
            "INSERT INTO phase1_a2_claims (claim_key, execution_id, attempt_id, "
            "claim_token_sha256) VALUES (?, ?, ?, ?) "
            "ON CONFLICT (claim_key) WHERE state = 'live' DO NOTHING",
            (
                proof.claim_key,
                proof.execution_id,
                proof.attempt_id,
                proof.claim_token_sha256,
            ),
        )
    except sqlite3.IntegrityError:
        raise A2SchemaError("claim-rejected") from None
    return cursor.lastrowid if cursor.rowcount == 1 else None


def release_claim(connection: sqlite3.Connection, claim_seq: int) -> bool:
    """Mark a live claim released. Return whether a live row changed."""
    cursor = connection.execute(
        "UPDATE phase1_a2_claims SET state = 'released' "
        "WHERE claim_seq = ? AND state = 'live'",
        (claim_seq,),
    )
    return cursor.rowcount == 1
