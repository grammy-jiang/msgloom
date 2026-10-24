"""
C0-14d: v2 finalization held, race, lost-claim and rollback tests.

Every database and proof directory lives under ``tmp_path``. The C0-14b and
C0-14c helpers are imported, not copied. No async finalize facade exists yet
(C0-14e adds one), so the cancellation tests run the fenced finalizer in an
executor thread under a real asyncio task.
"""

from __future__ import annotations

import asyncio
import sqlite3
import threading
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

from msgloom.a2_kedro.contracts.identity import AttemptProof
from msgloom.a2_kedro.contracts.receipt import (
    CompletionReceipt,
    TerminalRoot,
)
from msgloom.contracts import ResultRef, TerminalStatus
from msgloom.persistence.a2_producer_binding import (
    A2ProducerFenceError,
    finalize_a2_workset_fenced,
    workset_owner,
)
from msgloom.persistence.a2_receipt_errors import A2ReceiptError
from msgloom.persistence.a2_receipt_store import ReceiptStore
from msgloom.persistence.a2_schema import (
    A2SchemaError,
    acquire_claim,
    migrate_schema4_to_v5,
    release_claim,
)
from msgloom.persistence.a2_workset_finalize import (
    A2FinalizeError,
    FinalizeRequest,
    FinalizeResult,
    finalize_a2_intake_workset_v2,
)
from msgloom.persistence.codecs import encode_result_refs
from msgloom.preparation_pipeline.intake_models import workset_claim_key
from tests.a2_kedro import helpers_c0_14b as hb
from tests.a2_kedro.helpers import WORKSET_REF, accepted_ref, check, hexd, mutate
from tests.a2_kedro.helpers_c0_14b import Env
from tests.a2_kedro.test_c0_14c import World, row_of, v1_finalize, v2_finalize
from tests.persistence.test_a2_schema_fixtures import GATE, raw
from tests.phase1_foundation import intake_completion_helpers as c
from tests.phase1_foundation import intake_helpers as h

COMPLETE, INCOMPLETE = TerminalStatus.COMPLETE, TerminalStatus.INCOMPLETE
Finalizer = Callable[
    [sqlite3.Connection, ReceiptStore, FinalizeRequest], FinalizeResult
]
FINALIZERS = [
    pytest.param(finalize_a2_intake_workset_v2, id="bare"),
    pytest.param(finalize_a2_workset_fenced, id="fenced"),
]
UNPROVEN: dict[Finalizer, str] = {
    finalize_a2_intake_workset_v2: "accepted-result-missing",
    finalize_a2_workset_fenced: "stage-unproven",
}
STORE_PROOF = "put_receipt_proof"
ROTATION_BUG = pytest.mark.xfail(strict=True, raises=A2SchemaError, reason="major")


@pytest.fixture
def env(tmp_path: Path) -> Iterator[Env]:
    yield from hb.build_env(tmp_path)


def make_held_world(tmp_path: Path, path: Path, store: Any) -> World:
    """Admit one intake-held entry, migrate to schema 5, take a v2 claim."""
    value, saved, owner, _ = c.admit(store, count=0, held=True)
    db = raw(path)
    migrate_schema4_to_v5(db, GATE)
    ref = ResultRef(saved.result_id, saved.kind, saved.schema_version)
    proof = AttemptProof(
        execution_id="exec-a1",
        attempt_id="a1",
        claim_key=workset_claim_key(ref.result_id),
        claim_token_sha256=hexd("c"),
    )
    if acquire_claim(db, proof) is None:
        pytest.fail("v2 claim must be acquired")
    db.close()
    (tmp_path / "proofs").mkdir()
    receipt = CompletionReceipt(
        workset=ref,
        status=INCOMPLETE,
        policy_version="policy-1",
        intake_held_count=len(value.held),
    )
    receipts = ReceiptStore(tmp_path / "proofs")
    return World(path, store, value, ref, (), owner, receipts, receipt, proof)


