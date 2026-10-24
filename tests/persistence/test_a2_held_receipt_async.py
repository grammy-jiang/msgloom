"""
Async held-index and receipt facades (C0-13a); all state lives in tmp_path.

Worker gating uses threading events, not sleeps, so no test depends on timing
beyond a generous deadline. The gates sit INSIDE the real store operation
(inside the open held transaction, or just before the receipt file is
published), so a cancel arrives while the worker holds real state. The
facades must use the public ``Phase1Persistence.run_bounded`` hook only.
"""

from __future__ import annotations

import asyncio
import re
import threading
import time
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

import pytest

import msgloom.persistence.a2_held_receipt_async as facade_module
from msgloom.a2_kedro.contracts.held import HeldReason, InputDisposition
from msgloom.persistence import a2_held_store as held_store
from msgloom.persistence import a2_receipt_store as receipt_store
from msgloom.persistence.a2_held_receipt_async import HeldAsync, ReceiptAsync
from msgloom.persistence.a2_held_store import (
    TABLE,
    A2HeldConflict,
    A2HeldError,
    ensure_held_index,
)
from msgloom.persistence.a2_receipt_store import (
    GENESIS,
    A2ReceiptConflict,
    A2ReceiptError,
    build_receipt_proof,
)
from msgloom.persistence.a2_schema import A2SchemaError
from msgloom.persistence.async_store import Phase1Persistence
from tests.a2_kedro.helpers import WORKSET_REF, check, mutate, root_for, workset
from tests.a2_kedro.test_c0_14a import entry as claim_entry
from tests.a2_kedro.test_c0_14a import make_receipt
from tests.persistence.test_a2_schema_fixtures import raw

DEADLINE = 15.0
CANARY = "CANARY-PII-9a3e-bob@example.invalid"
WS = workset(selected=8)
COUNT = f"SELECT count(*) FROM {TABLE}"


@pytest.fixture
def path(tmp_path: Path) -> Path:
    """Return a file that holds the pending held-index table."""
    target = tmp_path / "held.sqlite"
    connection = raw(target)
    try:
        ensure_held_index(connection)
    finally:
        connection.close()
    return target


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """Return an empty receipt store root."""
    target = tmp_path / "receipts"
    target.mkdir()
    return target


def held(
    index: int, reason: HeldReason = HeldReason.PARSER_UNSUPPORTED
) -> InputDisposition:
    return InputDisposition.from_root(
        root_for(WS, index),
        reason,
        configuration_version="config-1",
        code_version="code-1",
    )


def rows(path: Path, sql: str = COUNT) -> int:
    """Count rows with a fresh connection."""
    connection = raw(path)
    try:
        return connection.execute(sql).fetchone()[0]
    finally:
        connection.close()


def run_with_persistence(
    tmp_path: Path,
    body: Callable[[Phase1Persistence], Coroutine[Any, Any, None]],
    *,
    limit: int = 1,
) -> None:
    """Open a Phase1Persistence in tmp_path, run ``body``, always close it."""

    async def exercise() -> None:
        url = f"sqlite:///{tmp_path / 'phase1.sqlite'}"
        persistence = await Phase1Persistence.open(url, max_concurrent_threads=limit)
        try:
            await body(persistence)
        finally:
            await persistence.close()

    asyncio.run(exercise())


async def wait_for(event: threading.Event) -> None:
    """Yield to the loop until a worker thread sets ``event``."""
    deadline = time.monotonic() + DEADLINE
    while not event.is_set():
        if time.monotonic() > deadline:
            pytest.fail("worker thread did not reach the gate in time")
        await asyncio.sleep(0.005)


class Gate:
    """Forward to the real store function after the test releases the gate."""

    def __init__(self, real: Callable[..., Any]) -> None:
        self.real = real
        self.entered = threading.Event()
        self.release = threading.Event()
        self.finished = threading.Event()

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self.entered.set()
        try:
            if not self.release.wait(timeout=DEADLINE):
                raise TimeoutError("gate was not released")
            return self.real(*args, **kwargs)
        finally:
            self.finished.set()


