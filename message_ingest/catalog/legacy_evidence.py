"""Migrate the known response-only raw-evidence table to the current schema."""

from __future__ import annotations

import hashlib
from typing import cast

from sqlalchemy import Table, inspect
from sqlalchemy.engine import Connection
from sqlalchemy.schema import CreateTable

from message_ingest.catalog.models.acquisition import RawHttpEvidence

_TABLE = "raw_http_evidence"
_LEGACY_TABLE = "_msgloom_raw_http_evidence_legacy_v1"
_LEGACY_COLUMNS = frozenset(
    {
        "evidence_id",
        "source_id",
        "run_id",
        "purpose",
        "request_url",
        "request_method",
        "response_status",
        "response_headers",
        "body_sha256",
        "body_path",
        "body_bytes",
        "observed_at",
        "origin",
    }
)
_LEGACY_BODY_COLUMNS = ("body_sha256", "body_path", "body_bytes")
_EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
_FINGERPRINT_DOMAIN = b"msgloom-legacy-raw-http-evidence-v1\\0"


def migrate_legacy_evidence(connection: Connection) -> None:
    """
    Replace only the exact response-only evidence schema under the writer lock.

    The historical body_* fields describe response payloads and are kept
    verbatim as nullable compatibility columns. They must become nullable:
    current ORM inserts do not know those obsolete columns, and retaining the
    historical NOT NULL constraints would make every new capture fail.

    The current request/response columns are backfilled without inventing
    unavailable facts. Historical acquisition used GET requests only, so the
    request body is recorded as empty. Request headers and response URLs were
    not captured and remain empty/unknown. Migration-only fingerprints are
    domain-separated by evidence ID so they cannot intentionally match current
    Scrapy request fingerprints or participate in cache aliasing.

    The caller owns BEGIN IMMEDIATE and commit/rollback. Unknown partial schemas
    fail before any DDL. A current schema, including one that retains the three
    nullable legacy body columns, is a no-op.
    """
    table = cast(Table, RawHttpEvidence.__table__)
    inspector = inspect(connection)
    if not inspector.has_table(_TABLE):
        return

    metadata = {column["name"]: column for column in inspector.get_columns(_TABLE)}
    columns = set(metadata)
    current_columns = set(table.columns.keys())
    if current_columns <= columns:
        incompatible = [
            name
            for name in _LEGACY_BODY_COLUMNS
            if name in metadata and not metadata[name]["nullable"]
        ]
        if incompatible:
            raise ValueError(
                "Unsupported raw_http_evidence compatibility schema: current "
                "columns are present but obsolete body columns still block new "
                f"writes with NOT NULL constraints: {sorted(incompatible)}"
            )
        return

    if columns != _LEGACY_COLUMNS:
        raise ValueError(
            "Unsupported raw_http_evidence schema: expected the complete "
            "current schema or the exact legacy column set; "
            f"missing current columns: {sorted(current_columns - columns)}; "
            f"missing legacy columns: {sorted(_LEGACY_COLUMNS - columns)}; "
            f"unexpected legacy columns: {sorted(columns - _LEGACY_COLUMNS)}"
        )

    rows = (
        connection.exec_driver_sql(
            "SELECT evidence_id, source_id, run_id, purpose, request_url, "
            "request_method, response_status, response_headers, body_sha256, "
            "body_path, body_bytes, observed_at, origin "
            "FROM raw_http_evidence ORDER BY evidence_id"
        )
        .mappings()
        .all()
    )

    connection.exec_driver_sql(f"ALTER TABLE {_TABLE} RENAME TO {_LEGACY_TABLE}")
    connection.execute(CreateTable(table))
    for definition in (
        "body_sha256 VARCHAR(64)",
        "body_path TEXT",
        "body_bytes INTEGER",
    ):
        connection.exec_driver_sql(f"ALTER TABLE {_TABLE} ADD COLUMN {definition}")

    insert_columns = [column.name for column in table.columns] + list(
        _LEGACY_BODY_COLUMNS
    )
    placeholders = ", ".join("?" for _ in insert_columns)
    insert_sql = (
        f"INSERT INTO {_TABLE} ({', '.join(insert_columns)}) VALUES ({placeholders})"
    )

    for row in rows:
        evidence_id = row["evidence_id"]
        values = {
            "evidence_id": evidence_id,
            "source_id": row["source_id"],
            "run_id": row["run_id"],
            "purpose": row["purpose"],
            "observed_at": row["observed_at"],
            "origin": row["origin"],
            "request_fingerprint": hashlib.sha256(
                _FINGERPRINT_DOMAIN + evidence_id.encode("utf-8")
            ).hexdigest(),
            "request_url": row["request_url"],
            "request_method": row["request_method"],
            "request_headers": "{}",
            "request_body_sha256": _EMPTY_SHA256,
            "request_body_path": "",
            "request_body_bytes": 0,
            "response_url": None,
            "response_status": row["response_status"],
            "response_headers": row["response_headers"],
            "response_body_sha256": row["body_sha256"],
            "response_body_path": row["body_path"],
            "response_body_bytes": row["body_bytes"],
            "response_flags": "[]",
            "error_type": None,
            "error_message": None,
            "body_sha256": row["body_sha256"],
            "body_path": row["body_path"],
            "body_bytes": row["body_bytes"],
        }
        connection.exec_driver_sql(
            insert_sql, tuple(values[name] for name in insert_columns)
        )

    connection.exec_driver_sql(f"DROP TABLE {_LEGACY_TABLE}")

    for index in table.indexes:
        index.create(connection, checkfirst=True)
    connection.exec_driver_sql(
        "CREATE INDEX ix_raw_http_evidence_body_sha256 "
        "ON raw_http_evidence (body_sha256)"
    )