@pytest.fixture
def held_world(tmp_path: Path) -> Iterator[World]:
    path = tmp_path / "held.sqlite"
    store = h.store(path)
    try:
        yield make_held_world(tmp_path, path, store)
    finally:
        store.close()


def proof_files(world: World) -> list[str]:
    return sorted(p.name for p in world.receipts._root.rglob("*") if p.is_file())


def pending_ids(world: World) -> list[str]:
    """Return ids from the public v1 pending listing (read only)."""
    listed = world.store.list_preparation_intake_worksets(world.value.scope)
    return [state.workset.result_id for state in listed]


def expect_refusal(
    env: Env,
    finalizer: Finalizer,
    reason: str,
    request: FinalizeRequest | None = None,
) -> None:
    """The finalizer must refuse with ``reason`` and leave no terminal row."""
    before = env.snapshot()
    with pytest.raises(A2ReceiptError) as caught:
        finalizer(env.db, env.store, request or env.request())
    check(caught.value.reason == reason, f"expected {reason}: {caught.value.reason}")
    check(not env.db.in_transaction, "transaction must be closed")
    check(env.snapshot() == before, "a refusal must change nothing")
    check(env.rows() == [hb.PENDING] and not env.files(), "no terminal row or proof")
    check(row_of(env.path) == [hb.PENDING], "a fresh connection sees no terminal row")


# Case 1: held-only finalizes to terminal INCOMPLETE ---------------------------


def test_intake_held_only_workset_finalizes_incomplete(held_world: World) -> None:
    w = held_world
    check(len(w.value.selections) == 0 and len(w.value.held) == 1, "held only")
    check(row_of(w.path)[0][0] == "pending", "starts pending")
    v2_finalize(w)
    want = ("terminal", "incomplete", "[]", hexd("c"), "exec-a1", "a1")
    check(row_of(w.path) == [want], "terminal INCOMPLETE columns")
    states = w.store.list_preparation_intake_worksets(w.value.scope, pending_only=False)
    check(
        [(s.state, s.terminal_status) for s in states] == [("terminal", INCOMPLETE)],
        "v1",
    )
    check(len(proof_files(w)) == 1, "one proof file")
    db = raw(w.path)
    check(workset_owner(db, w.ref.result_id) == "v2", "v2 owns the row")
    db.close()


def test_held_only_cannot_be_complete(held_world: World) -> None:
    w = held_world
    with pytest.raises(ValueError):
        mutate(w.receipt, status=COMPLETE)
    wrong = mutate(w.receipt, intake_held_count=2)
    db = raw(w.path)
    with pytest.raises(A2FinalizeError) as caught:
        finalize_a2_workset_fenced(
            db, w.receipts, FinalizeRequest(w.value, w.ref, wrong, w.proof)
        )
    db.close()
    check(caught.value.reason == "receipt-not-covering-workset", "wrong held count")
    check(row_of(w.path)[0][0] == "pending" and not proof_files(w), "nothing written")
    v2_finalize(w)
    check(row_of(w.path)[0][1] == "incomplete", "the right receipt finalizes")


def test_all_roots_held_finalizes_incomplete(env: Env) -> None:
    roots = []
    for index, char in enumerate("cd"):
        ref = accepted_ref(str(index + 3), "a2_input_disposition", "1")
        writer = hb.attempt_proof()
        stage = hb.stage_for(ref, char, writer, INCOMPLETE)
        hb.publish(
            env.db, stage, env.claim_seq, hb.saved_result(ref, char, writer, INCOMPLETE)
        )
        roots.append(
            TerminalRoot(
                workset_selection_index=index,
                result=ref,
                disposition="held",
                status=INCOMPLETE,
                selection=env.ws.selections[index],
            )
        )
    receipt = CompletionReceipt(
        workset=WORKSET_REF,
        status=INCOMPLETE,
        policy_version="policy-1",
        roots=tuple(roots),
        transition_batch=env.receipt.transition_batch,
    )
    with pytest.raises(ValueError):
        mutate(receipt, status=COMPLETE)
    result = finalize_a2_workset_fenced(env.db, env.store, env.request(receipt))
    check(result.outcome == "finalized", "finalized")
    refs = encode_result_refs([r.result for r in roots] + [hb.BATCH_REF])
    want = ("terminal", "incomplete", refs, hexd("c"), "exec-a1", "a1")
    check(row_of(env.path) == [want], "fresh connection reads terminal INCOMPLETE")


