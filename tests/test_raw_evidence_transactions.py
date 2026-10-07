"""Qualify raw capture transactions without waits inside writer locks."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import event, select

from message_ingest.catalog import Catalog, RawHttpEvidence


class CaptureFailure(RuntimeError):
    """Identify an ordinary injected persistence failure."""


def _capture(identity="capture", source="source-a", version=1):
    """Populate every persisted field for exact duplicate comparisons."""
    token = f"{source}-{version}"
    return RawHttpEvidence(
        evidence_id=identity,
        source_id=source,
        run_id=f"run-{token}",
        purpose=f"purpose-{token}",
        observed_at=f"2026-10-0{version}T00:00:00Z",
        origin="network" if version == 1 else "http_cache",
        request_fingerprint=f"fingerprint-{token}",
        request_url=f"https://example.test/{token}",
        request_method="GET",
        request_headers={"X-Test": [token]},
        request_body_sha256=token,
        request_body_path=f"/fixture/request-{token}",
        request_body_bytes=version,
        response_url=f"https://example.test/response/{token}",
        response_status=200 + version,
        response_headers={"X-Test": [token]},
        response_body_sha256=f"response-{token}",
        response_body_path=f"/fixture/response-{token}",
        response_body_bytes=version + 1,
        response_flags=[token],
        error_type=f"error-{token}",
        error_message=f"message-{token}",
    )


def _fields(row):
    """Compare every table column, including nullable capture metadata."""
    return {
        column.name: getattr(row, column.name)
        for column in RawHttpEvidence.__table__.columns
    }


def _rows(catalog):
    """Read committed capture snapshots outside any writer reservation."""
    with catalog.Session() as session:
        return [_fields(row) for row in session.scalars(select(RawHttpEvidence))]


def _mode(catalog, memory):
    """Check unchanged SQLite and pool settings after transaction cleanup."""
    with catalog.engine.connect() as connection:
        driver = connection.connection.driver_connection
        if driver.autocommit is not False:
            pytest.fail("Runtime connection lost explicit autocommit=False")
        journal = connection.exec_driver_sql("PRAGMA journal_mode").scalar()
        busy = connection.exec_driver_sql("PRAGMA busy_timeout").scalar()
    if journal != ("memory" if memory else "delete") or busy != 30000:
        pytest.fail(f"Transaction policy changed: {journal}, {busy}")
    if catalog.engine.pool.size() != 1 or catalog.engine.pool._max_overflow != 0:
        pytest.fail("Catalog pool policy changed")


@pytest.mark.parametrize("memory", [False, True])
@pytest.mark.parametrize("duplicate", [False, True])
def test_writer_reservation_precedes_duplicate_read(tmp_path, memory, duplicate):
    """Require writer intent before the first capture lookup on every path."""
    url = "sqlite://" if memory else f"sqlite:///{tmp_path / 'catalog.db'}"
    catalog = Catalog(url)
    original = _capture()
    expected = _fields(original)
    if duplicate:
        catalog.evidence.record(original)
    statements = []

    def trace(connection, cursor, statement, parameters, context, many):
        statements.append(statement.strip().upper())

    event.listen(catalog.engine, "before_cursor_execute", trace)
    try:
        actual = catalog.evidence.record(
            _capture(source="source-b", version=2) if duplicate else original
        )
        rows = _rows(catalog)
        _mode(catalog, memory)
    finally:
        event.remove(catalog.engine, "before_cursor_execute", trace)
        catalog.close()
    if actual != "capture" or rows != [expected]:
        pytest.fail("Capture replay changed the immutable first row")
    reads = [
        i
        for i, sql in enumerate(statements)
        if sql.startswith("SELECT") and "RAW_HTTP_EVIDENCE" in sql
    ]
    begins = [i for i, sql in enumerate(statements) if sql == "BEGIN IMMEDIATE"]
    if len(begins) != 1 or not reads or begins[0] >= reads[0]:
        pytest.fail(f"Duplicate read preceded writer reservation: {statements}")
    if statements.count("COMMIT") != 1:
        pytest.fail("Raw capture did not have exactly one owned commit")


@pytest.mark.parametrize("same_id", [False, True])
def test_independent_catalog_writers_and_duplicate_capture(tmp_path, same_id):
    """Release two real writers at an external barrier, then retain both."""
    url = f"sqlite:///{tmp_path / 'catalog.db'}"
    Catalog(url).close()
    ready = threading.Barrier(2)
    snapshots = {}

    def write(source):
        catalog = Catalog(url)
        row = _capture("shared" if same_id else source, source)
        snapshots[source] = _fields(row)
        try:
            ready.wait(5)
            return catalog.evidence.record(row)
        finally:
            catalog.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(write, source) for source in ("source-a", "source-b")
        ]
        results = [future.result(timeout=5) for future in futures]
    reopened = Catalog(url)
    try:
        rows = _rows(reopened)
        if same_id:
            if results != ["shared", "shared"] or len(rows) != 1:
                pytest.fail("Concurrent duplicate did not retain one capture")
            if rows[0] not in snapshots.values():
                pytest.fail("Concurrent duplicate mixed capture fields")
            reopened.evidence.record(_capture("shared", "conflict", 2))
            if _rows(reopened) != rows:
                pytest.fail("Conflicting replay changed any first-row field")
        elif sorted(rows, key=lambda row: row["source_id"]) != [
            snapshots["source-a"],
            snapshots["source-b"],
        ]:
            pytest.fail("Independent writers lost or crossed source ownership")
        reopened.evidence.record(_capture("independent", "source-c"))
        if len(_rows(reopened)) != len(rows) + 1:
            pytest.fail("Independent writer could not acquire a released lock")
        _mode(reopened, False)
    finally:
        reopened.close()


@pytest.mark.parametrize("memory", [False, True])
@pytest.mark.parametrize("failure", ["insert", "commit"])
def test_ordinary_failure_rolls_back_and_restores_driver(tmp_path, memory, failure):
    """Preserve error identity and restore modes before retry and reopen."""
    url = "sqlite://" if memory else f"sqlite:///{tmp_path / 'catalog.db'}"
    catalog = Catalog(url)
    catalog.evidence.record(_capture("retained"))
    before = _rows(catalog)
    error = CaptureFailure(failure)

    def after_sql(connection, cursor, statement, parameters, context, many):
        if failure == "insert" and statement.startswith("INSERT INTO raw_http"):
            raise error

    def before_sql(connection, cursor, statement, parameters, context, many):
        if failure == "commit" and statement == "COMMIT":
            raise error

    def before_commit(connection):
        if failure == "commit":
            raise error

    hooks = [
        ("after_cursor_execute", after_sql),
        ("before_cursor_execute", before_sql),
        ("commit", before_commit),
    ]
    for name, hook in hooks:
        event.listen(catalog.engine, name, hook)
    try:
        with pytest.raises(CaptureFailure) as caught:
            catalog.evidence.record(_capture("failed"))
        if caught.value is not error:
            pytest.fail("Ordinary transaction failure identity changed")
    finally:
        for name, hook in hooks:
            event.remove(catalog.engine, name, hook)
    try:
        if _rows(catalog) != before:
            pytest.fail("Failed capture transaction changed existing rows")
        _mode(catalog, memory)
        catalog.evidence.record(_capture("retry"))
        expected = _rows(catalog)
        if len(expected) != 2:
            pytest.fail("Retry did not commit once after rollback")
        _mode(catalog, memory)
    finally:
        catalog.close()
    if not memory:
        reopened = Catalog(url)
        try:
            if _rows(reopened) != expected:
                pytest.fail("Reopen lost committed captures after rollback")
            reopened.evidence.record(_capture("independent", "source-b"))
            _mode(reopened, False)
        finally:
            reopened.close()