def test_held_round_trip(path: Path, tmp_path: Path) -> None:
    async def body(persistence: Phase1Persistence) -> None:
        facade = HeldAsync(persistence, path)
        check(await facade.put(WORKSET_REF, held(0)) == "inserted", "first insert")
        outcomes = await facade.put_batch(WORKSET_REF, [held(1), held(2)])
        check(outcomes == ("inserted", "inserted"), "batch inserts")
        check(await facade.get(WORKSET_REF, 0) == held(0), "get returns the record")
        check(await facade.get(WORKSET_REF, 7) is None, "unknown index is absent")
        first = await facade.page(WORKSET_REF, limit=2)
        check([r.workset_index for r in first.rows] == [0, 1], "page one")
        check(first.next_cursor is not None, "more rows remain")
        second = await facade.page(WORKSET_REF, limit=2, after=first.next_cursor)
        check([r.workset_index for r in second.rows] == [2], "page two")
        check(second.next_cursor is None, "last page has no cursor")
        status = await facade.status(WORKSET_REF)
        check(status.total == 3 and status.incremental == 3, "status counts")

    run_with_persistence(tmp_path, body)
    check(rows(path) == 3, "three rows on disk")


def test_held_identical_replay_is_idempotent(path: Path, tmp_path: Path) -> None:
    async def body(persistence: Phase1Persistence) -> None:
        facade = HeldAsync(persistence, path)
        await facade.put(WORKSET_REF, held(0))
        check(await facade.put(WORKSET_REF, held(0)) == "replayed", "replays")
        check(await facade.get(WORKSET_REF, 0) == held(0), "record unchanged")

    run_with_persistence(tmp_path, body)
    check(rows(path) == 1, "no second row")


def test_held_conflict_raises_typed_error_without_state_change(
    path: Path, tmp_path: Path
) -> None:
    other_reason = held(0, HeldReason.INPUT_LIMIT)
    same_selection = mutate(held(0), workset_index=5)
    private = mutate(held(3), code_version=CANARY)

    async def body(persistence: Phase1Persistence) -> None:
        facade = HeldAsync(persistence, path)
        await facade.put(WORKSET_REF, held(0))
        await facade.put(WORKSET_REF, held(3))
        with pytest.raises(A2HeldConflict) as caught:
            await facade.put(WORKSET_REF, other_reason)
        check("reason" in caught.value.fields, "names the changed field")
        with pytest.raises(A2HeldConflict):
            await facade.put(WORKSET_REF, same_selection)
        with pytest.raises(A2HeldConflict) as secret:
            await facade.put(WORKSET_REF, private)
        text = f"{secret.value} {secret.value.fields} {secret.value.reason}"
        check(CANARY not in text, "error carries no record text")
        with pytest.raises(A2HeldConflict):
            await facade.put_batch(WORKSET_REF, [held(1), other_reason])
        check(await facade.get(WORKSET_REF, 1) is None, "batch is all or nothing")
        check(await facade.get(WORKSET_REF, 0) == held(0), "stored row unchanged")
        check(await facade.get(WORKSET_REF, 5) is None, "no row at the new index")

    run_with_persistence(tmp_path, body)
    check(rows(path) == 2, "only the two original rows exist")


def test_refusals_use_typed_errors_and_create_nothing(tmp_path: Path) -> None:
    missing, no_root = tmp_path / "absent.sqlite", tmp_path / "no-such-root"
    empty = raw(tmp_path / "empty.sqlite")
    empty.close()

    async def body(persistence: Phase1Persistence) -> None:
        with pytest.raises(A2SchemaError, match="database-file-missing"):
            await HeldAsync(persistence, missing).put(WORKSET_REF, held(0))
        with pytest.raises(A2HeldError, match="held-index-missing"):
            await HeldAsync(persistence, tmp_path / "empty.sqlite").status(WORKSET_REF)
        with pytest.raises(A2ReceiptError) as caught:
            await ReceiptAsync(persistence, no_root).history(WORKSET_REF)
        check(caught.value.reason == "store-root-invalid", "typed refusal")
        check(str(no_root) not in str(caught.value), "no path in the error")

    run_with_persistence(tmp_path, body)
    check(not (missing.exists() or no_root.exists()), "nothing is created")
    schema = "SELECT count(*) FROM sqlite_schema"
    check(rows(tmp_path / "empty.sqlite", schema) == 0, "no table was created")


