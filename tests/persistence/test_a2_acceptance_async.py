"""
A2 acceptance contract tests through the async facade (C0-12d).

Every test drives :class:`AcceptanceAsync` with a real
:class:`Phase1Persistence`, real worker threads and real SQLite files under
``tmp_path``. Threading events gate the worker. No test sleeps to win a race.

Cancellation model. ``Phase1Persistence.run_bounded`` delays a cancel until
the worker thread ends, so a cancelled task never interrupts a transaction.
Two cases follow from this contract:

* A cancel after the commit leaves exactly one accepted row. This is case 1.
* A cancel before the commit cannot roll the row back, because the worker
  still finishes its commit. The test proves this. A rollback only happens
  when the worker itself fails before the commit. The test injects that
  failure while a real task cancel is pending, so the rollback path is also
  covered through the facade.
"""

from __future__ import annotations

import asyncio
import sqlite3
import threading
import time
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

import pytest

import msgloom.persistence.a2_acceptance_async as facade_module
from msgloom.a2_kedro.contracts.identity import AttemptProof, StageIdentity
from msgloom.contracts import Limitation, TerminalStatus
from msgloom.persistence.a2_acceptance_async import AcceptanceAsync
from msgloom.persistence.a2_acceptance_models import AcceptanceConflict
from msgloom.persistence.a2_schema import acquire_claim
from msgloom.persistence.a2_store import (
    Accepted,
    PublisherReceipt,
    accept_result,
    get_accepted,
)
from msgloom.persistence.async_store import Phase1Persistence
from tests.a2_kedro.helpers import check, hexd, proof, result_for, stage_identity
from tests.persistence.test_a2_schema_fixtures import build_schema5, raw

DEADLINE = 15.0
STAGE = "SELECT count(*) FROM phase1_a2_accepted_stages"
ATTEMPT = "SELECT outcome FROM phase1_a2_stage_attempts ORDER BY attempt_seq"
INCOMPLETE = {"status": TerminalStatus.INCOMPLETE}
BASE_LIMIT = {**INCOMPLETE, "limitations": (Limitation("code-x", "detail-base"),)}

#: Conflicting body under one key: name -> (base, changes, expected field).
CONFLICTS: dict[str, tuple[dict[str, Any], dict[str, Any], str]] = {
    "status": ({}, INCOMPLETE, "status"),
    "limitations": (
        BASE_LIMIT,
        {**INCOMPLETE, "limitations": (Limitation("code-x", "detail-other"),)},
        "limitations_digest",
    ),
    "metadata-sha": ({}, {"rule_version": "rule-other"}, "stage_metadata_sha256"),
}


def named_proof(name: str) -> AttemptProof:
    """Return a distinct attempt proof with its own claim key."""
    return AttemptProof(
        execution_id=f"exec-{name}",
        attempt_id=name,
        claim_key=f"prepare:{name}",
        claim_token_sha256=hexd("e"),
    )


def receipt(
    identity: StageIdentity, pub: AttemptProof | None = None, **changes: Any
) -> PublisherReceipt:
    """Return a receipt published by ``pub`` (default: fixture attempt w1)."""
    pub = pub if pub is not None else proof("w1")
    return PublisherReceipt(
        result_for(identity, attempt=pub.attempt_id, **changes), pub
    )


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


def rows(path: Path, sql: str) -> list[tuple[Any, ...]]:
    """Read with a fresh connection that never shares state with the worker."""
    connection = raw(path)
    try:
        return connection.execute(sql).fetchall()
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


class CommitGate:
    """
    Connection wrapper that pauses the worker at the ``COMMIT`` statement.

    ``when="before"`` pauses before SQLite runs ``COMMIT``. ``when="after"``
    pauses after SQLite committed. ``reached`` tells the test the worker is
    paused. ``release`` lets the worker go on. With ``fail`` set, a pause
    "before" raises that error instead of committing.
    """

    def __init__(
        self,
        inner: sqlite3.Connection,
        when: str,
        gate: GateState,
    ) -> None:
        self.inner = inner
        self.when = when
        self.gate = gate

    @property
    def in_transaction(self) -> bool:
        return self.inner.in_transaction

    def close(self) -> None:
        self.inner.close()

    def pause(self) -> None:
        self.gate.reached.set()
        if not self.gate.release.wait(timeout=DEADLINE):
            raise TimeoutError("gate was not released")

    def execute(self, sql: str, *args: object) -> sqlite3.Cursor:
        is_commit = sql.startswith("COMMIT")
        if is_commit and self.when == "before":
            self.pause()
            if self.gate.fail is not None:
                raise self.gate.fail
        cursor = self.inner.execute(sql, *args)  # type: ignore[arg-type]
        if is_commit and self.when == "after":
            self.pause()
        return cursor


