"""Validate and initialize only the additive Mail binding schema."""

import re

from sqlalchemy import Connection
from sqlalchemy.schema import CreateIndex, CreateTable

from message_ingest.catalog.models.microsoft.outlook._email_bindings import (
    MAIL_BINDING_TABLES,
)


def _normalized(sql: str) -> str:
    return re.sub(r"\s+", " ", sql.strip())


def initialize_mail_bindings(connection: Connection) -> None:
    """
    Validate the entire known set before DDL in the caller's writer lock.

    Exact table, index and guard definitions are this Mail-local version.
    There is no shared schema-version change or legacy backfill. The caller
    rolls back all DDL on failure. Insert guards also reject REPLACE when
    SQLite recursive triggers are disabled; idempotence is checked by stores.
    """
    expected: dict[str, tuple[str, str]] = {}
    for table in MAIL_BINDING_TABLES:
        expected[table.name] = (
            "table",
            str(CreateTable(table).compile(connection)),
        )
        for index in table.indexes:
            expected[str(index.name)] = (
                "index",
                str(CreateIndex(index).compile(connection)),
            )
        keys = [column.name for column in table.primary_key]
        match = " AND ".join(f"{key}=NEW.{key}" for key in keys)
        for operation in ("UPDATE", "DELETE", "INSERT"):
            name = f"{table.name}_immutable_{operation.lower()}"
            condition = (
                f" WHEN EXISTS (SELECT 1 FROM {table.name} WHERE {match})"
                if operation == "INSERT"
                else ""
            )
            expected[name] = (
                "trigger",
                (
                    f"CREATE TRIGGER {name} BEFORE {operation} ON {table.name}"
                    f"{condition} BEGIN SELECT RAISE(ABORT,"
                    " 'immutable Mail binding'); END"
                ),
            )
    names = {table.name for table in MAIL_BINDING_TABLES}
    rows = connection.exec_driver_sql(
        "SELECT type,name,tbl_name,sql FROM sqlite_master"
    ).all()
    present = {
        name: (kind, sql)
        for kind, name, parent, sql in rows
        if (name in expected or parent in names) and sql is not None
    }
    if present:
        if set(present) != set(expected) or any(
            present[name][0] != kind
            or _normalized(present[name][1]) != _normalized(sql)
            for name, (kind, sql) in expected.items()
        ):
            raise ValueError("Unknown or partial Mail binding schema")
        return
    for _, sql in expected.values():
        connection.exec_driver_sql(sql)
