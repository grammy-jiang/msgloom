"""
A2 acceptance contract tests (C0-12d); every database lives in tmp_path.

The tests drive the public functions of ``a2_store`` (schema 5 writer),
``a2_sqlite_store`` (isolated research store) and ``a2_acceptance_models``.
They cover replay across attempts, integrity conflicts, concurrent
legitimate claims, cancellation after commit, rollback and crash-style
failures, and the rule that errors never carry payload values. Races use
real threads with one connection each and no sleeps.
"""

from __future__ import annotations

import asyncio
import sqlite3
import threading
from collections.abc import Callable, Iterator
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest

from msgloom.a2_kedro.contracts.identity import AttemptProof, StageIdentity
from msgloom.contracts import Limitation, TerminalStatus
from msgloom.persistence.a2_acceptance_models import (
    AcceptanceConflict,
    accepted_stage_from_result,
)
from msgloom.persistence.a2_schema import acquire_claim, release_claim
from msgloom.persistence.a2_sqlite_store import A2ResearchStore
from msgloom.persistence.a2_store import (
    A2AcceptError,
    PublisherReceipt,
    accept_result,
    get_accepted,
)
from tests.a2_kedro.helpers import check, hexd, proof, result_for, stage_identity
from tests.persistence.test_a2_schema_fixtures import build_schema5, raw

CANARY = "CANARY-PII-9d2e-alice@example.invalid"
STAGE = "SELECT count(*) FROM phase1_a2_accepted_stages"
ATTEMPT = "SELECT outcome FROM phase1_a2_stage_attempts ORDER BY attempt_seq"

#: Differing bodies under one key: name -> (base, changes, expected fields).
#: ``base`` shapes the stored body. ``changes`` shapes the conflicting one.
INCOMPLETE = {"status": TerminalStatus.INCOMPLETE}
BASE_LIMIT = {**INCOMPLETE, "limitations": (Limitation("code-x", "detail-base"),)}
CONFLICTS: dict[str, tuple[dict[str, Any], dict[str, Any], set[str]]] = {
    "status": ({}, INCOMPLETE, {"status"}),
    "limitations": (
        BASE_LIMIT,
        {**INCOMPLETE, "limitations": (Limitation("code-x", CANARY),)},
        {"limitations_digest"},
    ),
    "payload-sha": ({}, {"sha": "b" * 64}, {"canonical_sha256"}),
    "metadata-sha": ({}, {"rule_version": CANARY}, {"stage_metadata_sha256"}),
}


class Tap:
    """
    Forwarding connection wrapper with deterministic statement hooks.

    ``before`` runs right before the first statement with the prefix.
    ``after`` raises the error right after that statement succeeded.
    ``fail`` raises the error instead of the ``nth`` matching statement.
    """

    def __init__(
        self,
        inner: sqlite3.Connection,
        *,
        before: tuple[str, Callable[[], None]] | None = None,
        after: tuple[str, BaseException] | None = None,
        fail: tuple[str, int, BaseException] | None = None,
    ) -> None:
        self.inner = inner
        self._before = before
        self._after = after
        self._fail = fail
        self._seen = 0

    @property
    def in_transaction(self) -> bool:
        return self.inner.in_transaction

    def close(self) -> None:
        self.inner.close()

    def execute(self, sql: str, *args: object) -> sqlite3.Cursor:
        if self._before is not None and sql.startswith(self._before[0]):
            hook, self._before = self._before[1], None
            hook()
        if self._fail is not None and sql.startswith(self._fail[0]):
            self._seen += 1
            if self._seen == self._fail[1]:
                raise self._fail[2]
        cursor = self.inner.execute(sql, *args)  # type: ignore[arg-type]
        if self._after is not None and sql.startswith(self._after[0]):
            error, self._after = self._after[1], None
            raise error
        return cursor


def other_proof(name: str) -> AttemptProof:
    return AttemptProof(
        execution_id=f"exec-{name}",
        attempt_id=name,
        claim_key=f"prepare:{name}",
        claim_token_sha256=hexd("e"),
    )


