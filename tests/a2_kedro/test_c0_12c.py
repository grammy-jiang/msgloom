"""
Async acceptance facade (C0-12c); every database lives in tmp_path.

Worker gating uses threading events, not sleeps, so no test depends on timing
beyond a generous deadline. The facade must use the public
``Phase1Persistence.run_bounded`` hook only.
"""

from __future__ import annotations

import asyncio
import re
import sqlite3
import threading
import time
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

import pytest

import msgloom.persistence.a2_acceptance_async as facade_module
from msgloom.a2_kedro.contracts.identity import StageIdentity
from msgloom.contracts import TerminalStatus
from msgloom.persistence.a2_acceptance_async import AcceptanceAsync
from msgloom.persistence.a2_acceptance_models import AcceptanceConflict
from msgloom.persistence.a2_schema import acquire_claim
from msgloom.persistence.a2_store import Accepted, PublisherReceipt, accept_result
from msgloom.persistence.async_store import Phase1Persistence
from tests.a2_kedro.helpers import check, hexd, proof, result_for, stage_identity
from tests.persistence.test_a2_schema_fixtures import build_schema5, raw

DEADLINE = 15.0
STAGE = "SELECT count(*) FROM phase1_a2_accepted_stages"
ATTEMPT = "SELECT count(*) FROM phase1_a2_stage_attempts"


@pytest.fixture
def path(tmp_path: Path) -> Path:
    """Return a schema 5 file whose live claim belongs to attempt w1."""
    built = build_schema5(tmp_path / "a2.sqlite")
    connection = raw(built)
    try:
        if acquire_claim(connection, proof("w1")) is None:
            pytest.fail("fixture claim must be acquired")
    finally:
        connection.close()
    return built


def receipt(identity: StageIdentity, **changes: Any) -> PublisherReceipt:
    return PublisherReceipt(result_for(identity, attempt="w1", **changes), proof("w1"))


def counts(path: Path) -> tuple[int, int]:
    """Read accepted-row and attempt-row counts with a fresh connection."""
    connection = raw(path)
    try:
        return (
            connection.execute(STAGE).fetchone()[0],
            connection.execute(ATTEMPT).fetchone()[0],
        )
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
    """Replace ``accept_result`` in the worker with a gated forwarder."""

    def __init__(self) -> None:
        self.entered = threading.Event()
        self.release = threading.Event()
        self.finished = threading.Event()

    def __call__(self, db: sqlite3.Connection, *args: Any) -> Accepted:
        self.entered.set()
        try:
            if not self.release.wait(timeout=DEADLINE):
                raise TimeoutError("gate was not released")
            return accept_result(db, *args)
        finally:
            self.finished.set()


def test_accept_then_read_back(path: Path, tmp_path: Path) -> None:
    identity = stage_identity()

    async def body(persistence: Phase1Persistence) -> None:
        facade = AcceptanceAsync(persistence, path)
        first = await facade.accept(identity, receipt(identity))
        check(first.outcome == "inserted", "first write inserts")
        stored = await facade.get(identity.logical_key())
        check(stored == first.record, "read back equals the accepted record")
        check(await facade.get(hexd("0")) is None, "unknown key reads as absent")

    run_with_persistence(tmp_path, body)
    check(counts(path) == (1, 1), "one row and one attempt on disk")


def test_identical_replay_is_idempotent(path: Path, tmp_path: Path) -> None:
    identity = stage_identity()

    async def body(persistence: Phase1Persistence) -> None:
        facade = AcceptanceAsync(persistence, path)
        first = await facade.accept(identity, receipt(identity))
        again = await facade.accept(identity, receipt(identity))
        check(again.outcome == "replayed", "identical replay replays")
        check(again.record == first.record, "replay returns the stored row")

    run_with_persistence(tmp_path, body)
    check(counts(path) == (1, 2), "one row, two attempt rows")


def test_conflicting_replay_is_rejected(path: Path, tmp_path: Path) -> None:
    identity = stage_identity()

    async def body(persistence: Phase1Persistence) -> None:
        facade = AcceptanceAsync(persistence, path)
        first = await facade.accept(identity, receipt(identity))
        with pytest.raises(AcceptanceConflict) as caught:
            await facade.accept(identity, receipt(identity, sha="b" * 64))
        check("canonical_sha256" in caught.value.fields, "names the field")
        with pytest.raises(AcceptanceConflict):
            await facade.accept(
                identity, receipt(identity, status=TerminalStatus.INCOMPLETE)
            )
        check(
            await facade.get(identity.logical_key()) == first.record,
            "stored row is unchanged",
        )

    run_with_persistence(tmp_path, body)
    check(counts(path)[0] == 1, "no second accepted row")


def test_missing_database_file_is_refused_not_created(tmp_path: Path) -> None:
    missing = tmp_path / "absent.sqlite"
    identity = stage_identity()

    async def body(persistence: Phase1Persistence) -> None:
        facade = AcceptanceAsync(persistence, missing)
        with pytest.raises(Exception, match="database-file-missing"):
            await facade.accept(identity, receipt(identity))
        with pytest.raises(Exception, match="database-file-missing"):
            await facade.get(identity.logical_key())

    run_with_persistence(tmp_path, body)
    check(not missing.exists(), "the facade never creates a database file")


