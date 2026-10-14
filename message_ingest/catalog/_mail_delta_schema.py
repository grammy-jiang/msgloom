"""Initialize and validate only additive causal Mail cursor tables.

Known-but-partial proof schemas are never modified. The durable absence epoch
is a separate additive table and is not inferred from a response timestamp.
"""

import re
from typing import cast

from sqlalchemy import Connection, Table
from sqlalchemy.schema import CreateIndex, CreateTable

from message_ingest.catalog.models.microsoft.outlook.email import (
    MailDeltaAbsenceGeneration,
    MailDeltaCandidateBase,
    MailFolderDeltaCandidateBase,
)


def _normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def initialize_mail_delta_baselines(connection: Connection) -> None:
    """Validate all present causal schemas before adding any missing table."""
    definitions: dict[str, dict[str, tuple[str, str]]] = {}
    for model in (
        MailDeltaCandidateBase,
        MailDeltaAbsenceGeneration,
        MailFolderDeltaCandidateBase,
    ):
        table = cast(Table, model.__table__)
        expected = {table.name: ("table", str(CreateTable(table).compile(connection)))}
        for index in table.indexes:
            if index.name is None:
                raise ValueError("Mail causal schema requires named indexes")
            expected[str(index.name)] = (
                "index",
                str(CreateIndex(index).compile(connection)),
            )
        if model in (MailDeltaCandidateBase, MailFolderDeltaCandidateBase):
            # Proof can be deleted for an expired folder, but not rewritten.
            for operation in ("UPDATE", "INSERT"):
                name = f"{table.name}_immutable_{operation.lower()}"
                keys = (
                    "source_id=NEW.source_id AND run_id=NEW.run_id "
                    "AND folder_id=NEW.folder_id"
                    if model is MailDeltaCandidateBase
                    else "source_id=NEW.source_id AND run_id=NEW.run_id"
                )
                condition = (
                    f" WHEN EXISTS (SELECT 1 FROM {table.name} WHERE {keys})"
                    if operation == "INSERT"
                    else ""
                )
                expected[name] = (
                    "trigger",
                    f"CREATE TRIGGER {name} BEFORE {operation} ON {table.name}"
                    + condition
                    + " BEGIN SELECT RAISE(ABORT, 'immutable Mail delta causal proof'); END",
                )
        definitions[table.name] = expected

    rows = connection.exec_driver_sql(
        "SELECT type,name,tbl_name,sql FROM sqlite_master"
    ).all()
    create: list[str] = []
    for name, expected in definitions.items():
        present = {
            row_name: (kind, sql)
            for kind, row_name, parent, sql in rows
            if (row_name in expected or parent == name) and sql is not None
        }
        if not present:
            create.extend(ddl for _, ddl in expected.values())
            continue
        if set(present) != set(expected) or any(
            present[key][0] != kind or _normalized(present[key][1]) != _normalized(ddl)
            for key, (kind, ddl) in expected.items()
        ):
            raise ValueError("Unknown or partial Mail delta causal schema")
    for ddl in create:
        connection.exec_driver_sql(ddl)


__all__ = ["initialize_mail_delta_baselines"]
