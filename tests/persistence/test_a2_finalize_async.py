"""
Async v2 Workset finalize facade (C0-14e); all state lives in ``tmp_path``.

The C0-14b helpers build the schema 5 file, the live claim, the accepted
stages and the receipt. Worker gating uses threading events and barriers,
not sleeps. Gates sit inside the real finalizer, just before the receipt
proof file is published, so a cancel arrives while the worker holds an open
``BEGIN IMMEDIATE`` transaction.
"""

from __future__ import annotations

import asyncio
import re
import sqlite3
import threading
import time
from collections.abc import Callable, Coroutine, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

import msgloom.persistence.a2_finalize_async as facade_module
from msgloom.persistence.a2_finalize_async import FinalizeAsync
from msgloom.persistence.a2_receipt_errors import A2ReceiptError
from msgloom.persistence.a2_receipt_store import ReceiptStore
from msgloom.persistence.a2_schema import release_claim
from msgloom.persistence.a2_workset_finalize import (
    A2FinalizeConflict,
    A2FinalizeError,
)
from msgloom.persistence.async_store import Phase1Persistence
from msgloom.persistence.codecs import encode_result_refs
from tests.a2_kedro import helpers_c0_14b as hb
from tests.a2_kedro.helpers import WORKSET_REF, check, hexd
from tests.a2_kedro.helpers_c0_14b import CANARY, Env
from tests.a2_kedro.test_c0_14b import make_receipt

DEADLINE = 15.0
STORE_PROOF = "put_receipt_proof"


@contextmanager
def open_env(base: Path) -> Iterator[Env]:
    """Build one disposable Workset environment under ``base``."""
    base.mkdir(exist_ok=True)
    built = hb.build_env(base)
    try:
        yield next(built)
    finally:
        next(built, None)


@pytest.fixture
def env(tmp_path: Path) -> Iterator[Env]:
    with open_env(tmp_path / "one") as built:
        yield built


def terminal_row(env: Env) -> tuple[Any, ...]:
    """Return the columns a successful finalize writes for the fixture."""
    refs = [root.result for root in env.receipt.roots] + [hb.BATCH_REF]
    return (
        "terminal",
        "complete",
        encode_result_refs(refs),
        hexd("c"),
        "exec-a1",
        "a1",
    )


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


def facade_for(persistence: Phase1Persistence, env: Env) -> FinalizeAsync:
    return FinalizeAsync(persistence, env.path, env.path.parent / "proofs")


async def wait_for(event: threading.Event) -> None:
    """Yield to the loop until a worker thread sets ``event``."""
    deadline = time.monotonic() + DEADLINE
    while not event.is_set():
        if time.monotonic() > deadline:
            pytest.fail("worker thread did not reach the gate in time")
        await asyncio.sleep(0.005)


def test_finalize_then_sync_readback(env: Env, tmp_path: Path) -> None:
    async def body(persistence: Phase1Persistence) -> None:
        result = await facade_for(persistence, env).finalize(env.request())
        check(result.outcome == "finalized", "first call finalizes")

    check(env.rows() == [hb.PENDING], "starts pending")
    run_with_persistence(tmp_path, body)
    check(env.rows() == [terminal_row(env)], "terminal columns read back")
    check(len(env.files()) == 1, "one proof file")
    check(env.store.get_receipt_proof(WORKSET_REF) is not None, "proof readable")
    check(not env.db.in_transaction, "no transaction left open")


def test_identical_replay_is_replayed(env: Env, tmp_path: Path) -> None:
    async def body(persistence: Phase1Persistence) -> None:
        facade = facade_for(persistence, env)
        first = await facade.finalize(env.request())
        second = await facade.finalize(env.request())
        check((first.outcome, second.outcome) == ("finalized", "replayed"), "order")

    run_with_persistence(tmp_path, body)
    check(env.rows() == [terminal_row(env)] and len(env.files()) == 1, "unchanged")


