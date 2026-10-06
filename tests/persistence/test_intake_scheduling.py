"""Durable bounded rotation cannot let failed work monopolize discovery."""

import asyncio
import threading

import pytest
from sqlalchemy import event

from msgloom.contracts import ExternalEffectState, TerminalStatus
from msgloom.persistence import DependencyNotReadyError, Phase1Persistence
from msgloom.persistence.records import SCHEMA_METADATA
from msgloom.persistence.schema_store import LEGACY_TERMINAL_PREFIX
from tests.phase1_foundation import intake_helpers as h


def admit(store, seq, target=None):
    """Admit a real immutable workset and release its intake claim."""
    target = target or h.scope()
    name = f"{target.consumer_id}-{target.stream}-{seq}"
    value = h.workset(
        previous=store.get_preparation_intake_cursor(target),
        seq=seq,
        target=target,
    )
    owner = h.claim(store, value, identity=name)
    saved = h.result(store, value, owner, result_id=name)
    store.finalize_preparation_intake(saved, value, claim=owner)
    store.finish_claim(owner, TerminalStatus.COMPLETE, ExternalEffectState.NONE)
    return saved


def selected(store, target=None, limit=1):
    """Read observable scheduling order from the public store API."""
    return [
        item.cutoff.last_release_entry_seq
        for item in store.select_preparation_intake_worksets(
            target or h.scope(), limit=limit
        )
    ]


def test_failed_oldest_does_not_monopolize_restarted_invocations(tmp_path):
    path = tmp_path / "rotation.db"
    store = h.store(path)
    for seq in (1, 2, 3):
        admit(store, seq)
    before = store.list_preparation_intake_worksets(h.scope())
    anchor = store.get_preparation_intake_cursor(h.scope())
    store.close()
    actual = []
    for attempt in range(6):
        store = h.store(path)
        try:
            page = store.select_preparation_intake_worksets(h.scope(), limit=1)
            actual.extend(item.cutoff.last_release_entry_seq for item in page)
            saved = store.get_result(page[0].workset.result_id)
            owner = h.processing_claim(store, saved, identity=f"failed-{attempt}")
            store.finish_claim(owner, TerminalStatus.FAILED, ExternalEffectState.NONE)
            if store.list_preparation_intake_worksets(h.scope()) != before:
                pytest.fail("Discovery mutated pending or terminal state")
            if store.get_preparation_intake_cursor(h.scope()) != anchor:
                pytest.fail("Scheduling moved the immutable admission cursor")
        finally:
            store.close()
    if actual != [1, 2, 3, 1, 2, 3]:
        pytest.fail(f"Failed pending work monopolized restart: {actual}")


def test_rotation_finishes_despite_new_admission_each_page(tmp_path):
    path = tmp_path / "arrivals.db"
    store = h.store(path)
    admit(store, 1)
    admit(store, 2)
    actual = selected(store)
    store.close()
    for seq in range(3, 9):
        store = h.store(path)
        try:
            admit(store, seq)
            actual.extend(selected(store))
        finally:
            store.close()
    if actual != [1, 2, 1, 2, 3, 4, 1]:
        pytest.fail(f"New arrivals prevented finite rotation: {actual}")


def test_wrap_is_bounded_unique_and_scope_isolated(tmp_path):
    store = h.store(tmp_path / "wrap.db")
    try:
        other = h.scope(consumer="other")
        for seq in (1, 2, 3):
            admit(store, seq)
            admit(store, seq, other)
        if selected(store, limit=2) != [1, 2]:
            pytest.fail("Initial page was not ordered and bounded")
        if selected(store, limit=2) != [3, 1]:
            pytest.fail("Page did not wrap once in deterministic order")
        if selected(store, other, limit=1) != [1]:
            pytest.fail("One consumer changed another consumer's rotation")
        if selected(store, limit=1024) != [2, 3, 1]:
            pytest.fail("Oversized page duplicated or lost pending work")
        if selected(store, h.scope(consumer="empty")):
            pytest.fail("Empty scope selected another scope's work")
    finally:
        store.close()


@pytest.mark.parametrize("limit", [0, -1, 1025, True, 1.0, "1"])
def test_invalid_limits_leave_rotation_unchanged(tmp_path, limit):
    store = h.store(tmp_path / "bounds.db")
    try:
        admit(store, 1)
        with pytest.raises(ValueError):
            selected(store, limit=limit)
        if selected(store) != [1]:
            pytest.fail("Invalid page changed rotation")
    finally:
        store.close()