def receipt(identity: StageIdentity, pub: AttemptProof, **changes: Any):
    result = result_for(identity, attempt=pub.attempt_id, **changes)
    return PublisherReceipt(result, pub)


def rows(path: Path, sql: str) -> list[tuple[Any, ...]]:
    connection = raw(path)
    try:
        return connection.execute(sql).fetchall()
    finally:
        connection.close()


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


def run_threads(targets: list[Callable[[], None]]) -> list[BaseException]:
    """Run targets as real threads; return the errors they raised."""
    errors: list[BaseException] = []

    def guarded(target: Callable[[], None]) -> None:
        try:
            target()
        except BaseException as error:  # noqa: BLE001 - reported to the test
            errors.append(error)

    threads = [threading.Thread(target=guarded, args=(t,)) for t in targets]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    check(not any(t.is_alive() for t in threads), "a worker thread hung")
    return errors


def test_same_key_replayed_across_attempts_is_idempotent(
    db: sqlite3.Connection, path: Path
) -> None:
    identity = stage_identity()
    first = accept_result(db, identity, receipt(identity, proof("w1")))
    check(release_claim(db, 1), "release w1")
    for name in ("w2", "w3"):
        seq = acquire_claim(db, proof(name))
        check(seq is not None, f"{name} claims")
        again = accept_result(db, identity, receipt(identity, proof(name)))
        check(again.outcome == "replayed", f"{name} replays")
        check(again.record == first.record, "stored row is returned")
        check(again.record.writer == proof("w1"), "first writer proof stays")
        check(release_claim(db, seq or 0), f"release {name}")
    check(db.execute(STAGE).fetchone()[0] == 1, "one accepted row")
    check(
        [r[0] for r in db.execute(ATTEMPT)] == ["inserted", "replayed", "replayed"],
        "each attempt is recorded once",
    )


def test_research_store_replay_across_attempts_is_idempotent(tmp_path: Path) -> None:
    identity = stage_identity()
    with A2ResearchStore.create(tmp_path / "r.sqlite") as store:
        records = [
            accepted_stage_from_result(
                identity, result_for(identity, attempt=n), proof(n)
            )
            for n in ("w1", "w2")
        ]
        check(store.accept_stage(records[0], proof("w1")) == "inserted", "insert")
        check(store.accept_stage(records[1], proof("w2")) == "replayed", "replay")
        check(store.accept_stage(records[1], proof("w2")) == "replayed", "again")
        stored = store.get_accepted(identity.logical_key())
        check(stored == records[0], "the first writer proof stays stored")
        check(store.count_accepted() == 1, "one accepted row")
        check(
            store.attempts(identity.logical_key())
            == (
                ("exec-w1", "w1", "inserted"),
                ("exec-w2", "w2", "replayed"),
            ),
            "one attempt row per attempt and outcome",
        )


@pytest.mark.parametrize("case", sorted(CONFLICTS))
def test_changed_body_under_same_key_conflicts(
    case: str, db: sqlite3.Connection, path: Path
) -> None:
    base, changes, expected = CONFLICTS[case]
    identity = stage_identity()
    first = accept_result(db, identity, receipt(identity, proof("w1"), **base))
    check(release_claim(db, 1), "release w1")
    check(acquire_claim(db, proof("w2")) is not None, "w2 claims")
    with pytest.raises(AcceptanceConflict) as caught:
        accept_result(db, identity, receipt(identity, proof("w2"), **changes))
    fields = set(caught.value.fields)
    check(expected <= fields, f"fields {fields} must include {expected}")
    text = str(caught.value) + repr(caught.value) + repr(caught.value.fields)
    check(CANARY not in text and "b" * 64 not in text, "error carries a value")
    check(get_accepted(db, identity.logical_key()) == first.record, "unchanged")
    check(db.execute(STAGE).fetchone()[0] == 1, "no second accepted row")
    check(not db.in_transaction, "no transaction left open")
    kept = rows(path, "SELECT outcome, conflict_fields FROM phase1_a2_stage_attempts")
    check(kept[-1][0] == "conflict", "the conflict attempt is committed")
    check(set(kept[-1][1].split(",")) == fields, "only field names are kept")
    check(CANARY not in repr(kept), "attempt rows carry no payload value")


