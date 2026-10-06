"""Accepted intake writes drain before cancellation or close can escape."""

import asyncio
import threading

import pytest
from sqlalchemy import event

from msgloom.persistence import Phase1Persistence


def test_cancelled_finalization_drains_atomic_write_and_reopens(tmp_path):
    from tests.phase1_foundation import intake_helpers as h

    async def exercise():
        path = tmp_path / "neutral.db"
        store = h.store(path)
        persistence = Phase1Persistence(store)
        value = h.workset()
        token = h.claim(store, value)
        saved = h.result(store, value, token)
        entered = threading.Event()
        proceed = threading.Event()

        def pause(_connection, _cursor, statement, _params, _context, _many):
            if statement.startswith("INSERT INTO phase1_preparation_intake_cursors"):
                entered.set()
                if not proceed.wait(10):
                    raise RuntimeError("test write did not receive release")

        event.listen(store.engine, "before_cursor_execute", pause)
        task = asyncio.create_task(
            persistence.finalize_preparation_intake(saved, value, claim=token)
        )
        try:
            if not await asyncio.to_thread(entered.wait, 10):
                pytest.fail("Real intake write never reached cursor insert")
            task.cancel()
            await asyncio.sleep(0)
            if task.done():
                pytest.fail("Cancellation escaped while the write was still active")
            proceed.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            if (
                await persistence.get_preparation_intake_cursor(value.scope)
                != value.cutoff
            ):
                pytest.fail("Accepted write did not drain atomically")
            if not await persistence.list_preparation_intake_worksets(value.scope):
                pytest.fail("Cancellation lost pending admitted work")
            if not await persistence.list_preparation_intake_held_entries(value.scope):
                pytest.fail("Cancellation lost held admission")
            owner = h.processing_claim(store, saved)
            await persistence.finalize_preparation_intake_workset(
                saved.result_id,
                saved.status,
                (),
                claim=owner,
            )
        finally:
            proceed.set()
            event.remove(store.engine, "before_cursor_execute", pause)
            await persistence.close()

    asyncio.run(exercise())


@pytest.mark.parametrize("phase", ["publication", "receipt", "terminal"])
def test_repeated_cancellation_drains_proof_transactions(tmp_path, phase):
    from msgloom.contracts import ExternalEffectState, TerminalStatus
    from tests.phase1_foundation import intake_completion_helpers as c
    from tests.phase1_foundation import intake_helpers as h
    from tests.phase1_foundation.test_preparation_plan_proof import (
        plan_publication,
        rows,
        semantic,
    )

    path = tmp_path / "neutral.db"
    store = h.store(path)
    outcome = None
    scope = None
    if phase == "terminal":
        workset, saved, owner, selections = c.admit(store)
        scope = workset.scope
        value = workset
        outcome = c.replay(store, owner, selections)
    else:
        owner, saved = plan_publication(store)
        value = semantic(store, saved)

    async def exercise():
        from dataclasses import replace

        persistence = Phase1Persistence(store)
        entered, proceed = threading.Event(), threading.Event()
        prefix = {
            "publication": "INSERT INTO phase1_preparation_result_bindings",
            "receipt": "UPDATE phase1_preparation_plan_proofs",
            "terminal": "UPDATE phase1_preparation_intake_worksets",
        }[phase]

        def pause(_connection, _cursor, statement, _params, _context, _many):
            if statement.startswith(prefix):
                entered.set()
                if not proceed.wait(10):
                    raise RuntimeError("test proof write did not receive release")

        event.listen(store.engine, "after_cursor_execute", pause)
        if phase == "publication":
            operation = persistence.append_result_with_data(
                replace(saved, result_id="second"),
                value,
                claim=owner,
            )
        elif phase == "receipt":
            operation = persistence.finish_claim(
                owner,
                TerminalStatus.COMPLETE,
                ExternalEffectState.NONE,
                accepted_preparation_results=(c.ref(saved),),
            )
        else:
            if outcome is None:
                pytest.fail("Terminal fixture lacks its accepted outcome")
            operation = persistence.finalize_preparation_intake_workset(
                saved.result_id,
                outcome.status,
                outcome.result_refs,
                claim=owner,
            )
        task = asyncio.create_task(operation)
        try:
            if not await asyncio.to_thread(entered.wait, 10):
                pytest.fail("Proof transaction never reached the barrier")
            for _ in range(2):
                task.cancel()
                await asyncio.sleep(0)
            closing = asyncio.create_task(persistence.close())
            await asyncio.sleep(0)
            if task.done() or closing.done():
                pytest.fail("Cancellation or close escaped an active proof write")
            proceed.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            await closing
        finally:
            proceed.set()
            event.remove(store.engine, "after_cursor_execute", pause)
            await persistence.close()

    asyncio.run(exercise())
    reopened = h.store(path)
    if phase == "publication":
        if reopened.get_result("second") is None:
            pytest.fail("Drained publication lost its result")
        if len(rows(reopened, "phase1_preparation_result_bindings")) != 2:
            pytest.fail("Drained publication lost its binding")
    elif phase == "receipt":
        history = rows(reopened, "phase1_claim_attempts")[0]
        if history["terminal_status"] != "complete" or rows(
            reopened, "phase1_work_claims"
        ):
            pytest.fail("Drained acceptance has contradictory terminal ownership")
        reopened.finish_claim(
            owner,
            TerminalStatus.COMPLETE,
            ExternalEffectState.NONE,
            accepted_preparation_results=(c.ref(saved),),
        )
    else:
        if scope is None:
            pytest.fail("Terminal fixture lacks its frozen scope")
        if reopened.list_preparation_intake_worksets(scope):
            pytest.fail("Drained terminal update lost exact accepted completion")
    reopened.close()
