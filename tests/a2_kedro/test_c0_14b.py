"""C0-14b: v2 Workset finalizer on a real SQLite file (``tmp_path`` only)."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from msgloom.a2_kedro.contracts.identity import AttemptProof
from msgloom.a2_kedro.contracts.receipt import (
    CompletionReceipt,
    TerminalRoot,
    TransitionBatch,
)
from msgloom.contracts import (
    ResultRef,
    StageResult,
    TerminalStatus,
)
from msgloom.persistence import a2_receipt_store
from msgloom.persistence.a2_acceptance_models import AcceptedStage
from msgloom.persistence.a2_receipt_errors import A2ReceiptConflict, A2ReceiptError
from msgloom.persistence.a2_receipt_store import ReceiptStore
from msgloom.persistence.a2_schema import A2SchemaError, acquire_claim, release_claim
from msgloom.persistence.a2_workset_finalize import (
    A2FinalizeConflict,
    A2FinalizeError,
    FinalizeRequest,
    FinalizeResult,
    finalize_a2_intake_workset_v2,
)
from msgloom.persistence.codecs import encode_result_refs
from msgloom.persistence.records import result_values
from msgloom.persistence.schema_store import LEGACY_TERMINAL_PREFIX
from msgloom.preparation_pipeline.intake_models import (
    PreparationIntakeWorkset,
    workset_claim_key,
)
from tests.a2_kedro.helpers import (
    WORKSET_REF,
    accepted_ref,
    check,
    hexd,
    result_for,
    stage_identity,
    workset,
)
from tests.persistence.test_a2_schema_fixtures import build_schema4, build_schema5, raw

CANARY = "CANARY-PII-9d2e-carol@example.invalid"
COMPLETE = TerminalStatus.COMPLETE
BATCH_REF = accepted_ref("5", "prepared_transitions", "2")
ROW = (
    "SELECT state, terminal_status, result_refs, terminal_claim_token, "
    "terminal_execution_id, terminal_attempt_id "
    "FROM phase1_preparation_intake_worksets"
)
PENDING = ("pending", None, "[]", None, None, None)


class InjectedStop(BaseException):
    """A BaseException that is not an Exception, like KeyboardInterrupt."""


class Hooked:
    """Forwarding connection wrapper: records SQL, fails a statement prefix."""

    def __init__(
        self,
        inner: sqlite3.Connection,
        fail: tuple[str, BaseException] | None = None,
    ) -> None:
        self.inner = inner
        self.fail = fail
        self.seen: list[str] = []

    @property
    def in_transaction(self) -> bool:
        return self.inner.in_transaction

    def execute(self, sql: str, *args: object) -> sqlite3.Cursor:
        self.seen.append(sql)
        if self.fail is not None and sql.startswith(self.fail[0]):
            error, self.fail = self.fail[1], None
            raise error
        return self.inner.execute(sql, *args)  # type: ignore[arg-type]


def attempt_proof(attempt: str = "a1", token: str = "c") -> AttemptProof:
    return AttemptProof(
        execution_id="exec-" + attempt,
        attempt_id=attempt,
        claim_key=workset_claim_key(WORKSET_REF.result_id),
        claim_token_sha256=hexd(token),
    )


def stage_for(ref: ResultRef, char: str, writer: AttemptProof) -> AcceptedStage:
    return AcceptedStage(
        logical_key=ref.result_id,
        output=ref,
        canonical_sha256=hexd(char),
        canonical_byte_count=10,
        semantic_data_id="d-" + ref.result_id[-4:],
        stage_metadata_sha256=hexd("b"),
        lineage_digest=hexd("c"),
        status=COMPLETE,
        limitations_digest=hexd("d"),
        writer=writer,
    )


@dataclass
class Env:
    path: Path
    db: sqlite3.Connection
    store: ReceiptStore
    ws: PreparationIntakeWorkset
    receipt: CompletionReceipt
    accepted: dict[str, AcceptedStage]
    claim_seq: int

    def request(
        self,
        receipt: CompletionReceipt | None = None,
        proof: AttemptProof | None = None,
        ws: PreparationIntakeWorkset | None = None,
    ) -> FinalizeRequest:
        return FinalizeRequest(
            ws or self.ws,
            WORKSET_REF,
            receipt or self.receipt,
            proof or attempt_proof(),
        )

    def rows(self) -> list[tuple[Any, ...]]:
        return [tuple(r) for r in self.db.execute(ROW)]

    def files(self) -> list[str]:
        return sorted(p.name for p in self.store._root.rglob("*") if p.is_file())

    def snapshot(self) -> tuple[Any, ...]:
        names = ("claims", "accepted_stages", "stage_attempts")
        extra = [list(self.db.execute(f"SELECT * FROM phase1_a2_{n}")) for n in names]
        return (self.rows(), extra, self.files())

    def run(self) -> FinalizeResult:
        return finalize_a2_intake_workset_v2(self.db, self.store, self.request())


def make_receipt(
    ws: PreparationIntakeWorkset, policy: str = "policy-1", transitions: bool = True
) -> CompletionReceipt:
    refs = [accepted_ref(str(i + 1), "prepared", "2") for i in range(2)]
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
    batch = TransitionBatch(
        transitions=ws.transitions, result=BATCH_REF, status=COMPLETE
    )
    return CompletionReceipt(
        workset=WORKSET_REF,
        status=COMPLETE,
        policy_version=policy,
        roots=roots,
        transition_batch=batch if transitions else None,
    )


def workset_result() -> StageResult:
    ref = WORKSET_REF
    return result_for(
        stage_identity(), result_id=ref.result_id, kind=ref.kind, schema_version="1"
    )


def insert_row(db: sqlite3.Connection, table: str, values: dict[str, Any]) -> None:
    names = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    db.execute(
        f"INSERT INTO {table} ({names}) VALUES ({marks})", tuple(values.values())
    )


@pytest.fixture
def env(tmp_path: Path) -> Iterator[Env]:
    path = build_schema5(tmp_path / "a2.sqlite")
    (tmp_path / "proofs").mkdir()
    db = raw(path)
    ws = workset(selected=2, transitions=2)
    insert_row(db, "phase1_stage_results", result_values(workset_result()))
    cutoff = ws.cutoff
    insert_row(
        db,
        "phase1_preparation_intake_worksets",
        {
            "result_id": WORKSET_REF.result_id,
            "scope_key": ws.scope.claim_key(),
            "cutoff_release_entry_seq": cutoff.last_release_entry_seq,
            "cutoff_release_entry_digest": cutoff.last_release_entry_digest or "",
            "state": "pending",
            "result_refs": encode_result_refs(()),
        },
    )
    seq = acquire_claim(db, attempt_proof())
    if seq is None:
        pytest.fail("fixture claim must be acquired")
    receipt = make_receipt(ws)
    accepted: dict[str, AcceptedStage] = {}
    for char, ref in zip(
        "abe", [r.result for r in receipt.roots] + [BATCH_REF], strict=True
    ):
        stage = stage_for(ref, char, attempt_proof())
        accepted[ref.result_id] = stage
        insert_row(db, "phase1_a2_accepted_stages", accepted_columns(stage, seq))
    yield Env(path, db, ReceiptStore(tmp_path / "proofs"), ws, receipt, accepted, seq)
    db.close()


def accepted_columns(stage: AcceptedStage, seq: int) -> dict[str, Any]:
    return {
        "logical_key": stage.logical_key,
        "kind": stage.output.kind,
        "schema_version": stage.output.schema_version,
        "status": stage.status.value,
        "canonical_sha256": stage.canonical_sha256,
        "canonical_byte_count": stage.canonical_byte_count,
        "semantic_data_id": stage.semantic_data_id,
        "stage_metadata_sha256": stage.stage_metadata_sha256,
        "lineage_digest": stage.lineage_digest,
        "limitations_digest": stage.limitations_digest,
        "writer_claim_seq": seq,
        "record_sha256": stage.record_sha256(),
        "record_json": stage.record_bytes().decode(),
    }


def refuse(
    env: Env,
    reason: str,
    request: FinalizeRequest | None = None,
    error: type[A2ReceiptError] = A2FinalizeError,
) -> A2ReceiptError:
    before = env.snapshot()
    with pytest.raises(error) as caught:
        finalize_a2_intake_workset_v2(env.db, env.store, request or env.request())
    check(
        caught.value.reason == reason, f"expected {reason}, got {caught.value.reason}"
    )
    check(str(caught.value) == reason, "message must be the reason code only")
    check(caught.value.__cause__ is None, "raw error must not chain")
    check(not env.db.in_transaction, "transaction must be closed")
    check(env.snapshot() == before, "a refused finalize must change nothing")
    return caught.value


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