@pytest.mark.parametrize("kind", ["success", "refusal"])
def test_worker_connection_is_closed_on_every_path(
    env: Env, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    real = facade_module.connect_existing
    opened: list[sqlite3.Connection] = []

    def recording(path: Path) -> sqlite3.Connection:
        connection = real(path)
        opened.append(connection)
        return connection

    monkeypatch.setattr(facade_module, "connect_existing", recording)
    request = env.request(
        proof=hb.attempt_proof("a9", "e") if kind == "refusal" else None
    )

    async def body(persistence: Phase1Persistence) -> None:
        facade = facade_for(persistence, env)
        if kind == "refusal":
            with pytest.raises(A2FinalizeError):
                await facade.finalize(request)
        else:
            await facade.finalize(request)

    run_with_persistence(tmp_path, body)
    check(len(opened) == 1, "one connection per call")
    with pytest.raises(sqlite3.ProgrammingError):
        opened[0].execute("SELECT 1")


def test_conflicting_terminal_values_propagate(env: Env, tmp_path: Path) -> None:
    other = env.request(proof=hb.attempt_proof("a2", "d"))
    seen: list[BaseException] = []

    async def body(persistence: Phase1Persistence) -> None:
        facade = facade_for(persistence, env)
        await facade.finalize(env.request())
        before = env.snapshot()
        try:
            await facade.finalize(other)
        except A2FinalizeConflict as error:
            seen.append(error)
        check(env.snapshot() == before, "a conflict changes nothing")

    run_with_persistence(tmp_path, body)
    check(len(seen) == 1, "A2FinalizeConflict reached the caller")
    conflict = seen[0]
    if not isinstance(conflict, A2FinalizeConflict):
        pytest.fail("wrong error type")
    check(conflict.reason == "terminal-conflict", "fixed reason")
    check("terminal_execution_id" in conflict.fields, "fields name the columns")
    check(env.rows() == [terminal_row(env)], "the first terminal values remain")


@pytest.mark.parametrize("kind", ["foreign", "released"])
def test_foreign_or_expired_claim_is_refused(
    env: Env, tmp_path: Path, kind: str
) -> None:
    if kind == "released":
        # The v2 claim table has no clock. "Expired" means released.
        check(release_claim(env.db, env.claim_seq), "claim released")
    request = env.request(
        proof=hb.attempt_proof("a9", "e") if kind == "foreign" else None
    )
    want = "claim-foreign" if kind == "foreign" else "claim-not-live"
    before = env.snapshot()

    async def body(persistence: Phase1Persistence) -> None:
        with pytest.raises(A2FinalizeError) as caught:
            await facade_for(persistence, env).finalize(request)
        check(caught.value.reason == want, f"reason {caught.value.reason}")
        check(caught.value.__cause__ is None, "raw error must not chain")

    run_with_persistence(tmp_path, body)
    check(env.snapshot() == before, "a refusal changes nothing")
    check(env.rows() == [hb.PENDING] and not env.files(), "still pending, no proof")


class Gate:
    """Replace ``put_receipt_proof``: block until released, then forward."""

    def __init__(self, fail: bool) -> None:
        self.real = ReceiptStore.put_receipt_proof
        self.fail = fail
        self.entered = threading.Event()
        self.release = threading.Event()
        self.finished = threading.Event()

    def method(self) -> Callable[..., Any]:
        """Return a plain function, so the class binds ``store`` to it."""

        def gated(store: ReceiptStore, *args: Any, **kwargs: Any) -> Any:
            return self.run(store, *args, **kwargs)

        return gated

    def run(self, store: ReceiptStore, *args: Any, **kwargs: Any) -> Any:
        self.entered.set()
        try:
            if not self.release.wait(timeout=DEADLINE):
                raise TimeoutError("gate was not released")
            if self.fail:
                raise A2ReceiptError("write-failed")
            return self.real(store, *args, **kwargs)
        finally:
            self.finished.set()


@pytest.mark.parametrize("fail", [False, True], ids=["worker-ok", "worker-fails"])
def test_cancel_while_worker_runs_then_replay(
    env: Env, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fail: bool
) -> None:
    gate = Gate(fail)
    monkeypatch.setattr(ReceiptStore, STORE_PROOF, gate.method())
    outcomes: list[str] = []

    async def body(persistence: Phase1Persistence) -> None:
        facade = facade_for(persistence, env)
        task = asyncio.ensure_future(facade.finalize(env.request()))
        await wait_for(gate.entered)
        task.cancel()
        await asyncio.sleep(0.05)
        check(not task.done(), "cancel waits for the running worker thread")
        check(env.rows() == [hb.PENDING], "the open transaction is not visible")
        asyncio.get_running_loop().call_later(0.01, gate.release.set)
        # run_bounded lets a worker failure propagate; success ends cancelled.
        with pytest.raises(A2ReceiptError if fail else asyncio.CancelledError):
            await task
        check(gate.finished.is_set(), "worker ended before the cancel completed")
        row, files = env.rows(), env.files()
        whole = row == [terminal_row(env)] and len(files) == 1
        untouched = row == [hb.PENDING] and not files
        check(whole or untouched, f"row is terminal with proof or untouched: {row}")
        check(whole is not fail, "outcome matches the worker result")
        monkeypatch.undo()
        outcomes.append((await facade.finalize(env.request())).outcome)
        outcomes.append((await facade.finalize(env.request())).outcome)

    run_with_persistence(tmp_path, body)
    want = ["finalized", "replayed"] if fail else ["replayed", "replayed"]
    check(outcomes == want, f"replay outcomes {outcomes}")
    check(env.rows() == [terminal_row(env)], "terminal after the replay")
    check(len(env.files()) == 1, "exactly one proof file")
    check(env.store.get_receipt_proof(WORKSET_REF) is not None, "proof readable")


def test_closed_persistence_rejects_before_any_connection(
    env: Env, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    opened: list[Path] = []
    real = facade_module.connect_existing

    def counted(path: Path, *args: Any, **kwargs: Any) -> sqlite3.Connection:
        opened.append(path)
        return real(path, *args, **kwargs)

    monkeypatch.setattr(facade_module, "connect_existing", counted)

    async def exercise() -> None:
        url = f"sqlite:///{tmp_path / 'phase1.sqlite'}"
        persistence = await Phase1Persistence.open(url)
        facade = facade_for(persistence, env)
        await persistence.close()
        with pytest.raises(RuntimeError):
            await facade.finalize(env.request())

    asyncio.run(exercise())
    check(opened == [], "no connection opened after close")
    check(env.rows() == [hb.PENDING] and not env.files(), "nothing written")

    async def control() -> None:
        url = f"sqlite:///{tmp_path / 'phase1.sqlite'}"
        persistence = await Phase1Persistence.open(url)
        try:
            await facade_for(persistence, env).finalize(env.request())
        finally:
            await persistence.close()

    asyncio.run(control())
    check(opened == [env.path], "the counter does see an open persistence call")


@pytest.mark.parametrize("round_number", range(3))
def test_concurrent_identical_requests_finalize_once(
    env: Env, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, round_number: int
) -> None:
    pair = threading.Barrier(2, timeout=DEADLINE)
    real = facade_module.connect_existing

    def meeting(path: Path, *args: Any, **kwargs: Any) -> sqlite3.Connection:
        connection = real(path, *args, **kwargs)
        pair.wait()  # both workers hold a connection before either locks
        return connection

    monkeypatch.setattr(facade_module, "connect_existing", meeting)
    results: list[str] = []

    async def body(persistence: Phase1Persistence) -> None:
        facade = facade_for(persistence, env)
        done = await asyncio.gather(
            facade.finalize(env.request()), facade.finalize(env.request())
        )
        results.extend(sorted(item.outcome for item in done))

    run_with_persistence(tmp_path, body, limit=2)
    check(results == ["finalized", "replayed"], f"outcomes {results}")
    check(env.rows() == [terminal_row(env)] and len(env.files()) == 1, "one terminal")


@pytest.mark.parametrize("limit", [1, 2])
def test_different_worksets_respect_the_slot_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, limit: int
) -> None:
    lock = threading.Lock()
    state = {"now": 0, "peak": 0}
    pair = threading.Barrier(2, timeout=DEADLINE)
    real = ReceiptStore.put_receipt_proof

    def counted(store: ReceiptStore, *args: Any, **kwargs: Any) -> Any:
        with lock:
            state["now"] += 1
            state["peak"] = max(state["peak"], state["now"])
        try:
            if limit == 2:
                pair.wait()  # proves two workers really overlap
            return real(store, *args, **kwargs)
        finally:
            with lock:
                state["now"] -= 1

    monkeypatch.setattr(ReceiptStore, STORE_PROOF, counted)
    with open_env(tmp_path / "one") as first, open_env(tmp_path / "two") as second:

        async def body(persistence: Phase1Persistence) -> None:
            done = await asyncio.gather(
                facade_for(persistence, first).finalize(first.request()),
                facade_for(persistence, second).finalize(second.request()),
            )
            check([d.outcome for d in done] == ["finalized"] * 2, "both finalize")

        run_with_persistence(tmp_path, body, limit=limit)
        check(state["peak"] == limit, f"peak concurrency {state['peak']} != {limit}")
        for env in (first, second):
            check(env.rows() == [terminal_row(env)], "terminal row")
            check(len(env.files()) == 1, "one proof file per store")


def test_failures_and_reprs_hide_request_data(
    env: Env, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = env.request(receipt=make_receipt(env.ws, policy=CANARY))
    other = env.request(receipt=make_receipt(env.ws, policy="policy-2"))
    texts: list[str] = [repr(request)]

    def leaky(*args: Any, **kwargs: Any) -> Any:
        raise sqlite3.OperationalError("disk I/O error " + CANARY)

    def record(error: BaseException) -> None:
        texts.extend([repr(error), str(error), str(error.args)])

    async def body(persistence: Phase1Persistence) -> None:
        facade = facade_for(persistence, env)
        monkeypatch.setattr(ReceiptStore, STORE_PROOF, leaky)
        with pytest.raises(A2FinalizeError) as database:
            await facade.finalize(request)
        record(database.value)
        monkeypatch.undo()
        env.db.execute("UPDATE phase1_preparation_intake_worksets SET scope_key = 'x'")
        with pytest.raises(A2FinalizeError) as scope:
            await facade.finalize(request)
        record(scope.value)
        env.db.execute(
            "UPDATE phase1_preparation_intake_worksets SET scope_key = ?",
            (env.ws.scope.claim_key(),),
        )
        texts.append(repr(await facade.finalize(request)))
        with pytest.raises(A2ReceiptError) as conflict:
            await facade.finalize(other)
        record(conflict.value)

    run_with_persistence(tmp_path, body)
    check(len(texts) == 11, f"every failure was recorded: {len(texts)}")
    for text in texts:
        check(CANARY not in text, "request data leaked into a message or repr")
    check(env.rows() == [terminal_row(env)], "the replay-safe terminal row stands")


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