class GateState:
    """Shared events between the test and the worker thread."""

    def __init__(self, fail: BaseException | None = None) -> None:
        self.reached = threading.Event()
        self.release = threading.Event()
        self.fail = fail


def install_gate(
    monkeypatch: pytest.MonkeyPatch, when: str, fail: BaseException | None = None
) -> GateState:
    """Make the facade run the real ``accept_result`` behind a CommitGate."""
    state = GateState(fail)

    def gated(
        db: sqlite3.Connection, identity: StageIdentity, pub: PublisherReceipt
    ) -> Accepted:
        wrapped = CommitGate(db, when, state)
        return accept_result(wrapped, identity, pub)  # type: ignore[arg-type]

    monkeypatch.setattr(facade_module, "accept_result", gated)
    return state


def test_cancel_after_commit_keeps_exactly_one_row(
    path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = install_gate(monkeypatch, "after")
    identity = stage_identity()
    seen: dict[str, Any] = {}

    async def body(persistence: Phase1Persistence) -> None:
        facade = AcceptanceAsync(persistence, path)
        task = asyncio.ensure_future(facade.accept(identity, receipt(identity)))
        await wait_for(state.reached)
        seen["during"] = rows(path, STAGE)  # SQLite has already committed
        task.cancel()
        state.release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        check(task.cancelled(), "the task ends as cancelled")
        monkeypatch.undo()
        seen["stored"] = await facade.get(identity.logical_key())
        again = await facade.accept(identity, receipt(identity))
        seen["again"] = again.outcome

    run_with_persistence(tmp_path, body)
    check(seen["during"] == [(1,)], "the row was committed before the cancel")
    check(seen["stored"] is not None, "read back through a fresh connection")
    check(seen["stored"].writer == proof("w1"), "the writer proof is stored")
    check(seen["again"] == "replayed", "replay after cancel is idempotent")
    check(rows(path, STAGE) == [(1,)], "exactly one accepted row, no duplicate")
    check(rows(path, ATTEMPT) == [("inserted",), ("replayed",)], "attempts")


def test_cancel_before_commit_still_commits_through_the_facade(
    path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = install_gate(monkeypatch, "before")
    identity = stage_identity()
    seen: dict[str, Any] = {}

    async def body(persistence: Phase1Persistence) -> None:
        facade = AcceptanceAsync(persistence, path)
        task = asyncio.ensure_future(facade.accept(identity, receipt(identity)))
        await wait_for(state.reached)
        seen["during"] = rows(path, STAGE)  # uncommitted data stays invisible
        task.cancel()
        await asyncio.sleep(0)
        check(not task.done(), "cancel waits for the worker thread to end")
        state.release.set()
        with pytest.raises(asyncio.CancelledError):
            await task

    run_with_persistence(tmp_path, body)
    check(seen["during"] == [(0,)], "no row is visible before the commit")
    check(rows(path, STAGE) == [(1,)], "the drained worker finished its commit")


def test_worker_failure_before_commit_rolls_back_under_a_pending_cancel(
    path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = install_gate(monkeypatch, "before", fail=ValueError("injected"))
    identity = stage_identity()
    seen: dict[str, Any] = {}

    async def body(persistence: Phase1Persistence) -> None:
        facade = AcceptanceAsync(persistence, path)
        task = asyncio.ensure_future(facade.accept(identity, receipt(identity)))
        await wait_for(state.reached)
        task.cancel()
        state.release.set()
        with pytest.raises((asyncio.CancelledError, ValueError)):
            await task
        seen["rows"] = rows(path, STAGE)
        seen["attempts"] = rows(path, ATTEMPT)
        monkeypatch.undo()
        done = await facade.accept(identity, receipt(identity))
        seen["retry"] = done.outcome

    run_with_persistence(tmp_path, body)
    check(seen["rows"] == [(0,)], "no accepted row after the rollback")
    check(seen["attempts"] == [], "no attempt row after the rollback")
    check(seen["retry"] == "inserted", "a retry inserts exactly once")
    check(rows(path, STAGE) == [(1,)], "one accepted row after the retry")


def test_same_key_across_attempts_replays_without_duplicate(
    path: Path, tmp_path: Path
) -> None:
    identity = stage_identity()
    setup = raw(path)
    try:
        if acquire_claim(setup, named_proof("w2")) is None:
            pytest.fail("second claim must be acquired")
    finally:
        setup.close()
    seen: list[Accepted] = []

    async def body(persistence: Phase1Persistence) -> None:
        facade = AcceptanceAsync(persistence, path)
        seen.append(await facade.accept(identity, receipt(identity)))
        seen.append(await facade.accept(identity, receipt(identity)))
        seen.append(await facade.accept(identity, receipt(identity, named_proof("w2"))))

    run_with_persistence(tmp_path, body)
    check([a.outcome for a in seen] == ["inserted", "replayed", "replayed"], "outcomes")
    check(seen[1].record == seen[0].record, "same attempt replay returns the row")
    check(seen[2].record == seen[0].record, "other attempt replay returns the row")
    check(rows(path, STAGE) == [(1,)], "exactly one accepted row")
    check(len(rows(path, ATTEMPT)) == 3, "one attempt row per call")


@pytest.mark.parametrize("case", sorted(CONFLICTS))
def test_conflicting_body_is_rejected_and_first_row_stays(
    case: str, path: Path, tmp_path: Path
) -> None:
    base, changes, expected = CONFLICTS[case]
    identity = stage_identity()
    seen: dict[str, Any] = {}

    async def body(persistence: Phase1Persistence) -> None:
        facade = AcceptanceAsync(persistence, path)
        first = await facade.accept(identity, receipt(identity, **base))
        with pytest.raises(AcceptanceConflict) as caught:
            await facade.accept(identity, receipt(identity, **changes))
        seen["fields"] = set(caught.value.fields)
        check(await facade.get(identity.logical_key()) == first.record, "unchanged")
        seen["first"] = first

    run_with_persistence(tmp_path, body)
    check(expected in seen["fields"], f"{seen['fields']} must name {expected}")
    check(rows(path, STAGE) == [(1,)], "no second accepted row")
    check(rows(path, ATTEMPT) == [("inserted",), ("conflict",)], "conflict kept")
    stored = raw(path)
    try:
        record = get_accepted(stored, identity.logical_key())
    finally:
        stored.close()
    check(record == seen["first"].record, "fresh connection sees the first row")


@pytest.mark.parametrize("workers", [2, 4])
def test_concurrent_legitimate_claims_yield_one_accepted_row(
    workers: int, path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = stage_identity()
    names = [f"r{n}" for n in range(workers)]
    setup = raw(path)
    try:
        for name in names:
            if acquire_claim(setup, named_proof(name)) is None:
                pytest.fail("claim must be acquired")
    finally:
        setup.close()
    start = threading.Barrier(workers, timeout=DEADLINE)

    def meet(db: sqlite3.Connection, ident: StageIdentity, pub: PublisherReceipt):
        start.wait()  # all workers are inside the facade at the same time
        return accept_result(db, ident, pub)

    monkeypatch.setattr(facade_module, "accept_result", meet)
    seen: list[Accepted] = []

    async def body(persistence: Phase1Persistence) -> None:
        facade = AcceptanceAsync(persistence, path)
        seen.extend(
            await asyncio.gather(
                *(
                    facade.accept(identity, receipt(identity, named_proof(n)))
                    for n in names
                )
            )
        )

    run_with_persistence(tmp_path, body, limit=workers)
    outcomes = sorted(a.outcome for a in seen)
    check(outcomes == ["inserted"] + ["replayed"] * (workers - 1), f"{outcomes}")
    check(len({a.record.logical_key for a in seen}) == 1, "one logical key")
    check(all(a.record == seen[0].record for a in seen), "same stored record")
    check(rows(path, STAGE) == [(1,)], "exactly one accepted row")
    check(len(rows(path, ATTEMPT)) == workers, "one attempt row per claim")
