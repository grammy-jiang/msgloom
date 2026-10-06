"""Admit owned table identifiers with SQLite's ASCII case semantics."""

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine

from msgloom.contracts import ExternalEffectState, TerminalStatus
from msgloom.persistence import IncompatibleSchemaError
from tests.phase1_foundation import intake_helpers as h
from tests.phase1_foundation.test_preparation_intake_schema_structure import snapshot


@pytest.mark.parametrize(
    "spelling",
    [
        "phase1_stage_results",
        "PHASE1_STAGE_RESULTS",
        "Phase1_Stage_Results",
        "PHASE1_SCHEMA_METADATA",
        "Phase1_Unknown_Table",
        "phase1_unknown_table",
    ],
)
def test_partial_owned_schema_refuses_before_public_store_writes(
    tmp_path: Path, spelling: str
) -> None:
    """Reject partial owned schemas before successful public admission."""
    path = tmp_path / "neutral.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            f'CREATE TABLE "{spelling}" (result_id VARCHAR NOT NULL PRIMARY KEY)'
        )
        connection.execute(f'INSERT INTO "{spelling}" VALUES (?)', ("retained",))
    before = snapshot(path), path.stat().st_mtime_ns, path.stat().st_ctime_ns
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
    try:
        try:
            opened = h.store(path)
        except IncompatibleSchemaError:
            rejected = True
        else:
            opened.close()
    finally:
        event.remove(Engine, "before_cursor_execute", record)
    after = snapshot(path), path.stat().st_mtime_ns, path.stat().st_ctime_ns
    if not rejected or writes or after != before:
        pytest.fail(
            f"Partial {spelling}: rejected={rejected}, writes={len(writes)}, "
            f"schema_rows_bytes_unchanged={after[0] == before[0]}, "
            f"mtime_unchanged={after[1] == before[1]}, "
            f"ctime_unchanged={after[2] == before[2]}"
        )


@pytest.mark.parametrize(
    "spelling",
    [
        "phaſe1_stage_results",
        "PHaſE1_stage_results",
        "phase１_stage_results",
        "phase1x_stage_results",
    ],
)
def test_unrelated_identifier_survives_real_public_intake_and_reopen(
    tmp_path: Path, spelling: str
) -> None:
    """
    Preserve Unicode lookalikes and unrelated prefixes as external tables.

    Unicode casefold or normalization would misclassify these identities.
    Real selection writes, intake finalization and reopen must remain usable;
    an external trigger's owned-looking name grants no table ownership.
    """
    path = tmp_path / "neutral.db"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            f'CREATE TABLE "{spelling}" (value TEXT NOT NULL);'
            "CREATE TABLE external_audit (value TEXT NOT NULL);"
            'CREATE TRIGGER "PHASE1_external_hook" '
            f'AFTER INSERT ON "{spelling}" BEGIN '
            "INSERT INTO external_audit VALUES (NEW.value); END;"
            f"INSERT INTO \"{spelling}\" VALUES ('before');"
        )
        external_before = connection.execute(
            "SELECT type, name, tbl_name, sql FROM main.sqlite_schema "
            "WHERE tbl_name IN (?, 'external_audit') ORDER BY type, name",
            (spelling,),
        ).fetchall()
    value = h.workset(selected=True)
    store = h.store(path)
    try:
        token = h.claim(store, value)
        selection = h.selection(store, token)
        saved = h.result(store, value, token)
        store.finalize_preparation_intake(saved, value, claim=token)
        store.finish_claim(token, TerminalStatus.COMPLETE, ExternalEffectState.NONE)
        if store.get_result(selection.result_id) != selection:
            pytest.fail("The admitted store cannot read its real selection write")
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
    with sqlite3.connect(path) as connection:
        external_after = connection.execute(
            "SELECT type, name, tbl_name, sql FROM main.sqlite_schema "
            "WHERE tbl_name IN (?, 'external_audit') ORDER BY type, name",
            (spelling,),
        ).fetchall()
        if external_after != external_before:
            pytest.fail("Initialization changed an unrelated schema object")
        rows = connection.execute(f'SELECT * FROM "{spelling}"').fetchall()
        if rows != [("before",)]:
            pytest.fail("Initialization changed unrelated table rows")
        connection.execute(f'INSERT INTO "{spelling}" VALUES (?)', ("after",))
        audit = connection.execute(
            "SELECT value FROM external_audit ORDER BY rowid"
        ).fetchall()
        if audit != [("before",), ("after",)]:
            pytest.fail("Initialization changed unrelated trigger behavior")
