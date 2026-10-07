"""Reject malformed owned schemas before migration or version writes."""

import re
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event

from msgloom.contracts import ResultSchemaRegistry
from msgloom.persistence import IncompatibleSchemaError
from msgloom.persistence.schema_store import initialize_schema
from msgloom.persistence.store import Phase1Store
from tests.phase1_foundation.test_preparation_intake_migration import legacy


def database(path: Path, version: str) -> None:
    """Create an exact reviewed schema without partial fixture migrations."""
    if version == "4":
        Phase1Store(f"sqlite:///{path}", ResultSchemaRegistry.phase1()).close()
    else:
        legacy(path, version)


def snapshot(path: Path) -> tuple:
    """Capture SQL definitions, every row, and exact database bytes."""
    with sqlite3.connect(path) as connection:
        definitions = tuple(
            connection.execute(
                "SELECT type, name, sql FROM sqlite_master ORDER BY type, name"
            )
        )
        rows = tuple(
            (name, tuple(connection.execute(f'SELECT * FROM "{name}"')))
            for kind, name, _ in definitions
            if kind == "table"
        )
    return definitions, rows, path.read_bytes()


def rebuild(connection, table, change):
    """Retain rows and indexes while damaging one table contract."""
    sql = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()[0]
    indexes = tuple(
        connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' "
            "AND tbl_name=? AND sql IS NOT NULL",
            (table,),
        )
    )
    changed = change(sql)
    if changed == sql:
        pytest.fail("Schema mutation did not alter the fixture")
    connection.execute(f'ALTER TABLE "{table}" RENAME TO fixture_old')
    for (index_sql,) in indexes:
        index_name = index_sql.split()[2]
        connection.execute(f"DROP INDEX {index_name}")
    connection.execute(changed)
    connection.execute(f'INSERT INTO "{table}" SELECT * FROM fixture_old')
    connection.execute("DROP TABLE fixture_old")
    for (index_sql,) in indexes:
        connection.execute(index_sql)


@pytest.mark.parametrize("version", ["2", "3", "4"])
@pytest.mark.parametrize(
    "damage",
    [
        "missing_input_refs",
        "metadata_column",
        "primary_key",
        "claim_token_unique",
        "required_index",
        "nullable",
        "column_type",
    ],
)
def test_malformed_legacy_or_current_schema_is_rejected_without_mutation(
    tmp_path, version, damage
):
    path = tmp_path / "neutral.db"
    database(path, version)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO phase1_schema_metadata VALUES ('sentinel', 'retained')"
        )
        if damage == "missing_input_refs":
            connection.execute(
                "ALTER TABLE phase1_stage_results DROP COLUMN input_refs"
            )
        elif damage == "metadata_column":
            connection.execute("ALTER TABLE phase1_schema_metadata DROP COLUMN value")
        elif damage == "required_index":
            connection.execute("DROP INDEX ix_phase1_stage_results_execution_id")
        else:
            table = (
                "phase1_work_claims"
                if damage == "claim_token_unique"
                else "phase1_stage_results"
            )

            def change(sql):
                if damage == "primary_key":
                    return re.sub(r",?\s*PRIMARY KEY \(result_id\)", "", sql)
                if damage == "claim_token_unique":
                    return re.sub(r",?\s*UNIQUE \(claim_token\)", "", sql)
                if damage == "nullable":
                    return sql.replace("input_refs TEXT NOT NULL", "input_refs TEXT")
                return sql.replace("input_refs TEXT", "input_refs INTEGER")

            rebuild(connection, table, change)
    before = snapshot(path)
    with pytest.raises(IncompatibleSchemaError):
        Phase1Store(f"sqlite:///{path}", ResultSchemaRegistry.phase1())
    if snapshot(path) != before:
        pytest.fail("Rejected schema changed definitions, rows, or database bytes")


@pytest.mark.parametrize(
    "damage",
    [
        "terminal_attempt",
        "cursor_identity",
        "workset_identity",
        "held_identity",
        "pending_index",
        "partial_index",
        "state_check",
    ],
)
def test_intake_structure_is_checked_on_v4_reopen(tmp_path, damage):
    path = tmp_path / "neutral.db"
    database(path, "4")
    with sqlite3.connect(path) as connection:
        if damage == "terminal_attempt":
            connection.execute(
                "ALTER TABLE phase1_preparation_intake_worksets "
                "DROP COLUMN terminal_attempt_id"
            )
        elif damage in {"pending_index", "partial_index"}:
            connection.execute("DROP INDEX phase1_intake_pending")
            if damage == "partial_index":
                connection.execute(
                    "CREATE INDEX phase1_intake_pending ON "
                    "phase1_preparation_intake_worksets "
                    "(scope_key, state, cutoff_release_entry_seq) "
                    "WHERE state='pending'"
                )
        else:
            table = {
                "cursor_identity": "phase1_preparation_intake_cursors",
                "workset_identity": "phase1_preparation_intake_worksets",
                "held_identity": "phase1_preparation_intake_held_entries",
                "state_check": "phase1_preparation_intake_worksets",
            }[damage]

            def change(sql):
                if damage == "cursor_identity":
                    return sql.replace(
                        "PRIMARY KEY (catalog_identity, source_id, stream, consumer_id)",
                        "PRIMARY KEY (catalog_identity, source_id, stream)",
                    )
                if damage == "state_check":
                    return sql.replace(
                        ", \n\tCHECK (state IN ('pending', 'terminal'))", ""
                    )
                return re.sub(r",?\s*UNIQUE \([^)]*\)", "", sql)

            rebuild(connection, table, change)
    before = snapshot(path)
    with pytest.raises(IncompatibleSchemaError):
        Phase1Store(f"sqlite:///{path}", ResultSchemaRegistry.phase1())
    if snapshot(path) != before:
        pytest.fail("Rejected v4 structure mutated the database")