def test_receipt_proof_put_then_get(root: Path, tmp_path: Path) -> None:
    receipt, accepted = make_receipt()
    proof = build_receipt_proof(receipt, accepted)

    async def body(persistence: Phase1Persistence) -> None:
        facade = ReceiptAsync(persistence, root)
        check(await facade.get_proof(WORKSET_REF) is None, "absent before put")
        check(await facade.put_proof(proof, receipt, accepted) == "inserted", "put")
        check(await facade.get_proof(WORKSET_REF) == proof, "get returns the proof")
        again = await facade.put_proof(proof, receipt, accepted)
        check(again == "replayed", "identical replay is idempotent")

    run_with_persistence(tmp_path, body)


def test_receipt_proof_conflict_and_invalid_proof(root: Path, tmp_path: Path) -> None:
    receipt, accepted = make_receipt()
    proof = build_receipt_proof(receipt, accepted)
    other, other_accepted = make_receipt(policy="policy-2")
    other_proof = build_receipt_proof(other, other_accepted)

    async def body(persistence: Phase1Persistence) -> None:
        facade = ReceiptAsync(persistence, root)
        with pytest.raises(A2ReceiptError, match="proof-receipt-mismatch"):
            await facade.put_proof(other_proof, receipt, accepted)
        check(await facade.get_proof(WORKSET_REF) is None, "bad proof stores nothing")
        await facade.put_proof(proof, receipt, accepted)
        with pytest.raises(A2ReceiptConflict) as caught:
            await facade.put_proof(other_proof, other, other_accepted)
        check(caught.value.reason == "receipt-proof-conflict", "typed conflict")
        check(await facade.get_proof(WORKSET_REF) == proof, "stored proof unchanged")

    run_with_persistence(tmp_path, body)


def test_claim_append_history_replay_and_conflict(root: Path, tmp_path: Path) -> None:
    first, second = claim_entry("claimed", "a1"), claim_entry("released", "a1")

    async def body(persistence: Phase1Persistence) -> None:
        facade = ReceiptAsync(persistence, root)
        check(await facade.history(WORKSET_REF) == (), "empty history")
        check(await facade.append(WORKSET_REF, first, 0) == "inserted", "seq 0")
        head = (await facade.history(WORKSET_REF))[0].entry_sha256
        outcome = await facade.append(WORKSET_REF, second, 1, expected_head_sha256=head)
        check(outcome == "inserted", "seq 1 with a head anchor")
        chain = await facade.history(WORKSET_REF)
        check([c.entry for c in chain] == [first, second], "history in order")
        check(chain[0].prev_sha256 == GENESIS, "chain starts at genesis")
        check(await facade.append(WORKSET_REF, first, 0) == "replayed", "replay")
        with pytest.raises(A2ReceiptConflict) as caught:
            await facade.append(WORKSET_REF, second, 0)
        check(caught.value.reason == "claim-history-rewrite", "no rewrite")
        with pytest.raises(A2ReceiptError, match="claim-gap"):
            await facade.append(WORKSET_REF, first, 5)
        with pytest.raises(A2ReceiptError, match="claim-head-mismatch"):
            await facade.history(WORKSET_REF, expected_head_sha256=GENESIS)
        check(await facade.history(WORKSET_REF) == chain, "history unchanged")

    run_with_persistence(tmp_path, body)


