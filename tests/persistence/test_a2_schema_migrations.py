"""
Explicit A2 schema 4 to 5 migration tool: refusals, rollback and restore.

Every database lives in ``tmp_path``. The tests never open a real database.
Failures are injected through a forwarding connection wrapper, so no test
depends on timing or on the host.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine

import msgloom.persistence.a2_schema as a2
import msgloom.persistence.a2_schema_migration as tool
from msgloom.persistence.a2_schema import (
    A2SchemaError,
    SchemaState,
    classify_schema,
)
from msgloom.persistence.a2_schema_migration import (
    CONFIRM_MIGRATE_FLAG,
    CONFIRM_RESTORE_FLAG,
    create_backup,
    file_sha256,
    main,
    migrate_database,
    restore_backup,
)
from msgloom.persistence.errors import IncompatibleSchemaError
from msgloom.persistence.schema_store import initialize_schema
from tests.a2_kedro.helpers import check
from tests.persistence.test_a2_schema_fixtures import (
    build_schema4,
    build_schema5,
    raw,
    snapshot,
)

CANARY = "CANARY-PII-5d2e-bob@example.invalid"


class InjectedStop(BaseException):
    """A BaseException that is not an Exception, like KeyboardInterrupt."""


class FailingConnection:
    """Forwarding wrapper that fails the first statement with a prefix."""

    def __init__(
        self, inner: sqlite3.Connection, fail: str, error: BaseException
    ) -> None:
        self.inner = inner
        self._fail: str | None = fail
        self._error = error
        self.statements: list[str] = []

    @property
    def in_transaction(self) -> bool:
        return self.inner.in_transaction

    def execute(self, sql: str, *args: object) -> sqlite3.Cursor:
        self.statements.append(sql)
        if self._fail is not None and sql.startswith(self._fail):
            self._fail = None
            raise self._error
        return self.inner.execute(sql, *args)  # type: ignore[arg-type]

    def executemany(self, sql: str, rows: object) -> sqlite3.Cursor:
        return self.inner.executemany(sql, rows)  # type: ignore[arg-type]

    def close(self) -> None:
        self.inner.close()


def inject(monkeypatch: pytest.MonkeyPatch, fail: str, error: BaseException) -> list:
    """Make the tool open a wrapper that fails once. Return the wrappers."""
    made: list[FailingConnection] = []
    real = tool.connect_existing

    def factory(path: Path) -> FailingConnection:
        wrapper = FailingConnection(real(path), fail, error)
        made.append(wrapper)
        return wrapper

    monkeypatch.setattr(tool, "connect_existing", factory)
    return made


@pytest.fixture
def schema4(tmp_path: Path) -> Path:
    return build_schema4(tmp_path / "live.sqlite")


@pytest.fixture
def backups(tmp_path: Path) -> Path:
    directory = tmp_path / "backups"
    directory.mkdir()
    return directory


def state_of(path: Path) -> SchemaState:
    db = raw(path)
    try:
        return classify_schema(db)
    finally:
        db.close()


def refusal(path: Path, backups: Path) -> str:
    with pytest.raises(A2SchemaError) as caught:
        migrate_database(path, backups, confirm=True)
    return caught.value.reason


def old_binary_accepts(path: Path) -> bool:
    """Run the real, unchanged A1 schema 4 guard. Read-only use."""
    engine = create_engine(f"sqlite:///{path}")
    try:
        initialize_schema(engine)
    except IncompatibleSchemaError:
        return False
    finally:
        engine.dispose()
    return True


def test_confirmation_flag_is_required_and_nothing_is_touched(
    schema4: Path, backups: Path
) -> None:
    before = schema4.read_bytes()
    for confirm in (False, None, 1, "yes"):
        with pytest.raises(A2SchemaError, match="confirmation-required"):
            migrate_database(schema4, backups, confirm=confirm)  # type: ignore[arg-type]
    with pytest.raises(A2SchemaError, match="confirmation-required"):
        migrate_database(schema4, backups)
    check(schema4.read_bytes() == before, "file changed without confirmation")
    check(not list(backups.iterdir()), "backup written without confirmation")


def test_missing_file_is_refused_and_never_created(
    tmp_path: Path, backups: Path
) -> None:
    missing = tmp_path / "missing.sqlite"
    check(refusal(missing, backups) == "database-file-missing", "reason")
    check(not missing.exists(), "the tool must not create a database")


def test_migration_takes_verified_backup_then_reaches_schema5(
    schema4: Path, backups: Path
) -> None:
    original = schema4.read_bytes()
    before = snapshot(schema4)
    result = migrate_database(schema4, backups, confirm=True)
    check(result.status == "migrated", "status")
    check(state_of(schema4) is SchemaState.SCHEMA5, "must be schema5")
    check(
        result.backup_path is not None and result.backup_path.parent == backups, "dir"
    )
    check(result.backup_sha256 == file_sha256(result.backup_path), "digest")
    check(snapshot(result.backup_path) == before, "backup holds schema4 dump")
    check(state_of(result.backup_path) is SchemaState.SCHEMA4, "backup state")
    check(result.backup_path.stat().st_mode & 0o077 == 0, "backup mode must be 0600")
    check(schema4.read_bytes() != original, "source must change")


def test_rerun_on_schema5_is_idempotent(schema4: Path, backups: Path) -> None:
    migrate_database(schema4, backups, confirm=True)
    migrated = schema4.read_bytes()
    other = backups.parent / "second"
    other.mkdir()
    result = migrate_database(schema4, other, confirm=True)
    check(result.status == "already-migrated", "status")
    check(result.backup_path is None and result.backup_sha256 is None, "no backup")
    check(not list(other.iterdir()), "no backup file on a no-op")
    check(schema4.read_bytes() == migrated, "no-op must not write")


def test_backup_never_overwrites_and_needs_existing_directory(
    schema4: Path, backups: Path, tmp_path: Path
) -> None:
    path, _ = create_backup(schema4, backups)
    stamp = path.read_bytes()
    with pytest.raises(A2SchemaError, match="backup-exists"):
        create_backup(schema4, backups)
    check(path.read_bytes() == stamp, "existing backup was overwritten")
    with pytest.raises(A2SchemaError, match="backup-dir-missing"):
        create_backup(schema4, tmp_path / "absent")
    check(not (tmp_path / "absent").exists(), "the tool must not create the dir")


def _downgrade(path: Path, version: str, drop: tuple[str, ...]) -> None:
    db = raw(path)
    try:
        db.execute("PRAGMA foreign_keys = OFF")
        for table in drop:
            db.execute(f"DROP TABLE {table}")
        db.execute(
            'UPDATE phase1_schema_metadata SET value = ? WHERE "key" = ?',
            (version, "schema_version"),
        )
        db.execute(
            'DELETE FROM phase1_schema_metadata WHERE "key" = ?',
            ("preparation_proof_revision",),
        )
    finally:
        db.close()


_V3_DROP = (
    "phase1_preparation_result_bindings",
    "phase1_preparation_plan_proofs",
    "phase1_preparation_intake_held_entries",
    "phase1_preparation_intake_worksets",
    "phase1_preparation_intake_cursors",
)


@pytest.mark.parametrize(
    ("version", "drop"),
    [("3", _V3_DROP), ("2", (*_V3_DROP, "phase1_reconciliations"))],
    ids=["v3", "v2"],
)
def test_v2_and_v3_inputs_are_rejected_as_unsupported(
    tmp_path: Path, backups: Path, version: str, drop: tuple[str, ...]
) -> None:
    path = build_schema4(tmp_path / "old.sqlite")
    _downgrade(path, version, drop)
    before = path.read_bytes()
    check(refusal(path, backups) == "unreviewed-table-set", "clear reason code")
    check(path.read_bytes() == before, "unsupported input must stay untouched")
    check(not list(backups.iterdir()), "no backup for an unsupported input")


def _rename_table(db: sqlite3.Connection) -> None:
    db.execute("ALTER TABLE phase1_reconciliations RENAME TO phase1_reconciliationz")


def _extra_index(db: sqlite3.Connection) -> None:
    db.execute("CREATE INDEX phase1_extra ON phase1_stage_results (result_id)")


def _drop_index(db: sqlite3.Connection) -> None:
    name = db.execute(
        "SELECT name FROM sqlite_schema WHERE type='index' AND sql IS NOT NULL "
        "AND name LIKE 'ix_phase1_%' ORDER BY name"
    ).fetchone()
    if name is None:
        pytest.fail("fixture has no explicit index to drop")
    db.execute(f'DROP INDEX "{name[0]}"')


def _trigger(db: sqlite3.Connection) -> None:
    db.execute(
        "CREATE TRIGGER phase1_t AFTER DELETE ON phase1_stage_results "
        "BEGIN SELECT 1; END"
    )


def _a2_table(db: sqlite3.Connection) -> None:
    db.execute("CREATE TABLE phase1_a2_claims (x INTEGER)")


def _bad_version(db: sqlite3.Connection) -> None:
    db.execute(
        "UPDATE phase1_schema_metadata SET value = '9' WHERE \"key\" = 'schema_version'"
    )


def _extra_key(db: sqlite3.Connection) -> None:
    db.execute(
        "INSERT INTO phase1_schema_metadata (\"key\", value) VALUES ('rogue', 'x')"
    )


MUTATIONS = {
    "table-name": (_rename_table, "unreviewed-table-set"),
    "extra-index": (_extra_index, "schema4-definition-mismatch"),
    "dropped-index": (_drop_index, "schema4-definition-mismatch"),
    "trigger": (_trigger, "view-or-trigger-present"),
    "a2-table-in-schema4": (_a2_table, "unreviewed-table-set"),
    "version": (_bad_version, "unreviewed-version-pair"),
    "metadata-key": (_extra_key, "unknown-metadata-key"),
}


@pytest.mark.parametrize(
    ("mutate", "expected"), list(MUTATIONS.values()), ids=list(MUTATIONS)
)
def test_modified_schema4_is_refused_before_any_write(
    tmp_path: Path, backups: Path, mutate: object, expected: str
) -> None:
    path = build_schema4(tmp_path / "mod.sqlite")
    db = raw(path)
    try:
        mutate(db)  # type: ignore[operator]
    finally:
        db.close()
    before = path.read_bytes()
    check(refusal(path, backups) == expected, f"expected reason {expected}")
    check(path.read_bytes() == before, "refused input must stay byte-identical")
    check(not list(backups.iterdir()), "no backup for a refused input")


def test_non_database_file_is_refused_without_leaking_content(
    tmp_path: Path, backups: Path
) -> None:
    path = tmp_path / "junk.sqlite"
    path.write_text(CANARY * 50)
    reason = refusal(path, backups)
    check(CANARY not in reason and str(tmp_path) not in reason, "leak in reason")


@pytest.mark.parametrize(
    "error",
    [sqlite3.OperationalError(CANARY), KeyboardInterrupt(), InjectedStop()],
    ids=["sqlite-error", "keyboard-interrupt", "base-exception"],
)
def test_injected_ddl_failure_rolls_back_to_identical_schema4(
    schema4: Path,
    backups: Path,
    monkeypatch: pytest.MonkeyPatch,
    error: BaseException,
) -> None:
    before = schema4.read_bytes()
    dump = snapshot(schema4)
    wrappers = inject(monkeypatch, "CREATE TABLE phase1_a2_accepted_stages", error)
    with pytest.raises(BaseException) as caught:
        migrate_database(schema4, backups, confirm=True)
    if isinstance(error, sqlite3.Error):
        check(isinstance(caught.value, A2SchemaError), "must map to reason code")
        check(CANARY not in str(caught.value), "error text must not leak")
        check(caught.value.__cause__ is None, "no chained database error")
    else:
        check(caught.value is error, "the original exception must surface")
    check("ROLLBACK" in wrappers[0].statements, "rollback must be issued")
    check(schema4.read_bytes() == before, "schema4 must be byte-identical")
    check(snapshot(schema4) == dump, "dump must be unchanged")
    check(state_of(schema4) is SchemaState.SCHEMA4, "still schema4")
    backup = backups / f"{schema4.name}{tool.BACKUP_SUFFIX}"
    check(backup.is_file(), "the verified backup is kept after a failure")


@pytest.mark.parametrize(
    "error",
    [sqlite3.OperationalError(CANARY), KeyboardInterrupt()],
    ids=["sqlite-error", "keyboard-interrupt"],
)
def test_injected_commit_failure_rolls_back(
    schema4: Path,
    backups: Path,
    monkeypatch: pytest.MonkeyPatch,
    error: BaseException,
) -> None:
    before = schema4.read_bytes()
    wrappers = inject(monkeypatch, "COMMIT", error)
    with pytest.raises(BaseException) as caught:
        migrate_database(schema4, backups, confirm=True)
    if isinstance(error, sqlite3.Error):
        check(isinstance(caught.value, A2SchemaError), "must map to reason code")
        check(caught.value.reason == "migration-failed", "reason")
    else:
        check(caught.value is error, "the original exception must surface")
    check("ROLLBACK" in wrappers[0].statements, "rollback must be issued")
    check(schema4.read_bytes() == before, "schema4 must be byte-identical")
    check(state_of(schema4) is SchemaState.SCHEMA4, "still schema4")


def test_source_change_between_backup_and_migration_is_refused(
    schema4: Path, backups: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = tool.create_backup

    def stale(source: Path, directory: Path) -> tuple[Path, str]:
        result = real(source, directory)
        db = raw(source)
        try:
            db.execute(
                'INSERT INTO phase1_schema_metadata ("key", value) '
                "VALUES ('preparation_proof_legacy_terminal:late', 's')"
            )
        finally:
            db.close()
        return result

    monkeypatch.setattr(tool, "create_backup", stale)
    check(refusal(schema4, backups) == "source-changed-after-backup", "reason")
    check(state_of(schema4) is SchemaState.SCHEMA4, "still schema4")


def test_concurrent_writer_lock_refuses_and_retry_succeeds(
    schema4: Path, backups: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(a2, "BUSY_TIMEOUT_SECONDS", 0.05)
    before = schema4.read_bytes()
    writer = raw(schema4)
    try:
        writer.execute("BEGIN IMMEDIATE")
        check(refusal(schema4, backups) == "migration-lock-failed", "lock reason")
    finally:
        writer.execute("ROLLBACK")
        writer.close()
    check(schema4.read_bytes() == before, "locked attempt must not write")
    fresh = tmp_path / "retry"
    fresh.mkdir()
    check(migrate_database(schema4, fresh, confirm=True).status == "migrated", "retry")


def test_old_binary_rejects_schema5_and_restore_brings_it_back(
    schema4: Path, backups: Path
) -> None:
    check(old_binary_accepts(schema4), "the schema4 guard must accept schema4")
    result = migrate_database(schema4, backups, confirm=True)
    check(not old_binary_accepts(schema4), "schema4 guard must reject schema5")
    check(state_of(schema4) is SchemaState.SCHEMA5, "refusal must not alter file")
    check(result.backup_path is not None and result.backup_sha256 is not None, "backup")
    restore_backup(result.backup_path, schema4, result.backup_sha256, confirm=True)
    check(state_of(schema4) is SchemaState.SCHEMA4, "restored to schema4")
    check(old_binary_accepts(schema4), "old binary accepts the restored file")
    check(snapshot(schema4) == snapshot(result.backup_path), "restored dump")


def test_restore_checks_digest_confirmation_and_backup_state(
    schema4: Path, backups: Path, tmp_path: Path
) -> None:
    path, digest = create_backup(schema4, backups)
    target = build_schema5(tmp_path / "t.sqlite")
    before = target.read_bytes()
    with pytest.raises(A2SchemaError, match="confirmation-required"):
        restore_backup(path, target, digest)
    with pytest.raises(A2SchemaError, match="restore-digest-shape"):
        restore_backup(path, target, "ABC", confirm=True)
    with pytest.raises(A2SchemaError, match="backup-digest-mismatch"):
        restore_backup(path, target, "0" * 64, confirm=True)
    with pytest.raises(A2SchemaError, match="backup-file-missing"):
        restore_backup(tmp_path / "none", target, digest, confirm=True)
    check(target.read_bytes() == before, "refused restore must not write")
    tampered = path.read_bytes()
    path.write_bytes(tampered[:-1] + bytes([tampered[-1] ^ 1]))
    with pytest.raises(A2SchemaError, match="backup-digest-mismatch"):
        restore_backup(path, target, digest, confirm=True)
    check(target.read_bytes() == before, "tampered backup must not restore")


def test_restore_refuses_a_schema5_file_even_with_matching_digest(
    tmp_path: Path,
) -> None:
    path = build_schema5(tmp_path / "five.sqlite")
    target = build_schema5(tmp_path / "target.sqlite")
    with pytest.raises(A2SchemaError, match="not-schema4"):
        restore_backup(path, target, file_sha256(path), confirm=True)


def test_main_requires_flag_and_reports_reason_codes_only(
    schema4: Path, backups: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = ["migrate", "--db", str(schema4), "--backup-dir", str(backups)]
    check(main(argv) == 1, "missing flag must refuse")
    captured = capsys.readouterr()
    check("confirmation-required" in captured.err, "reason code")
    check(str(schema4) not in captured.err + captured.out, "no path in output")
    with pytest.raises(SystemExit) as parse_error:
        main(["migrate", "--db", str(schema4)])
    check(parse_error.value.code == 2, "argument errors exit with 2")
    capsys.readouterr()
    check(main([*argv, CONFIRM_MIGRATE_FLAG]) == 0, "confirmed run")
    out = capsys.readouterr().out
    check("status=migrated" in out and "backup_sha256=" in out, "status lines")
    check(str(backups) not in out, "no path in output")
    check(main([*argv, CONFIRM_MIGRATE_FLAG]) == 0, "idempotent rerun")
    check("status=already-migrated" in capsys.readouterr().out, "no-op status")


def test_main_restore_round_trip(
    schema4: Path, backups: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    result = migrate_database(schema4, backups, confirm=True)
    capsys.readouterr()
    argv = [
        "restore",
        "--db",
        str(schema4),
        "--backup",
        str(result.backup_path),
        "--backup-sha256",
        str(result.backup_sha256),
    ]
    check(main(argv) == 1, "restore needs its flag")
    check(state_of(schema4) is SchemaState.SCHEMA5, "still migrated")
    check(main([*argv, CONFIRM_RESTORE_FLAG]) == 0, "restore ok")
    check(state_of(schema4) is SchemaState.SCHEMA4, "back to schema4")
