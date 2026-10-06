"""Qualify writer cleanup with real SQLite faults and connection loss."""

from __future__ import annotations

import asyncio
import sqlite3

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import QueuePool
from test_raw_evidence_transactions import _capture, _fields, _mode, _rows

from message_ingest.catalog import Catalog

MODES = ("file", "memory", "memory-colon")


@pytest.fixture(params=MODES)
def database(tmp_path, request):
    """Create one isolated catalog in each supported existing driver mode."""
    mode = request.param
    url = {
        "file": f"sqlite:///{tmp_path / 'catalog.db'}",
        "memory": "sqlite://",
        "memory-colon": "sqlite:///:memory:",
    }[mode]
    catalog = Catalog(url)
    catalog.evidence.record(_capture("baseline"))
    try:
        yield catalog, mode
    finally:
        catalog.close()


def _inject(catalog, error, phase="insert"):
    """Observe real engine ownership and inject at an exact SQL boundary."""
    connections, drivers, invalidations, connects, statements, entries = (
        [],
        [],
        [],
        [],
        [],
        [],
    )
    outcome = None

    def after(connection, cursor, statement, parameters, context, many):
        statements.append(statement)
        if (phase == "insert" and statement.startswith("INSERT INTO raw_http")) or (
            phase in ("begin-exit", "post-commit")
            and statement == ("COMMIT" if phase == "post-commit" else "BEGIN IMMEDIATE")
        ):
            raise error

    def before(connection, cursor, statement, parameters, context, many):
        if connection not in connections:
            connections.append(connection)
            drivers.append(connection.connection.driver_connection)
        if (phase == "commit" and statement == "COMMIT") or (
            phase == "begin" and statement == "BEGIN IMMEDIATE"
        ):
            raise error

    def invalidated(driver, record, exception):
        invalidations.append((driver, exception))

    def connected(driver, record):
        connects.append(driver)

    hooks = [
        ("before_cursor_execute", before),
        ("after_cursor_execute", after),
        ("invalidate", invalidated),
        ("connect", connected),
    ]
    for name, hook in hooks:
        event.listen(catalog.engine, name, hook)
    try:
        if phase.startswith(("body", "begin")):
            with catalog.writer_session() as session:
                entries.append(True)
                session.add(_capture("failed"))
                session.flush()
                if phase == "body-invalidate":
                    session.connection().invalidate(error)
                raise error
        else:
            catalog.evidence.record(_capture("failed"))
    except (RuntimeError, asyncio.CancelledError, sqlite3.Error) as caught:
        outcome = caught
    finally:
        for name, hook in hooks:
            event.remove(catalog.engine, name, hook)
    return {
        "outcome": outcome,
        "connections": connections,
        "drivers": drivers,
        "invalidations": invalidations,
        "connects": connects,
        "statements": statements,
        "entries": entries,
        "checkedout": catalog.engine.pool.checkedout(),
    }


def _ownership(result):
    """Reject a held transaction, pool checkout or cleanup reconnection."""
    if result["checkedout"] != 0 or result["connects"]:
        pytest.fail("Fault cleanup leaked checkout or reconnected the driver")
    if not result["connections"] or any(
        not connection.closed or connection.in_transaction()
        for connection in result["connections"]
    ):
        pytest.fail("Fault cleanup retained SQLAlchemy transaction ownership")


def _exit(catalog):
    """Require the historical E5 initiating object after a real raw INSERT."""
    error = asyncio.CancelledError("exact synthetic after-cursor E5 exit")
    result = _inject(catalog, error)
    _ownership(result)
    if result["outcome"] is not error:
        pytest.fail(f"E5 initiating exception was masked: {result['outcome']!r}")
    if result["invalidations"] != [(result["drivers"][0], error)]:
        pytest.fail("Exact injected exit did not invalidate the actual driver")
    if sum(sql.startswith("INSERT INTO raw_http") for sql in result["statements"]) != 1:
        pytest.fail("E5 did not follow exactly one actual SQLite INSERT")
    if "ROLLBACK" in result["statements"] or "COMMIT" in result["statements"]:
        pytest.fail("Invalidated cleanup attempted more SQL")
    return result


