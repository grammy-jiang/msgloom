"""A2 schema recognition, guarded migration, rollback and error hygiene."""

from __future__ import annotations

import subprocess
import sys
import textwrap
import traceback
from pathlib import Path

import pytest
from sqlalchemy.dialects import sqlite as sqlite_dialect
from sqlalchemy.schema import CreateIndex, CreateTable

import msgloom.persistence.a2_schema as a2
from msgloom.persistence.a2_schema import (
    A2_TABLES,
    SCHEMA4_DIGEST,
    SCHEMA4_TABLES,
    A2SchemaError,
    MigrationGate,
    SchemaState,
    classify_schema,
    connect_existing,
    migrate_schema4_to_v5,
    require_schema5,
)
from msgloom.persistence.errors import IncompatibleSchemaError
from msgloom.persistence.models import Phase1Base
from tests.a2_kedro.helpers import check
from tests.persistence.test_a2_schema_fixtures import (
    GATE,
    build_schema4,
    build_schema5,
    raw,
    snapshot,
)


@pytest.fixture
def schema4(tmp_path: Path) -> Path:
    return build_schema4(tmp_path / "s4.sqlite")


@pytest.fixture
def schema5(tmp_path: Path) -> Path:
    return build_schema5(tmp_path / "s5.sqlite")


REPO_ROOT = Path(__file__).resolve().parents[2]
CANARY = "CANARY-PII-8c1f-alice@example.invalid"


def reason(path: Path) -> str:
    db = raw(path)
    try:
        with pytest.raises(A2SchemaError) as caught:
            classify_schema(db)
    finally:
        db.close()
    return caught.value.reason


def test_pinned_digest_matches_live_models_and_real_file(schema4: Path) -> None:
    dialect = sqlite_dialect.dialect()
    pairs = []
    for name, table in Phase1Base.metadata.tables.items():
        pairs.append((name, str(CreateTable(table).compile(dialect=dialect))))
        pairs += [
            (str(index.name), str(CreateIndex(index).compile(dialect=dialect)))
            for index in table.indexes
        ]
    check(set(Phase1Base.metadata.tables) == SCHEMA4_TABLES, "table set pin")
    check(a2._sql_digest(pairs) == SCHEMA4_DIGEST, "digest drifted from models")
    db = raw(schema4)
    try:
        check(classify_schema(db) is SchemaState.SCHEMA4, "real file recognized")
    finally:
        db.close()


def test_open_and_read_checks_never_create_or_change_anything(
    schema4: Path, tmp_path: Path
) -> None:
    before = (snapshot(schema4), schema4.read_bytes())
    db = connect_existing(schema4)
    try:
        check(classify_schema(db) is SchemaState.SCHEMA4, "schema4 state")
        with pytest.raises(A2SchemaError) as caught:
            require_schema5(db)
    finally:
        db.close()
    check(caught.value.reason == "migration-required", "must demand migration")
    check((snapshot(schema4), schema4.read_bytes()) == before, "file changed")
    missing = tmp_path / "missing.sqlite"
    with pytest.raises(A2SchemaError, match="database-file-missing"):
        connect_existing(missing)
    check(not missing.exists(), "connect_existing must not create a file")
    check(issubclass(A2SchemaError, IncompatibleSchemaError), "error hierarchy")


def test_migration_activates_schema5_and_keeps_legacy_keys(tmp_path: Path) -> None:
    path = build_schema4(
        tmp_path / "l.sqlite", legacy_keys=("preparation_proof_legacy_terminal:r1",)
    )
    db = raw(path)
    try:
        migrate_schema4_to_v5(db, GATE)
        check(classify_schema(db) is SchemaState.SCHEMA5, "schema5 state")
        require_schema5(db)
        meta = dict(db.execute('SELECT "key", value FROM phase1_schema_metadata'))
        tables = {
            row[0]
            for row in db.execute("SELECT name FROM sqlite_schema WHERE type='table'")
        }
    finally:
        db.close()
    check(
        meta["schema_version"] == "5" and meta["preparation_proof_revision"] == "1",
        "versions",
    )
    check(meta["a2_schema_revision"] == "1", "a2 revision")
    check(meta["a2_producer_marker"] == a2.PRODUCER_MARKER, "producer marker")
    check("preparation_proof_legacy_terminal:r1" in meta, "legacy key kept")
    check(A2_TABLES <= tables and SCHEMA4_TABLES <= tables, "table sets")