# Case 2: the pending queue ----------------------------------------------------


def test_finalized_workset_leaves_the_pending_queue(held_world: World) -> None:
    w = held_world
    check(pending_ids(w) == [w.ref.result_id], "pending before finalize")
    foreign = AttemptProof(**{**w.proof.model_dump(), "attempt_id": "a9"})
    request = FinalizeRequest(w.value, w.ref, w.receipt, foreign)
    db = raw(w.path)
    with pytest.raises(A2FinalizeError) as caught:
        finalize_a2_workset_fenced(db, w.receipts, request)
    db.close()
    check(caught.value.reason == "claim-foreign", "foreign claim refused")
    check(pending_ids(w) == [w.ref.result_id], "a refusal keeps it pending")
    v2_finalize(w)
    check(pending_ids(w) == [], "no longer pending after v2 finalize")
    listed = w.store.list_preparation_intake_worksets(w.value.scope, pending_only=False)
    check(
        [s.workset.result_id for s in listed] == [w.ref.result_id], "kept as terminal"
    )


@ROTATION_BUG
def test_rotation_before_migration_still_migrates(tmp_path: Path) -> None:
    # major: the v1 rotation key makes migrate_schema4_to_v5 raise
    # ``unknown-metadata-key``. Every v1 scheduler run writes that key.
    path = tmp_path / "rotated.sqlite"
    store = h.store(path)
    try:
        value, _, _, _ = c.admit(store, count=0, held=True)
        check(len(store.select_preparation_intake_worksets(value.scope)) == 1, "v1")
        db = raw(path)
        migrate_schema4_to_v5(db, GATE)
        db.close()
    finally:
        store.close()


@ROTATION_BUG
def test_v1_rotation_after_migration_does_not_block_v2(held_world: World) -> None:
    # major: a long-lived v1 store writes the rotation key after migration.
    # ``require_schema5`` then refuses every v2 finalize.
    w = held_world
    check(len(w.store.select_preparation_intake_worksets(w.value.scope)) == 1, "v1")
    v2_finalize(w)
    check(pending_ids(w) == [], "gone from the queue")


# Case 3: v1 versus v2 race ----------------------------------------------------


