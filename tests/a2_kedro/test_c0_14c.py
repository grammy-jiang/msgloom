"""C0-14c: v1/v2 writer fence and producer binding (``tmp_path`` SQLite only)."""

from __future__ import annotations

import asyncio
import sqlite3
import threading
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from msgloom.a2_kedro.contracts.identity import AttemptProof
from msgloom.a2_kedro.contracts.receipt import CompletionReceipt, TerminalRoot
from msgloom.contracts import ResultRef, TerminalStatus
from msgloom.persistence import a2_producer_binding as binding
from msgloom.persistence import intake_store
from msgloom.persistence.a2_producer_binding import (
    A2ProducerFenceError,
    attempt_producer,
    bind_workset_producers,
    finalize_a2_workset_fenced,
    require_v1_writer_allowed,
    stage_producer,
    workset_owner,
)
from msgloom.persistence.a2_receipt_errors import A2ReceiptError
from msgloom.persistence.a2_receipt_store import ReceiptStore
from msgloom.persistence.a2_schema import acquire_claim, migrate_schema4_to_v5
from msgloom.persistence.a2_workset_finalize import A2FinalizeError, FinalizeRequest
from msgloom.persistence.errors import ImmutableRecordError
from msgloom.persistence.store import Phase1Store
from msgloom.preparation_pipeline.intake_models import (
    PreparationIntakeWorkset,
    workset_claim_key,
)
from tests.a2_kedro.helpers import WORKSET_REF, accepted_ref, check, hexd
from tests.a2_kedro.helpers_c0_14b import (
    ROW,
    Env,
    Hooked,
    InjectedStop,
    attempt_proof,
    build_env,
    insert_row,
    publish,
    saved_result,
    stage_for,
)
from tests.persistence.test_a2_schema_fixtures import GATE, raw
from tests.phase1_foundation import intake_completion_helpers as c
from tests.phase1_foundation import intake_helpers as h

KEY = workset_claim_key(WORKSET_REF.result_id)
ROW_PENDING = ("pending", None, "[]", None, None, None)
TERMINAL_V1 = (
    "UPDATE phase1_preparation_intake_worksets SET state = 'terminal', "
    "terminal_status = 'complete', terminal_claim_token = 'raw-v1-token', "
    "terminal_execution_id = 'exec-v1', terminal_attempt_id = 'a-v1'"
)


@pytest.fixture
def env(tmp_path: Path) -> Iterator[Env]:
    yield from build_env(tmp_path)


def legacy_attempt(db: sqlite3.Connection, key: str = KEY, execution: str = "exec-v1"):
    insert_row(
        db,
        "phase1_claim_attempts",
        {
            "claim_token": "raw-v1-token",
            "claim_key": key,
            "claim_kind": "prepare",
            "execution_id": execution,
            "attempt_id": "a-v1",
            "started_at": "2026-01-01T00:00:00",
            "external_effect": "none",
        },
    )


def fenced(env: Env, request: FinalizeRequest | None = None):
    return finalize_a2_workset_fenced(env.db, env.store, request or env.request())


def refused(env: Env, reason: str, request: FinalizeRequest | None = None) -> None:
    before = env.snapshot()
    with pytest.raises(A2ProducerFenceError) as caught:
        fenced(env, request)
    error = caught.value
    check(error.reason == reason, f"expected {reason}, got {error.reason}")
    check(str(error) == reason and error.__cause__ is None, "fixed reason only")
    check(isinstance(error, (A2ReceiptError, ImmutableRecordError)), "typed")
    check(not env.db.in_transaction, "transaction must be closed")
    check(env.snapshot() == before, "a refusal must change nothing")


def test_v2_wins_then_replay_and_binding(env: Env) -> None:
    check(fenced(env).outcome == "finalized", "first finalize")
    check(workset_owner(env.db, WORKSET_REF.result_id) == "v2", "v2 owns")
    check(fenced(env).outcome == "replayed", "v2 replay passes the fence")
    info = bind_workset_producers(env.db, WORKSET_REF.result_id)
    check(info.owner == "v2", "binding owner")
    check([(a.attempt_id, a.producer) for a in info.attempts] == [("a1", "v2")], "v2")
    check("exec-a1" not in repr(info) and "a1" not in repr(info.attempts[0]), "redact")


def test_pending_workset_has_no_owner(env: Env) -> None:
    check(workset_owner(env.db, WORKSET_REF.result_id) is None, "pending")
    check(workset_owner(env.db, "missing-id") is None, "unknown id has no owner")


