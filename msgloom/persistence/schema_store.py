"""Explicit neutral persistence schema creation and migrations."""

from __future__ import annotations

from typing import cast

from sqlalchemy import Table, inspect, select, update
from sqlalchemy.engine import Connection, Engine

from msgloom.persistence.errors import IncompatibleSchemaError
from msgloom.persistence.models import Phase1Base, ReconciliationRecord
from msgloom.persistence.records import SCHEMA_METADATA

_SCHEMA_VERSION = "3"
_PREVIOUS_VERSION = "2"


def initialize_schema(engine: Engine) -> None:
    """Create schema v3 or explicitly migrate the exact v2 table set."""
    expected = set(Phase1Base.metadata.tables)
    reconciliation_table = cast(Table, ReconciliationRecord.__table__)
    previous = expected - {reconciliation_table.name}
    with engine.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            existing = {
                name
                for name in inspect(connection).get_table_names()
                if name.startswith("phase1_")
            }
            if not existing:
                Phase1Base.metadata.create_all(connection)
                connection.execute(
                    SCHEMA_METADATA.insert().values(
                        key="schema_version", value=_SCHEMA_VERSION
                    )
                )
            else:
                if existing != previous and existing != expected:
                    raise IncompatibleSchemaError(
                        "neutral table set requires an explicit migration"
                    )
                version = _version(connection)
                if existing == previous and version == _PREVIOUS_VERSION:
                    reconciliation_table.create(connection)
                    connection.execute(
                        update(SCHEMA_METADATA)
                        .where(SCHEMA_METADATA.c.key == "schema_version")
                        .values(value=_SCHEMA_VERSION)
                    )
                elif existing == previous or version != _SCHEMA_VERSION:
                    raise IncompatibleSchemaError(
                        "neutral schema version requires an explicit migration"
                    )
            connection.exec_driver_sql("COMMIT")
        except BaseException:
            connection.exec_driver_sql("ROLLBACK")
            raise


def _version(connection: Connection) -> str | None:
    return connection.execute(
        select(SCHEMA_METADATA.c.value).where(SCHEMA_METADATA.c.key == "schema_version")
    ).scalar_one_or_none()