@pytest.mark.parametrize("round_number", range(5))
def test_v1_v2_race_has_one_terminal_winner(tmp_path: Path, round_number: int) -> None:
    path = tmp_path / "race.sqlite"
    store = h.store(path)
    try:
        w = make_held_world(tmp_path, path, store)
        barrier = threading.Barrier(2)
        outcomes: dict[str, BaseException | None] = {}

        def run(name: str, action: Callable[[World], None]) -> None:
            barrier.wait(10)
            try:
                action(w)
                outcomes[name] = None
            except BaseException as error:  # noqa: BLE001 - recorded
                outcomes[name] = error

        threads = [
            threading.Thread(target=run, args=("v1", v1_finalize)),
            threading.Thread(target=run, args=("v2", v2_finalize)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(30)
        winners = [n for n, error in outcomes.items() if error is None]
        errors = [e for e in outcomes.values() if e is not None]
        check(len(winners) == 1 and len(errors) == 1, f"one winner: {outcomes}")
        loser = errors[0]
        check(isinstance(loser, A2ProducerFenceError), f"typed refusal: {loser!r}")
        want = "legacy-finalized" if winners[0] == "v1" else "v2-finalized"
        check(getattr(loser, "reason", "") == want, "reason names the winner")
        rows = row_of(path)
        check(len(rows) == 1 and rows[0][:2] == ("terminal", "incomplete"), "one row")
        check(len(proof_files(w)) == (winners[0] == "v2"), "proof only for v2")
        check(pending_ids(w) == [], "the winner removed it from the queue")
    finally:
        store.close()


# Case 4: missing root and forged refs -----------------------------------------


def covering(env: Env, roots: tuple[TerminalRoot, ...]) -> CompletionReceipt:
    return CompletionReceipt(
        workset=WORKSET_REF,
        status=COMPLETE,
        policy_version="policy-1",
        roots=roots,
        transition_batch=env.receipt.transition_batch,
    )


@pytest.mark.parametrize("finalizer", FINALIZERS)
def test_forged_root_ref_is_refused_then_real_receipt_works(
    env: Env, finalizer: Finalizer
) -> None:
    first = env.receipt.roots[0]
    forged_root = TerminalRoot(
        workset_selection_index=0,
        result=accepted_ref("7", "prepared", "2"),
        disposition="prepared",
        status=COMPLETE,
        selection=first.selection,
    )
    forged = covering(env, (forged_root, *env.receipt.roots[1:]))
    expect_refusal(env, finalizer, UNPROVEN[finalizer], env.request(forged))
    check(finalizer(env.db, env.store, env.request()).outcome == "finalized", "real")


def test_receipt_missing_a_root_is_refused(env: Env) -> None:
    finalizer = finalize_a2_workset_fenced
    short = covering(env, env.receipt.roots[:1])
    expect_refusal(env, finalizer, "receipt-not-covering-workset", env.request(short))
    check(finalizer(env.db, env.store, env.request()).outcome == "finalized", "full")


@pytest.mark.parametrize("finalizer", FINALIZERS)
def test_deleted_accepted_root_is_refused_then_restored(
    env: Env, finalizer: Finalizer
) -> None:
    key = env.receipt.roots[0].result.result_id
    for table in ("a2_stage_attempts", "a2_accepted_stages"):
        env.db.execute(f"DELETE FROM phase1_{table} WHERE logical_key = ?", (key,))
    expect_refusal(env, finalizer, UNPROVEN[finalizer])
    columns = hb.accepted_columns(env.accepted[key], env.claim_seq)
    hb.insert_row(env.db, "phase1_a2_accepted_stages", columns)
    history = {"logical_key": key, "claim_seq": env.claim_seq, "outcome": "inserted"}
    hb.insert_row(env.db, "phase1_a2_stage_attempts", history)
    check(
        finalizer(env.db, env.store, env.request()).outcome == "finalized", "restored"
    )


# Case 5: lost claim -----------------------------------------------------------


@pytest.mark.parametrize("finalizer", FINALIZERS)
def test_superseded_claim_is_refused_and_successor_finalizes(
    env: Env, finalizer: Finalizer
) -> None:
    check(release_claim(env.db, env.claim_seq), "first claim released")
    successor = hb.attempt_proof("a2", "d")
    check(acquire_claim(env.db, successor) is not None, "successor is live")
    expect_refusal(env, finalizer, "claim-foreign")
    done = finalizer(env.db, env.store, env.request(proof=successor))
    check(done.outcome == "finalized", "successor finalizes")
    check(row_of(env.path)[0][4:] == ("exec-a2", "a2"), "successor identity stored")


@pytest.mark.parametrize("finalizer", FINALIZERS)
def test_released_claim_is_refused_and_cannot_be_revived(
    env: Env, finalizer: Finalizer
) -> None:
    # The v2 claim table has no lease or clock. "Expired" means released.
    check(release_claim(env.db, env.claim_seq), "claim released")
    expect_refusal(env, finalizer, "claim-not-live")
    with pytest.raises(A2SchemaError) as caught:
        acquire_claim(env.db, hb.attempt_proof())
    check(caught.value.reason == "claim-rejected", "a released proof stays dead")
    expect_refusal(env, finalizer, "claim-not-live")
    fresh = hb.attempt_proof("a3", "f")
    check(acquire_claim(env.db, fresh) is not None, "a new attempt claims")
    check(
        finalizer(env.db, env.store, env.request(proof=fresh)).outcome == "finalized",
        "new",
    )


# Case 6: crash between the UPDATE and the receipt write -----------------------


@pytest.mark.parametrize("failure", [RuntimeError("boom"), hb.InjectedStop()], ids=type)
def test_crash_after_update_rolls_back_then_retry_runs_once(
    env: Env, monkeypatch: pytest.MonkeyPatch, failure: BaseException
) -> None:
    seen: list[str] = []

    def crash(*args: object, **kwargs: object) -> None:
        sql = "SELECT state FROM phase1_preparation_intake_worksets"
        seen.append(env.db.execute(sql).fetchone()[0])
        raise failure

    before = env.snapshot()
    monkeypatch.setattr(env.store, STORE_PROOF, crash)
    with pytest.raises(type(failure)):
        finalize_a2_workset_fenced(env.db, env.store, env.request())
    check(seen == ["terminal"], "the UPDATE ran before the crash point")
    check(not env.db.in_transaction and env.snapshot() == before, "rolled back")
    check(row_of(env.path) == [hb.PENDING], "fresh connection sees no terminal row")
    check(not env.files(), "no receipt file")
    check(env.store.get_receipt_proof(WORKSET_REF) is None, "no receipt proof")
    monkeypatch.undo()
    first = finalize_a2_workset_fenced(env.db, env.store, env.request())
    check(first.outcome == "finalized", "clean retry succeeds")
    second = finalize_a2_workset_fenced(env.db, env.store, env.request())
    check(second.outcome == "replayed", "a second retry only replays")
    check([r[0] for r in row_of(env.path)] == ["terminal"], "one terminal row")
    check(len(env.files()) == 1, "exactly one receipt file")


# Case 7: cancellation of a real asyncio task ----------------------------------
# No async finalize facade exists yet, so the task wraps run_in_executor.


def run_cancelled(env: Env, monkeypatch: pytest.MonkeyPatch, fail: bool) -> None:
    """Cancel the task while the worker waits inside the transaction."""
    entered, release = threading.Event(), threading.Event()
    real = ReceiptStore.put_receipt_proof

    def gated(self: ReceiptStore, *args: Any, **kwargs: Any) -> Any:
        entered.set()
        if not release.wait(10) or fail:
            raise hb.InjectedStop
        return real(self, *args, **kwargs)

    monkeypatch.setattr(ReceiptStore, STORE_PROOF, gated)

    def work() -> None:
        db = raw(env.path)
        try:
            finalize_a2_workset_fenced(db, env.store, env.request())
        finally:
            db.close()

    pool = ThreadPoolExecutor(max_workers=2)

    async def main() -> None:
        loop = asyncio.get_running_loop()
        task = asyncio.ensure_future(loop.run_in_executor(pool, work))
        await loop.run_in_executor(pool, entered.wait, 10)
        check(row_of(env.path) == [hb.PENDING], "uncommitted work is invisible")
        task.cancel()
        await asyncio.wait([task])
        check(task.cancelled(), "the real task ended cancelled")
        check(row_of(env.path) == [hb.PENDING], "cancel alone changes nothing")
        release.set()

    try:
        asyncio.run(main())
    finally:
        release.set()
        pool.shutdown(wait=True)


@pytest.mark.parametrize("fail", [False, True], ids=["worker-ok", "worker-fails"])
def test_cancelled_task_is_whole_or_rolled_back(
    env: Env, monkeypatch: pytest.MonkeyPatch, fail: bool
) -> None:
    run_cancelled(env, monkeypatch, fail)
    if not fail:
        check(row_of(env.path)[0][0] == "terminal", "the worker finished whole")
        check(len(env.files()) == 1, "terminal row implies one proof file")
        return
    check(row_of(env.path) == [hb.PENDING] and not env.files(), "rolled back")
    monkeypatch.undo()
    check(env.run().outcome == "finalized", "retry after cancel works")