@pytest.mark.parametrize("case", sorted(CONFLICTS))
def test_research_store_conflicts_on_changed_body(case: str, tmp_path: Path) -> None:
    base, changes, expected = CONFLICTS[case]
    identity = stage_identity()
    with A2ResearchStore.create(tmp_path / "r.sqlite") as store:
        first = accepted_stage_from_result(
            identity, result_for(identity, **base), proof("w1")
        )
        other = accepted_stage_from_result(
            identity, result_for(identity, attempt="w2", **changes), proof("w2")
        )
        store.accept_stage(first, proof("w1"))
        with pytest.raises(AcceptanceConflict) as caught:
            store.accept_stage(other, proof("w2"))
        check(expected <= set(caught.value.fields), "names the differing field")
        check(CANARY not in str(caught.value) + repr(caught.value), "leak")
        check(store.get_accepted(identity.logical_key()) == first, "unchanged")
        check(store.count_accepted() == 1, "no second accepted row")
        outcomes = [row[2] for row in store.attempts(identity.logical_key())]
        check(outcomes == ["inserted", "conflict"], "conflict attempt is kept")


def race_round(path: Path, identity: StageIdentity, workers: int) -> dict[str, str]:
    """Run one barrier-started race of legitimate claims; return outcomes."""
    names = [f"r{n}" for n in range(workers)]
    setup = raw(path)
    try:
        for name in names:
            check(acquire_claim(setup, other_proof(name)) is not None, "claim")
    finally:
        setup.close()
    barrier = threading.Barrier(workers)
    outcomes: dict[str, str] = {}

    def make(name: str) -> Callable[[], None]:
        def work() -> None:
            connection = raw(path)
            try:
                pub = receipt(identity, other_proof(name))
                barrier.wait(timeout=30)
                outcomes[name] = accept_result(connection, identity, pub).outcome
            finally:
                connection.close()

        return work

    errors = run_threads([make(name) for name in names])
    check(not errors, f"unexpected errors: {[type(e).__name__ for e in errors]}")
    return outcomes


@pytest.mark.parametrize("workers", [2, 4])
def test_concurrent_legitimate_claims_never_duplicate(
    workers: int, tmp_path: Path
) -> None:
    identity = stage_identity()
    for round_no in range(3):
        path = build_schema5(tmp_path / f"race-{workers}-{round_no}.sqlite")
        outcomes = race_round(path, identity, workers)
        values = sorted(outcomes.values())
        check(values == ["inserted"] + ["replayed"] * (workers - 1), f"{values}")
        check(rows(path, STAGE) == [(1,)], "exactly one accepted row")
        winner = next(n for n, o in outcomes.items() if o == "inserted")
        stored = raw(path)
        try:
            record = get_accepted(stored, identity.logical_key())
        finally:
            stored.close()
        check(record is not None and record.writer == other_proof(winner), "writer")
        kept = [r[0] for r in rows(path, ATTEMPT)]
        check(sorted(kept) == values, "one attempt row per worker")


def test_claim_race_has_one_winner_and_the_loser_cannot_accept(path: Path) -> None:
    identity = stage_identity()
    barrier = threading.Barrier(2)
    won: dict[str, int | None] = {}

    def make(name: str) -> Callable[[], None]:
        def work() -> None:
            connection = raw(path)
            try:
                barrier.wait(timeout=30)
                won[name] = acquire_claim(connection, proof_for_key(name))
            finally:
                connection.close()

        return work

    def proof_for_key(name: str) -> AttemptProof:
        return other_proof("shared").model_copy(
            update={"execution_id": f"exec-{name}", "attempt_id": name}
        )

    errors = run_threads([make("c1"), make("c2")])
    check(not errors, "no thread error")
    winners = [name for name, seq in won.items() if seq is not None]
    check(len(winners) == 1, f"exactly one claim wins, got {won}")
    loser = "c2" if winners == ["c1"] else "c1"
    with closing(raw(path)) as connection:
        pub = receipt(identity, proof_for_key(loser))
        with pytest.raises(A2AcceptError) as caught:
            accept_result(connection, identity, pub)
        check(caught.value.reason == "claim-foreign", "loser holds no live claim")
        check(connection.execute(STAGE).fetchone()[0] == 0, "nothing written")
        win = receipt(identity, proof_for_key(winners[0]))
        check(accept_result(connection, identity, win).outcome == "inserted", "win")