@pytest.mark.parametrize("version", ["2", "3"])
def test_migration_ddl_failure_rolls_back_schema_rows_and_version(tmp_path, version):
    path = tmp_path / "neutral.db"
    database(path, version)
    before = snapshot(path)
    engine = create_engine(f"sqlite:///{path}", connect_args={"autocommit": True})

    def fail(_connection, _cursor, statement, _params, _context, _many):
        if statement.lstrip().startswith(
            "CREATE TABLE phase1_preparation_intake_worksets"
        ):
            raise RuntimeError("injected DDL failure")

    event.listen(engine, "after_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="injected DDL failure"):
            initialize_schema(engine)
    finally:
        engine.dispose()
    if snapshot(path) != before:
        pytest.fail("Failed explicit migration changed schema, rows, or version")


@pytest.mark.parametrize(
    "mutation",
    [
        "one_table",
        "tables_no_marker",
        "marker_no_tables",
        "unknown_revision",
        "binding_index",
        "proof_column",
        "proof_identity",
        "proof_check",
    ],
)
def test_proof_revision_mismatch_fails_without_mutation(tmp_path, mutation):
    path = tmp_path / "neutral.db"
    database(path, "4")
    with sqlite3.connect(path) as connection:
        if mutation in {"one_table", "marker_no_tables"}:
            connection.execute(
                "DROP TABLE IF EXISTS phase1_preparation_result_bindings"
            )
            if mutation == "marker_no_tables":
                connection.execute(
                    "DROP TABLE IF EXISTS phase1_preparation_plan_proofs"
                )
            connection.execute(
                "INSERT OR REPLACE INTO phase1_schema_metadata "
                "VALUES ('preparation_proof_revision', '1')"
            )
        elif mutation == "tables_no_marker":
            connection.execute(
                "DELETE FROM phase1_schema_metadata "
                "WHERE key='preparation_proof_revision'"
            )
        elif mutation == "unknown_revision":
            connection.execute(
                "INSERT OR REPLACE INTO phase1_schema_metadata "
                "VALUES ('preparation_proof_revision', '999')"
            )
        elif mutation == "binding_index":
            connection.execute("DROP INDEX phase1_preparation_bindings_by_token")
        elif mutation == "proof_column":
            connection.execute(
                "ALTER TABLE phase1_preparation_plan_proofs DROP COLUMN code_version"
            )
        else:

            def change(sql):
                if mutation == "proof_identity":
                    return re.sub(r",?\s*PRIMARY KEY \(claim_token\)", "", sql)
                return sql.replace(
                    "accepted_status IN ('complete', 'incomplete')",
                    "accepted_status IN ('complete', 'incomplete', 'failed')",
                )

            rebuild(connection, "phase1_preparation_plan_proofs", change)
    before = snapshot(path)
    modified = path.stat().st_mtime_ns
    with pytest.raises(IncompatibleSchemaError):
        Phase1Store(f"sqlite:///{path}", ResultSchemaRegistry.phase1())
    if snapshot(path) != before or path.stat().st_mtime_ns != modified:
        pytest.fail("Rejected proof revision changed bytes, mtime, or schema")


@pytest.mark.parametrize("version", ["2", "3", "old4"])
def test_proof_ddl_failure_rolls_back_entire_migration(tmp_path, version):
    from tests.phase1_foundation.test_preparation_intake_migration import old_v4

    path = tmp_path / "neutral.db"
    if version == "old4":
        old_v4(path)
    else:
        database(path, version)
    before = snapshot(path)
    engine = create_engine(f"sqlite:///{path}", connect_args={"autocommit": True})

    def fail(_connection, _cursor, statement, _params, _context, _many):
        if statement.lstrip().startswith(
            "CREATE TABLE phase1_preparation_result_bindings"
        ):
            raise RuntimeError("injected proof DDL failure")

    event.listen(engine, "after_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="injected proof DDL failure"):
            initialize_schema(engine)
    finally:
        engine.dispose()
    if snapshot(path) != before:
        pytest.fail("Proof extension failure partially migrated the database")
