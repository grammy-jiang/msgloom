"""Reject undeclared owned triggers before schema or metadata writes."""

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event

from msgloom.contracts import ExternalEffectState, TerminalStatus
from msgloom.persistence import IncompatibleSchemaError
from msgloom.persistence.models import Phase1Base
from msgloom.persistence.schema_store import initialize_schema
from tests.phase1_foundation import intake_helpers as h
from tests.phase1_foundation.test_preparation_intake_schema_structure import snapshot
from tests.phase1_foundation.test_schema_collations import VERSIONS, fixture


def require_rejected_unchanged(path: Path) -> None:
    """Require refusal without DDL, row, byte or file timestamp changes."""
    before = snapshot(path), path.stat().st_mtime_ns, path.stat().st_ctime_ns
    engine = create_engine(f"sqlite:///{path}", connect_args={"autocommit": True})
    writes = []

    def record(_connection, _cursor, statement, _params, _context, _many):
        if (
            statement.lstrip()
            .upper()
            .startswith(
                ("CREATE", "ALTER", "DROP", "INSERT", "UPDATE", "DELETE", "REPLACE")
            )
        ):
            writes.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    rejected = False
    try:
        try:
            initialize_schema(engine)
        except IncompatibleSchemaError:
            rejected = True
    finally:
        engine.dispose()
    after = snapshot(path), path.stat().st_mtime_ns, path.stat().st_ctime_ns
    if not rejected or writes or after != before:
        pytest.fail(
            f"Owned trigger: rejected={rejected}, writes={len(writes)}, "
            f"schema_rows_bytes_unchanged={after[0] == before[0]}, "
            f"mtime_unchanged={after[1] == before[1]}, "
            f"ctime_unchanged={after[2] == before[2]}"
        )


@pytest.mark.parametrize("version", VERSIONS)
@pytest.mark.parametrize("behavior", ["suppress_result", "mutate_metadata"])
def test_owned_trigger_rejects_before_any_persistent_mutation(
    tmp_path, version, behavior
):
    """Refuse silent result suppression and migration metadata mutations."""
    path = tmp_path / "neutral.db"
    fixture(path, version)
    with sqlite3.connect(path) as connection:
        if behavior == "suppress_result":
            connection.execute(
                'CREATE TRIGGER "unrelated hook; arbitrary name" '
                'BEFORE INSERT ON "PHASE1_STAGE_RESULTS" '
                "BEGIN SELECT RAISE(IGNORE); END"
            )
        else:
            connection.execute(
                "CREATE TRIGGER extension_change_sentinel "
                "AFTER UPDATE ON phase1_schema_metadata "
                "WHEN NEW.key='schema_version' BEGIN "
                "UPDATE phase1_schema_metadata SET value='changed-by-trigger' "
                "WHERE key='sentinel'; END"
            )
        triggers = connection.execute(
            "SELECT tbl_name FROM main.sqlite_schema WHERE type='trigger'"
        ).fetchall()
        expected = (
            "PHASE1_STAGE_RESULTS"
            if behavior == "suppress_result"
            else "phase1_schema_metadata"
        )
        if triggers != [(expected,)]:
            pytest.fail("Fixture does not attach its trigger to the owned table")
    require_rejected_unchanged(path)


@pytest.mark.parametrize("table", sorted(Phase1Base.metadata.tables))
def test_every_owned_table_refuses_even_an_inert_trigger(tmp_path, table):
    """No owned table declares a persistent trigger of any name or timing."""
    path = tmp_path / "neutral.db"
    fixture(path, "4")
    with sqlite3.connect(path) as connection:
        connection.execute(
            f'CREATE TRIGGER "external-looking hook" AFTER DELETE ON "{table}" '
            "WHEN 0 BEGIN SELECT 1; END"
        )
    require_rejected_unchanged(path)


@pytest.mark.parametrize("version", (*VERSIONS, "fresh"))
@pytest.mark.parametrize("external_trigger", [False, True])
def test_supported_schemas_preserve_external_ownership_and_real_intake(
    tmp_path, version, external_trigger
):
    """Keep valid migrations, real writes and exact intake state on reopen."""
    path = tmp_path / "neutral.db"
    if version != "fresh":
        fixture(path, version)
    external_before = None
    if external_trigger:
        with sqlite3.connect(path) as connection:
            connection.executescript(
                "CREATE TABLE extension_data (value TEXT NOT NULL);"
                "CREATE TABLE extension_audit (value TEXT NOT NULL);"
                "CREATE TRIGGER phase1_arbitrary_external_hook "
                "AFTER INSERT ON extension_data BEGIN "
                "INSERT INTO extension_audit VALUES (NEW.value); END;"
                "INSERT INTO extension_data VALUES ('before');"
            )
            external_before = connection.execute(
                "SELECT type, name, tbl_name, sql FROM main.sqlite_schema "
                "WHERE tbl_name IN ('extension_data', 'extension_audit') "
                "ORDER BY type, name"
            ).fetchall()
    store = h.store(path)
    value = h.workset(selected=True)
    try:
        token = h.claim(store, value)
        selection = h.selection(store, token)
        saved = h.result(store, value, token)
        store.finalize_preparation_intake(saved, value, claim=token)
        store.finish_claim(token, TerminalStatus.COMPLETE, ExternalEffectState.NONE)
        if store.get_result(saved.result_id) != saved:
            pytest.fail("Successful intake did not persist its exact StageResult")
    finally:
        store.close()
    store = h.store(path)
    try:
        if store.get_result(selection.result_id) != selection:
            pytest.fail("The real input selection did not survive reopen")
        if store.get_result(saved.result_id) != saved:
            pytest.fail("The admitted StageResult did not survive reopen")
        if saved.semantic_data_ref is None:
            pytest.fail("Intake result lacks semantic data")
        if store.load_semantic_data(saved.semantic_data_ref) != value:
            pytest.fail("The immutable workset changed across reopen")
        if store.get_preparation_intake_cursor(value.scope) != value.cutoff:
            pytest.fail("The exact cursor did not survive reopen")
        pending = store.list_preparation_intake_worksets(value.scope)
        if len(pending) != 1 or pending[0].workset.result_id != saved.result_id:
            pytest.fail("The admitted pending workset did not survive reopen")
    finally:
        store.close()
    with sqlite3.connect(path) as connection:
        if version != "fresh":
            sentinel = connection.execute(
                "SELECT value FROM phase1_schema_metadata WHERE key='sentinel'"
            ).fetchone()
            if sentinel != ("retained",):
                pytest.fail("A supported migration changed existing metadata")
        if not external_trigger:
            return
        external_after = connection.execute(
            "SELECT type, name, tbl_name, sql FROM main.sqlite_schema "
            "WHERE tbl_name IN ('extension_data', 'extension_audit') "
            "ORDER BY type, name"
        ).fetchall()
        if external_after != external_before:
            pytest.fail("Neutral initialization changed an external schema object")
        connection.execute("INSERT INTO extension_data VALUES ('after')")
        audit = connection.execute(
            "SELECT value FROM extension_audit ORDER BY rowid"
        ).fetchall()
        if audit != [("before",), ("after",)]:
            pytest.fail("Neutral initialization changed external trigger behavior")
