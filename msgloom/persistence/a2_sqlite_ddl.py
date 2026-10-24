"""
Own DDL for the isolated A2 C0 research SQLite store.

CANDIDATE/RESEARCH. These statements create ``a2c0_*`` tables in a fresh,
disposable database file only. They are never applied to a real msgloom
database and are not part of ``schema_store`` or any schema autoload. Final
table names, constraints and migration belong to the database owner
(C0-11a to C0-11e).

Constraints enforce the shape the Python models already check, so a direct
SQL write cannot store a malformed key, digest or status either.
"""

from __future__ import annotations

#: Marker value stored in ``a2c0_meta`` so a file is recognizably ours.
MARKER = "a2-c0-research-store@1"

_HEX64 = "length({col}) = 64 AND {col} NOT GLOB '*[^0-9a-f]*'"

STATEMENTS: tuple[str, ...] = (
    "CREATE TABLE a2c0_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
    f"""CREATE TABLE a2c0_accepted_stage (
        logical_key TEXT PRIMARY KEY CHECK (
            length(logical_key) = 76 AND logical_key LIKE 'a2-accepted:%'
            AND substr(logical_key, 13) NOT GLOB '*[^0-9a-f]*'),
        result_id TEXT NOT NULL UNIQUE,
        kind TEXT NOT NULL,
        schema_version TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('complete', 'incomplete')),
        record_sha256 TEXT NOT NULL CHECK ({_HEX64.format(col="record_sha256")}),
        record_json TEXT NOT NULL CHECK (length(record_json) <= 16384),
        CHECK (result_id = logical_key)
    )""",
    """
    CREATE TABLE a2c0_stage_attempt (
        attempt_seq INTEGER PRIMARY KEY AUTOINCREMENT,
        logical_key TEXT NOT NULL,
        execution_id TEXT NOT NULL,
        attempt_id TEXT NOT NULL,
        claim_key TEXT NOT NULL,
        claim_token_sha256 TEXT NOT NULL,
        outcome TEXT NOT NULL CHECK (outcome IN ('inserted', 'replayed', 'conflict')),
        conflict_fields TEXT,
        UNIQUE (logical_key, execution_id, attempt_id, outcome)
    )""",
    f"""CREATE TABLE a2c0_receipt (
        workset_id TEXT NOT NULL,
        policy_version TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('complete', 'incomplete')),
        receipt_sha256 TEXT NOT NULL CHECK ({_HEX64.format(col="receipt_sha256")}),
        receipt_json TEXT NOT NULL CHECK (length(receipt_json) <= 1048576),
        PRIMARY KEY (workset_id, policy_version)
    )""",
)
