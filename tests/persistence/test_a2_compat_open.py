"""
Compatibility of the existing ``Phase1Store`` open with A2 schema files.

C0-11e. ``Phase1Store(database_url, registry)`` is the real open path. It
calls ``initialize_schema``. These tests only use it. They prove that open
leaves a schema 4 file logically unchanged and that only the explicit
migration tool reaches schema 5. They also record what open does with a
schema 5 file. Every database lives in ``tmp_path``.
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest

import msgloom.persistence.store as store_module
from msgloom.contracts import ResultSchemaRegistry
from msgloom.persistence.a2_schema import SchemaState, classify_schema
from msgloom.persistence.a2_schema_migration import migrate_database
from msgloom.persistence.errors import IncompatibleSchemaError
from msgloom.persistence.store import Phase1Store
from tests.a2_kedro.helpers import check
from tests.persistence.test_a2_schema_fixtures import (
    build_schema4,
    build_schema5,
    raw,
)

PROTECTED_MODULES = (
    "schema_store",
    "store",
    "intake_store",
    "async_store",
    "intake_completion",
)


def logical_state(path: Path) -> tuple[tuple[tuple[str, ...], ...], str, int]:
    """
    Return sqlite_master rows, a digest of the logical dump and user_version.

    The digest covers the SQL dump, not file bytes. It ignores mtime and
    page layout, so it is portable.
    """
    db = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    try:
        master = tuple(
            tuple(map(str, row))
            for row in db.execute(
                "SELECT type, name, tbl_name, rootpage <> 0, sql "
                "FROM sqlite_master ORDER BY type, name"
            )
        )
        digest = hashlib.sha256()
        for line in db.iterdump():
            digest.update(line.encode() + b"\n")
        version = int(db.execute("PRAGMA user_version").fetchone()[0])
    finally:
        db.close()
    return master, digest.hexdigest(), version


def metadata(path: Path) -> list[tuple[str, str]]:
    db = raw(path)
    try:
        return [
            (str(k), str(v))
            for k, v in db.execute(
                'SELECT "key", value FROM phase1_schema_metadata ORDER BY 1'
            )
        ]
    finally:
        db.close()


def open_store(path: Path) -> Phase1Store:
    return Phase1Store(f"sqlite:///{path}", ResultSchemaRegistry.phase1())


@pytest.fixture
def schema4(tmp_path: Path) -> Path:
    directory = tmp_path / "data"
    directory.mkdir()
    return build_schema4(
        directory / "live.sqlite", legacy_keys=("preparation_proof_legacy_terminal:r",)
    )


def test_open_of_schema4_changes_no_table_version_or_metadata(schema4: Path) -> None:
    before = logical_state(schema4)
    meta_before = metadata(schema4)
    check(("schema_version", "4") in meta_before, "fixture must be schema 4")
    store = open_store(schema4)
    store.close()
    check(logical_state(schema4) == before, "open changed tables or logical dump")
    check(metadata(schema4) == meta_before, "open changed schema_version meta")
    check(before[2] == logical_state(schema4)[2], "user_version changed")
    db = raw(schema4)
    try:
        check(classify_schema(db) is SchemaState.SCHEMA4, "still exact schema 4")
        names = {r[0] for r in db.execute("SELECT name FROM sqlite_master")}
    finally:
        db.close()
    check(not any(n.startswith("phase1_a2_") for n in names), "A2 table created")


def test_repeated_open_and_store_use_never_reach_schema5(schema4: Path) -> None:
    before = logical_state(schema4)
    for _ in range(3):
        store = open_store(schema4)
        try:
            check(store.get_result("absent-result") is None, "read works")
        finally:
            store.close()
    check(logical_state(schema4) == before, "open plus read changed the file")


def test_explicit_migration_is_the_only_path_to_schema5(
    schema4: Path, tmp_path: Path
) -> None:
    open_store(schema4).close()
    db = raw(schema4)
    try:
        check(classify_schema(db) is SchemaState.SCHEMA4, "open must not migrate")
    finally:
        db.close()
    backups = tmp_path / "backups"
    backups.mkdir()
    check(migrate_database(schema4, backups, confirm=True).status == "migrated", "run")
    db = raw(schema4)
    try:
        check(classify_schema(db) is SchemaState.SCHEMA5, "explicit path migrates")
    finally:
        db.close()


def test_no_protected_module_references_the_migration_or_a2_schema() -> None:
    root = Path(store_module.__file__).parent
    for name in PROTECTED_MODULES:
        text = (root / f"{name}.py").read_text()
        check("a2_schema" not in text, f"{name} must not reach the A2 migration")


def test_open_of_schema5_is_refused_and_leaves_the_file_unchanged(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "five"
    directory.mkdir()
    path = build_schema5(directory / "live.sqlite")
    before = logical_state(path)
    meta_before = metadata(path)
    with pytest.raises(IncompatibleSchemaError):
        open_store(path)
    check(logical_state(path) == before, "refused open changed the file")
    check(metadata(path) == meta_before, "refused open changed metadata")
    check(("schema_version", "5") in meta_before, "fixture must be schema 5")
