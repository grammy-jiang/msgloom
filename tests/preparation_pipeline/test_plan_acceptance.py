"""Only normal producer completion may accept an exact plan manifest."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from msgloom.contracts import AttemptIdentity, TerminalStatus
from msgloom.persistence import DependencyNotReadyError
from msgloom.preparation_pipeline import PreparationHandler
from tests.phase1_foundation import intake_completion_helpers as c
from tests.phase1_foundation import intake_helpers as h


@pytest.mark.parametrize("interruption", ["timeout", "superseded", "cancelled"])
def test_interrupted_plan_outputs_cannot_finish_intake(
    tmp_path,
    monkeypatch,
    interruption,
):
    store = h.store(tmp_path / "neutral.db")
    value, saved, owner, selections = c.admit(store)
    produced = []

    async def interrupt(_self, _request, _records, prepared_refs, _versions, state):
        produced.extend(prepared_refs)
        if interruption == "timeout":
            raise TimeoutError
        if interruption == "cancelled":
            raise asyncio.CancelledError
        with store._write_transaction() as connection:
            connection.execute(
                text(
                    "UPDATE phase1_work_claims SET expires_at=:expiry "
                    "WHERE claim_token=:token"
                ),
                {
                    "expiry": (datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
                    "token": state.claim.token,
                },
            )
        store.acquire_claim(
            state.claim.claim_key,
            state.claim.kind,
            state.claim.execution,
            AttemptIdentity("replacement"),
            (),
            60,
        )
        raise RuntimeError("superseded after prepared output")

    monkeypatch.setattr(PreparationHandler, "_filter_all", interrupt)
    if interruption == "cancelled":
        with pytest.raises(asyncio.CancelledError):
            c.replay(store, owner, selections)
    else:
        outcome = c.replay(store, owner, selections)
        expected = (
            TerminalStatus.INCOMPLETE
            if interruption == "timeout"
            else TerminalStatus.FAILED
        )
        if outcome.status is not expected:
            pytest.fail("Repair changed the manual interruption status")
    with pytest.raises(DependencyNotReadyError):
        store.finalize_preparation_intake_workset(
            saved.result_id,
            TerminalStatus.INCOMPLETE,
            tuple(produced),
            claim=owner,
        )
    if len(store.list_preparation_intake_worksets(value.scope)) != 1:
        pytest.fail("Interrupted producer cleared pending work")
    store.close()


def test_cancellation_before_acceptance_handoff_has_no_receipt(tmp_path, monkeypatch):
    from tests.phase1_foundation.test_preparation_plan_proof import rows

    store = h.store(tmp_path / "neutral.db")
    value, _saved, owner, selections = c.admit(store)
    original = PreparationHandler._group_all

    async def cancel_after_groups(self, *args):
        result = await original(self, *args)
        task = asyncio.current_task()
        if task is None:
            pytest.fail("Handler is not executing in an owned task")
        task.cancel()
        return result

    monkeypatch.setattr(PreparationHandler, "_group_all", cancel_after_groups)
    with pytest.raises(asyncio.CancelledError):
        c.replay(store, owner, selections)
    if any(
        row["accepted_status"] is not None
        for row in rows(
            store,
            "phase1_preparation_plan_proofs",
        )
    ):
        pytest.fail("Cancellation before producer handoff created acceptance")
    if len(store.list_preparation_intake_worksets(value.scope)) != 1:
        pytest.fail("Cancelled handoff lost pending work")
    store.close()


def test_manual_live_acceptance_drains_cancellation_without_contradictory_history(
    tmp_path,
):
    import threading
    from typing import cast

    from sqlalchemy import event

    from msgloom.persistence import Phase1Persistence
    from msgloom.sources import CollectedSourceReader
    from tests.phase1_foundation.test_preparation_plan_proof import rows
    from tests.preparation_pipeline.helpers import plan
    from tests.preparation_pipeline.test_lifecycle import _fixture, _request

    async def exercise():
        path = tmp_path / "neutral.db"
        store = h.store(path)
        persistence = Phase1Persistence(store)
        source, reader = _fixture()
        entered, proceed = threading.Event(), threading.Event()

        def pause(_connection, _cursor, statement, _params, _context, _many):
            if statement.startswith("UPDATE phase1_preparation_plan_proofs"):
                entered.set()
                if not proceed.wait(10):
                    raise RuntimeError("accepted handler did not receive release")

        event.listen(store.engine, "after_cursor_execute", pause)
        handler = PreparationHandler(
            persistence,
            cast(CollectedSourceReader, reader),
            plan(source, attempt=AttemptIdentity("manual-live"), parser_profiles=()),
        )
        task = asyncio.create_task(handler.run(_request("manual-live", source)))
        try:
            if not await asyncio.to_thread(entered.wait, 10):
                pytest.fail("Manual LIVE producer never accepted its manifest")
            task.cancel()
            await asyncio.sleep(0)
            task.cancel()
            if task.done():
                pytest.fail("Cancellation escaped accepted terminal transaction")
            proceed.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            proof = rows(store, "phase1_preparation_plan_proofs")[0]
            history = rows(store, "phase1_claim_attempts")[0]
            if proof["accepted_status"] != "incomplete" or (
                history["terminal_status"] != proof["accepted_status"]
            ):
                pytest.fail("Accepted commit was followed by contradictory cleanup")
            if "collected_selection" not in proof["accepted_result_refs"]:
                pytest.fail("Manual LIVE receipt omitted its capture publication")
            if rows(store, "phase1_work_claims"):
                pytest.fail("Accepted manual plan retained stale ownership")
        finally:
            proceed.set()
            event.remove(store.engine, "after_cursor_execute", pause)
            await persistence.close()

    asyncio.run(exercise())
