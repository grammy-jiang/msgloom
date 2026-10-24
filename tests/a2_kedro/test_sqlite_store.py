"""Isolated SQLite append-or-verify store; every database lives in tmp_path."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

import pytest

from msgloom.a2_kedro.contracts.receipt import CompletionReceipt, TerminalRoot
from msgloom.contracts import Limitation, ResultRef, TerminalStatus
from msgloom.persistence.a2_acceptance_models import (
    AcceptanceConflict,
    AcceptedStage,
    accepted_stage_from_result,
)
from msgloom.persistence.a2_sqlite_store import A2ResearchStore, A2StoreError
from tests.a2_kedro.helpers import (
    WORKSET_REF,
    accepted_ref,
    check,
    hexd,
    proof,
    result_for,
    stage_identity,
    workset,
)

COMPLETE, INCOMPLETE = TerminalStatus.COMPLETE, TerminalStatus.INCOMPLETE


@pytest.fixture
def store_path(tmp_path: Path) -> Path:
    return tmp_path / "a2.sqlite"


@pytest.fixture
def store(store_path: Path):
    with A2ResearchStore.create(store_path) as opened:
        yield opened


def raw(path: Path) -> sqlite3.Connection:
    """Open a second, autocommit connection for direct SQL checks."""
    return sqlite3.connect(path, isolation_level=None)


def record(attempt: str = "a1", **result_changes) -> AcceptedStage:
    identity = stage_identity()
    return accepted_stage_from_result(
        identity,
        result_for(identity, attempt=attempt, **result_changes),
        proof(attempt),
    )


def stage_for(ref: ResultRef, status: TerminalStatus = COMPLETE) -> AcceptedStage:
    return AcceptedStage(
        logical_key=ref.result_id,
        output=ref,
        canonical_sha256="a" * 64,
        canonical_byte_count=10,
        semantic_data_id="d-" + ref.result_id[-4:],
        stage_metadata_sha256="b" * 64,
        lineage_digest="c" * 64,
        status=status,
        limitations_digest="d" * 64,
        writer=proof(),
    )


def test_create_refuses_existing_paths_and_missing_directory(tmp_path: Path) -> None:
    existing = tmp_path / "real.sqlite"
    sqlite3.connect(existing).execute(
        "CREATE TABLE phase1_marker (x)"
    ).connection.close()
    before = existing.read_bytes()
    with pytest.raises(A2StoreError, match="existing path"):
        A2ResearchStore.create(existing)
    with pytest.raises(A2StoreError, match="existing path"):
        A2ResearchStore.create(tmp_path)
    with pytest.raises(A2StoreError, match="directory"):
        A2ResearchStore.create(tmp_path / "missing" / "a2.sqlite")
    check(existing.read_bytes() == before, "existing database must stay unchanged")


def test_open_existing_requires_our_marker(tmp_path: Path) -> None:
    foreign = tmp_path / "foreign.sqlite"
    sqlite3.connect(foreign).execute("CREATE TABLE other (x)").connection.close()
    with pytest.raises(A2StoreError, match="not an A2 research store"):
        A2ResearchStore.open_existing(foreign)
    garbage = tmp_path / "garbage.sqlite"
    garbage.write_bytes(b"not a database" * 100)
    with pytest.raises(A2StoreError):
        A2ResearchStore.open_existing(garbage)
    with pytest.raises(A2StoreError, match="does not exist"):
        A2ResearchStore.open_existing(tmp_path / "none.sqlite")
    own = tmp_path / "own.sqlite"
    A2ResearchStore.create(own).close()
    with A2ResearchStore.open_existing(own) as reopened:
        check(reopened.count_accepted() == 0, "reopened empty store")


def test_only_research_tables_exist(tmp_path: Path) -> None:
    path = tmp_path / "a2.sqlite"
    A2ResearchStore.create(path).close()
    with sqlite3.connect(path) as db:
        names = {
            row[0]
            for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    names.discard("sqlite_sequence")
    check(all(name.startswith("a2c0_") for name in names), f"unexpected tables {names}")


def test_insert_then_equal_replay_by_a_new_attempt(store: A2ResearchStore) -> None:
    first = record("a1")
    check(store.accept_stage(first, proof("a1")) == "inserted", "insert")
    check(store.accept_stage(first, proof("a1")) == "replayed", "same attempt replay")
    check(
        store.accept_stage(record("a2"), proof("a2")) == "replayed",
        "new attempt replay",
    )
    check(store.count_accepted() == 1, "exactly one accepted row")
    check(store.get_accepted(first.logical_key) == first, "original proof kept")
    check(
        store.attempts(first.logical_key)
        == (
            ("exec-a1", "a1", "inserted"),
            ("exec-a1", "a1", "replayed"),
            ("exec-a2", "a2", "replayed"),
        ),
        "attempt history",
    )


def test_conflict_fails_closed_keeps_original_and_records_attempts(
    store: A2ResearchStore,
) -> None:
    first = record("a1")
    store.accept_stage(first, proof("a1"))
    conflicts = [
        record("a2", sha="b" * 64),
        record("a3", status=INCOMPLETE, limitations=(Limitation("l", "d"),)),
    ]
    for other in conflicts:
        with pytest.raises(AcceptanceConflict):
            store.accept_stage(other, other.writer)
    check(store.get_accepted(first.logical_key) == first, "original unchanged")
    check(store.count_accepted() == 1, "no second accepted row")
    outcomes = [row[2] for row in store.attempts(first.logical_key)]
    check(outcomes == ["inserted", "conflict", "conflict"], f"attempt rows {outcomes}")


def test_two_legitimate_claims_racing_produce_one_accepted_row(tmp_path: Path) -> None:
    path = tmp_path / "race.sqlite"
    A2ResearchStore.create(path).close()
    barrier = threading.Barrier(2)
    results: list[str] = []

    def writer(attempt: str) -> None:
        with A2ResearchStore.open_existing(path) as mine:
            barrier.wait()
            try:
                results.append(mine.accept_stage(record(attempt), proof(attempt)))
            except AcceptanceConflict:
                results.append("conflict")

    threads = [threading.Thread(target=writer, args=(name,)) for name in ("r1", "r2")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    check(sorted(results) == ["inserted", "replayed"], f"race outcomes {results}")
    with A2ResearchStore.open_existing(path) as check_store:
        check(check_store.count_accepted() == 1, "single accepted row after race")


def test_failure_inside_the_transaction_rolls_everything_back(
    store: A2ResearchStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("simulated crash after the stage insert")

    first = record("a1")
    monkeypatch.setattr(store, "_attempt", explode)
    with pytest.raises(RuntimeError):
        store.accept_stage(first, proof("a1"))
    monkeypatch.undo()
    check(store.count_accepted() == 0, "stage insert must roll back")
    check(store.attempts(first.logical_key) == (), "no attempt row")
    check(store.accept_stage(first, proof("a1")) == "inserted", "retry succeeds")


def test_database_checks_reject_direct_malformed_rows(
    store: A2ResearchStore, store_path: Path
) -> None:
    db = raw(store_path)
    insert = (
        "INSERT INTO a2c0_accepted_stage VALUES (?, ?, 'prepared', '2', ?, ?, '{}')"
    )
    good_key = "a2-accepted:" + hexd("1")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(insert, ("short", "short", "complete", hexd("1")))
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            insert,
            (
                "a2-accepted:" + "G" * 64,
                "a2-accepted:" + "G" * 64,
                "complete",
                hexd("1"),
            ),
        )
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(insert, (good_key, good_key, "failed", hexd("1")))
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(insert, (good_key, good_key, "complete", "xyz"))
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            insert, (good_key, "a2-accepted:" + hexd("2"), "complete", hexd("1"))
        )
    db.execute(insert, (good_key, good_key, "complete", hexd("1")))
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(insert, (good_key, good_key, "complete", hexd("1")))


def test_tampered_stored_record_is_detected(
    store: A2ResearchStore, store_path: Path
) -> None:
    first = record("a1")
    store.accept_stage(first, proof("a1"))
    raw(store_path).execute(
        "UPDATE a2c0_accepted_stage SET record_json = replace(record_json, 'a', 'b')"
    )
    with pytest.raises(A2StoreError, match="fails its digest"):
        store.get_accepted(first.logical_key)
    with pytest.raises(A2StoreError, match="fails its digest"):
        store.accept_stage(first, proof("a1"))


def make_receipt(
    store: A2ResearchStore,
    *,
    store_second: bool = True,
    status: TerminalStatus = COMPLETE,
):
    ws = workset(2)
    refs = [accepted_ref("1", "prepared", "2"), accepted_ref("2", "prepared", "2")]
    store.accept_stage(stage_for(refs[0]), proof())
    if store_second:
        store.accept_stage(stage_for(refs[1]), proof())
    roots = tuple(
        TerminalRoot(
            workset_selection_index=i,
            result=ref,
            disposition="prepared",
            status=COMPLETE,
            selection=ws.selections[i],
        )
        for i, ref in enumerate(refs)
    )
    return CompletionReceipt(
        workset=WORKSET_REF, status=status, policy_version="policy-1", roots=roots
    )


def receipt_rows(path: Path) -> int:
    return raw(path).execute("SELECT count(*) FROM a2c0_receipt").fetchone()[0]


def test_receipt_needs_an_accepted_proof_for_every_root(
    store: A2ResearchStore, store_path: Path
) -> None:
    missing = make_receipt(store, store_second=False)
    with pytest.raises(A2StoreError, match="no accepted proof"):
        store.append_receipt(missing)
    check(receipt_rows(store_path) == 0, "no receipt row")


def test_receipt_disagreeing_with_proof_status_is_refused(
    store: A2ResearchStore, store_path: Path
) -> None:
    receipt = make_receipt(store)
    ref = receipt.roots[0].result
    raw(store_path).execute(
        "DELETE FROM a2c0_accepted_stage WHERE logical_key = ?", (ref.result_id,)
    )
    store.accept_stage(stage_for(ref, INCOMPLETE), proof())
    with pytest.raises(A2StoreError, match="disagrees"):
        store.append_receipt(receipt)


def test_receipt_append_or_verify(store: A2ResearchStore, store_path: Path) -> None:
    receipt = make_receipt(store)
    check(store.append_receipt(receipt) == "inserted", "insert")
    check(store.append_receipt(receipt) == "replayed", "replay")
    check(
        CompletionReceipt.model_validate_json(receipt.model_dump_json()) == receipt,
        "json",
    )
    changed = CompletionReceipt(
        workset=WORKSET_REF,
        status=COMPLETE,
        policy_version="policy-1",
        roots=receipt.roots[:1],
    )
    with pytest.raises(A2StoreError, match="conflicting receipt"):
        store.append_receipt(changed)
    check(receipt_rows(store_path) == 1, "original receipt unchanged")
