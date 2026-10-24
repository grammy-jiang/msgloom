"""A2 migration: COMMIT failure and a file that changes before the lock."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest

from msgloom.persistence.a2_schema import (
    A2_TABLES,
    A2SchemaError,
    SchemaState,
    classify_schema,
    migrate_schema4_to_v5,
)
from tests.a2_kedro.helpers import check
from tests.persistence.test_a2_schema_fixtures import (
    GATE,
    build_schema4,
    raw,
    snapshot,
)

CANARY = "CANARY-PII-5d2e-bob@example.invalid"


class HookedConnection:
    """
    Thin forwarding wrapper around a real connection.

    ``before`` runs once, right before the first statement that starts with
    the given prefix. ``fail`` raises ``sqlite3.OperationalError`` for the
    first statement with the given prefix and does not forward it.
    """

    def __init__(
        self,
        inner: sqlite3.Connection,
        *,
        before: tuple[str, Callable[[], None]] | None = None,
        fail: str | None = None,
    ) -> None:
        self._inner = inner
        self._before = before
        self._fail = fail

    @property
    def in_transaction(self) -> bool:
        return self._inner.in_transaction

    def execute(self, sql: str, *args: object) -> sqlite3.Cursor:
        if self._before is not None and sql.startswith(self._before[0]):
            hook, self._before = self._before[1], None
            hook()
        if self._fail is not None and sql.startswith(self._fail):
            self._fail = None
            raise sqlite3.OperationalError(f"{CANARY} forced failure")
        return self._inner.execute(sql, *args)  # type: ignore[arg-type]

    def executemany(self, sql: str, rows: object) -> sqlite3.Cursor:
        return self._inner.executemany(sql, rows)  # type: ignore[arg-type]


def test_commit_failure_rolls_back_and_later_migration_succeeds(
    tmp_path: Path,
) -> None:
    path = build_schema4(tmp_path / "s4.sqlite")
    before = (snapshot(path), path.read_bytes())
    inner = raw(path)
    try:
        wrapped = HookedConnection(inner, fail="COMMIT")
        with pytest.raises(A2SchemaError) as caught:
            migrate_schema4_to_v5(wrapped, GATE)  # type: ignore[arg-type]
        check(caught.value.reason == "migration-failed", "reason code")
        check(CANARY not in repr(caught.value) + str(caught.value), "leak")
        check(caught.value.__cause__ is None, "raw error must not chain")
        check(not inner.in_transaction, "transaction must be closed")
    finally:
        inner.close()
    check(snapshot(path) == before[0], "schema rows must be unchanged")
    check(path.read_bytes() == before[1], "file bytes must be unchanged")
    db = raw(path)
    try:
        check(classify_schema(db) is SchemaState.SCHEMA4, "still schema4")
        names = {r[0] for r in db.execute("SELECT name FROM sqlite_schema")}
        check(not names & A2_TABLES, "no A2 table may remain")
        migrate_schema4_to_v5(db, GATE)
        check(classify_schema(db) is SchemaState.SCHEMA5, "later migration works")
    finally:
        db.close()


def _add_foreign(path: Path) -> None:
    other = raw(path)
    try:
        other.execute("CREATE TABLE phase1_late_extra (x)")
    finally:
        other.close()


def _add_a2_table(path: Path) -> None:
    other = raw(path)
    try:
        other.execute("CREATE TABLE phase1_a2_claims (x)")
    finally:
        other.close()


def _add_key(path: Path) -> None:
    other = raw(path)
    try:
        other.execute("INSERT INTO phase1_schema_metadata VALUES ('rogue', 'x')")
    finally:
        other.close()


def _add_trigger(path: Path) -> None:
    other = raw(path)
    try:
        other.execute(
            "CREATE TRIGGER late AFTER INSERT ON phase1_schema_metadata "
            "BEGIN SELECT 1; END"
        )
    finally:
        other.close()


def _migrate_elsewhere(path: Path) -> None:
    other = raw(path)
    try:
        migrate_schema4_to_v5(other, GATE)
    finally:
        other.close()


@pytest.mark.parametrize(
    ("change", "code"),
    [
        (_add_foreign, "unreviewed-table-set"),
        (_add_a2_table, "unreviewed-table-set"),
        (_add_key, "unknown-metadata-key"),
        (_add_trigger, "view-or-trigger-present"),
        (_migrate_elsewhere, "not-schema4"),
    ],
)
def test_file_changed_between_classification_and_lock_is_refused(
    tmp_path: Path, change: Callable[[Path], None], code: str
) -> None:
    path = build_schema4(tmp_path / "s4.sqlite")
    inner = raw(path)
    try:
        check(classify_schema(inner) is SchemaState.SCHEMA4, "pre-lock schema4")
        after_change: list[tuple[tuple[str, ...], ...]] = []

        def hook() -> None:
            change(path)
            after_change.append(snapshot(path))

        wrapped = HookedConnection(inner, before=("BEGIN IMMEDIATE", hook))
        with pytest.raises(A2SchemaError) as caught:
            migrate_schema4_to_v5(wrapped, GATE)  # type: ignore[arg-type]
        check(
            caught.value.reason == code, f"expected {code}, got {caught.value.reason}"
        )
        check(len(after_change) == 1, "the change must run before the lock")
        check(not inner.in_transaction, "transaction must be closed")
    finally:
        inner.close()
    check(snapshot(path) == after_change[0], "refused migration must not write")