def test_second_migration_is_refused_and_changes_nothing(schema5: Path) -> None:
    before = snapshot(schema5)
    db = raw(schema5)
    try:
        with pytest.raises(A2SchemaError) as caught:
            migrate_schema4_to_v5(db, GATE)
    finally:
        db.close()
    check(caught.value.reason == "not-schema4", "idempotency guard")
    check(snapshot(schema5) == before, "second run must not change the file")


@pytest.mark.parametrize(
    ("gate", "code"),
    [
        (MigrationGate("B" * 64, SCHEMA4_DIGEST), "operator-gate-backup-digest"),
        (MigrationGate("b" * 63, SCHEMA4_DIGEST), "operator-gate-backup-digest"),
        (MigrationGate("b" * 64 + "\n", SCHEMA4_DIGEST), "operator-gate-backup-digest"),
        (MigrationGate("b" * 64, "0" * 64), "operator-gate-schema-digest"),
        (None, "operator-gate-required"),
    ],
)
def test_gate_is_required_and_validated(schema4: Path, gate, code: str) -> None:
    before = snapshot(schema4)
    db = raw(schema4)
    try:
        with pytest.raises(A2SchemaError) as caught:
            migrate_schema4_to_v5(db, gate)
    finally:
        db.close()
    check(caught.value.reason == code, f"reason {caught.value.reason}")
    check(snapshot(schema4) == before, "refused gate must not write")


def test_open_transaction_is_refused(schema4: Path) -> None:
    db = raw(schema4)
    try:
        db.execute("BEGIN")
        with pytest.raises(A2SchemaError, match="open-transaction"):
            migrate_schema4_to_v5(db, GATE)
        db.execute("ROLLBACK")
    finally:
        db.close()


@pytest.mark.parametrize(
    ("version", "revision"),
    [
        ("2", "1"),
        ("3", "1"),
        ("5", "1"),
        ("04", "1"),
        ("", "1"),
        ("4", "2"),
        ("4", None),
    ],
)
def test_wrong_version_pairs_are_rejected(schema4: Path, version, revision) -> None:
    db = raw(schema4)
    db.execute(
        "UPDATE phase1_schema_metadata SET value = ? WHERE \"key\" = 'schema_version'",
        (version,),
    )
    if revision is None:
        db.execute(
            "DELETE FROM phase1_schema_metadata WHERE \"key\" = 'preparation_proof_revision'"
        )
    else:
        db.execute(
            "UPDATE phase1_schema_metadata SET value = ? WHERE \"key\" = 'preparation_proof_revision'",
            (revision,),
        )
    db.close()
    before = snapshot(schema4)
    check(reason(schema4) == "unreviewed-version-pair", "version pair")
    db = raw(schema4)
    try:
        with pytest.raises(A2SchemaError):
            migrate_schema4_to_v5(db, GATE)
    finally:
        db.close()
    check(snapshot(schema4) == before, "rejected file must stay as it was")


def mutate_file(path: Path, *statements: str) -> None:
    db = raw(path)
    try:
        for statement in statements:
            db.execute(statement)
    finally:
        db.close()