@pytest.mark.parametrize("target", ["held", "receipt"])
@pytest.mark.parametrize("limit", [1, 2])
def test_semaphore_bound_is_respected(
    path: Path,
    root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
    limit: int,
) -> None:
    lock = threading.Lock()
    state = {"now": 0, "peak": 0, "seen": 0}
    pair = threading.Barrier(2, timeout=DEADLINE)
    receipt, accepted = make_receipt()
    proof = build_receipt_proof(receipt, accepted)

    def counted(real: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with lock:
                state["now"] += 1
                state["seen"] += 1
                state["peak"] = max(state["peak"], state["now"])
                first_wave = state["seen"] <= limit
            try:
                if limit == 2 and first_wave:
                    pair.wait()  # proves two workers really overlap
                time.sleep(0.01)
                return real(*args, **kwargs)
            finally:
                with lock:
                    state["now"] -= 1

        return wrapper

    async def body(persistence: Phase1Persistence) -> None:
        held_facade = HeldAsync(persistence, path)
        receipt_facade = ReceiptAsync(persistence, root)
        await held_facade.put(WORKSET_REF, held(0))
        await receipt_facade.put_proof(proof, receipt, accepted)
        monkeypatch.setattr(held_store, "_checked", counted(held_store._checked))
        monkeypatch.setattr(
            receipt_store, "read_bounded", counted(receipt_store.read_bounded)
        )
        if target == "held":
            work = [held_facade.get(WORKSET_REF, 0) for _ in range(6)]
        else:
            work = [receipt_facade.get_proof(WORKSET_REF) for _ in range(6)]
        results = await asyncio.gather(*work)
        check(len(set(map(repr, results))) == 1, "all calls read the same state")

    run_with_persistence(tmp_path, body, limit=limit)
    check(state["seen"] == 6, "every call reached a worker")
    check(state["peak"] == limit, f"peak concurrency {state['peak']} != {limit}")


def test_held_cancel_inside_open_transaction_drains_worker(
    path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = Gate(held_store._put_one)
    monkeypatch.setattr(held_store, "_put_one", gate)
    checked: dict[str, bool] = {}

    async def body(persistence: Phase1Persistence) -> None:
        facade = HeldAsync(persistence, path)
        task = asyncio.ensure_future(facade.put(WORKSET_REF, held(0)))
        await wait_for(gate.entered)
        task.cancel()
        await asyncio.sleep(0.05)
        check(not task.done(), "cancel waits for the running worker thread")
        check(rows(path) == 0, "the open transaction is not visible yet")
        asyncio.get_running_loop().call_later(0.01, gate.release.set)
        with pytest.raises(asyncio.CancelledError):
            await task
        check(gate.finished.is_set(), "worker operation ended before cancel")
        stored = await facade.get(WORKSET_REF, 0)
        check(
            (stored is not None, rows(path)) in {(True, 1), (False, 0)},
            "row is fully committed or fully absent",
        )
        checked["committed"] = stored is not None
        check(await facade.put(WORKSET_REF, held(0)) in {"inserted", "replayed"}, "ok")

    run_with_persistence(tmp_path, body)
    check(checked.get("committed") is True, "worker finished its commit")
    check(rows(path) == 1, "replay after cancel leaves one row")


def test_claim_cancel_before_publish_drains_worker(
    root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = Gate(receipt_store.create_once)
    monkeypatch.setattr(receipt_store, "create_once", gate)
    item = claim_entry("claimed", "a1")
    checked: dict[str, int] = {}

    async def body(persistence: Phase1Persistence) -> None:
        facade = ReceiptAsync(persistence, root)
        task = asyncio.ensure_future(facade.append(WORKSET_REF, item, 0))
        await wait_for(gate.entered)
        task.cancel()
        await asyncio.sleep(0.05)
        check(not task.done(), "cancel waits for the running worker thread")
        asyncio.get_running_loop().call_later(0.01, gate.release.set)
        with pytest.raises(asyncio.CancelledError):
            await task
        check(gate.finished.is_set(), "worker operation ended before cancel")
        chain = await facade.history(WORKSET_REF)
        check(len(chain) in {0, 1}, "history is whole or absent")
        checked["length"] = len(chain)
        check(await facade.append(WORKSET_REF, item, 0) == "replayed", "replay")

    run_with_persistence(tmp_path, body)
    check(checked.get("length") == 1, "worker finished its publish")


def test_failed_worker_rolls_back_and_frees_the_slot(
    path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*args: Any) -> Any:
        raise ValueError("injected worker failure")

    real = held_store._put_one
    monkeypatch.setattr(held_store, "_put_one", broken)

    async def body(persistence: Phase1Persistence) -> None:
        facade = HeldAsync(persistence, path)
        with pytest.raises(ValueError, match="injected"):
            await facade.put_batch(WORKSET_REF, [held(0), held(1)])
        check(await facade.get(WORKSET_REF, 0) is None, "no row after rollback")
        monkeypatch.setattr(held_store, "_put_one", real)
        check(await facade.put(WORKSET_REF, held(0)) == "inserted", "slot was freed")

    run_with_persistence(tmp_path, body)
    check(rows(path) == 1, "only the later write exists")


def test_close_waits_for_accepted_calls_and_rejects_later_ones(
    path: Path, root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = Gate(held_store._put_one)
    monkeypatch.setattr(held_store, "_put_one", gate)
    item = claim_entry("claimed", "a1")

    async def exercise() -> None:
        url = f"sqlite:///{tmp_path / 'phase1.sqlite'}"
        persistence = await Phase1Persistence.open(url)
        facade = HeldAsync(persistence, path)
        receipts = ReceiptAsync(persistence, root)
        call = asyncio.ensure_future(facade.put(WORKSET_REF, held(0)))
        await wait_for(gate.entered)
        closing = asyncio.ensure_future(persistence.close())
        await asyncio.sleep(0.05)
        check(not closing.done(), "close waits for the accepted call")
        with pytest.raises(RuntimeError):
            await facade.get(WORKSET_REF, 0)
        with pytest.raises(RuntimeError):
            await receipts.append(WORKSET_REF, item, 0)
        gate.release.set()
        check(await call == "inserted", "accepted call completed")
        await closing
        with pytest.raises(RuntimeError):
            await facade.put(WORKSET_REF, held(1))
        with pytest.raises(RuntimeError):
            await receipts.history(WORKSET_REF)

    asyncio.run(exercise())
    check(rows(path) == 1, "the call accepted before close committed")
    check(not list(root.iterdir()), "rejected receipt calls wrote nothing")


FORBIDDEN = {
    "private store": re.compile(r"(?<![A-Za-z0-9])_store\b"),
    "private call": re.compile(r"(?<![A-Za-z0-9])_call\b"),
    "thread start": re.compile(r"\bto_thread\b"),
    "private attribute of another object": re.compile(r"\b(?!self\.)\w+\._[a-z]"),
    "own semaphore": re.compile(r"\bSemaphore\b"),
}


def test_facade_source_has_no_reach_in() -> None:
    source = Path(facade_module.__file__).read_text(encoding="utf-8")
    found = [name for name, pattern in FORBIDDEN.items() if pattern.search(source)]
    check(not found, f"facade source contains forbidden patterns: {found}")
    check("run_bounded" in source, "facade must use the public hook")
    check(len(source.splitlines()) < 500, "module stays under 500 lines")


def test_scan_patterns_detect_a_reach_in() -> None:
    bad = "self._persistence._store.x\nawait asyncio.to_thread(f)\nx._call(g)\n"
    bad += "gate = asyncio.Semaphore(2)\n"
    hits = {name for name, pattern in FORBIDDEN.items() if pattern.search(bad)}
    check(
        {"private store", "private call", "thread start", "own semaphore"} <= hits,
        f"scan must detect reach-ins, found {hits}",
    )
    clean = "from msgloom.persistence.a2_held_store import put_held\n"
    check(not any(p.search(clean) for p in FORBIDDEN.values()), "held store is fine")
