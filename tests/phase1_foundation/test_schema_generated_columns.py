"""Reject generated replacements for ordinary owned persistence columns."""

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

from msgloom.contracts import ExternalEffectState, TerminalStatus
from tests.phase1_foundation import intake_helpers as h
from tests.phase1_foundation.test_preparation_intake_schema_structure import rebuild
from tests.phase1_foundation.test_schema_collations import (
    RESULTS,
    VERSIONS,
    fixture,
    require_rejected_unchanged,
)


def generated_fixture(path: Path, version: str, kind: str, syntax: str) -> None:
    """Retain a sentinel row while replacing one column in a test database."""
    fixture(path, version)
    with sqlite3.connect(path) as connection:
        ddl = connection.execute(
            "SELECT sql FROM sqlite_schema WHERE type='table' AND name=?",
            (RESULTS,),
        ).fetchone()[0]
        indexes = connection.execute(
            "SELECT sql FROM sqlite_schema WHERE type='index' "
            "AND tbl_name=? AND sql IS NOT NULL",
            (RESULTS,),
        ).fetchall()
        columns = [
            row[1]
            for row in connection.execute(f"PRAGMA table_info({RESULTS})")
            if row[1] != "input_refs"
        ]
        names = ", ".join(f'"{name}"' for name in columns)
        rows = connection.execute(f"SELECT {names} FROM {RESULTS}").fetchall()
        changed = ddl.replace(
            "input_refs TEXT NOT NULL",
            f"input_refs TEXT {syntax} ('[]') {kind} NOT NULL",
        )
        if changed == ddl:
            pytest.fail("Generated-column fixture did not change the schema")
        connection.execute(f"DROP TABLE {RESULTS}")
        connection.execute(changed)
        for (index,) in indexes:
            connection.execute(index)
        parameters = ", ".join("?" for _ in columns)
        connection.executemany(
            f"INSERT INTO {RESULTS} ({names}) VALUES ({parameters})", rows
        )


@pytest.mark.parametrize("version", VERSIONS)
@pytest.mark.parametrize("kind,hidden", [("STORED", 3), ("VIRTUAL", 2)])
@pytest.mark.parametrize("syntax", ["GENERATED ALWAYS AS", "AS"])
def test_generated_column_rejects_before_persistent_mutation(
    tmp_path, version, kind, hidden, syntax
):
    """Reject both SQLite generated forms without changing durable state."""
    path = tmp_path / "neutral.db"
    generated_fixture(path, version, kind, syntax)
    with sqlite3.connect(path) as connection:
        native = connection.execute(
            "SELECT hidden FROM pragma_table_xinfo(?) WHERE name='input_refs'",
            (RESULTS,),
        ).fetchone()
    engine = create_engine(f"sqlite:///{path}")
    try:
        column = next(
            item
            for item in inspect(engine).get_columns(RESULTS)
            if item["name"] == "input_refs"
        )
    finally:
        engine.dispose()
    computed = column.get("computed")
    if (
        native != (hidden,)
        or computed is None
        or computed.get("persisted") != (kind == "STORED")
    ):
        pytest.fail("Fixture lacks actual native and reflected generated semantics")
    require_rejected_unchanged(path)


@pytest.mark.parametrize("version", VERSIONS)
@pytest.mark.parametrize("explicit_binary", [False, True])
def test_supported_ordinary_columns_migrate_and_accept_real_writes(
    tmp_path, version, explicit_binary
):
    """Preserve ordinary writes and exact replay after every supported open."""
    path = tmp_path / "neutral.db"
    fixture(path, version)
    if explicit_binary:
        with sqlite3.connect(path) as connection:
            rebuild(
                connection,
                RESULTS,
                lambda sql: sql.replace(
                    "result_id VARCHAR NOT NULL",
                    '"result_id" VARCHAR /* COLLATE NOCASE */ '
                    'COLLATE "BiNaRy" NOT NULL',
                ),
            )
    store = h.store(path)
    try:
        token = h.claim(store)
        saved = h.selection(store, token)
        if saved.semantic_data_ref is None:
            pytest.fail("Ordinary selection write lacks semantic data")
        expected = store.load_semantic_data(saved.semantic_data_ref)
        store.finish_claim(token, TerminalStatus.COMPLETE, ExternalEffectState.NONE)
    finally:
        store.close()
    store = h.store(path)
    try:
        if store.get_result(saved.result_id) != saved:
            pytest.fail("Ordinary result write did not survive exact reopen")
        if saved.semantic_data_ref is None:
            pytest.fail("Ordinary selection write lacks semantic data")
        value = store.load_semantic_data(saved.semantic_data_ref)
        if value != expected:
            pytest.fail("Selection semantic reference changed across reopen")
    finally:
        store.close()
