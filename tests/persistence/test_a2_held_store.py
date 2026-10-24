"""
A2 held index (C0-13); every database lives in tmp_path.

Failures are injected through a forwarding connection wrapper. Two real
connections cover the concurrent writers.
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Callable, Iterator
from dataclasses import fields
from pathlib import Path

import pytest

from msgloom.a2_kedro.contracts.held import HeldReason, InputDisposition
from msgloom.contracts import ResultRef, VersionRef
from msgloom.persistence.a2_held_store import (
    MAX_LIMIT,
    TABLE,
    A2HeldConflict,
    A2HeldError,
    HeldCursor,
    HeldStatus,
    ensure_held_index,
    get_held,
    held_status,
    list_held,
    put_held,
    put_many,
)
from msgloom.persistence.a2_schema import A2SchemaError, SchemaState, classify_schema
from tests.a2_kedro.helpers import (
    WORKSET_REF,
    check,
    hexd,
    mutate,
    root_for,
    workset,
)
from tests.persistence.test_a2_schema_fixtures import build_schema4, build_schema5, raw

CANARY = "CANARY-PII-9a3e-bob@example.invalid"
OTHER_REF = ResultRef("intake-workset:" + hexd("8"), "preparation_intake_workset", "1")
WS = workset(selected=8)
COUNT = f"SELECT count(*) FROM {TABLE}"


class InjectedStop(BaseException):
    """A BaseException that is not an Exception, like KeyboardInterrupt."""


class Hooked:
    """Forwarding wrapper: records statements; one-shot failure by prefix."""

    def __init__(
        self,
        inner: sqlite3.Connection,
        fail: tuple[str, BaseException] | None = None,
    ) -> None:
        self.inner = inner
        self.statements: list[str] = []
        self._fail = fail

    @property
    def in_transaction(self) -> bool:
        return self.inner.in_transaction

    def execute(self, sql: str, *args: object) -> sqlite3.Cursor:
        self.statements.append(sql)
        if self._fail is not None and sql.startswith(self._fail[0]):
            error, self._fail = self._fail[1], None
            raise error
        return self.inner.execute(sql, *args)  # type: ignore[arg-type]


@pytest.fixture
def path(tmp_path: Path) -> Path:
    target = tmp_path / "held.sqlite"
    db = raw(target)
    try:
        ensure_held_index(db)
    finally:
        db.close()
    return target


@pytest.fixture
def db(path: Path) -> Iterator[sqlite3.Connection]:
    connection = raw(path)
    yield connection
    connection.close()


def held(
    index: int,
    reason: HeldReason = HeldReason.PARSER_UNSUPPORTED,
    config: str = "config-1",
) -> InputDisposition:
    return InputDisposition.from_root(
        root_for(WS, index),
        reason,
        configuration_version=config,
        code_version="code-1",
    )


def baseline(index: int = 9) -> InputDisposition:
    return InputDisposition(
        selected=ResultRef(f"baseline-sel-{index}", "collected_selection", "1"),
        workset_index=index,
        selection_sha256=hexd("4"),
        reason=HeldReason.PROOF_MISSING,
        configuration_version=CANARY,
        code_version=CANARY,
        baseline_source=VersionRef("source", "id-1", "v1"),
        baseline_approval=CANARY,
    )


def count(db: sqlite3.Connection) -> int:
    return db.execute(COUNT).fetchone()[0]


def indexes(page) -> list[int]:
    return [row.workset_index for row in page.rows]


def test_ensure_is_idempotent_and_exact(tmp_path: Path) -> None:
    db = raw(tmp_path / "a.sqlite")
    try:
        check(ensure_held_index(db) == "created", "first call creates")
        check(ensure_held_index(db) == "present", "second call is a no-op")
        db.execute(f"DROP TABLE {TABLE}")
        db.execute(f"CREATE TABLE {TABLE} (workset_id TEXT)")
        with pytest.raises(A2HeldError) as caught:
            ensure_held_index(db)
        check(caught.value.reason == "held-index-definition-mismatch", "drift")
        with pytest.raises(A2HeldError) as caught:
            list_held(db, WORKSET_REF, limit=1)
        check(caught.value.reason == "held-index-definition-mismatch", "fail closed")
    finally:
        db.close()


def test_store_functions_never_create_the_table(tmp_path: Path) -> None:
    db = raw(tmp_path / "empty.sqlite")
    try:
        with pytest.raises(A2HeldError) as caught:
            put_held(db, WORKSET_REF, held(0))
        check(caught.value.reason == "held-index-missing", "no implicit create")
        check(
            db.execute("SELECT count(*) FROM sqlite_schema").fetchone()[0] == 0, "empty"
        )
    finally:
        db.close()


def test_phase1_files_need_an_ack_and_exact_schema5(tmp_path: Path) -> None:
    s5 = build_schema5(tmp_path / "s5.sqlite")
    db = raw(s5)
    try:
        with pytest.raises(A2HeldError) as caught:
            ensure_held_index(db)
        check(caught.value.reason == "phase1-database-refused", "refused")
        check(ensure_held_index(db, pending_integration_ack=True) == "created", "ack")
        check(classify_schema(db) is SchemaState.SCHEMA5, "still exact schema 5")
        put_held(db, WORKSET_REF, held(0))
        check(count(db) == 1, "coexists with schema 5")
    finally:
        db.close()
    s4 = raw(build_schema4(tmp_path / "s4.sqlite"))
    try:
        with pytest.raises(A2SchemaError) as caught:
            ensure_held_index(s4, pending_integration_ack=True)
        check(caught.value.reason == "migration-required", "schema 4")
        names = {r[0] for r in s4.execute("SELECT name FROM sqlite_schema")}
        check(TABLE not in names, "nothing created on schema 4")
    finally:
        s4.close()


def test_worksets_are_isolated(db: sqlite3.Connection) -> None:
    put_many(db, WORKSET_REF, [held(0), held(1)])
    put_many(db, OTHER_REF, [held(0, HeldReason.INPUT_LIMIT), held(2)])
    check(count(db) == 4, "four rows")
    a = list_held(db, WORKSET_REF, limit=10)
    b = list_held(db, OTHER_REF, limit=10)
    check(indexes(a) == [0, 1] and indexes(b) == [0, 2], "each sees its own")
    check(b.rows[0].reason is HeldReason.INPUT_LIMIT, "same index, other record")
    check(held_status(db, WORKSET_REF).total == 2, "status is scoped")
    check(held_status(db, OTHER_REF).by_reason[0][0] == "input_limit", "status b")
    foreign = ResultRef("intake-workset:" + hexd("7"), WORKSET_REF.kind, "1")
    check(list_held(db, foreign, limit=10).rows == (), "unknown workset is empty")
    check(get_held(db, foreign, 0) is None, "get is scoped")
    check(get_held(db, WORKSET_REF, 0) == held(0), "get returns the record")
    with pytest.raises(A2HeldError):
        list_held(db, ResultRef("x", "collected_selection", "1"), limit=1)
    with pytest.raises(A2HeldError):
        list_held(db, None, limit=1)  # type: ignore[arg-type]


def test_limit_and_cursor_bound_every_page(db: sqlite3.Connection) -> None:
    put_many(db, WORKSET_REF, [held(i) for i in (5, 3, 0, 7, 1, 6, 2)])
    seen: list[list[int]] = []
    cursor = None
    while True:
        page = list_held(db, WORKSET_REF, limit=3, after=cursor)
        check(len(page.rows) <= 3, "page above limit")
        seen.append(indexes(page))
        if page.next_cursor is None:
            break
        cursor = page.next_cursor
    check(seen == [[0, 1, 2], [3, 5, 6], [7]], f"pages {seen}")
    exact = list_held(db, WORKSET_REF, limit=7)
    check(len(exact.rows) == 7 and exact.next_cursor is None, "exact fit ends")
    one = list_held(db, WORKSET_REF, limit=1)
    check(one.next_cursor == HeldCursor(WORKSET_REF.result_id, 0), "keyset cursor")
    for bad in (0, -1, MAX_LIMIT + 1, True, None, "5", 2.0):
        with pytest.raises(A2HeldError):
            list_held(db, WORKSET_REF, limit=bad)  # type: ignore[arg-type]
    check(len(list_held(db, WORKSET_REF, limit=MAX_LIMIT).rows) == 7, "max limit")
    other = HeldCursor(OTHER_REF.result_id, 0)
    with pytest.raises(A2HeldError) as caught:
        list_held(db, WORKSET_REF, limit=2, after=other)
    check(caught.value.reason == "cursor-foreign", "cursor is workset bound")
    with pytest.raises(A2HeldError):
        list_held(
            db, WORKSET_REF, limit=2, after=HeldCursor(WORKSET_REF.result_id, 5000)
        )


def test_cursor_is_stable_when_rows_arrive_between_pages(
    db: sqlite3.Connection,
) -> None:
    put_many(db, WORKSET_REF, [held(0), held(2), held(4)])
    first = list_held(db, WORKSET_REF, limit=2)
    put_held(db, WORKSET_REF, held(1))
    put_held(db, WORKSET_REF, held(6))
    rest = list_held(db, WORKSET_REF, limit=5, after=first.next_cursor)
    check(indexes(first) == [0, 2] and indexes(rest) == [4, 6], "no repeat")


def test_reason_filter_pages_only_that_reason(db: sqlite3.Connection) -> None:
    items = [
        held(i, HeldReason.INPUT_LIMIT if i % 2 else HeldReason.PROOF_MISSING)
        for i in range(6)
    ]
    put_many(db, WORKSET_REF, items)
    page = list_held(db, WORKSET_REF, limit=2, reason=HeldReason.INPUT_LIMIT)
    rest = list_held(
        db, WORKSET_REF, limit=2, reason=HeldReason.INPUT_LIMIT, after=page.next_cursor
    )
    check(indexes(page) == [1, 3] and indexes(rest) == [5], "filtered pages")
    check(rest.next_cursor is None, "last page")


def test_replay_is_idempotent_and_batches_are_atomic(db: sqlite3.Connection) -> None:
    check(put_held(db, WORKSET_REF, held(0)) == "inserted", "insert")
    check(put_held(db, WORKSET_REF, held(0)) == "replayed", "replay")
    check(count(db) == 1, "one row")
    outcomes = put_many(db, WORKSET_REF, [held(0), held(1)])
    check(outcomes == ("replayed", "inserted"), "mixed batch")
    clash = held(2, HeldReason.INPUT_LIMIT)
    other = held(0, HeldReason.INPUT_LIMIT)
    with pytest.raises(A2HeldConflict):
        put_many(db, WORKSET_REF, [clash, other])
    check(count(db) == 2, "the failed batch left nothing behind")
    for size in (0, 1025):
        with pytest.raises(A2HeldError):
            put_many(db, WORKSET_REF, [held(0)] * size)
    with pytest.raises(A2HeldError):
        put_held(db, WORKSET_REF, "not a record")  # type: ignore[arg-type]


def test_conflicting_writes_are_rejected_without_change(db: sqlite3.Connection) -> None:
    put_held(db, WORKSET_REF, held(0))
    before = db.execute(f"SELECT * FROM {TABLE}").fetchall()
    with pytest.raises(A2HeldConflict) as caught:
        put_held(db, WORKSET_REF, held(0, HeldReason.INPUT_LIMIT, CANARY))
    check(set(caught.value.fields) == {"reason", "configuration_version"}, "fields")
    check(CANARY not in repr(caught.value) + str(caught.value), "no value in error")
    moved = mutate(held(0), workset_index=4)
    with pytest.raises(A2HeldConflict) as again:
        put_held(db, WORKSET_REF, moved)
    check("workset_index" in again.value.fields, "same selection, other index")
    check(db.execute(f"SELECT * FROM {TABLE}").fetchall() == before, "unchanged")
    check(not db.in_transaction, "no transaction left open")


def test_status_view_has_only_closed_values_and_counts(db: sqlite3.Connection) -> None:
    put_many(
        db,
        WORKSET_REF,
        [
            held(0, config=CANARY),
            held(1, HeldReason.INPUT_LIMIT, CANARY),
            held(2, HeldReason.INPUT_LIMIT),
            baseline(),
        ],
    )
    spy = Hooked(db)
    status = held_status(spy, WORKSET_REF)  # type: ignore[arg-type]
    check(
        status.total == 4 and status.baseline == 1 and status.incremental == 3, "counts"
    )
    check(
        status.by_reason
        == (("input_limit", 2), ("parser_unsupported", 1), ("proof_missing", 1)),
        f"reasons {status.by_reason}",
    )
    check(status.by_repair_class == (("operator_repair", 4),), "repair class")
    check(CANARY not in repr(status), "status leaked record text")
    check(
        {f.name for f in fields(HeldStatus)}
        == {"total", "baseline", "incremental", "by_reason", "by_repair_class"},
        "status shape is closed",
    )
    sql = " ".join(spy.statements)
    for column in ("record_json", "selected_id", "selection_sha256", "version"):
        check(column not in sql.split("FROM")[0], f"status selects {column}")
    check("record_json" not in sql, "status never reads the record")
    page = list_held(db, WORKSET_REF, limit=10)
    check(CANARY not in repr(page), "list rows carry no version or approval text")
    check(held_status(db, OTHER_REF).total == 0, "empty workset")


@pytest.mark.parametrize(
    "error", [InjectedStop(), KeyboardInterrupt(), RuntimeError(CANARY)]
)
def test_failure_inside_a_write_rolls_back(path: Path, error: BaseException) -> None:
    inner = raw(path)
    try:
        wrapped = Hooked(inner, ("INSERT INTO", error))
        with pytest.raises(type(error)):
            put_many(wrapped, WORKSET_REF, [held(0), held(1)])  # type: ignore[arg-type]
        check(not inner.in_transaction, "transaction must be closed")
        check(count(inner) == 0, "nothing stored")
        check(put_held(inner, WORKSET_REF, held(0)) == "inserted", "retry works")
    finally:
        inner.close()


def test_failed_commit_rolls_back_without_leaking(path: Path) -> None:
    inner = raw(path)
    try:
        boom = sqlite3.OperationalError(f"{CANARY} forced")
        wrapped = Hooked(inner, ("COMMIT", boom))
        with pytest.raises(A2HeldError) as caught:
            put_held(wrapped, WORKSET_REF, held(0))  # type: ignore[arg-type]
        check(caught.value.reason == "commit-failed", "reason")
        check(CANARY not in repr(caught.value) + str(caught.value), "leak")
        check(caught.value.__cause__ is None, "no chain")
        check(not inner.in_transaction and count(inner) == 0, "rolled back")
    finally:
        inner.close()


def _race(path: Path, items: tuple[InputDisposition, InputDisposition]) -> list[object]:
    barrier = threading.Barrier(2)
    results: list[object] = []

    def worker(item: InputDisposition) -> None:
        connection = raw(path)
        try:
            barrier.wait(timeout=10)
            try:
                results.append(put_held(connection, WORKSET_REF, item))
            except A2HeldConflict as error:
                results.append(error)
        finally:
            connection.close()

    threads = [threading.Thread(target=worker, args=(item,)) for item in items]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    return results


def test_concurrent_identical_writers_produce_one_row(path: Path) -> None:
    results = _race(path, (held(0), held(0)))
    check(sorted(map(str, results)) == ["inserted", "replayed"], f"got {results}")
    db = raw(path)
    try:
        check(count(db) == 1, "one row")
    finally:
        db.close()


def test_concurrent_conflicting_writers_produce_one_conflict(path: Path) -> None:
    results = _race(path, (held(0), held(0, HeldReason.INPUT_LIMIT)))
    kinds = sorted(type(item).__name__ for item in results)
    check(kinds == ["A2HeldConflict", "str"], f"got {results}")
    db = raw(path)
    try:
        check(count(db) == 1, "one row")
    finally:
        db.close()


def test_tampered_rows_fail_closed(db: sqlite3.Connection) -> None:
    put_held(db, WORKSET_REF, held(0))
    db.execute(f"UPDATE {TABLE} SET record_json = record_json || ' '")
    for action in (
        lambda: get_held(db, WORKSET_REF, 0),
        lambda: put_held(db, WORKSET_REF, held(0)),
    ):
        _expect_corrupt(action)


def _expect_corrupt(action: Callable[[], object]) -> None:
    with pytest.raises(A2HeldError) as caught:
        action()
    check(caught.value.reason == "stored-record-corrupt", "corrupt row refused")


def test_check_constraints_reject_direct_bad_rows(db: sqlite3.Connection) -> None:
    bad = (
        WORKSET_REF.result_id,
        0,
        "s",
        "z" * 64,
        "other",
        "operator_repair",
        0,
        hexd("1"),
        "{}",
    )
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(f"INSERT INTO {TABLE} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", bad)