def test_research_store_threads_never_duplicate(tmp_path: Path) -> None:
    identity = stage_identity()
    path = tmp_path / "race.sqlite"
    A2ResearchStore.create(path).close()
    names = ["t1", "t2", "t3", "t4"]
    barrier = threading.Barrier(len(names))
    outcomes: list[str] = []

    def make(name: str) -> Callable[[], None]:
        def work() -> None:
            record = accepted_stage_from_result(
                identity, result_for(identity, attempt=name), proof(name)
            )
            with A2ResearchStore.open_existing(path) as store:
                barrier.wait(timeout=30)
                outcomes.append(store.accept_stage(record, proof(name)))

        return work

    errors = run_threads([make(name) for name in names])
    check(not errors, f"unexpected errors: {[type(e).__name__ for e in errors]}")
    check(sorted(outcomes) == ["inserted"] + ["replayed"] * 3, f"{outcomes}")
    with A2ResearchStore.open_existing(path) as store:
        check(store.count_accepted() == 1, "exactly one accepted row")
        check(len(store.attempts(identity.logical_key())) == 4, "four attempts")


@pytest.mark.parametrize(
    "stop",
    [asyncio.CancelledError(), KeyboardInterrupt()],
    ids=lambda e: type(e).__name__,
)
def test_cancel_after_commit_keeps_the_row(
    stop: BaseException, db: sqlite3.Connection, path: Path
) -> None:
    identity = stage_identity()
    tapped = Tap(db, after=("COMMIT", stop))
    with pytest.raises(type(stop)):
        accept_result(tapped, identity, receipt(identity, proof("w1")))  # type: ignore[arg-type]
    check(not db.in_transaction, "no transaction left open")
    reader = raw(path)
    try:
        record = get_accepted(reader, identity.logical_key())
        check(record is not None, "the committed row is found by read-back")
        check(record.writer == proof("w1"), "the writer proof is stored")  # type: ignore[union-attr]
    finally:
        reader.close()
    again = accept_result(db, identity, receipt(identity, proof("w1")))
    check(again.outcome == "replayed", "retry after cancel replays")
    check(rows(path, STAGE) == [(1,)], "still one accepted row")


@pytest.mark.parametrize(
    "error", [RuntimeError(CANARY), KeyboardInterrupt()], ids=["error", "interrupt"]
)
def test_failure_after_insert_rolls_back_every_table(
    error: BaseException, db: sqlite3.Connection, path: Path
) -> None:
    identity = stage_identity()
    # The second claim read is the final check, after the row and attempt.
    tapped = Tap(db, fail=("SELECT claim_seq", 2, error))
    with pytest.raises(type(error)):
        accept_result(tapped, identity, receipt(identity, proof("w1")))  # type: ignore[arg-type]
    check(not db.in_transaction, "transaction must be closed")
    check(rows(path, STAGE) == [(0,)], "the accepted row rolled back")
    check(rows(path, ATTEMPT) == [], "the attempt row rolled back")
    check(
        accept_result(db, identity, receipt(identity, proof("w1"))).outcome
        == "inserted",
        "a retry inserts once",
    )