def test_v1_finalized_workset_is_refused_for_v2(env: Env) -> None:
    env.db.execute(TERMINAL_V1)
    legacy_attempt(env.db)
    check(workset_owner(env.db, WORKSET_REF.result_id) == "legacy", "legacy owns")
    refused(env, "legacy-finalized")


def test_late_v1_row_is_mapped_by_the_lock_conflict(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(binding, "_precheck", lambda db, request: None)
    env.db.execute(TERMINAL_V1)
    legacy_attempt(env.db)
    refused(env, "legacy-finalized")


def test_forged_terminal_owner_is_refused(env: Env) -> None:
    env.db.execute(TERMINAL_V1.replace("raw-v1-token", hexd("f")))
    refused(env, "terminal-owner-unproven")


def test_terminal_row_proven_by_both_producers_is_ambiguous(env: Env) -> None:
    fenced(env)
    insert_row(
        env.db,
        "phase1_claim_attempts",
        {
            "claim_token": hexd("c"),
            "claim_key": KEY,
            "claim_kind": "prepare",
            "execution_id": "exec-a1",
            "attempt_id": "a1",
            "started_at": "2026-01-01T00:00:00",
            "external_effect": "none",
        },
    )
    refused(env, "producer-ambiguous")


def test_wrong_workset_id_is_refused_by_the_finalizer(env: Env) -> None:
    other = ResultRef("intake-workset:" + hexd("8"), WORKSET_REF.kind, "1")
    request = FinalizeRequest(env.ws, other, env.receipt, attempt_proof())
    before = env.snapshot()
    with pytest.raises(A2FinalizeError) as caught:
        fenced(env, request)
    check(not isinstance(caught.value, A2ProducerFenceError), "finalizer error")
    check(caught.value.reason == "receipt-not-covering-workset", "reason")
    check(env.snapshot() == before, "nothing changed")


def test_missing_root_proof_is_refused(env: Env) -> None:
    first = env.receipt.roots[0].result.result_id
    env.db.execute(
        "DELETE FROM phase1_a2_stage_attempts WHERE logical_key = ?", (first,)
    )
    env.db.execute(
        "DELETE FROM phase1_a2_accepted_stages WHERE logical_key = ?", (first,)
    )
    refused(env, "stage-unproven")
    env.db.execute("DELETE FROM phase1_stage_results WHERE result_id = ?", (first,))
    refused(env, "stage-unproven")


def test_legacy_attempt_stage_is_not_v2_proven(env: Env) -> None:
    first = env.receipt.roots[0].result.result_id
    env.db.execute(
        "DELETE FROM phase1_a2_stage_attempts WHERE logical_key = ?", (first,)
    )
    env.db.execute(
        "DELETE FROM phase1_a2_accepted_stages WHERE logical_key = ?", (first,)
    )
    env.db.execute(
        "UPDATE phase1_stage_results SET execution_id = 'exec-v1', "
        "attempt_id = 'a-v1' WHERE result_id = ?",
        (first,),
    )
    legacy_attempt(env.db, key="legacy-stage-key")
    check(stage_producer(env.db, first) == "legacy", "legacy stage")
    check(stage_producer(env.db, env.receipt.roots[1].result.result_id) == "v2", "v2")
    refused(env, "legacy-attempt-stage")


def test_mixed_attempt_history_is_allowed_and_bound(env: Env) -> None:
    legacy_attempt(env.db)
    info = bind_workset_producers(env.db, WORKSET_REF.result_id)
    got = {(a.execution_id, a.producer) for a in info.attempts}
    check(got == {("exec-v1", "legacy"), ("exec-a1", "v2")}, "both producers bound")
    check(info.owner is None, "still pending")
    check(fenced(env).outcome == "finalized", "v2 proof stages finalize")


def test_attempt_claimed_by_both_producers_is_refused(env: Env) -> None:
    legacy_attempt(env.db, key="other", execution="exec-a1")
    env.db.execute("UPDATE phase1_claim_attempts SET attempt_id = 'a1'")
    with pytest.raises(A2ProducerFenceError):
        attempt_producer(env.db, "exec-a1", "a1")
    refused(env, "attempt-ambiguous")


def test_unknown_attempt_has_no_producer(env: Env) -> None:
    check(attempt_producer(env.db, "nobody", "none") is None, "unknown attempt")
    check(attempt_producer(env.db, "exec-a1", "a1") == "v2", "v2 attempt")


def test_fence_check_failure_leaves_no_write(env: Env) -> None:
    hooked = Hooked(
        env.db, ("SELECT state, terminal_claim_token", sqlite3.OperationalError("x"))
    )
    before = env.snapshot()
    with pytest.raises(A2ProducerFenceError) as caught:
        finalize_a2_workset_fenced(hooked, env.store, env.request())  # type: ignore[arg-type]
    check(caught.value.reason == "fence-check-failed", "fixed reason")
    check(caught.value.__cause__ is None, "raw error must not chain")
    check(not any(s.startswith(("BEGIN", "UPDATE")) for s in hooked.seen), "no write")
    check(env.snapshot() == before and env.rows() == [ROW_PENDING], "unchanged")
    check(fenced(env).outcome == "finalized", "retry works")


def test_base_exception_after_the_fence_rolls_back(env: Env) -> None:
    hooked = Hooked(env.db, ("UPDATE phase1_preparation", InjectedStop()))
    before = env.snapshot()
    with pytest.raises(InjectedStop):
        finalize_a2_workset_fenced(hooked, env.store, env.request())  # type: ignore[arg-type]
    check(not env.db.in_transaction and env.snapshot() == before, "rolled back")


def test_v1_hook_reads_only_the_schema_when_no_a2_table(tmp_path: Path) -> None:
    store = h.store(tmp_path / "v1.db")
    store.close()
    db = raw(tmp_path / "v1.db")
    hooked = Hooked(db)
    require_v1_writer_allowed(hooked, "any-id")
    check(hooked.seen == [binding._A2_TABLE], "one sqlite_master read only")
    db.close()


class Gated(Hooked):
    """Block the first statement until the test opens the gate."""

    def __init__(self, inner: sqlite3.Connection) -> None:
        super().__init__(inner)
        self.entered = threading.Event()
        self.gate = threading.Event()
        self.done = threading.Event()

    def execute(self, sql: str, *args: object) -> sqlite3.Cursor:
        self.entered.set()
        if not self.gate.wait(10):
            raise InjectedStop
        return super().execute(sql, *args)


def run_fenced(env: Env, hooked_for: Callable[[sqlite3.Connection], Hooked]) -> None:
    """Run the fenced finalizer on a fresh connection owned by this thread."""
    db = raw(env.path)
    hooked = hooked_for(db)
    try:
        finalize_a2_workset_fenced(hooked, env.store, env.request())  # type: ignore[arg-type]
    finally:
        db.close()
        if isinstance(hooked, Gated):
            hooked.done.set()


def test_cancel_during_the_transaction_rolls_back(env: Env) -> None:
    def hooked_for(db: sqlite3.Connection) -> Hooked:
        return Hooked(db, ("UPDATE phase1_preparation", asyncio.CancelledError()))

    async def main() -> bool:
        task = asyncio.ensure_future(asyncio.to_thread(run_fenced, env, hooked_for))
        await asyncio.wait([task])
        return task.cancelled()

    check(asyncio.run(main()), "the real task ended cancelled")
    check(env.rows() == [ROW_PENDING] and not env.files(), "pending, no proof file")


def test_cancel_while_the_fence_check_waits_never_tears_the_row(env: Env) -> None:
    holder: list[Gated] = []

    def hooked_for(db: sqlite3.Connection) -> Hooked:
        holder.append(Gated(db))
        return holder[0]

    async def main() -> None:
        task = asyncio.ensure_future(asyncio.to_thread(run_fenced, env, hooked_for))
        while not holder:
            await asyncio.sleep(0.01)
        await asyncio.to_thread(holder[0].entered.wait, 10)
        task.cancel()
        await asyncio.wait([task])
        check(task.cancelled(), "task cancelled while the check waits")
        holder[0].gate.set()
        await asyncio.to_thread(holder[0].done.wait, 20)

    asyncio.run(main())
    check(env.rows()[0][0] == "terminal" and len(env.files()) == 1, "whole, not torn")


@dataclass
class World:
    path: Path
    store: Phase1Store
    value: PreparationIntakeWorkset
    ref: ResultRef
    refs: tuple[ResultRef, ...]
    owner: Any
    receipts: ReceiptStore
    receipt: CompletionReceipt
    proof: AttemptProof


def make_world(tmp_path: Path) -> World:
    """A real v1 Workset on a migrated file, plus v2 proof for the same row."""
    path = tmp_path / "world.sqlite"
    store = h.store(path)
    value, saved, owner, selections = c.admit(store, count=2)
    refs = c.replay(store, owner, selections).result_refs
    db = raw(path)
    migrate_schema4_to_v5(db, GATE)
    ref = ResultRef(saved.result_id, saved.kind, saved.schema_version)
    proof = AttemptProof(
        execution_id="exec-a1",
        attempt_id="a1",
        claim_key=workset_claim_key(ref.result_id),
        claim_token_sha256=hexd("c"),
    )
    seq = acquire_claim(db, proof)
    if seq is None:
        pytest.fail("v2 claim must be acquired")
    roots = []
    for index, char in enumerate("ab"):
        result = accepted_ref(str(index + 1), "prepared", "2")
        publish(
            db, stage_for(result, char, proof), seq, saved_result(result, char, proof)
        )
        roots.append(
            TerminalRoot(
                workset_selection_index=index,
                result=result,
                disposition="prepared",
                status=TerminalStatus.COMPLETE,
                selection=value.selections[index],
            )
        )
    db.close()
    (tmp_path / "proofs").mkdir()
    receipt = CompletionReceipt(
        workset=ref,
        status=TerminalStatus.COMPLETE,
        policy_version="policy-1",
        roots=tuple(roots),
    )
    proofs = ReceiptStore(tmp_path / "proofs")
    return World(path, store, value, ref, refs, owner, proofs, receipt, proof)


def v1_finalize(world: World) -> None:
    world.store.finalize_preparation_intake_workset(
        world.ref.result_id, TerminalStatus.INCOMPLETE, world.refs, claim=world.owner
    )


def v2_finalize(world: World) -> None:
    db = raw(world.path)
    try:
        request = FinalizeRequest(
            world.value,
            world.ref,
            world.receipt,
            world.proof,
        )
        finalize_a2_workset_fenced(db, world.receipts, request)
    finally:
        db.close()


def row_of(path: Path) -> list[tuple[Any, ...]]:
    db = raw(path)
    try:
        return [tuple(r) for r in db.execute(ROW)]
    finally:
        db.close()


def test_v1_is_refused_after_v2_and_writes_nothing(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    try:
        v2_finalize(world)
        before = row_of(world.path)
        with pytest.raises(A2ProducerFenceError) as caught:
            v1_finalize(world)
        check(caught.value.reason == "v2-finalized", "typed v1 refusal")
        check(isinstance(caught.value, ImmutableRecordError), "v1 error family")
        check(row_of(world.path) == before, "v1 wrote nothing")
    finally:
        world.store.close()


def test_v2_is_refused_after_v1(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    try:
        v1_finalize(world)
        before = row_of(world.path)
        with pytest.raises(A2ProducerFenceError) as caught:
            v2_finalize(world)
        check(caught.value.reason == "legacy-finalized", "typed v2 refusal")
        check(row_of(world.path) == before, "v2 wrote nothing")
        v1_finalize(world)
        check(row_of(world.path) == before, "v1 replay stays idempotent")
    finally:
        world.store.close()


def test_v1_failure_inside_the_fence_rolls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = make_world(tmp_path)
    calls: list[int] = []
    real: Callable[[Any, str], None] = intake_store.require_v1_writer_allowed

    def flaky(connection: Any, result_id: str) -> None:
        calls.append(1)
        if len(calls) == 3:
            raise InjectedStop
        real(connection, result_id)

    monkeypatch.setattr(intake_store, "require_v1_writer_allowed", flaky)
    try:
        with pytest.raises(InjectedStop):
            v1_finalize(world)
        check(row_of(world.path)[0][0] == "pending", "UPDATE was rolled back")
        monkeypatch.setattr(intake_store, "require_v1_writer_allowed", real)
        v1_finalize(world)
        check(row_of(world.path)[0][0] == "terminal", "retry finalizes")
    finally:
        world.store.close()


@pytest.mark.parametrize("round_number", range(6))
def test_two_threads_exactly_one_writer_wins(tmp_path: Path, round_number: int) -> None:
    world = make_world(tmp_path)
    barrier = threading.Barrier(2)
    outcomes: dict[str, BaseException | None] = {}

    def run(name: str, action: Callable[[World], None]) -> None:
        barrier.wait(10)
        try:
            action(world)
            outcomes[name] = None
        except BaseException as error:  # noqa: BLE001 - recorded for the test
            outcomes[name] = error

    threads = [
        threading.Thread(target=run, args=("v1", v1_finalize)),
        threading.Thread(target=run, args=("v2", v2_finalize)),
    ]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(30)
        winners = [name for name, error in outcomes.items() if error is None]
        losers = [error for error in outcomes.values() if error is not None]
        check(len(winners) == 1 and len(losers) == 1, f"one winner: {outcomes}")
        check(isinstance(losers[0], A2ProducerFenceError), f"typed: {losers[0]!r}")
        db = raw(world.path)
        owner = workset_owner(db, world.ref.result_id)
        db.close()
        check(owner == ("v2" if winners[0] == "v2" else "legacy"), "owner is winner")
    finally:
        world.store.close()
