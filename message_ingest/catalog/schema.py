"""Serialize additive SQLite schema initialization across catalog instances."""

import sqlite3
from typing import cast

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from message_ingest.catalog.models.base import Base


def initialize_schema(database_url: str, *, in_memory: bool) -> bytes | None:
    """
    Add missing tables under a writer transaction on a disposable connection.

    Driver autocommit leaves SQL transaction control to this function. Acquire
    the writer lock before ``create_all`` inspects any table. A failed lock
    acquisition has no transaction to roll back; DDL failures do. Closing the
    connection and disposing the engine also run when initialization fails.
    Existing rows and source bindings are never changed here.

    Private memory databases disappear when this connection closes. Return
    their committed schema image for the runtime connection to restore. File
    databases need no copy and return ``None``.
    """
    engine = create_engine(
        database_url,
        connect_args={"autocommit": True, "timeout": 5.0},
        poolclass=NullPool,
    )
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            try:
                Base.metadata.create_all(connection)
                connection.exec_driver_sql("COMMIT")
            except BaseException:
                connection.exec_driver_sql("ROLLBACK")
                raise
            if in_memory:
                driver = cast(
                    sqlite3.Connection, connection.connection.driver_connection
                )
                return driver.serialize()
            return None
    finally:
        engine.dispose()
