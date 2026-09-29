"""Verify transactional migration of the exact response-only evidence table."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from threading import Barrier

import pytest
from scrapy import Request
from sqlalchemy import event, inspect, select

from message_ingest.catalog import Base, Catalog, RawHttpEvidence
from message_ingest.fingerprints.microsoft_graph import (
    RepresentationAwareRequestFingerprinter,
)

# Keep the historical DDL independent of current model metadata. In particular,
# old response_status and body_* columns have NOT NULL and no server default.
_LEGACY_DDL = """
CREATE TABLE raw_http_evidence (
    evidence_id VARCHAR(32) NOT NULL,
    source_id VARCHAR(200) NOT NULL,
    run_id VARCHAR(32),
    purpose VARCHAR(80),
    request_url TEXT NOT NULL,
    request_method VARCHAR(16) NOT NULL,
    response_status INTEGER NOT NULL,
    response_headers JSON NOT NULL,
    body_sha256 VARCHAR(64) NOT NULL,
    body_path TEXT NOT NULL,
    body_bytes INTEGER NOT NULL,
    observed_at VARCHAR(40) NOT NULL,
    origin VARCHAR(24) NOT NULL,
    PRIMARY KEY (evidence_id)
)
"""
_LEGACY_COLUMNS = (
    "evidence_id, source_id, run_id, purpose, request_url, request_method, "
    "response_status, response_headers, body_sha256, body_path, body_bytes, "
    "observed_at, origin"
)


@pytest.fixture
def legacy_path(tmp_path: Path) -> Path:
    """Create real response blobs and two captures with historical SQL only."""
    path = tmp_path / "legacy.sqlite3"
    with closing(sqlite3.connect(path)) as connection:
        connection.execute(_LEGACY_DDL)
        for column in (
            "source_id",
            "run_id",
            "purpose",
            "observed_at",
            "origin",
            "body_sha256",
        ):
            connection.execute(
                f"CREATE INDEX ix_raw_http_evidence_{column} "
                f"ON raw_http_evidence ({column})"
            )
        for number, body in enumerate((b'{"value": []}\n', b"\x00raw\xffpayload")):
            blob = tmp_path / f"response {number}.bin"
            blob.write_bytes(body)
            connection.execute(
                f"INSERT INTO raw_http_evidence ({_LEGACY_COLUMNS}) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"legacy-{number}",
                    f"source-{number}",
                    "run-0" if number == 0 else None,
                    "message-list" if number == 0 else None,
                    "https://graph.microsoft.com/v1.0/me/messages?%24top=2",
                    "GET",
                    200 if number == 0 else 503,
                    '{ "Content-Type": ["application/json"], "X-Order": ["b", "a"] }',
                    hashlib.sha256(body).hexdigest(),
                    str(blob),
                    len(body),
                    f"2026-09-2{number}T03:04:05.123456+10:00",
                    "network" if number == 0 else "http_cache",
                ),
            )
        connection.commit()
    return path


def _legacy_rows(path: Path):
    """Read original fields without JSON decoding or timestamp conversion."""
    with closing(sqlite3.connect(path)) as connection:
        connection.row_factory = sqlite3.Row
        return {
            row["evidence_id"]: dict(row)
            for row in connection.execute(
                f"SELECT {_LEGACY_COLUMNS} FROM raw_http_evidence ORDER BY evidence_id"
            )
        }


def _snapshot(path: Path) -> tuple[str, ...]:
    """Capture schema, indexes, and all SQL values for no-op/rollback checks."""
    with closing(sqlite3.connect(path)) as connection:
        return tuple(connection.iterdump())


def test_legacy_evidence_backfill_preserves_rows_and_indexes(legacy_path: Path) -> None:
    before = _legacy_rows(legacy_path)
    blobs = {
        row["body_path"]: Path(row["body_path"]).read_bytes() for row in before.values()
    }
    catalog = Catalog(f"sqlite:///{legacy_path}")
    try:
        with catalog.Session() as session:
            captures = session.scalars(select(RawHttpEvidence)).all()
        if len(captures) != 2 or {row.evidence_id for row in captures} != set(before):
            pytest.fail("Migration changed the evidence row count or identity")
        fingerprints: set[str] = set()
        fingerprinter = RepresentationAwareRequestFingerprinter(b"test-source-context")
        for capture in captures:
            original = before[capture.evidence_id]
            for name, value in original.items():
                if name.startswith("body_") or name == "response_headers":
                    continue
                if getattr(capture, name) != value:
                    pytest.fail(f"Migration changed the provider field {name}")
            if capture.response_headers != json.loads(original["response_headers"]):
                pytest.fail("ORM could not load the preserved response headers")
            response_metadata = (
                capture.response_body_sha256,
                capture.response_body_path,
                capture.response_body_bytes,
            )
            if response_metadata != (
                original["body_sha256"],
                original["body_path"],
                original["body_bytes"],
            ):
                pytest.fail("Legacy response metadata was not copied exactly")
            if (
                capture.request_body_sha256,
                capture.request_body_path,
                capture.request_body_bytes,
            ) != (hashlib.sha256(b"").hexdigest(), "", 0):
                pytest.fail("Legacy request metadata must describe an empty body")
            if (
                capture.request_headers,
                capture.response_url,
                capture.response_flags,
                capture.error_type,
                capture.error_message,
            ) != ({}, None, [], None, None):
                pytest.fail("Migration invented unavailable request/response metadata")
            if re.fullmatch(r"[0-9a-f]{64}", capture.request_fingerprint) is None:
                pytest.fail("Expected a migration-only SHA-256 fingerprint")
            fingerprints.add(capture.request_fingerprint)
            current_fingerprint = fingerprinter.fingerprint(
                Request(capture.request_url, method=capture.request_method)
            ).hex()
            if (
                catalog.evidence.find_cached_response(
                    source_id=capture.source_id,
                    request_fingerprint=current_fingerprint,
                    response_body_sha256=capture.response_body_sha256,
                )
                is not None
            ):
                pytest.fail("A current request aliased to historical evidence")
        if len(fingerprints) != len(captures):
            pytest.fail("Historical fingerprints must be distinct per evidence row")
        with catalog.engine.connect() as connection:
            inspector = inspect(connection)
            table = Base.metadata.tables["raw_http_evidence"]
            columns = {column["name"] for column in inspector.get_columns(table.name)}
            if columns != set(table.columns.keys()) | set(_LEGACY_COLUMNS.split(", ")):
                pytest.fail("Migration lost legacy columns or omitted current columns")
            indexes = {
                index["name"]: index["column_names"]
                for index in inspector.get_indexes(table.name)
            }
            for index in table.indexes:
                if indexes.get(index.name) != [column.name for column in index.columns]:
                    pytest.fail(f"Missing current model index: {index.name}")
            if indexes.get("ix_raw_http_evidence_body_sha256") != ["body_sha256"]:
                pytest.fail("Migration removed the historical response digest index")
    finally:
        catalog.close()
    if _legacy_rows(legacy_path) != before:
        pytest.fail("Migration changed original SQL values, including JSON text")
    for path, body in blobs.items():
        if Path(path).read_bytes() != body:
            pytest.fail("Migration changed a historical response payload file")

    snapshot = _snapshot(legacy_path)
    reopened = Catalog(f"sqlite:///{legacy_path}")
    reopened.close()
    if _snapshot(legacy_path) != snapshot:
        pytest.fail("Reopening migrated evidence changed schema, indexes, or values")


@pytest.mark.parametrize(
    "alteration",
    [
        "ADD COLUMN request_fingerprint VARCHAR(64)",
        "ADD COLUMN unknown_metadata TEXT",
        "DROP COLUMN body_bytes",
    ],
)
def test_unknown_partial_evidence_schema_fails_closed(
    legacy_path: Path, alteration: str
) -> None:
    with closing(sqlite3.connect(legacy_path)) as connection:
        connection.execute(f"ALTER TABLE raw_http_evidence {alteration}")
        connection.commit()
    before = _snapshot(legacy_path)
    with pytest.raises(ValueError, match="Unsupported raw_http_evidence schema"):
        Catalog(f"sqlite:///{legacy_path}")
    if _snapshot(legacy_path) != before:
        pytest.fail("Rejected schema was silently rewritten or partially initialized")


def test_current_evidence_schema_and_rows_are_unchanged(tmp_path: Path) -> None:
    """Current captures retain their actual metadata when the catalog reopens."""
    path = tmp_path / "current.sqlite3"
    catalog = Catalog(f"sqlite:///{path}")
    try:
        catalog.evidence.record(
            RawHttpEvidence(
                evidence_id="current-0",
                source_id="source-0",
                observed_at="2026-09-29T01:02:03+00:00",
                origin="network",
                request_fingerprint="a" * 64,
                request_url="https://graph.microsoft.com/v1.0/me",
                request_method="POST",
                request_headers={"Content-Type": ["application/json"]},
                request_body_sha256="b" * 64,
                request_body_path="request.bin",
                request_body_bytes=12,
                response_url=None,
                response_status=None,
                response_headers={},
                response_body_sha256=hashlib.sha256(b"").hexdigest(),
                response_body_path="empty.bin",
                response_body_bytes=0,
                response_flags=["partial"],
                error_type="ConnectionLost",
                error_message="Connection closed before a response",
            )
        )
    finally:
        catalog.close()
    before = _snapshot(path)
    reopened = Catalog(f"sqlite:///{path}")
    reopened.close()
    if _snapshot(path) != before:
        pytest.fail("Migration rewrote a current capture or changed its schema")


def test_legacy_migration_rolls_back_with_later_schema_failure(
    legacy_path: Path,
) -> None:
    """Backfill and indexes must roll back with the enclosing create_all."""
    before = _snapshot(legacy_path)
    first_table = Base.metadata.sorted_tables[0]

    def fail_after_create(target, connection, **kwargs) -> None:
        fingerprint = connection.exec_driver_sql(
            "SELECT request_fingerprint FROM raw_http_evidence LIMIT 1"
        ).scalar_one()
        if re.fullmatch(r"[0-9a-f]{64}", fingerprint) is None:
            pytest.fail("Injected failure must follow a real evidence backfill")
        raise RuntimeError("injected post-migration failure")

    event.listen(first_table, "after_create", fail_after_create)
    try:
        with pytest.raises(RuntimeError, match="injected post-migration failure"):
            Catalog(f"sqlite:///{legacy_path}")
    finally:
        event.remove(first_table, "after_create", fail_after_create)
    if _snapshot(legacy_path) != before:
        pytest.fail("Schema failure left partial legacy columns, values, or indexes")
    catalog = Catalog(f"sqlite:///{legacy_path}")
    catalog.close()


def test_concurrent_legacy_catalog_initialization(legacy_path: Path) -> None:
    """Only one writer migrates; later initializers see the committed schema."""
    before = _legacy_rows(legacy_path)
    barrier = Barrier(3)

    def open_catalog() -> dict[str, str]:
        barrier.wait(timeout=10)
        catalog = Catalog(f"sqlite:///{legacy_path}")
        try:
            with catalog.Session() as session:
                return {
                    row.evidence_id: row.request_fingerprint
                    for row in session.scalars(select(RawHttpEvidence))
                }
        finally:
            catalog.close()

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(open_catalog) for _ in range(3)]
        results = [future.result(timeout=15) for future in futures]
    if any(result != results[0] for result in results[1:]):
        pytest.fail("Concurrent initialization produced inconsistent evidence")
    if set(results[0]) != set(before) or len(set(results[0].values())) != 2:
        pytest.fail("Concurrent migration lost rows or produced duplicate fingerprints")
    if _legacy_rows(legacy_path) != before:
        pytest.fail("Concurrent initialization changed historical fields")


def test_migrated_table_accepts_current_evidence_writes(legacy_path: Path) -> None:
    """Compatibility columns must not block current ORM inserts after migration."""
    catalog = Catalog(f"sqlite:///{legacy_path}")
    try:
        current = RawHttpEvidence(
            evidence_id="current-after-migration",
            source_id="source-new",
            run_id=None,
            purpose="todo-task-lists-page",
            observed_at="2026-09-29T00:55:00+00:00",
            origin="network",
            request_fingerprint="c" * 64,
            request_url="https://graph.microsoft.com/v1.0/me/todo/lists",
            request_method="GET",
            request_headers={},
            request_body_sha256=hashlib.sha256(b"").hexdigest(),
            request_body_path="",
            request_body_bytes=0,
            response_url="https://graph.microsoft.com/v1.0/me/todo/lists",
            response_status=None,
            response_headers={},
            response_body_sha256=hashlib.sha256(b"").hexdigest(),
            response_body_path="empty.bin",
            response_body_bytes=0,
            response_flags=[],
            error_type="ConnectionLost",
            error_message=None,
        )
        if catalog.evidence.record(current) != current.evidence_id:
            pytest.fail("Current evidence insert did not return its identity")
        with catalog.Session() as session:
            stored = session.get(RawHttpEvidence, current.evidence_id)
            if stored is None or stored.response_status is not None:
                pytest.fail(
                    "Migrated table changed current nullable response semantics"
                )
        with catalog.engine.connect() as connection:
            compat = connection.exec_driver_sql(
                "SELECT body_sha256, body_path, body_bytes "
                "FROM raw_http_evidence WHERE evidence_id = ?",
                (current.evidence_id,),
            ).one()
            if tuple(compat) != (None, None, None):
                pytest.fail("Current writes must not fabricate obsolete body_* values")
            columns = {
                column["name"]: column
                for column in inspect(connection).get_columns("raw_http_evidence")
            }
            for name in ("body_sha256", "body_path", "body_bytes"):
                if not columns[name]["nullable"]:
                    pytest.fail(
                        f"Compatibility column {name} still blocks current writes"
                    )
    finally:
        catalog.close()