def test_crash_before_commit_leaves_no_trace(path: Path) -> None:
    identity = stage_identity()
    inner = raw(path)
    acquire_claim(inner, proof("w1"))
    seen: list[int] = []

    def crash() -> None:
        # An uncommitted row is invisible to other connections.
        seen.append(rows(path, STAGE)[0][0])
        inner.close()

    tapped = Tap(inner, before=("COMMIT", crash))
    with pytest.raises(A2AcceptError) as caught:
        accept_result(tapped, identity, receipt(identity, proof("w1")))  # type: ignore[arg-type]
    check(seen == [0], "uncommitted data must stay invisible")
    check(caught.value.reason == "commit-failed", "reason code")
    check(caught.value.__cause__ is None, "raw error must not chain")
    check(rows(path, "PRAGMA integrity_check") == [("ok",)], "file stays sound")
    check(rows(path, STAGE) == [(0,)], "no accepted row after the crash")
    check(rows(path, ATTEMPT) == [], "no attempt row after the crash")
    check(
        rows(path, "SELECT state FROM phase1_a2_claims") == [("live",)],
        "the claim is untouched",
    )
    retry = raw(path)
    try:
        done = accept_result(retry, identity, receipt(identity, proof("w1")))
        check(done.outcome == "inserted", "recovery accepts once")
    finally:
        retry.close()


@pytest.mark.parametrize("committed", [True, False], ids=["after", "before"])
def test_research_store_commit_boundary(committed: bool, tmp_path: Path) -> None:
    identity = stage_identity()
    path = tmp_path / "r.sqlite"
    A2ResearchStore.create(path).close()
    record = accepted_stage_from_result(identity, result_for(identity), proof("w1"))
    conn = raw(path)
    stop: BaseException = asyncio.CancelledError()
    tap = Tap(conn, after=("COMMIT", stop))
    if not committed:
        stop = sqlite3.OperationalError(CANARY)
        tap = Tap(conn, fail=("COMMIT", 1, stop))
    store = A2ResearchStore(tap)  # type: ignore[arg-type]
    try:
        with pytest.raises(type(stop)):
            store.accept_stage(record, proof("w1"))
        check(not tap.in_transaction, "transaction must be closed")
    finally:
        store.close()
    with A2ResearchStore.open_existing(path) as reopened:
        key = identity.logical_key()
        check((reopened.get_accepted(key) == record) is committed, "read-back")
        check(reopened.count_accepted() == int(committed), "row count")
        want = "replayed" if committed else "inserted"
        check(reopened.accept_stage(record, proof("w1")) == want, "retry")
        check(reopened.count_accepted() == 1, "one accepted row")


def test_payload_values_never_reach_errors_or_storage(
    db: sqlite3.Connection, path: Path
) -> None:
    identity = stage_identity()
    limited = (Limitation("code-x", CANARY),)
    kwargs = {"status": TerminalStatus.INCOMPLETE, "limitations": limited}
    accept_result(db, identity, receipt(identity, proof("w1"), **kwargs))
    dump = "\n".join(db.iterdump())
    check(CANARY not in dump, "payload text must not be stored")
    with pytest.raises(AcceptanceConflict) as caught:
        accept_result(db, identity, receipt(identity, proof("w1")))
    check(CANARY not in str(caught.value) + repr(caught.value), "conflict leak")
    wrong = stage_identity(code_version=CANARY)
    mismatch = PublisherReceipt(result_for(identity, attempt="w1"), proof("w1"))
    with pytest.raises(A2AcceptError) as refused:
        accept_result(db, wrong, mismatch)
    text = str(refused.value) + repr(refused.value)
    check(refused.value.reason == "plan-mismatch", "reason code")
    check(CANARY not in text and str(path) not in text, "plan error leak")
    tapped = Tap(db, fail=("SELECT claim_seq", 1, sqlite3.OperationalError(CANARY)))
    with pytest.raises(A2AcceptError) as database:
        accept_result(tapped, identity, receipt(identity, proof("w1")))  # type: ignore[arg-type]
    check(CANARY not in str(database.value) + repr(database.value), "sql leak")
    check(database.value.__cause__ is None, "raw error must not chain")
    check("record_json" not in str(database.value), "no column names")
