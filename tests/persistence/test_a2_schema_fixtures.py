"""
Shared fixtures for the A2 schema tests; every database is in ``tmp_path``.

The schema 4 file is built from the live A1 SQLAlchemy metadata with
synthetic rows only. No test here opens a real database.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlalchemy import create_engine

from msgloom.persistence.a2_schema import (
    PROOF_REVISION,
    SCHEMA4_DIGEST,
    SCHEMA4_VERSION,
    MigrationGate,
    migrate_schema4_to_v5,
)
from msgloom.persistence.models import Phase1Base
from msgloom.persistence.records import SCHEMA_METADATA

GATE = MigrationGate(backup_sha256="b" * 64, schema4_digest=SCHEMA4_DIGEST)


def build_schema4(path: Path, *, legacy_keys: tuple[str, ...] = ()) -> Path:
    """Create a synthetic schema 4 file (12 tables, version 4, revision 1)."""
    engine = create_engine(f"sqlite:///{path}")
    try:
        with engine.begin() as connection:
            Phase1Base.metadata.create_all(connection)
            rows = [
                {"key": "schema_version", "value": SCHEMA4_VERSION},
                {"key": "preparation_proof_revision", "value": PROOF_REVISION},
            ]
            rows += [{"key": key, "value": "scope-x"} for key in legacy_keys]
            connection.execute(SCHEMA_METADATA.insert(), rows)
    finally:
        engine.dispose()
    return path


def raw(path: Path) -> sqlite3.Connection:
    """Open an autocommit connection with foreign keys on."""
    connection = sqlite3.connect(path, isolation_level=None, timeout=10)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def snapshot(path: Path) -> tuple[tuple[str, ...], ...]:
    """Return every schema row and metadata row for before/after checks."""
    db = raw(path)
    try:
        rows = tuple(
            tuple(map(str, row))
            for row in db.execute(
                "SELECT type, name, tbl_name, sql FROM sqlite_schema ORDER BY name"
            )
        )
        meta: tuple[tuple[str, str], ...] = ()
        if any(row[1] == "phase1_schema_metadata" for row in rows):
            meta = tuple(
                (str(k), str(v))
                for k, v in db.execute(
                    'SELECT "key", value FROM phase1_schema_metadata ORDER BY 1'
                )
            )
    finally:
        db.close()
    return rows + meta


def build_schema5(path: Path) -> Path:
    """Create a synthetic schema 4 file and migrate it to schema 5."""
    build_schema4(path)
    db = raw(path)
    try:
        migrate_schema4_to_v5(db, GATE)
    finally:
        db.close()
    return path
