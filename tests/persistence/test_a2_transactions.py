"""
A2 transactions: rollback on COMMIT failure and on any BaseException.

Every database lives in ``tmp_path``. A forwarding wrapper injects the
failures, so no test depends on timing or on the host.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from msgloom.persistence.a2_acceptance_models import (
    AcceptedStage,
    accepted_stage_from_result,
)
from msgloom.persistence.a2_schema import (
    A2SchemaError,
    SchemaState,
    classify_schema,
    migrate_schema4_to_v5,
)
from msgloom.persistence.a2_sqlite_store import A2ResearchStore
from msgloom.persistence.a2_txn import rollback_quietly
from tests.a2_kedro.helpers import check, proof, result_for, stage_identity
from tests.persistence.test_a2_schema_fixtures import (
    GATE,
    build_schema4,
    raw,
    snapshot,
)


class InjectedStop(BaseException):
    """A BaseException that is not an Exception, like KeyboardInterrupt."""


class FailingConnection:
    """
    Forwarding wrapper that fails the first statement with a given prefix.

    ``error`` is raised instead of forwarding that statement. With
    ``close_first`` the real connection closes before the raise. With
    ``end_transaction`` a real ``ROLLBACK`` runs before the raise, so the
    transaction is already over. ``rollback_error`` makes every later
    ``ROLLBACK`` raise. ``statements`` lists each attempted statement.
    """

    def __init__(
        self,
        inner: sqlite3.Connection,
        fail: str,
        error: BaseException,
        *,
        close_first: bool = False,
        end_transaction: bool = False,
        rollback_error: Exception | None = None,
    ) -> None:
        self.inner = inner
        self._fail: str | None = fail
        self._error = error
        self._close_first = close_first
        self._end_transaction = end_transaction
        self._rollback_error = rollback_error
        self.statements: list[str] = []

    @property
    def in_transaction(self) -> bool:
        return self.inner.in_transaction

    def execute(self, sql: str, *args: object) -> sqlite3.Cursor:
        self.statements.append(sql)
        if self._fail is not None and sql.startswith(self._fail):
            self._fail = None
            if self._close_first:
                self.inner.close()
            if self._end_transaction:
                self.inner.execute("ROLLBACK")
            raise self._error
        if sql == "ROLLBACK" and self._rollback_error is not None:
            raise self._rollback_error
        return self.inner.execute(sql, *args)  # type: ignore[arg-type]

    def executemany(self, sql: str, rows: object) -> sqlite3.Cursor:
        return self.inner.executemany(sql, rows)  # type: ignore[arg-type]

    def close(self) -> None:
        self.inner.close()


BASE_ERRORS = [KeyboardInterrupt(), SystemExit(3), InjectedStop()]


def _ids(errors: list[BaseException]) -> list[str]:
    return [type(error).__name__ for error in errors]


def _wrapped_schema4(
    tmp_path: Path, error: BaseException, **options: object
) -> tuple[Path, FailingConnection]:
    path = build_schema4(tmp_path / "s4.sqlite")
    return path, FailingConnection(raw(path), "COMMIT", error, **options)  # type: ignore[arg-type]


def _check_still_schema4(path: Path, before: tuple[tuple[str, ...], ...]) -> None:
    check(snapshot(path) == before, "schema rows must be unchanged")
    db = raw(path)
    try:
        check(classify_schema(db) is SchemaState.SCHEMA4, "still schema4")
    finally:
        db.close()


@pytest.mark.parametrize("error", BASE_ERRORS, ids=_ids(BASE_ERRORS))
def test_migration_commit_base_exception_rolls_back_and_reraises(
    tmp_path: Path, error: BaseException
) -> None:
    path, wrapped = _wrapped_schema4(tmp_path, error)
    before = snapshot(path)
    try:
        with pytest.raises(BaseException) as caught:
            migrate_schema4_to_v5(wrapped, GATE)  # type: ignore[arg-type]
        check(caught.value is error, "the original exception must surface")
        check("ROLLBACK" in wrapped.statements, "rollback must be issued")
        check(not wrapped.in_transaction, "transaction must be closed")
    finally:
        wrapped.close()
    _check_still_schema4(path, before)


@pytest.mark.parametrize("error", BASE_ERRORS, ids=_ids(BASE_ERRORS))
def test_migration_body_base_exception_rolls_back_and_reraises(
    tmp_path: Path, error: BaseException
) -> None:
    path = build_schema4(tmp_path / "s4.sqlite")
    before = snapshot(path)
    wrapped = FailingConnection(raw(path), "UPDATE phase1_schema_metadata", error)
    try:
        with pytest.raises(BaseException) as caught:
            migrate_schema4_to_v5(wrapped, GATE)  # type: ignore[arg-type]
        check(caught.value is error, "the original exception must surface")
        check(not wrapped.in_transaction, "transaction must be closed")
    finally:
        wrapped.close()
    _check_still_schema4(path, before)


@pytest.mark.parametrize(
    "options",
    [
        {"close_first": True},
        {"end_transaction": True},
        {"rollback_error": sqlite3.OperationalError("cannot rollback")},
    ],
    ids=["connection-closed", "transaction-ended", "rollback-raises"],
)
def test_migration_commit_failure_with_dead_transaction_keeps_original(
    tmp_path: Path, options: dict[str, object]
) -> None:
    error = sqlite3.OperationalError("commit failed")
    path, wrapped = _wrapped_schema4(tmp_path, error, **options)
    before = snapshot(path)
    try:
        with pytest.raises(A2SchemaError) as caught:
            migrate_schema4_to_v5(wrapped, GATE)  # type: ignore[arg-type]
        check(caught.value.reason == "migration-failed", "reason code")
        check(caught.value.__cause__ is None, "raw error must not chain")
    finally:
        wrapped.close()
    _check_still_schema4(path, before)


@pytest.mark.parametrize("error", BASE_ERRORS, ids=_ids(BASE_ERRORS))
def test_migration_base_exception_survives_a_closed_connection(
    tmp_path: Path, error: BaseException
) -> None:
    path, wrapped = _wrapped_schema4(tmp_path, error, close_first=True)
    before = snapshot(path)
    with pytest.raises(BaseException) as caught:
        migrate_schema4_to_v5(wrapped, GATE)  # type: ignore[arg-type]
    check(caught.value is error, "rollback must not mask the original")
    _check_still_schema4(path, before)


def test_rollback_quietly_ignores_a_closed_connection(tmp_path: Path) -> None:
    db = raw(tmp_path / "x.sqlite")
    db.execute("BEGIN IMMEDIATE")
    db.close()
    rollback_quietly(db)
    idle = raw(tmp_path / "y.sqlite")
    try:
        rollback_quietly(idle)
        check(not idle.in_transaction, "idle connection stays idle")
    finally:
        idle.close()


def _stage() -> tuple[AcceptedStage, object]:
    identity = stage_identity()
    result = result_for(identity, attempt="a1")
    return accepted_stage_from_result(identity, result, proof("a1")), proof("a1")


def _store_with(
    tmp_path: Path, error: BaseException, **options: object
) -> tuple[Path, FailingConnection, A2ResearchStore]:
    path = tmp_path / "a2.sqlite"
    A2ResearchStore.create(path).close()
    wrapped = FailingConnection(
        sqlite3.connect(path, isolation_level=None),
        "COMMIT",
        error,
        **options,  # type: ignore[arg-type]
    )
    return path, wrapped, A2ResearchStore(wrapped)  # type: ignore[arg-type]


def _accepted_rows(path: Path) -> int:
    db = sqlite3.connect(path, isolation_level=None)
    try:
        return db.execute("SELECT count(*) FROM a2c0_accepted_stage").fetchone()[0]
    finally:
        db.close()


@pytest.mark.parametrize("error", BASE_ERRORS, ids=_ids(BASE_ERRORS))
def test_store_commit_base_exception_rolls_back_and_reraises(
    tmp_path: Path, error: BaseException
) -> None:
    path, wrapped, store = _store_with(tmp_path, error)
    stage, attempt = _stage()
    try:
        with pytest.raises(BaseException) as caught:
            store.accept_stage(stage, attempt)  # type: ignore[arg-type]
        check(caught.value is error, "the original exception must surface")
        check("ROLLBACK" in wrapped.statements, "rollback must be issued")
        check(not wrapped.in_transaction, "transaction must be closed")
    finally:
        wrapped.close()
    check(_accepted_rows(path) == 0, "no row may survive the failed commit")


@pytest.mark.parametrize(
    "options",
    [
        {"close_first": True},
        {"end_transaction": True},
        {"rollback_error": sqlite3.OperationalError("cannot rollback")},
    ],
    ids=["connection-closed", "transaction-ended", "rollback-raises"],
)
def test_store_commit_failure_with_dead_transaction_keeps_original(
    tmp_path: Path, options: dict[str, object]
) -> None:
    error = sqlite3.OperationalError("commit failed")
    path, wrapped, store = _store_with(tmp_path, error, **options)
    stage, attempt = _stage()
    try:
        with pytest.raises(sqlite3.OperationalError) as caught:
            store.accept_stage(stage, attempt)  # type: ignore[arg-type]
        check(caught.value is error, "the original exception must surface")
    finally:
        wrapped.close()
    check(_accepted_rows(path) == 0, "no row may survive the failed commit")


@pytest.mark.parametrize("error", BASE_ERRORS, ids=_ids(BASE_ERRORS))
def test_store_create_removes_the_file_when_commit_is_interrupted(
    tmp_path: Path, error: BaseException, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "a2.sqlite"
    seen: list[FailingConnection] = []

    def connect(target: Path) -> FailingConnection:
        wrapped = FailingConnection(
            sqlite3.connect(target, isolation_level=None), "COMMIT", error
        )
        seen.append(wrapped)
        return wrapped

    monkeypatch.setattr(A2ResearchStore, "_connect", staticmethod(connect))
    with pytest.raises(BaseException) as caught:
        A2ResearchStore.create(path)
    check(caught.value is error, "the original exception must surface")
    check("ROLLBACK" in seen[0].statements, "rollback must be issued")
    check(not path.exists(), "a half-created store file must be removed")