def _surviving(catalog, mode, result, error, before):
    """Verify all old fields, original mode and later real writer usability."""
    _ownership(result)
    if result["outcome"] is not error or result["invalidations"]:
        pytest.fail("Ordinary error identity or surviving driver changed")
    if _rows(catalog) != before:
        pytest.fail("Failed writer changed a prior column or retained its INSERT")
    with catalog.engine.connect() as connection:
        if connection.connection.driver_connection is not result["drivers"][0]:
            pytest.fail("Ordinary failure replaced its surviving driver")
    _mode(catalog, mode != "file")
    catalog.evidence.record(_capture("subsequent"))
    if len(_rows(catalog)) != len(before) + 1:
        pytest.fail("Subsequent independent writer could not commit")


def test_writer_e5_after_real_insert_preserves_exit_identity(database):
    """Keep synthetic exit identity on file and both memory URL spellings."""
    catalog, _ = database
    _exit(catalog)


@pytest.mark.parametrize("phase", ["insert", "begin-exit", "body-invalidate"])
def test_writer_invalidated_cleanup_releases_transaction_and_pool(database, phase):
    """Clear ownership after invalidation without accessing a dead driver."""
    catalog, _ = database
    error = asyncio.CancelledError(phase)
    result = _inject(catalog, error, phase)
    _ownership(result)
    if result["outcome"] is not error or len(result["invalidations"]) != 1:
        pytest.fail("Invalidated unwind lost its initiating exit")


def test_writer_ordinary_insert_failure_rolls_back_exact_rows(database):
    """
    Preserve every baseline field after a real INSERT then ordinary error.
    """
    catalog, mode = database
    before = _rows(catalog)
    error = RuntimeError("after actual INSERT")
    result = _inject(catalog, error)
    _surviving(catalog, mode, result, error, before)


def test_writer_commit_failure_rolls_back_and_restores_surviving_mode(database):
    """Fail before SQLite COMMIT and retain exact rollback and driver mode."""
    catalog, mode = database
    before = _rows(catalog)
    error = RuntimeError("before actual COMMIT")
    result = _inject(catalog, error, "commit")
    if not any(sql.startswith("INSERT INTO raw_http") for sql in result["statements"]):
        pytest.fail("Commit fault did not follow a real INSERT")
    _surviving(catalog, mode, result, error, before)


@pytest.mark.parametrize("exit_fault", [False, True])
def test_writer_begin_failure_restores_valid_mode_and_releases_pool(
    database, exit_fault
):
    """Keep entry failures outside the body with no abandoned transaction."""
    catalog, mode = database
    before = _rows(catalog)
    error = asyncio.CancelledError("BEGIN") if exit_fault else RuntimeError("BEGIN")
    result = _inject(catalog, error, "begin-exit" if exit_fault else "begin")
    _ownership(result)
    if result["entries"] or result["outcome"] is not error:
        pytest.fail("Writer BEGIN failure entered the body or changed identity")
    if exit_fault:
        if result["invalidations"] != [(result["drivers"][0], error)]:
            pytest.fail("BEGIN exit did not invalidate the original driver")
    else:
        _surviving(catalog, mode, result, error, before)


def test_writer_file_invalidation_preserves_prior_rows_and_reopen(tmp_path):
    """Qualify exact file preservation separately from pool reconnection."""
    url = f"sqlite:///{tmp_path / 'catalog.db'}"
    catalog = Catalog(url)
    catalog.evidence.record(_capture("baseline"))
    before = _rows(catalog)
    try:
        _exit(catalog)
        if _rows(catalog) != before:
            pytest.fail("File invalidation changed prior immutable capture fields")
        catalog.evidence.record(_capture("same-instance"))
        _mode(catalog, False)
        expected = _rows(catalog)
    finally:
        catalog.close()
    reopened = Catalog(url)
    try:
        if _rows(reopened) != expected:
            pytest.fail("Independent file reopen lost surviving committed data")
        reopened.evidence.record(_capture("independent"))
        if len(_rows(reopened)) != 3:
            pytest.fail("Independent catalog could not write after invalidation")
        _mode(reopened, False)
    finally:
        reopened.close()


