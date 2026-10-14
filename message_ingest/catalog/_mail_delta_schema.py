"""Add and validate only the causal Mail candidate proof table.

Existing catalog tables keep their historical DDL. An unrecognized table with
this name must fail initialization before any new writes are performed.
"""

import re
from typing import cast

from sqlalchemy import Connection, Table
from sqlalchemy.schema import CreateIndex, CreateTable

from message_ingest.catalog.models.microsoft.outlook.email import MailDeltaCandidateBase


def _normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def initialize_mail_delta_baselines(connection: Connection) -> None:
    table = cast(Table, MailDeltaCandidateBase.__table__)
    expected = {table.name: ("table", str(CreateTable(table).compile(connection)))}
    for index in table.indexes:
        if index.name is None:
            raise ValueError("Mail causal schema requires named indexes")
        expected[str(index.name)] = (
            "index",
            str(CreateIndex(index).compile(connection)),
        )
    # Proof may be deleted with an expired folder, but never rewritten for an
    # existing run/source/folder. Guard direct SQL as well as store invariants.
    table_name = table.name
    for operation in ("UPDATE", "INSERT"):
        name = f"{table_name}_immutable_{operation.lower()}"
        condition = (
            " WHEN EXISTS (SELECT 1 FROM "
            + table_name
            + " WHERE source_id=NEW.source_id AND run_id=NEW.run_id "
            + "AND folder_id=NEW.folder_id)"
            if operation == "INSERT"
            else ""
        )
        expected[name] = (
            "trigger",
            f"CREATE TRIGGER {name} BEFORE {operation} ON {table_name}"
            + condition
            + " BEGIN SELECT RAISE(ABORT, 'immutable Mail delta causal proof'); END",
        )
    rows = connection.exec_driver_sql(
        "SELECT type,name,tbl_name,sql FROM sqlite_master"
    ).all()
    present = {
        name: (kind, sql)
        for kind, name, parent, sql in rows
        if (name in expected or parent == table.name) and sql is not None
    }
    if present:
        if set(present) != set(expected) or any(
            present[key][0] != kind or _normalized(present[key][1]) != _normalized(ddl)
            for key, (kind, ddl) in expected.items()
        ):
            raise ValueError("Unknown or partial Mail delta causal schema")
        return
    for _, ddl in expected.values():
        connection.exec_driver_sql(ddl)


__all__ = ["initialize_mail_delta_baselines"]
