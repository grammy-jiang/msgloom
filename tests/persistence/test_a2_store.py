"""
A2 guarded acceptance writer (C0-12b); every database lives in tmp_path.

Failures are injected through a forwarding connection wrapper, so no test
depends on timing or on the host. Two real connections cover the races.
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from msgloom.a2_kedro.contracts.identity import AttemptProof, StageIdentity
from msgloom.contracts import Limitation, ResultRef, TerminalStatus
from msgloom.persistence.a2_acceptance_models import AcceptanceConflict
from msgloom.persistence.a2_schema import (
    A2SchemaError,
    acquire_claim,
    release_claim,
)
from msgloom.persistence.a2_store import (
    A2AcceptError,
    PublisherReceipt,
    accept_result,
    get_accepted,
)
from tests.a2_kedro.helpers import (
    accepted_ref,
    check,
    hexd,
    proof,
    result_for,
    stage_identity,
)
from tests.persistence.test_a2_schema_fixtures import build_schema4, build_schema5, raw

CANARY = "CANARY-PII-7c1f-bob@example.invalid"
STAGE = "SELECT count(*) FROM phase1_a2_accepted_stages"
ATTEMPT = "SELECT count(*) FROM phase1_a2_stage_attempts"


class InjectedStop(BaseException):
    """A BaseException that is not an Exception, like KeyboardInterrupt."""


class Hooked:
    """
    Forwarding connection wrapper with one-shot hooks on a statement prefix.

    ``before`` runs once right before the first matching statement.
    ``fail`` raises the given error instead of forwarding that statement.
    """

    def __init__(
        self,
        inner: sqlite3.Connection,
        *,
        before: tuple[str, Callable[[], None]] | None = None,
        fail: tuple[str, BaseException] | None = None,
    ) -> None:
        self.inner = inner
        self._before = before
        self._fail = fail

    @property
    def in_transaction(self) -> bool:
        return self.inner.in_transaction

    def execute(self, sql: str, *args: object) -> sqlite3.Cursor:
        if self._before is not None and sql.startswith(self._before[0]):
            hook, self._before = self._before[1], None
            hook()
        if self._fail is not None and sql.startswith(self._fail[0]):
            error, self._fail = self._fail[1], None
            raise error
        return self.inner.execute(sql, *args)  # type: ignore[arg-type]

    def executemany(self, sql: str, rows: object) -> sqlite3.Cursor:
        return self.inner.executemany(sql, rows)  # type: ignore[arg-type]


@pytest.fixture
def path(tmp_path: Path) -> Path:
    return build_schema5(tmp_path / "a2.sqlite")


@pytest.fixture
def db(path: Path) -> Iterator[sqlite3.Connection]:
    connection = raw(path)
    if acquire_claim(connection, proof("w1")) is None:
        pytest.fail("fixture claim must be acquired")
    yield connection
    connection.close()


def receipt(
    identity: StageIdentity, attempt: str = "w1", **changes: object
) -> PublisherReceipt:
    return PublisherReceipt(
        result_for(identity, attempt=attempt, **changes), proof(attempt)
    )


def count(db: sqlite3.Connection, sql: str = STAGE) -> int:
    return db.execute(sql).fetchone()[0]


def refused(
    db: object, identity: StageIdentity, pub: PublisherReceipt, reason: str
) -> None:
    with pytest.raises(A2AcceptError) as caught:
        accept_result(db, identity, pub)  # type: ignore[arg-type]
    check(caught.value.reason == reason, f"expected {reason}")
    check(str(caught.value) == reason, "message must be the reason code only")
    check(caught.value.__cause__ is None, "raw error must not chain")


def test_insert_then_identical_replay_is_idempotent(db: sqlite3.Connection) -> None:
    identity = stage_identity()
    first = accept_result(db, identity, receipt(identity))
    check(first.outcome == "inserted", "first write inserts")
    again = accept_result(db, identity, receipt(identity))
    check(again.outcome == "replayed", "identical replay replays")
    check(again.record == first.record, "replay returns the stored row")
    check(get_accepted(db, identity.logical_key()) == first.record, "stored row")
    check(count(db) == 1, "exactly one accepted row")
    check(first.record.writer == proof("w1"), "publisher proof is the writer")
    check(not db.in_transaction, "no transaction left open")
    outcomes = [
        r[0] for r in db.execute("SELECT outcome FROM phase1_a2_stage_attempts")
    ]
    check(outcomes == ["inserted", "replayed"], "attempts record both calls")


def test_replay_by_another_live_claim_keeps_first_writer(
    db: sqlite3.Connection,
) -> None:
    identity = stage_identity()
    first = accept_result(db, identity, receipt(identity))
    check(release_claim(db, 1), "release w1")
    check(acquire_claim(db, proof("w2")) is not None, "w2 takes the claim key")
    again = accept_result(db, identity, receipt(identity, "w2"))
    check(again.outcome == "replayed", "legitimate second claim replays")
    check(again.record.writer == first.record.writer, "first writer stays")
    check(count(db) == 1, "still one row")


def test_different_body_under_same_key_is_rejected(db: sqlite3.Connection) -> None:
    identity = stage_identity()
    first = accept_result(db, identity, receipt(identity))
    other = receipt(identity, sha="b" * 64)
    with pytest.raises(AcceptanceConflict) as caught:
        accept_result(db, identity, other)
    check("canonical_sha256" in caught.value.fields, "names the field")
    check("b" * 64 not in str(caught.value), "no value in the error")
    check(get_accepted(db, identity.logical_key()) == first.record, "unchanged")
    check(count(db) == 1, "no second row")
    rows = db.execute("SELECT outcome FROM phase1_a2_stage_attempts").fetchall()
    check(("conflict",) in rows, "conflict attempt is committed")
    status = receipt(
        identity,
        status=TerminalStatus.INCOMPLETE,
        limitations=(Limitation("code-x", "detail-x"),),
    )
    with pytest.raises(AcceptanceConflict):
        accept_result(db, identity, status)


def test_claim_must_be_live_and_the_publishers(db: sqlite3.Connection) -> None:
    identity = stage_identity()
    refused(db, identity, receipt(identity, "w2"), "claim-foreign")
    forged = AttemptProof(
        execution_id="exec-w1",
        attempt_id="w1",
        claim_key="prepare:ws",
        claim_token_sha256=hexd("f"),
    )
    refused(
        db,
        identity,
        PublisherReceipt(result_for(identity, attempt="w1"), forged),
        "claim-foreign",
    )
    other_key = proof("w1").model_copy(update={"claim_key": "prepare:none"})
    refused(
        db,
        identity,
        PublisherReceipt(result_for(identity, attempt="w1"), other_key),
        "claim-not-live",
    )
    check(release_claim(db, 1), "release the claim")
    refused(db, identity, receipt(identity), "claim-not-live")
    check(count(db) == 0 and count(db, ATTEMPT) == 0, "nothing written")
    check(not db.in_transaction, "no transaction left open")


def test_required_inputs_must_be_accepted_stages(db: sqlite3.Connection) -> None:
    root = stage_identity()
    child = stage_identity(stage_kind="parsed_parts", upstream=(root.result_ref(),))
    refused(db, child, receipt(child), "required-input-missing")
    wrong = stage_identity(
        stage_kind="parsed_parts",
        upstream=(accepted_ref("1", "zones", "1"),),
    )
    accept_result(db, root, receipt(root))
    check(count(db) == 1, "only the root is stored")
    refused(db, wrong, receipt(wrong), "required-input-missing")
    bad = stage_identity(
        stage_kind="parsed_parts",
        upstream=(ResultRef(root.logical_key(), "zones", "1"),),
    )
    refused(db, bad, receipt(bad), "required-input-mismatch")
    check(accept_result(db, child, receipt(child)).outcome == "inserted", "chain")
    check(count(db) == 2, "root and child")


def test_wrong_receipt_binding_and_plan_are_refused(db: sqlite3.Connection) -> None:
    identity = stage_identity()
    mixed = PublisherReceipt(result_for(identity, attempt="w2"), proof("w1"))
    refused(db, identity, mixed, "receipt-binding-mismatch")
    plan = stage_identity(code_version="code-other")
    refused(db, plan, receipt(identity), "plan-mismatch")
    foreign = result_for(identity, attempt="w1", result_id="a2-accepted:" + hexd("7"))
    refused(db, identity, PublisherReceipt(foreign, proof("w1")), "plan-mismatch")
    check(count(db) == 0 and count(db, ATTEMPT) == 0, "nothing written")


def test_failures_inside_the_transaction_roll_back(path: Path) -> None:
    identity = stage_identity()
    cases: list[tuple[str, BaseException]] = [
        ("INSERT INTO phase1_a2_accepted_stages", InjectedStop()),
        ("INSERT OR IGNORE INTO phase1_a2_stage_attempts", KeyboardInterrupt()),
        ("INSERT OR IGNORE INTO phase1_a2_stage_attempts", RuntimeError(CANARY)),
    ]
    for prefix, error in cases:
        inner = raw(path)
        try:
            acquire_claim(inner, proof("w1"))
            wrapped = Hooked(inner, fail=(prefix, error))
            with pytest.raises(type(error)):
                accept_result(wrapped, identity, receipt(identity))  # type: ignore[arg-type]
            check(not inner.in_transaction, "transaction must be closed")
            check(count(inner) == 0, "stage row must roll back")
            check(count(inner, ATTEMPT) == 0, "attempt row must roll back")
            check(
                accept_result(inner, identity, receipt(identity)).outcome == "inserted",
                "retry works",
            )
            inner.execute("DELETE FROM phase1_a2_stage_attempts")
            inner.execute("DELETE FROM phase1_a2_accepted_stages")
        finally:
            inner.close()


def test_failed_commit_rolls_back_without_leaking(db: sqlite3.Connection) -> None:
    identity = stage_identity()
    error = sqlite3.OperationalError(f"{CANARY} forced failure")
    wrapped = Hooked(db, fail=("COMMIT", error))
    with pytest.raises(A2AcceptError) as caught:
        accept_result(wrapped, identity, receipt(identity))  # type: ignore[arg-type]
    check(caught.value.reason == "commit-failed", "reason code")
    check(CANARY not in repr(caught.value) + str(caught.value), "leak")
    check(caught.value.__cause__ is None, "raw error must not chain")
    check(not db.in_transaction, "transaction must be closed")
    check(count(db) == 0, "row must roll back")


def test_sql_error_maps_to_a_code_without_leak(db: sqlite3.Connection) -> None:
    identity = stage_identity()
    error = sqlite3.OperationalError(f"{CANARY} disk")
    wrapped = Hooked(db, fail=("SELECT claim_seq", error))
    refused(wrapped, identity, receipt(identity), "database-error")
    check(not db.in_transaction and count(db) == 0, "rolled back")


def test_claim_released_before_the_lock_is_refused(path: Path) -> None:
    identity = stage_identity()
    inner = raw(path)
    try:
        acquire_claim(inner, proof("w1"))

        def release_elsewhere() -> None:
            other = raw(path)
            try:
                release_claim(other, 1)
            finally:
                other.close()

        wrapped = Hooked(inner, before=("BEGIN IMMEDIATE", release_elsewhere))
        refused(wrapped, identity, receipt(identity), "claim-not-live")
        check(count(inner) == 0, "no row without a live claim")
    finally:
        inner.close()


def test_claim_cannot_change_between_check_and_insert(path: Path) -> None:
    identity = stage_identity()
    inner = raw(path)
    errors: list[str] = []
    try:
        acquire_claim(inner, proof("w1"))

        def release_elsewhere() -> None:
            other = sqlite3.connect(path, timeout=0.05, isolation_level=None)
            try:
                release_claim(other, 1)
            except sqlite3.OperationalError as error:
                errors.append(str(error))
            finally:
                other.close()

        wrapped = Hooked(
            inner, before=("INSERT INTO phase1_a2_accepted_stages", release_elsewhere)
        )
        done = accept_result(wrapped, identity, receipt(identity))  # type: ignore[arg-type]
        check(done.outcome == "inserted", "the writer holds the lock")
        check(len(errors) == 1 and "locked" in errors[0], "second writer is locked out")
        state = inner.execute("SELECT state FROM phase1_a2_claims").fetchone()[0]
        check(state == "live", "claim stayed live through the insert")
    finally:
        inner.close()


def _other_proof(name: str) -> AttemptProof:
    return AttemptProof(
        execution_id=f"exec-{name}",
        attempt_id=name,
        claim_key=f"prepare:{name}",
        claim_token_sha256=hexd("e"),
    )


def _race(path: Path, shas: tuple[str, str]) -> list[object]:
    identity = stage_identity()
    names = ("r1", "r2")
    setup = raw(path)
    try:
        for name in names:
            acquire_claim(setup, _other_proof(name))
    finally:
        setup.close()
    barrier = threading.Barrier(2)
    results: list[object] = []

    def worker(name: str, sha: str) -> None:
        connection = raw(path)
        try:
            pub = PublisherReceipt(
                result_for(identity, attempt=name, sha=sha), _other_proof(name)
            )
            barrier.wait(timeout=10)
            try:
                results.append(accept_result(connection, identity, pub).outcome)
            except AcceptanceConflict as error:
                results.append(error)
        finally:
            connection.close()

    threads = [
        threading.Thread(target=worker, args=(n, s))
        for n, s in zip(names, shas, strict=True)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    return results


def test_two_writers_with_one_body_produce_one_row(path: Path) -> None:
    results = _race(path, ("a" * 64, "a" * 64))
    check(sorted(map(str, results)) == ["inserted", "replayed"], f"got {results}")
    check_db = raw(path)
    try:
        check(count(check_db) == 1, "one accepted row")
    finally:
        check_db.close()


def test_two_writers_with_two_bodies_produce_one_row_and_one_conflict(
    path: Path,
) -> None:
    results = _race(path, ("a" * 64, "b" * 64))
    kinds = sorted(type(item).__name__ for item in results)
    check(kinds == ["AcceptanceConflict", "str"], f"got {results}")
    check_db = raw(path)
    try:
        check(count(check_db) == 1, "one accepted row")
        rows = check_db.execute("SELECT outcome FROM phase1_a2_stage_attempts")
        check(("conflict",) in rows.fetchall(), "conflict attempt kept")
    finally:
        check_db.close()


def test_errors_never_carry_ids_tokens_or_paths(path: Path) -> None:
    identity = stage_identity()
    secret = AttemptProof(
        execution_id=f"exec-{CANARY}",
        attempt_id=CANARY,
        claim_key=f"prepare:{CANARY}",
        claim_token_sha256=hexd("d"),
    )
    pub = PublisherReceipt(result_for(identity, attempt=CANARY), secret)
    connection = raw(path)
    try:
        for target in (pub, PublisherReceipt(result_for(identity), secret)):
            with pytest.raises(A2AcceptError) as caught:
                accept_result(connection, identity, target)
            text = repr(caught.value) + str(caught.value)
            check(CANARY not in text, "claim data leaked")
            check(str(path) not in text and "a2.sqlite" not in text, "path leaked")
    finally:
        connection.close()


def test_schema4_and_open_transactions_are_refused(tmp_path: Path) -> None:
    identity = stage_identity()
    old = raw(build_schema4(tmp_path / "old.sqlite"))
    try:
        with pytest.raises(A2SchemaError) as caught:
            accept_result(old, identity, receipt(identity))
        check(caught.value.reason == "migration-required", "needs schema 5")
        check(not old.in_transaction, "no transaction left open")
    finally:
        old.close()
    current = raw(build_schema5(tmp_path / "new.sqlite"))
    try:
        current.execute("BEGIN")
        refused(current, identity, receipt(identity), "open-transaction")
        current.execute("ROLLBACK")
    finally:
        current.close()


def test_a_tampered_stored_row_fails_closed(db: sqlite3.Connection) -> None:
    identity = stage_identity()
    accept_result(db, identity, receipt(identity))
    db.execute("UPDATE phase1_a2_accepted_stages SET record_json = record_json || ' '")
    refused(db, identity, receipt(identity), "stored-record-corrupt")
    with pytest.raises(A2AcceptError):
        get_accepted(db, identity.logical_key())
