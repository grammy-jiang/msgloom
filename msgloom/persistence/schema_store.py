"""Explicit neutral persistence schema creation and ordered migrations."""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing

from sqlalchemy import CheckConstraint, UniqueConstraint, inspect, select, update
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.schema import CreateIndex, CreateTable, Table

from msgloom.persistence.errors import IncompatibleSchemaError
from msgloom.persistence.models import Phase1Base
from msgloom.persistence.records import (
    INTAKE_CURSORS,
    INTAKE_HELD_ENTRIES,
    INTAKE_WORKSETS,
    PREPARATION_PLAN_PROOFS,
    PREPARATION_RESULT_BINDINGS,
    RECONCILIATIONS,
    SCHEMA_METADATA,
)

_SCHEMA_VERSION = "4"
_SQLITE_ASCII_LOWER = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"
)
_INTAKE_TABLES = (INTAKE_CURSORS, INTAKE_WORKSETS, INTAKE_HELD_ENTRIES)
_PROOF_TABLES = (PREPARATION_PLAN_PROOFS, PREPARATION_RESULT_BINDINGS)
_V3 = {
    "phase1_schema_metadata",
    "phase1_stage_results",
    "phase1_semantic_data",
    "phase1_operation_outcomes",
    "phase1_work_claims",
    "phase1_claim_attempts",
    "phase1_reconciliations",
}
_CANDIDATE_V4 = _V3 | {
    "phase1_preparation_intake_cursors",
    "phase1_preparation_intake_worksets",
    "phase1_preparation_intake_held_entries",
}
_LEGACY_DIGEST = "3cf62de248147e6897146c95b8fd03c8de9e6633845698b9d9332aaff26fd181"
LEGACY_TERMINAL_PREFIX = "preparation_proof_legacy_terminal:"


def initialize_schema(engine: Engine) -> None:
    """
    Atomically migrate exact v2/v3/candidate-v4 to proof revision 1.

    The pinned candidate contract prevents future metadata additions from
    redefining legacy schemas by subtraction. No historical proof is guessed.
    Legacy terminal ids get explicit recovery holds in owned metadata; their
    immutable workset rows remain unchanged.
    """
    expected = _CANDIDATE_V4 | {table.name for table in _PROOF_TABLES}
    v2 = _V3 - {RECONCILIATIONS.name}
    with engine.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            _require_pinned_legacy_contract(connection)
            _require_no_owned_triggers(connection)
            inspector = inspect(connection)
            # Tables and views share SQLite's identifier namespace. Refuse
            # owned-name views before fresh creation or any migration writes.
            if any(
                name.translate(_SQLITE_ASCII_LOWER) in expected
                for name in inspector.get_view_names()
            ):
                raise IncompatibleSchemaError("view occupies a neutral table name")
            # SQLite folds ASCII identifier case only. Retain actual names
            # so noncanonical owned schemas fail the exact table-set gate;
            # they must never enter the fresh-database creation branch.
            existing = {
                name
                for name in inspector.get_table_names()
                if name.translate(_SQLITE_ASCII_LOWER).startswith("phase1_")
            }
            if not existing:
                _require_available_names(connection, expected)
                Phase1Base.metadata.create_all(connection)
                connection.execute(
                    SCHEMA_METADATA.insert(),
                    [
                        {"key": "schema_version", "value": _SCHEMA_VERSION},
                        {"key": "preparation_proof_revision", "value": "1"},
                    ],
                )
            else:
                if existing not in (v2, _V3, _CANDIDATE_V4, expected):
                    raise IncompatibleSchemaError("unreviewed neutral table set")
                _require_structure(connection, existing)
                metadata = dict(
                    connection.execute(
                        select(SCHEMA_METADATA.c.key, SCHEMA_METADATA.c.value)
                    )
                    .tuples()
                    .all()
                )
                version = metadata.get("schema_version")
                revision = metadata.get("preparation_proof_revision")
                if (existing, version) not in (
                    (v2, "2"),
                    (_V3, "3"),
                    (_CANDIDATE_V4, "4"),
                    (expected, "4"),
                ) or (
                    revision != "1" if existing == expected else revision is not None
                ):
                    raise IncompatibleSchemaError("unreviewed neutral proof revision")
                if existing != expected:
                    if any(key.startswith(LEGACY_TERMINAL_PREFIX) for key in metadata):
                        raise IncompatibleSchemaError(
                            "legacy proof markers without revision"
                        )
                    _require_available_names(connection, expected - existing)
                    if version == "2":
                        RECONCILIATIONS.create(connection)
                        _set_version(connection, "3")
                        version = "3"
                    if version == "3":
                        for table in _INTAKE_TABLES:
                            table.create(connection)
                        _set_version(connection, "4")
                    for table in _PROOF_TABLES:
                        table.create(connection)
                    # An indexed metadata row per legacy disposition is an
                    # explicit hold, never inferred producer attribution.
                    connection.execute(
                        SCHEMA_METADATA.insert().from_select(
                            ["key", "value"],
                            select(
                                LEGACY_TERMINAL_PREFIX + INTAKE_WORKSETS.c.result_id,
                                INTAKE_WORKSETS.c.scope_key,
                            ).where(INTAKE_WORKSETS.c.state == "terminal"),
                        )
                    )
                    connection.execute(
                        SCHEMA_METADATA.insert().values(
                            key="preparation_proof_revision",
                            value="1",
                        )
                    )
            connection.exec_driver_sql("COMMIT")
        except BaseException:
            connection.exec_driver_sql("ROLLBACK")
            raise


