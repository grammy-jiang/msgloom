"""Reject owned-name views before any persistent schema initialization."""

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from msgloom.contracts import ExternalEffectState, TerminalStatus
from msgloom.persistence import IncompatibleSchemaError
from tests.phase1_foundation import intake_helpers as h
from tests.phase1_foundation.test_preparation_intake_migration import (
    PROOF_TABLES,
    V3_TABLES,
    V4_TABLES,
)
from tests.phase1_foundation.test_schema_collations import fixture

OWNED_TABLES = V3_TABLES | V4_TABLES | PROOF_TABLES
MISSING_TABLES = {
    "fresh": OWNED_TABLES,
    "2": {"phase1_reconciliations"} | V4_TABLES | PROOF_TABLES,
    "3": V4_TABLES | PROOF_TABLES,
    "old4": PROOF_TABLES,
}


def snapshot(path: Path) -> dict:
    """Capture persistent schema, rows, bytes and filesystem timestamps."""
    with closing(sqlite3.connect(f"file:{path}?mode=ro", uri=True)) as connection:
        schema = connection.execute(
            "SELECT type, name, tbl_name, sql FROM main.sqlite_schema "
            "ORDER BY type, name"
        ).fetchall()
        rows = {
            name: connection.execute(f'SELECT * FROM "{name}"').fetchall()
            for kind, name, _, _ in schema
            if kind in {"table", "view"}
        }
    details = path.stat()
    return {
        "schema": schema,
        "rows": rows,
        "bytes_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "mtime_ns": details.st_mtime_ns,
        "ctime_ns": details.st_ctime_ns,
    }


@pytest.mark.parametrize("case", ["lower", "upper", "mixed"])
@pytest.mark.parametrize(
    "version,table",
    [
        (version, table)
        for version, tables in MISSING_TABLES.items()
        for table in sorted(tables)
    ],
)
def test_owned_view_refuses_before_public_store_writes(
    tmp_path: Path, version: str, table: str, case: str, record_property
) -> None:
    """
    Refuse every owned view collision at fresh and migration entry points.

    Later migration targets must be checked before earlier migration writes.
    Observe the real public constructor, including rejected SQL attempts;
    rollback alone does not satisfy admission without persistent writes.
    """
    path = tmp_path / "neutral.db"
    if version != "fresh":
        fixture(path, version)
    spelling = table.upper() if case == "upper" else table
    if case == "mixed":
        spelling = table.replace("phase1_", "PhAsE1_")
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("CREATE TABLE external_rows (value TEXT NOT NULL)")
        connection.execute("INSERT INTO external_rows VALUES ('retained')")
        connection.execute(
            f'CREATE VIEW "{spelling}" AS SELECT value AS result_id FROM external_rows'
        )
    before = snapshot(path)
    writes = []

    def record(connection, _cursor, statement, _params, _context, _many):
        if connection.engine.url.database == str(path) and (
            statement.lstrip()
            .upper()
            .startswith(
                ("CREATE", "ALTER", "DROP", "INSERT", "UPDATE", "DELETE", "REPLACE")
            )
        ):
            writes.append(statement)

    event.listen(Engine, "before_cursor_execute", record)
    rejected = False
    error = None
    try:
        try:
            opened = h.store(path)
        except IncompatibleSchemaError:
            rejected = True
        except SQLAlchemyError as unexpected:
            error = repr(unexpected)
        else:
            opened.close()
    finally:
        event.remove(Engine, "before_cursor_execute", record)
    after = snapshot(path)
    preserved = {key: before[key] == after[key] for key in before}
    record_property(
        "admission_evidence",
        json.dumps(
            {
                "version": version,
                "view": spelling,
                "rejected": rejected,
                "unexpected_error": error,
                "persistent_sql": writes,
                "before": before,
                "after": after,
                "preserved": preserved,
            }
        ),
    )
    if not rejected or error or writes or not all(preserved.values()):
        pytest.fail(
            f"View {spelling} in {version}: rejected={rejected}, "
            f"error={error}, writes={len(writes)}, preserved={preserved}"
        )


@pytest.mark.parametrize("version", ["fresh", "2", "3", "old4", "4"])
@pytest.mark.parametrize(
    "spelling",
    [
        "external_view",
        "PHASE1_unknown_view",
        "phaſe1_stage_results",
        "phase１_stage_results",
        "phase1_stage_results_extra",
    ],
)
def test_unrelated_view_survives_public_intake_and_reopen(
    tmp_path: Path, version: str, spelling: str
) -> None:
    """Preserve unrelated views and triggers with real supported store APIs."""
    path = tmp_path / "neutral.db"
    if version != "fresh":
        fixture(path, version)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.executescript(
            "CREATE TABLE external_rows (value TEXT NOT NULL);"
            "CREATE TABLE external_audit (value TEXT NOT NULL);"
            'CREATE TRIGGER "phase1_stage_results" '
            "AFTER INSERT ON external_rows BEGIN "
            "INSERT INTO external_audit VALUES (NEW.value); END;"
            "INSERT INTO external_rows VALUES ('before');"
            f'CREATE VIEW "{spelling}" AS SELECT value FROM external_rows;'
        )
    before = snapshot(path)
    value = h.workset(selected=True)
    store = h.store(path)
    try:
        token = h.claim(store, value)
        selection = h.selection(store, token)
        saved = h.result(store, value, token)
        store.finalize_preparation_intake(saved, value, claim=token)
        store.finish_claim(token, TerminalStatus.COMPLETE, ExternalEffectState.NONE)
        if store.get_result(selection.result_id) != selection:
            pytest.fail("The admitted store cannot read its selection write")
    finally:
        store.close()
    reopened = h.store(path)
    try:
        if reopened.get_result(selection.result_id) != selection:
            pytest.fail("The exact selection did not survive reopen")
        if reopened.get_result(saved.result_id) != saved:
            pytest.fail("The immutable intake result did not survive reopen")
        if saved.semantic_data_ref is None:
            pytest.fail("The intake result lacks semantic data")
        if reopened.load_semantic_data(saved.semantic_data_ref) != value:
            pytest.fail("The immutable intake workset changed across reopen")
        if reopened.get_preparation_intake_cursor(value.scope) != value.cutoff:
            pytest.fail("The exact cursor did not survive reopen")
        pending = reopened.list_preparation_intake_worksets(value.scope)
        if len(pending) != 1 or pending[0].workset.result_id != saved.result_id:
            pytest.fail("The pending workset did not survive reopen")
    finally:
        reopened.close()
    after = snapshot(path)
    external = {"external_rows", "external_audit", spelling}
    if [row for row in after["schema"] if row[2] in external] != [
        row for row in before["schema"] if row[2] in external
    ]:
        pytest.fail("Initialization changed an unrelated schema object")
    if any(after["rows"][name] != before["rows"][name] for name in external):
        pytest.fail("Initialization changed unrelated table or view rows")
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("INSERT INTO external_rows VALUES ('after')")
        if connection.execute(f'SELECT * FROM "{spelling}"').fetchall() != [
            ("before",),
            ("after",),
        ]:
            pytest.fail("Initialization changed unrelated view behavior")
        if connection.execute("SELECT * FROM external_audit").fetchall() != [
            ("before",),
            ("after",),
        ]:
            pytest.fail("Initialization changed unrelated trigger behavior")