@pytest.mark.parametrize(
    ("statements", "code"),
    [
        (("DROP TABLE phase1_preparation_plan_proofs",), "unreviewed-table-set"),
        (("DROP TABLE phase1_reconciliations",), "unreviewed-table-set"),
        (("CREATE TABLE phase1_extra (x)",), "unreviewed-table-set"),
        (("CREATE TABLE phase1_a2_claims (x)",), "unreviewed-table-set"),
        (("CREATE TABLE Phase1_A2_Other (x)",), "unreviewed-a2-table"),
        (
            ("CREATE INDEX extra_ix ON phase1_stage_results (status)",),
            "schema4-definition-mismatch",
        ),
        (("CREATE VIEW v AS SELECT 1",), "view-or-trigger-present"),
        (
            (
                "CREATE TRIGGER t AFTER INSERT ON phase1_stage_results BEGIN SELECT 1; END",
            ),
            "view-or-trigger-present",
        ),
        (
            ("INSERT INTO phase1_schema_metadata VALUES ('rogue', 'x')",),
            "unknown-metadata-key",
        ),
        (
            ("INSERT INTO phase1_schema_metadata VALUES ('a2_schema_revision', '1')",),
            "unknown-metadata-key",
        ),
    ],
)
def test_unknown_or_partial_schema4_is_rejected(
    schema4: Path, statements, code: str
) -> None:
    mutate_file(schema4, *statements)
    before = snapshot(schema4)
    check(reason(schema4) == code, f"expected {code}")
    db = raw(schema4)
    try:
        with pytest.raises(A2SchemaError):
            migrate_schema4_to_v5(db, GATE)
    finally:
        db.close()
    check(snapshot(schema4) == before, "unknown shape must not be repaired")


def test_empty_and_foreign_and_garbage_files_are_rejected(tmp_path: Path) -> None:
    empty = tmp_path / "empty.sqlite"
    raw(empty).close()
    check(reason(empty) == "no-neutral-schema", "empty file")
    foreign = tmp_path / "foreign.sqlite"
    mutate_file(foreign, "CREATE TABLE other (x)")
    check(reason(foreign) == "no-neutral-schema", "foreign schema")
    garbage = tmp_path / "garbage.sqlite"
    garbage.write_bytes(b"not a database" * 200)
    check(reason(garbage) == "file-is-not-a-database", "garbage file")


@pytest.mark.parametrize(
    ("statements", "code"),
    [
        (("DROP TABLE phase1_a2_stage_attempts",), "unreviewed-table-set"),
        (("CREATE INDEX x_ix ON phase1_a2_claims (state)",), "a2-definition-mismatch"),
        (("DROP INDEX phase1_a2_claims_live",), "a2-definition-mismatch"),
        (
            (
                "DROP TABLE phase1_a2_stage_attempts",
                "CREATE TABLE phase1_a2_stage_attempts (attempt_seq INTEGER PRIMARY KEY)",
            ),
            "a2-definition-mismatch",
        ),
        (
            (
                "UPDATE phase1_schema_metadata SET value = '4' WHERE \"key\" = 'schema_version'",
            ),
            "unreviewed-version-pair",
        ),
        (
            (
                "UPDATE phase1_schema_metadata SET value = 'other' WHERE \"key\" = 'a2_producer_marker'",
            ),
            "unreviewed-version-pair",
        ),
        (
            (
                "DELETE FROM phase1_schema_metadata WHERE \"key\" = 'a2_schema_revision'",
            ),
            "unreviewed-version-pair",
        ),
        (
            ("CREATE TRIGGER t AFTER INSERT ON phase1_a2_claims BEGIN SELECT 1; END",),
            "view-or-trigger-present",
        ),
    ],
)
def test_partial_or_altered_schema5_fails_closed(
    schema5: Path, statements, code: str
) -> None:
    mutate_file(schema5, *statements)
    check(reason(schema5) == code, f"expected {code}")
    db = raw(schema5)
    try:
        with pytest.raises(A2SchemaError):
            require_schema5(db)
    finally:
        db.close()


def test_schema4_tables_with_version5_marker_is_rejected(schema4: Path) -> None:
    mutate_file(
        schema4,
        "UPDATE phase1_schema_metadata SET value = '5' WHERE \"key\" = 'schema_version'",
    )
    check(reason(schema4) == "unreviewed-version-pair", "version 5 without A2 tables")