def test_terminal_work_is_skipped_without_hiding_pending(tmp_path):
    store = h.store(tmp_path / "terminal.db")
    try:
        first = admit(store, 1)
        admit(store, 2)
        owner = h.processing_claim(store, first)
        store.finalize_preparation_intake_workset(
            first.result_id, TerminalStatus.COMPLETE, (), claim=owner
        )
        if selected(store, limit=1024) != [2]:
            pytest.fail("Selection returned terminal work or lost pending work")
    finally:
        store.close()


def test_legacy_recovery_hold_blocks_rotation_only_in_its_scope(tmp_path):
    store = h.store(tmp_path / "hold.db")
    try:
        admit(store, 1)
        other = h.scope(consumer="other")
        admit(store, 1, other)
        with store.engine.begin() as connection:
            connection.execute(
                SCHEMA_METADATA.insert().values(
                    key=LEGACY_TERMINAL_PREFIX + "legacy",
                    value=h.scope().claim_key(),
                )
            )
        with pytest.raises(DependencyNotReadyError, match="recovery-hold"):
            selected(store)
        if selected(store, other) != [1]:
            pytest.fail("Legacy hold escaped its own scope")
    finally:
        store.close()


@pytest.mark.parametrize("existing", [False, True])
def test_failed_rotation_write_rolls_back_and_restarts(tmp_path, existing):
    path = tmp_path / "rollback.db"
    store = h.store(path)
    for seq in (1, 2, 3):
        admit(store, seq)
    if existing:
        selected(store)

    def reject(_conn, _cursor, statement, _params, _context, _many):
        if statement.startswith(
            ("INSERT INTO phase1_schema_metadata", "UPDATE phase1_schema_metadata")
        ):
            raise RuntimeError("injected rotation write failure")

    event.listen(store.engine, "after_cursor_execute", reject)
    try:
        with pytest.raises(RuntimeError, match="injected rotation"):
            selected(store)
    finally:
        event.remove(store.engine, "after_cursor_execute", reject)
        store.close()
    store = h.store(path)
    try:
        if selected(store) != ([2] if existing else [1]):
            pytest.fail("Failed selection leaked a rotation advance")
    finally:
        store.close()


def test_async_cancellation_drains_rotation_before_restart(tmp_path):
    path = tmp_path / "cancel.db"

    async def exercise():
        store = h.store(path)
        for seq in (1, 2, 3):
            admit(store, seq)
        persistence = Phase1Persistence(store)
        entered, proceed = threading.Event(), threading.Event()

        def pause(_conn, _cursor, statement, _params, _context, _many):
            if statement.startswith("INSERT INTO phase1_schema_metadata"):
                entered.set()
                if not proceed.wait(5):
                    raise RuntimeError("rotation barrier was not released")

        event.listen(store.engine, "after_cursor_execute", pause)
        task = asyncio.create_task(
            persistence.select_preparation_intake_worksets(h.scope(), limit=1)
        )
        try:
            if not await asyncio.to_thread(entered.wait, 5):
                pytest.fail("Selection did not reach its durable write")
            task.cancel()
            turn = asyncio.get_running_loop().create_future()
            asyncio.get_running_loop().call_soon(turn.set_result, None)
            await turn
            if task.done():
                pytest.fail("Cancellation escaped an active rotation write")
            proceed.set()
            with pytest.raises(asyncio.CancelledError):
                await task
        finally:
            proceed.set()
            event.remove(store.engine, "after_cursor_execute", pause)
            await persistence.close()

    asyncio.run(exercise())
    store = h.store(path)
    try:
        if selected(store) != [2]:
            pytest.fail("Cancelled selection lost its committed rotation")
    finally:
        store.close()


def test_independent_store_connections_share_serial_rotation(tmp_path):
    path = tmp_path / "concurrent.db"
    first = h.store(path)
    second = h.store(path)
    try:
        for seq in (1, 2, 3):
            admit(first, seq)
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(selected, store) for store in (first, second)]
            pages = sorted(future.result(timeout=5) for future in futures)
        if pages != [[1], [2]]:
            pytest.fail(f"Concurrent discovery lost rotation updates: {pages}")
        if selected(first) != [3]:
            pytest.fail("Concurrent rotation did not preserve the next position")
    finally:
        first.close()
        second.close()
