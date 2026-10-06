"""Preflight shared SQLite names before persistent initialization writes."""

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
from tests.phase1_foundation.test_schema_collations import fixture
from tests.phase1_foundation.test_schema_view_admission import snapshot

REPORTED_COLLISIONS = (
    ("fresh", "phase1_stage_results"),
    ("fresh", "PHASE1_STAGE_RESULTS"),
    ("fresh", "PhAsE1_STAGE_RESULTS"),
    ("2", "phase1_preparation_result_bindings"),
    ("3", "PHASE1_PREPARATION_RESULT_BINDINGS"),
    ("old4", "PhAsE1_preparation_result_bindings"),
    ("fresh", "phase1_intake_pending"),
    ("3", "phase1_intake_pending"),
)
INDEX_TARGETS = {
    "fresh": (
        "ix_phase1_stage_results_execution_id",
        "ix_phase1_stage_results_kind",
        "ix_phase1_claim_attempts_claim_key",
        "ix_phase1_reconciliations_claim_key",
        "ix_phase1_reconciliations_claim_token",
        "phase1_intake_pending",
        "phase1_intake_held",
        "phase1_preparation_bindings_by_token",
    ),
    "2": (
        "ix_phase1_reconciliations_claim_key",
        "phase1_preparation_bindings_by_token",
    ),
    "3": ("phase1_intake_pending", "phase1_preparation_bindings_by_token"),
    "old4": ("phase1_preparation_bindings_by_token",),
}


def spellings(name: str) -> tuple[str, str, str]:
    """Vary only ASCII identifier case, including a mixed spelling."""
    return name, name.upper(), name.replace("phase1", "PhAsE1")


def occupant(path: Path, version: str, kind: str, name: str) -> None:
    """Place an external object in a name needed by initialization."""
    if version != "fresh":
        fixture(path, version)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("CREATE TABLE external_rows (value TEXT NOT NULL)")
        connection.execute("INSERT INTO external_rows VALUES ('retained')")
        if kind == "index":
            connection.execute(f'CREATE INDEX "{name}" ON external_rows (value)')
        elif kind == "view":
            connection.execute(
                f'CREATE VIEW "{name}" AS SELECT value FROM external_rows'
            )
        else:
            connection.execute(f'CREATE TABLE "{name}" (value TEXT NOT NULL)')
            connection.execute(f'INSERT INTO "{name}" VALUES (?)', ("retained",))


def require_refused(path: Path, record_property) -> None:
    """Observe public admission, SQL attempts and file preservation."""
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
        "namespace_admission_evidence",
        json.dumps(
            {
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
            f"rejected={rejected}, error={error}, writes={len(writes)}, "
            f"preserved={preserved}"
        )


@pytest.mark.parametrize(
    "version,name",
    sorted(
        set(REPORTED_COLLISIONS)
        | {
            (version, spelling)
            for version, name in REPORTED_COLLISIONS
            for spelling in spellings(name.lower())
        }
    ),
)
def test_reported_index_collisions_refuse_before_writes(
    tmp_path: Path, version: str, name: str, record_property
) -> None:
    """Retain all eight independent reproductions and ASCII case variants."""
    path = tmp_path / "neutral.db"
    occupant(path, version, "index", name)
    require_refused(path, record_property)


@pytest.mark.parametrize("kind", ["table", "view", "index"])
@pytest.mark.parametrize(
    "version,name",
    [
        (version, spelling)
        for version, names in INDEX_TARGETS.items()
        for name in names
        for spelling in spellings(name)
    ],
)
def test_explicit_index_namespace_refuses_before_any_migration_write(
    tmp_path: Path, version: str, name: str, kind: str, record_property
) -> None:
    """Cover every fresh index and early/late selected migration conflicts."""
    path = tmp_path / "neutral.db"
    occupant(path, version, kind, name)
    require_refused(path, record_property)


@pytest.mark.parametrize("version", ["fresh", "2", "3", "old4", "4"])
@pytest.mark.parametrize(
    "name",
    [
        "external_lookup",
        "phase1_unreviewed_index",
        "phaſe1_stage_results",
        "phase１_intake_pending",
        "phase1_stage_results_extra",
    ],
)
def test_unrelated_names_preserve_public_writes_and_reopen(
    tmp_path: Path, version: str, name: str
) -> None:
    """Keep unrelated indexes/views and independent trigger names usable."""
    path = tmp_path / "neutral.db"
    occupant(path, version, "index", name)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.executescript(
            "CREATE TABLE external_audit (value TEXT NOT NULL);"
            "CREATE VIEW external_view AS SELECT value FROM external_rows;"
            'CREATE TRIGGER "phase1_intake_pending" '
            "AFTER INSERT ON external_rows BEGIN "
            "INSERT INTO external_audit VALUES (NEW.value); END;"
        )
    before = snapshot(path)
    store = h.store(path)
    try:
        token = h.claim(store)
        saved = h.selection(store, token)
        store.finish_claim(token, TerminalStatus.COMPLETE, ExternalEffectState.NONE)
        if store.get_result(saved.result_id) != saved:
            pytest.fail("Admitted public store cannot read its selection write")
    finally:
        store.close()
    reopened = h.store(path)
    try:
        if reopened.get_result(saved.result_id) != saved:
            pytest.fail("The exact selection did not survive reopen")
    finally:
        reopened.close()
    after = snapshot(path)
    external = {"external_rows", "external_audit", "external_view"}
    if [row for row in after["schema"] if row[2] in external] != [
        row for row in before["schema"] if row[2] in external
    ]:
        pytest.fail("Initialization changed unrelated schema objects")
    if any(after["rows"][key] != before["rows"][key] for key in external):
        pytest.fail("Initialization changed unrelated table or view rows")
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("INSERT INTO external_rows VALUES ('after')")
        if connection.execute("SELECT * FROM external_audit").fetchall() != [
            ("after",)
        ]:
            pytest.fail("An owned-looking trigger name lost its independence")
        if connection.execute("SELECT * FROM external_view").fetchall() != [
            ("retained",),
            ("after",),
        ]:
            pytest.fail("Initialization changed unrelated view behavior")