def _require_available_names(connection: Connection, tables: set[str]) -> None:
    """
    Reject occupied names needed by the selected creation or migration.

    Tables, views and indexes share one main namespace; triggers do not.
    Check all target tables and explicit indexes before persistent DDL or
    metadata statements. A later rollback does not satisfy this boundary.
    """
    names = tables | {
        str(index.name)
        for name in tables
        for index in Phase1Base.metadata.tables[name].indexes
    }
    names = {name.translate(_SQLITE_ASCII_LOWER) for name in names}
    occupied = connection.exec_driver_sql(
        "SELECT name FROM main.sqlite_schema WHERE type IN ('table', 'view', 'index')"
    ).scalars()
    if any(name.translate(_SQLITE_ASCII_LOWER) in names for name in occupied):
        raise IncompatibleSchemaError("occupied neutral creation namespace")


def _require_pinned_legacy_contract(connection: Connection) -> None:
    """Keep the 8dfad67 legacy definition independent of future additions."""
    statements = []
    for name in sorted(_CANDIDATE_V4):
        table = Phase1Base.metadata.tables[name]
        statements.append(str(CreateTable(table).compile(dialect=connection.dialect)))
        statements.extend(
            str(CreateIndex(index).compile(dialect=connection.dialect))
            for index in sorted(table.indexes, key=lambda item: str(item.name))
        )
    canonical = "\n".join(" ".join(sql.split()) for sql in statements)
    if hashlib.sha256(canonical.encode()).hexdigest() != _LEGACY_DIGEST:
        raise IncompatibleSchemaError(
            "candidate-v4 definition requires explicit review"
        )


def _require_no_owned_triggers(connection: Connection) -> None:
    """
    Refuse persistent triggers attached to any owned neutral table.

    The owner declares none. Match SQLite table identifiers independently of
    trigger names, using native ASCII case folding for identifier spelling.
    This does not change BINARY comparisons of stored identity values.
    """
    names = tuple(Phase1Base.metadata.tables)
    parameters = ", ".join("?" for _ in names)
    trigger = connection.exec_driver_sql(
        "SELECT name FROM main.sqlite_schema WHERE type = 'trigger' "
        f"AND tbl_name COLLATE NOCASE IN ({parameters}) LIMIT 1",
        names,
    ).first()
    if trigger is not None:
        raise IncompatibleSchemaError("undeclared trigger on a neutral table")


def _set_version(connection: Connection, version: str) -> None:
    connection.execute(
        update(SCHEMA_METADATA)
        .where(SCHEMA_METADATA.c.key == "schema_version")
        .values(value=version)
    )


