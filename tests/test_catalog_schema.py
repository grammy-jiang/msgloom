"""
Verify the catalog uses the expected SQLAlchemy schema without legacy tables.
"""

from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, inspect, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError

from message_ingest.catalog import Base, Catalog


@pytest.mark.parametrize("url", ["sqlite:///:memory:", "sqlite://"])
def test_memory_schema_survives_startup_and_worker_checkouts(url: str) -> None:
    """Private catalogs retain their schema and normal runtime transactions."""
    catalog = Catalog(url)
    independent = Catalog(url)
    table = Base.metadata.tables["messages"]

    def write_and_read() -> None:
        with catalog.engine.begin() as connection:
            if set(inspect(connection).get_table_names()) != set(Base.metadata.tables):
                pytest.fail("Memory catalog lost its initialized schema")
            connection.execute(
                table.insert().values(
                    source_id="memory-source",
                    message_id="committed",
                    is_removed=False,
                    latest_observed_at="2026-09-27T00:00:00+00:00",
                )
            )
        with catalog.engine.connect() as connection:
            connection.execute(
                table.insert().values(
                    source_id="memory-source",
                    message_id="rolled-back",
                    is_removed=False,
                    latest_observed_at="2026-09-27T00:00:00+00:00",
                )
            )
            connection.rollback()

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(write_and_read).result(timeout=5)
        with catalog.engine.connect() as connection:
            if connection.execute(select(table.c.message_id)).scalars().all() != [
                "committed"
            ]:
                pytest.fail("Memory catalog did not preserve commit/rollback behavior")
        with independent.engine.connect() as connection:
            if connection.execute(select(table)).first() is not None:
                pytest.fail("Private memory catalogs unexpectedly share rows")
    finally:
        catalog.close()
        independent.close()


def _url(path: Path) -> str:
    return f"sqlite:///{path}"


def test_fresh_catalog_creates_current_sqlalchemy_schema(tmp_path: Path) -> None:
    path = tmp_path / "catalog.sqlite3"

    catalog = Catalog(_url(path))
    try:
        with catalog.engine.connect() as connection:
            tables = set(inspect(connection).get_table_names())
        if set(Base.metadata.tables) != tables:
            pytest.fail("Expected: set(Base.metadata.tables) == tables")
    finally:
        catalog.close()

    if path.stat().st_mode & 511 != 384:
        pytest.fail("Expected: path.stat().st_mode & 0o777 == 0o600")


def test_reopening_current_catalog_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "catalog.sqlite3"

    first = Catalog(_url(path))
    first.close()
    second = Catalog(_url(path))
    try:
        with second.engine.connect() as connection:
            tables = set(inspect(connection).get_table_names())
        if set(Base.metadata.tables) != tables:
            pytest.fail("Expected: set(Base.metadata.tables) == tables")
    finally:
        second.close()


def test_schema_lock_failure_preserves_original_error(tmp_path: Path) -> None:
    """A failed BEGIN has nothing to roll back and must close its connection."""
    path = tmp_path / "locked.sqlite3"
    blocker = sqlite3.connect(path, autocommit=True)
    blocker.execute("BEGIN IMMEDIATE")
    connections: list[sqlite3.Connection] = []
    disposed: list[Engine] = []
    statements: list[str] = []

    def no_wait(connection, connection_record) -> None:
        connection.execute("PRAGMA busy_timeout=0")
        connection.set_trace_callback(statements.append)
        connections.append(connection)

    def record_disposal(engine: Engine) -> None:
        disposed.append(engine)

    event.listen(Engine, "connect", no_wait)
    event.listen(Engine, "engine_disposed", record_disposal)
    try:
        with pytest.raises(OperationalError, match="database is locked") as error:
            Catalog(_url(path))
        if error.value.statement != "BEGIN IMMEDIATE":
            pytest.fail("Lock failure was replaced by a cleanup error")
        if not isinstance(error.value.orig, sqlite3.OperationalError):
            pytest.fail("Expected the original SQLite lock error")
        # The dialect can query its isolation level before our first SQL.
        if [sql for sql in statements if sql != "PRAGMA read_uncommitted"] != [
            "BEGIN IMMEDIATE"
        ]:
            pytest.fail(f"Unexpected SQL after lock failure: {statements!r}")
        if len(connections) != 1 or len(disposed) != 1:
            pytest.fail("Expected disposal of the failed schema engine only")
        with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
            connections[0].execute("SELECT 1")
    finally:
        event.remove(Engine, "connect", no_wait)
        event.remove(Engine, "engine_disposed", record_disposal)
        blocker.execute("ROLLBACK")
        blocker.close()

    catalog = Catalog(_url(path))
    catalog.close()


def test_schema_ddl_failure_rolls_back_and_releases_writer(tmp_path: Path) -> None:
    """An error after real DDL must leave no partial schema or writer lock."""
    url = _url(tmp_path / "failed-ddl.sqlite3")
    first_table = Base.metadata.sorted_tables[0]
    statements: list[str] = []

    def record_sql(connection, connection_record) -> None:
        connection.set_trace_callback(statements.append)

    def fail_after_create(target, connection, **kwargs) -> None:
        raise RuntimeError("injected DDL failure")

    event.listen(Engine, "connect", record_sql)
    event.listen(first_table, "after_create", fail_after_create)
    try:
        with pytest.raises(RuntimeError, match="injected DDL failure"):
            Catalog(url)
    finally:
        event.remove(first_table, "after_create", fail_after_create)
        event.remove(Engine, "connect", record_sql)
    if not any("CREATE TABLE" in statement for statement in statements):
        pytest.fail("Expected real DDL before the injected failure")
    if statements[-1] != "ROLLBACK":
        pytest.fail("Expected explicit rollback of the failed schema transaction")

    engine = create_engine(url)
    try:
        if inspect(engine).get_table_names():
            pytest.fail("DDL failure left a partial schema")
    finally:
        engine.dispose()
    catalog = Catalog(url)
    catalog.close()
