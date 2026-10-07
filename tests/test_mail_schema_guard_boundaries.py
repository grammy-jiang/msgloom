"""Keep shared guard repair behind complete Mail schema validation."""

import hashlib
import sqlite3

import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine
from test_acquisition_handoff_immutability import populate

from message_ingest.catalog import Catalog

MAIL_TABLES = (
    "mail_component_captures",
    "mail_application_bindings",
    "mail_inventory_pages",
    "mail_inventory_members",
)
MAIL_GUARDS = {
    f"{table}_immutable_{operation}"
    for table in MAIL_TABLES
    for operation in ("insert", "update", "delete")
}
SHARED_GUARDS = {
    "immutable_acquisition_facts_INSERT",
    "immutable_acquisition_release_groups_INSERT",
    "immutable_acquisition_release_entries_INSERT",
    "immutable_acquisition_release_entry_facts_INSERT",
    "immutable_acquisition_ledger_metadata_INSERT",
    "immutable_acquisition_run_outcomes_INSERT",
    "canonical_acquisition_entry_member",
}


def snapshot(database):
    """Read all schema, rows and file bytes without catalog initialization."""
    with sqlite3.connect(database) as connection:
        schema = connection.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY name"
        ).fetchall()
        rows = {
            name: connection.execute(f'SELECT * FROM "{name}"').fetchall()
            for kind, name, _, _ in schema
            if kind == "table"
        }
    return schema, rows, hashlib.sha256(database.read_bytes()).hexdigest()


def seeded(tmp_path):
    """Populate real facts, releases, catalog identity and run history."""
    database = tmp_path / "guards.db"
    catalog = Catalog(f"sqlite:///{database}")
    try:
        populate(catalog)
    finally:
        catalog.close()
    schema, rows, _ = snapshot(database)
    for table in (
        "acquisition_facts",
        "acquisition_release_groups",
        "acquisition_release_entries",
        "acquisition_release_entry_facts",
        "acquisition_ledger_metadata",
        "acquisition_run_outcomes",
    ):
        if not rows[table]:
            pytest.fail(f"Guard fixture has no immutable history in {table}")
    definitions = {name: sql for kind, name, _, sql in schema if kind == "trigger"}
    actual_mail = {name for name in definitions if name.startswith("mail_")}
    actual_shared = {
        name
        for name, sql in definitions.items()
        if "BEFORE INSERT" in sql and name not in MAIL_GUARDS
    }
    if actual_mail != MAIL_GUARDS or actual_shared != SHARED_GUARDS:
        pytest.fail("Fixture did not contain the exact twelve and seven guards")
    return database, definitions


def remove(database, names):
    """Remove only the explicit nonempty expected fixture guard set."""
    if not names:
        pytest.fail("Empty removal cannot exercise guard recovery")
    with sqlite3.connect(database) as connection:
        for name in sorted(names):
            connection.execute(f'DROP TRIGGER "{name}"')


def rejected_without_ddl(database):
    """Prove rejection executes no DDL and preserves every byte and row."""
    before = snapshot(database)
    statements = []

    def record(connection, cursor, statement, parameters, context, many):
        if statement.lstrip().split()[0].upper() in {"CREATE", "ALTER", "DROP"}:
            statements.append(statement)

    event.listen(Engine, "before_cursor_execute", record)
    try:
        with pytest.raises(ValueError, match="Unknown or partial Mail binding schema"):
            Catalog(f"sqlite:///{database}")
    finally:
        event.remove(Engine, "before_cursor_execute", record)
    if statements or snapshot(database) != before:
        pytest.fail(f"Rejected reopen changed database or issued DDL: {statements}")


@pytest.mark.parametrize("guard", sorted(MAIL_GUARDS))
def test_each_missing_mail_guard_rejects_before_ddl(tmp_path, guard):
    """Each of twelve missing Mail guards refuses before any schema repair."""
    database, _ = seeded(tmp_path)
    remove(database, {guard})
    rejected_without_ddl(database)


def test_shared_guard_recovery_preserves_complete_mail_schema(tmp_path):
    """Recover all seven shared guards with all twelve Mail guards intact."""
    database, definitions = seeded(tmp_path)
    original_schema, original_rows, _ = snapshot(database)
    remove(database, SHARED_GUARDS)
    removed_schema, rows, _ = snapshot(database)
    remaining = {name for kind, name, _, _ in removed_schema if kind == "trigger"}
    if set(definitions) - remaining != SHARED_GUARDS or rows != original_rows:
        pytest.fail("Fixture removed the wrong guards or changed history")
    if not MAIL_GUARDS <= remaining:
        pytest.fail("Shared guard fixture removed a Mail guard")
    Catalog(f"sqlite:///{database}").close()
    schema, rows, _ = snapshot(database)
    if schema != original_schema or rows != original_rows:
        pytest.fail("Shared repair changed definitions, identity or immutable rows")
    restored = {name: sql for kind, name, _, sql in schema if kind == "trigger"}
    for name in MAIL_GUARDS | SHARED_GUARDS:
        if restored.get(name) != definitions[name]:
            pytest.fail(f"Guard definition changed during shared repair: {name}")


def test_partial_mail_schema_blocks_shared_guard_repair(tmp_path):
    """Missing Mail validation must precede even valid shared guard repair."""
    database, _ = seeded(tmp_path)
    remove(database, SHARED_GUARDS | {"mail_component_captures_immutable_insert"})
    rejected_without_ddl(database)
    schema, _, _ = snapshot(database)
    if SHARED_GUARDS & {name for kind, name, _, _ in schema if kind == "trigger"}:
        pytest.fail("Rejected partial Mail schema repaired shared guards")
