"""C0-14b: v2 Workset finalizer on a real SQLite file (``tmp_path`` only)."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from msgloom.a2_kedro.contracts.identity import AttemptProof
from msgloom.contracts import TerminalStatus
from msgloom.persistence import a2_receipt_store
from msgloom.persistence.a2_receipt_errors import A2ReceiptConflict, A2ReceiptError
from msgloom.persistence.a2_receipt_store import ReceiptStore
from msgloom.persistence.a2_schema import A2SchemaError, release_claim
from msgloom.persistence.a2_workset_finalize import (
    A2FinalizeConflict,
    A2FinalizeError,
    FinalizeRequest,
    finalize_a2_intake_workset_v2,
)
from msgloom.persistence.codecs import encode_result_refs
from msgloom.persistence.schema_store import LEGACY_TERMINAL_PREFIX
from tests.a2_kedro.helpers import WORKSET_REF, check, hexd, workset
from tests.a2_kedro.helpers_c0_14b import (
    BATCH_REF,
    CANARY,
    PENDING,
    Env,
    Hooked,
    InjectedStop,
    accepted_columns,
    attempt_proof,
    build_env,
    insert_row,
    make_receipt,
    refuse,
)
from tests.persistence.test_a2_schema_fixtures import build_schema4, raw


@pytest.fixture
def env(tmp_path: Path) -> Iterator[Env]:
    yield from build_env(tmp_path)


def test_happy_path_finalizes_row_and_writes_proof(env: Env) -> None:
    check(env.rows() == [PENDING], "starts pending")
    result = env.run()
    check(result.outcome == "finalized", "outcome")
    (row,) = env.rows()
    refs = [r.result for r in env.receipt.roots] + [BATCH_REF]
    want = (
        "terminal",
        "complete",
        encode_result_refs(refs),
        hexd("c"),
        "exec-a1",
        "a1",
    )
    check(row == want, "terminal columns")
    pending = env.db.execute(
        "SELECT count(*) FROM phase1_preparation_intake_worksets WHERE state = 'pending'"
    ).fetchone()[0]
    check(pending == 0, "no pending row is left")
    stored = env.store.get_receipt_proof(WORKSET_REF)
    check(stored is not None and stored.receipt_sha256 == env.receipt.digest(), "proof")
    check(len(env.files()) == 1, "exactly one proof file")
    check(not env.db.in_transaction, "committed")


def test_recheck_reads_no_payload_tables(env: Env) -> None:
    hooked = Hooked(env.db)
    finalize_a2_intake_workset_v2(hooked, env.store, env.request())  # type: ignore[arg-type]
    for sql in hooked.seen:
        check("phase1_semantic_data" not in sql, "payload table must not be read")
    check(hooked.seen[0] == "BEGIN IMMEDIATE", "one immediate transaction")
    check(hooked.seen.count("COMMIT") == 1, "one commit")


def test_identical_replay_is_idempotent(env: Env) -> None:
    env.run()
    after = env.snapshot()
    check(env.run().outcome == "replayed", "replay outcome")
    check(env.snapshot() == after, "replay changes nothing")


def test_replay_restores_a_missing_proof_file(env: Env) -> None:
    env.run()
    for path in env.store._root.rglob("receipt-proof.json"):
        path.unlink()
    rows = env.rows()
    check(env.run().outcome == "replayed", "replay outcome")
    check(env.rows() == rows and len(env.files()) == 1, "file restored")


def test_other_claim_after_finalize_is_a_conflict(env: Env) -> None:
    env.run()
    request = env.request(proof=attempt_proof("a2", "d"))
    error = refuse(env, "terminal-conflict", request, A2FinalizeConflict)
    fields = getattr(error, "fields", ())
    want = ("terminal_claim_token", "terminal_execution_id", "terminal_attempt_id")
    check(fields == want, "conflict names the changed columns only")


def test_other_receipt_after_finalize_is_a_conflict(env: Env) -> None:
    env.run()
    other = env.request(receipt=make_receipt(env.ws, policy="policy-2"))
    refuse(env, "receipt-proof-conflict", other, A2ReceiptConflict)


def test_v1_terminal_row_is_refused(env: Env) -> None:
    env.db.execute(
        "UPDATE phase1_preparation_intake_worksets SET state = 'terminal', "
        "terminal_status = 'complete', terminal_claim_token = 'raw-v1-token', "
        "terminal_execution_id = 'e', terminal_attempt_id = 'a'"
    )
    refuse(env, "terminal-conflict", error=A2FinalizeConflict)


ROW_FAULTS = [
    ("DELETE FROM phase1_preparation_intake_worksets", "workset-not-admitted"),
    ("DELETE FROM phase1_stage_results", "workset-result-missing"),
    (
        "UPDATE phase1_preparation_intake_worksets SET scope_key = 'other'",
        "workset-scope-mismatch",
    ),
    (
        "UPDATE phase1_preparation_intake_worksets SET cutoff_release_entry_seq = 9",
        "workset-cutoff-mismatch",
    ),
]


@pytest.mark.parametrize(("sql", "reason"), ROW_FAULTS)
def test_unknown_or_foreign_workset_row_is_refused(
    env: Env, sql: str, reason: str
) -> None:
    env.db.execute(sql)
    refuse(env, reason)


def test_legacy_recovery_hold_is_refused(env: Env) -> None:
    insert_row(
        env.db,
        "phase1_schema_metadata",
        {"key": LEGACY_TERMINAL_PREFIX + WORKSET_REF.result_id, "value": "scope-x"},
    )
    refuse(env, "legacy-recovery-hold")


def test_released_and_foreign_claims_are_refused(env: Env) -> None:
    refuse(env, "claim-foreign", env.request(proof=attempt_proof("a9", "e")))
    release_claim(env.db, env.claim_seq)
    refuse(env, "claim-not-live")


def test_receipt_that_does_not_cover_the_workset_is_refused(env: Env) -> None:
    short = make_receipt(env.ws, transitions=False)
    refuse(env, "receipt-not-covering-workset", env.request(receipt=short))
    smaller = workset(selected=1, transitions=2)
    refuse(env, "receipt-not-covering-workset", env.request(ws=smaller))


def test_wrong_claim_key_is_refused(env: Env) -> None:
    data = {**attempt_proof().model_dump(), "claim_key": "prepare:other"}
    refuse(env, "claim-key-mismatch", env.request(proof=AttemptProof(**data)))


def test_missing_or_changed_accepted_stage_is_refused(env: Env) -> None:
    key = BATCH_REF.result_id
    env.db.execute("PRAGMA foreign_keys = OFF")
    env.db.execute(
        "DELETE FROM phase1_a2_accepted_stages WHERE logical_key = ?", (key,)
    )
    refuse(env, "accepted-result-missing", error=A2ReceiptError)
    stage = env.accepted[key].model_copy(update={"status": TerminalStatus.INCOMPLETE})
    insert_row(
        env.db, "phase1_a2_accepted_stages", accepted_columns(stage, env.claim_seq)
    )
    refuse(env, "accepted-result-mismatch", error=A2ReceiptError)


def test_schema4_file_is_refused(tmp_path: Path) -> None:
    path = build_schema4(tmp_path / "v4.sqlite")
    (tmp_path / "proofs").mkdir()
    db = raw(path)
    ws = workset(selected=2, transitions=2)
    request = FinalizeRequest(ws, WORKSET_REF, make_receipt(ws), attempt_proof())
    try:
        with pytest.raises(A2SchemaError):
            finalize_a2_intake_workset_v2(
                db, ReceiptStore(tmp_path / "proofs"), request
            )
        check(not db.in_transaction, "rolled back")
    finally:
        db.close()


@pytest.mark.parametrize("prefix", ["UPDATE phase1_preparation", "COMMIT"])
def test_sql_failure_rolls_everything_back(env: Env, prefix: str) -> None:
    before = env.snapshot()
    error = sqlite3.OperationalError("disk I/O error " + CANARY)
    hooked = Hooked(env.db, fail=(prefix, error))
    with pytest.raises(A2FinalizeError) as caught:
        finalize_a2_intake_workset_v2(hooked, env.store, env.request())  # type: ignore[arg-type]
    check(CANARY not in repr(caught.value) + str(caught.value), "canary leaked")
    check(not env.db.in_transaction, "rolled back")
    check(env.rows() == [PENDING], "row is still pending")
    if prefix == "UPDATE phase1_preparation":
        check(env.snapshot() == before, "nothing written, no proof file")
    check(env.run().outcome == "finalized", "a retry succeeds")
    check(len(env.files()) == 1, "one proof after the retry")


def test_proof_write_failure_leaves_row_pending(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    def failing(*_args: object) -> bool:
        raise A2ReceiptError("write-failed")

    monkeypatch.setattr(a2_receipt_store, "create_once", failing)
    refuse(env, "write-failed", error=A2ReceiptError)
    check(env.rows() == [PENDING], "row is still pending")
    monkeypatch.undo()
    check(env.run().outcome == "finalized", "a retry succeeds")


def test_crash_between_proof_write_and_commit(env: Env) -> None:
    hooked = Hooked(env.db, fail=("COMMIT", InjectedStop()))
    with pytest.raises(InjectedStop):
        finalize_a2_intake_workset_v2(hooked, env.store, env.request())  # type: ignore[arg-type]
    check(not env.db.in_transaction, "the open transaction was rolled back")
    check(len(env.files()) == 1, "the orphan proof is the exact write-once proof")
    stored = env.store.get_receipt_proof(WORKSET_REF)
    # A different receipt cannot take over the orphan; the row stays pending.
    other_request = env.request(receipt=make_receipt(env.ws, policy="policy-2"))
    refuse(env, "receipt-proof-conflict", other_request, A2ReceiptConflict)
    check(env.run().outcome == "finalized", "the same receipt completes")
    check(env.store.get_receipt_proof(WORKSET_REF) == stored, "proof unchanged")


def test_crash_before_update_leaves_nothing(env: Env) -> None:
    before = env.snapshot()
    hooked = Hooked(env.db, fail=("UPDATE phase1_preparation", InjectedStop()))
    with pytest.raises(InjectedStop):
        finalize_a2_intake_workset_v2(hooked, env.store, env.request())  # type: ignore[arg-type]
    check(env.snapshot() == before, "no row change and no proof file")
    check(not env.db.in_transaction, "rolled back")


def test_open_transaction_is_refused(env: Env) -> None:
    env.db.execute("BEGIN")
    with pytest.raises(A2FinalizeError) as caught:
        env.run()
    check(caught.value.reason == "open-transaction", "reason")
    check(env.db.in_transaction, "the caller's own transaction is left alone")
    env.db.execute("ROLLBACK")
    check(env.rows() == [PENDING], "nothing written")


def test_canary_never_appears_in_errors_or_repr(env: Env) -> None:
    request = env.request(receipt=make_receipt(env.ws, policy=CANARY))
    check(CANARY not in repr(request), "request repr must hide data")
    env.db.execute("UPDATE phase1_preparation_intake_worksets SET scope_key = 'x'")
    with pytest.raises(A2ReceiptError) as scope:
        finalize_a2_intake_workset_v2(env.db, env.store, request)
    env.db.execute(
        "UPDATE phase1_preparation_intake_worksets SET scope_key = ?",
        (env.ws.scope.claim_key(),),
    )
    result = finalize_a2_intake_workset_v2(env.db, env.store, request)
    other = env.request(receipt=make_receipt(env.ws, policy="policy-2"))
    with pytest.raises(A2ReceiptError) as conflict:
        finalize_a2_intake_workset_v2(env.db, env.store, other)
    for text in (repr(result), repr(scope.value), repr(conflict.value)):
        check(CANARY not in text, "canary leaked")
    check(CANARY not in str(conflict.value.args), "canary leaked into args")