def test_failure_inside_migration_rolls_back_to_schema4(
    schema4: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = (snapshot(schema4), schema4.read_bytes())

    def boom(_connection) -> None:
        raise RuntimeError(CANARY)

    monkeypatch.setattr(a2, "_activate", boom)
    db = raw(schema4)
    try:
        with pytest.raises(RuntimeError):
            migrate_schema4_to_v5(db, GATE)
        check(not db.in_transaction, "transaction must be closed")
    finally:
        db.close()
    check(snapshot(schema4) == before[0], "schema4 must be intact")
    db = raw(schema4)
    try:
        check(classify_schema(db) is SchemaState.SCHEMA4, "still schema4")
    finally:
        db.close()


def test_interrupt_and_bad_ddl_roll_back(
    schema4: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = snapshot(schema4)

    def interrupt(_connection) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(a2, "_activate", interrupt)
    db = raw(schema4)
    try:
        with pytest.raises(KeyboardInterrupt):
            migrate_schema4_to_v5(db, GATE)
    finally:
        db.close()
    check(snapshot(schema4) == before, "interrupt must roll back")
    bad = (*a2.A2_OBJECTS, ("table", "phase1_a2_bad", "CREATE TABLE phase1_a2_bad (x"))
    monkeypatch.setattr(a2, "A2_OBJECTS", bad)
    db = raw(schema4)
    try:
        with pytest.raises(A2SchemaError, match="migration-failed"):
            migrate_schema4_to_v5(db, GATE)
    finally:
        db.close()
    check(snapshot(schema4) == before, "failed DDL must roll back every table")


def test_process_crash_before_commit_leaves_schema4(schema4: Path) -> None:
    script = textwrap.dedent(
        """
        import os, sys
        sys.path.insert(0, sys.argv[1])
        import msgloom.persistence.a2_schema as a2
        a2._activate = lambda connection: os._exit(7)
        connection = a2.connect_existing(__import__("pathlib").Path(sys.argv[2]))
        a2.migrate_schema4_to_v5(
            connection, a2.MigrationGate(sys.argv[3], a2.SCHEMA4_DIGEST)
        )
        """
    )
    before = snapshot(schema4)
    done = subprocess.run(
        [sys.executable, "-c", script, str(REPO_ROOT), str(schema4), "c" * 64],
        capture_output=True,
        timeout=120,
        check=False,
    )
    check(done.returncode == 7, f"child must crash on purpose, got {done.returncode}")
    check(snapshot(schema4) == before, "crash must leave schema4 intact")
    db = raw(schema4)
    try:
        check(classify_schema(db) is SchemaState.SCHEMA4, "recovered as schema4")
        migrate_schema4_to_v5(db, GATE)
        check(classify_schema(db) is SchemaState.SCHEMA5, "migration works after crash")
    finally:
        db.close()


def formatted(error: BaseException) -> str:
    return "".join(traceback.format_exception(error)) + repr(error) + str(error)


def test_errors_never_leak_paths_keys_or_sql(tmp_path: Path) -> None:
    folder = tmp_path / CANARY
    folder.mkdir()
    errors: list[A2SchemaError] = []
    cases = {
        "garbage": lambda p: p.write_bytes((CANARY * 400).encode()),
        "foreign": lambda p: mutate_file(p, f'CREATE TABLE "{CANARY}" (x)'),
        "table": lambda p: (
            build_schema4(p),
            mutate_file(p, f'CREATE TABLE "phase1_{CANARY}" (x)'),
        ),
        "key": lambda p: (
            build_schema4(p),
            mutate_file(
                p, f"INSERT INTO phase1_schema_metadata VALUES ('{CANARY}', '{CANARY}')"
            ),
        ),
        "trigger": lambda p: (
            build_schema4(p),
            mutate_file(p, f'CREATE VIEW "{CANARY}" AS SELECT 1'),
        ),
    }
    for name, make in cases.items():
        path = folder / f"{name}.sqlite"
        make(path)
        db = raw(path)
        try:
            for call in (classify_schema, lambda c: migrate_schema4_to_v5(c, GATE)):
                try:
                    call(db)
                except A2SchemaError as error:
                    errors.append(error)
        finally:
            db.close()
    with pytest.raises(A2SchemaError) as missing:
        connect_existing(folder / "absent.sqlite")
    errors.append(missing.value)
    check(len(errors) >= 9, f"expected many refusals, got {len(errors)}")
    for error in errors:
        check(CANARY not in formatted(error), f"leak in {error.reason}")
        check(str(folder) not in formatted(error), "path leaked")