@pytest.mark.parametrize("url", ["sqlite://", "sqlite:///:memory:"])
def test_writer_memory_invalidation_reports_database_loss(url):
    """Observe destroyed schema and data without inventing memory recovery."""
    catalog = Catalog(url)
    catalog.evidence.record(_capture("lost-baseline"))
    try:
        _exit(catalog)
        with catalog.engine.connect() as connection:
            tables = (
                connection.exec_driver_sql(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                .scalars()
                .all()
            )
        if tables:
            pytest.fail("Invalidated memory driver unexpectedly retained schema")
        with pytest.raises(OperationalError, match="no such table"):
            _rows(catalog)
        with pytest.raises(OperationalError, match="no such table"):
            catalog.evidence.record(_capture("unrecoverable"))
        pool = catalog.engine.pool
        if not isinstance(pool, QueuePool):
            pytest.fail("Catalog changed its required pool class")
        if pool.checkedout() != 0:
            pytest.fail("Visible memory-loss failure retained a checkout")
    finally:
        catalog.close()
    fresh = Catalog(url)
    try:
        if _rows(fresh):
            pytest.fail("Independent memory catalog was not a new empty database")
        fresh.evidence.record(_capture("new-database"))
        if [row["evidence_id"] for row in _rows(fresh)] != ["new-database"]:
            pytest.fail("New memory catalog invented rescue of prior data")
    finally:
        fresh.close()


def test_writer_normal_duplicate_and_error_modes_remain_unchanged(database):
    """
    Reserve before every duplicate lookup and retain the complete first row.
    """
    catalog, mode = database
    statements = []

    def trace(connection, cursor, statement, parameters, context, many):
        statements.append(statement)

    event.listen(catalog.engine, "before_cursor_execute", trace)
    try:
        result = catalog.evidence.record(_capture("baseline", "conflicting", 2))
    finally:
        event.remove(catalog.engine, "before_cursor_execute", trace)
    if result != "baseline" or _rows(catalog) != [_fields(_capture("baseline"))]:
        pytest.fail("Duplicate replay mutated an immutable first-row field")
    if statements[0] != "BEGIN IMMEDIATE" or statements[-1] != "COMMIT":
        pytest.fail("Duplicate early return lost writer-before-read ownership")
    _mode(catalog, mode != "file")


def test_writer_body_failure_keeps_initiating_error(database):
    """Preserve body errors after a real flush and before commit."""
    catalog, mode = database
    error = RuntimeError("body")
    before = _rows(catalog)
    result = _inject(catalog, error, "body")
    _ownership(result)
    if result["outcome"] is not error or _rows(catalog) != before:
        pytest.fail("Body failure lost identity or failed transaction rollback")
    _mode(catalog, mode != "file")


@pytest.mark.parametrize("exit_fault", [False, True])
def test_writer_completed_commit_preserves_durable_outcome(database, exit_fault):
    """Never claim rollback after the real SQLite COMMIT has completed."""
    catalog, mode = database
    error = (
        asyncio.CancelledError("after COMMIT")
        if exit_fault
        else RuntimeError("after COMMIT")
    )
    result = _inject(catalog, error, "post-commit")
    _ownership(result)
    if result["outcome"] is not error or "COMMIT" not in result["statements"]:
        pytest.fail("Post-COMMIT failure lost actual commit or error identity")
    if "ROLLBACK" in result["statements"]:
        pytest.fail("Cleanup fabricated rollback after completed COMMIT")
    if mode != "file" and exit_fault:
        with pytest.raises(OperationalError, match="no such table"):
            _rows(catalog)
        return
    if sorted(row["evidence_id"] for row in _rows(catalog)) != ["baseline", "failed"]:
        pytest.fail("A completed COMMIT was incorrectly reported as rolled back")
    _mode(catalog, mode != "file")


def test_writer_native_dbapi_wrapper_identity_is_preserved(database):
    """Preserve the actual SQLAlchemy wrapper and its native driver error."""
    catalog, mode = database
    delivered = []
    before = _rows(catalog)
    with (
        pytest.raises(OperationalError) as caught,
        catalog.writer_session() as session,
    ):
        session.add(_capture("failed"))
        session.flush()
        try:
            session.execute(text("SELECT * FROM missing_fault_fixture"))
        except OperationalError as error:
            delivered.append(error)
            raise
    if delivered != [caught.value] or not isinstance(caught.value.orig, sqlite3.Error):
        pytest.fail("Helper replaced or flattened the delivered DBAPI wrapper")
    if _rows(catalog) != before or catalog.engine.pool.checkedout() != 0:
        pytest.fail("DBAPI body error failed to release or roll back the writer")
    _mode(catalog, mode != "file")