@pytest.mark.parametrize("limit", [1, 2])
def test_semaphore_bound_is_respected(
    path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, limit: int
) -> None:
    lock = threading.Lock()
    state = {"now": 0, "peak": 0, "seen": 0}
    pair = threading.Barrier(2, timeout=DEADLINE)

    def counted(db: sqlite3.Connection, *args: Any) -> Accepted:
        with lock:
            state["now"] += 1
            state["seen"] += 1
            state["peak"] = max(state["peak"], state["now"])
            first_wave = state["seen"] <= limit
        try:
            if limit == 2 and first_wave:
                pair.wait()  # proves two workers really overlap
            time.sleep(0.01)
            return accept_result(db, *args)
        finally:
            with lock:
                state["now"] -= 1

    monkeypatch.setattr(facade_module, "accept_result", counted)
    identities = [stage_identity(scope_key=hexd(c)) for c in "123456"]

    async def body(persistence: Phase1Persistence) -> None:
        facade = AcceptanceAsync(persistence, path)
        outcomes = await asyncio.gather(
            *(facade.accept(i, receipt(i)) for i in identities)
        )
        check(all(o.outcome == "inserted" for o in outcomes), "all insert")

    run_with_persistence(tmp_path, body, limit=limit)
    check(state["seen"] == len(identities), "every call reached a worker")
    check(state["peak"] == limit, f"peak concurrency {state['peak']} != {limit}")
    check(counts(path)[0] == len(identities), "all rows committed")


def test_cancel_drains_worker_and_row_is_all_or_nothing(
    path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = Gate()
    monkeypatch.setattr(facade_module, "accept_result", gate)
    identity = stage_identity()
    checked: dict[str, bool] = {}

    async def body(persistence: Phase1Persistence) -> None:
        facade = AcceptanceAsync(persistence, path)
        task = asyncio.ensure_future(facade.accept(identity, receipt(identity)))
        await wait_for(gate.entered)
        task.cancel()
        await asyncio.sleep(0.05)
        check(not task.done(), "cancel waits for the running worker thread")
        asyncio.get_running_loop().call_later(0.01, gate.release.set)
        with pytest.raises(asyncio.CancelledError):
            await task
        check(gate.finished.is_set(), "worker operation ended before cancel")
        stored = await facade.get(identity.logical_key())
        rows, attempts = counts(path)
        check(
            (stored is not None, rows, attempts) in {(True, 1, 1), (False, 0, 0)},
            "row and attempt are fully committed or fully absent",
        )
        checked["committed"] = stored is not None
        again = await facade.accept(identity, receipt(identity))
        check(again.outcome in {"inserted", "replayed"}, "replay after cancel")

    run_with_persistence(tmp_path, body)
    check(checked.get("committed") is True, "worker finished its commit")
    check(counts(path)[0] == 1, "replay after cancel leaves one row")


def test_failed_worker_leaves_no_row(
    path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(db: sqlite3.Connection, *args: Any) -> Accepted:
        raise ValueError("injected worker failure")

    monkeypatch.setattr(facade_module, "accept_result", broken)
    identity = stage_identity()

    async def body(persistence: Phase1Persistence) -> None:
        facade = AcceptanceAsync(persistence, path)
        with pytest.raises(ValueError, match="injected"):
            await facade.accept(identity, receipt(identity))
        check(await facade.get(identity.logical_key()) is None, "no row")
        # The slot is free again: a later call still runs.
        monkeypatch.setattr(facade_module, "accept_result", accept_result)
        done = await facade.accept(identity, receipt(identity))
        check(done.outcome == "inserted", "slot was released after failure")

    run_with_persistence(tmp_path, body)


def test_close_waits_for_accepted_calls_and_rejects_later_ones(
    path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = Gate()
    monkeypatch.setattr(facade_module, "accept_result", gate)
    identity = stage_identity()
    other = stage_identity(scope_key=hexd("7"))

    async def exercise() -> None:
        url = f"sqlite:///{tmp_path / 'phase1.sqlite'}"
        persistence = await Phase1Persistence.open(url)
        facade = AcceptanceAsync(persistence, path)
        call = asyncio.ensure_future(facade.accept(identity, receipt(identity)))
        await wait_for(gate.entered)
        closing = asyncio.ensure_future(persistence.close())
        await asyncio.sleep(0.05)
        check(not closing.done(), "close waits for the accepted call")
        with pytest.raises(RuntimeError):
            await facade.accept(other, receipt(other))
        with pytest.raises(RuntimeError):
            await facade.get(identity.logical_key())
        gate.release.set()
        accepted = await call
        check(accepted.outcome == "inserted", "accepted call completed")
        await closing
        with pytest.raises(RuntimeError):
            await facade.accept(other, receipt(other))

    asyncio.run(exercise())
    check(counts(path) == (1, 1), "the call accepted before close committed")


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
    hits = [name for name, pattern in FORBIDDEN.items() if pattern.search(bad)]
    check(
        {"private store", "private call", "thread start"} <= set(hits),
        f"scan must detect reach-ins, found {hits}",
    )
    clean = "from msgloom.persistence.a2_store import accept_result\n"
    check(not any(p.search(clean) for p in FORBIDDEN.values()), "a2_store is fine")