def _require_structure(connection: Connection, names: set[str]) -> None:
    """
    Validate the owned SQL contract before reading versions or changing DDL.

    Versions 2 and 3 use unchanged definitions for their existing tables.
    Compare those definitions against the single owner metadata, including
    identity constraints and query indexes. Never repair malformed structures
    implicitly or infer compatibility merely from table names. Columns must
    remain ordinary writable columns, never computed replacements.
    """
    inspector = inspect(connection)
    for name in sorted(names):
        table = Phase1Base.metadata.tables[name]
        actual_columns = {
            column["name"]: (
                str(column["type"].compile(dialect=connection.dialect)),
                column["nullable"],
                column["default"],
                column.get("computed"),
            )
            for column in inspector.get_columns(name)
        }
        expected_columns = {
            column.name: (
                str(column.type.compile(dialect=connection.dialect)),
                column.nullable,
                None,
                None,
            )
            for column in table.columns
        }
        primary = inspector.get_pk_constraint(name)["constrained_columns"]
        unique = {
            tuple(item["column_names"])
            for item in inspector.get_unique_constraints(name)
        }
        expected_unique = {
            tuple(column.name for column in constraint.columns)
            for constraint in table.constraints
            if isinstance(constraint, UniqueConstraint)
        }
        indexes = inspector.get_indexes(name)
        actual_indexes = {
            (item["name"], tuple(item["column_names"]), bool(item["unique"]))
            for item in indexes
        }
        expected_indexes = {
            (index.name, tuple(column.name for column in index.columns), index.unique)
            for index in table.indexes
        }
        checks = {
            " ".join(item["sqltext"].split())
            for item in inspector.get_check_constraints(name)
        }
        expected_checks = {
            " ".join(str(constraint.sqltext).split())
            for constraint in table.constraints
            if isinstance(constraint, CheckConstraint)
        }
        if (
            actual_columns != expected_columns
            or primary != [column.name for column in table.primary_key.columns]
            or unique != expected_unique
            or actual_indexes != expected_indexes
            or any(item.get("dialect_options") for item in indexes)
            or checks != expected_checks
            or inspector.get_foreign_keys(name)
        ):
            raise IncompatibleSchemaError(
                f"neutral table {name} does not match its reviewed structure"
            )
        _require_binary_comparisons(connection, table)


def _require_binary_comparisons(connection: Connection, table: Table) -> None:
    """
    Require native BINARY column defaults and ascending BINARY index keys.

    SQLite reflection omits column collations. Parse the saved table DDL in
    an empty, disposable memory database and inspect an index that inherits
    every column default. This uses SQLite's parser, not DDL text matching
    or unstable EXPLAIN opcodes. Explicit PK/index COLLATE clauses cannot
    conceal a different column default. No rows are copied and no probe DDL
    or writes touch the persistent database.

    Inspect every persisted PK, unique and query index separately because
    each key can override its column's collation and sort direction.
    """
    index_names = connection.exec_driver_sql(
        "SELECT name FROM pragma_index_list(?, 'main')", (table.name,)
    ).scalars()
    for name in index_names:
        keys = connection.exec_driver_sql(
            'SELECT name, "desc", coll FROM pragma_index_xinfo(?, ?) '
            'WHERE "key" = 1 ORDER BY seqno',
            (name, "main"),
        ).all()
        if not keys or any(
            column not in table.columns
            or descending != 0
            or collation.upper() != "BINARY"
            for column, descending, collation in keys
        ):
            raise IncompatibleSchemaError(
                f"neutral index {name} does not use reviewed BINARY keys"
            )
    ddl = connection.exec_driver_sql(
        "SELECT sql FROM main.sqlite_schema WHERE type = 'table' AND name = ?",
        (table.name,),
    ).scalar_one()
    quote = connection.dialect.identifier_preparer.quote_identifier
    columns = ", ".join(quote(column.name) for column in table.columns)
    try:
        with closing(sqlite3.connect(":memory:")) as probe:
            probe.execute(ddl)
            probe.execute(
                "CREATE INDEX phase1_column_collations ON "
                f"{quote(table.name)} ({columns})"
            )
            defaults = probe.execute(
                "SELECT name, coll FROM pragma_index_xinfo(?) "
                'WHERE "key" = 1 ORDER BY seqno',
                ("phase1_column_collations",),
            ).fetchall()
    except sqlite3.Error as error:
        raise IncompatibleSchemaError(
            f"neutral table {table.name} collations could not be validated"
        ) from error
    if [(name, collation.upper()) for name, collation in defaults] != [
        (column.name, "BINARY") for column in table.columns
    ]:
        raise IncompatibleSchemaError(
            f"neutral table {table.name} does not use reviewed BINARY columns"
        )
