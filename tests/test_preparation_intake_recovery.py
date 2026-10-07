"""Failure injection retains atomic admission and reusable exact selections."""

import asyncio

import pytest
from sqlalchemy import update

from msgloom.persistence.records import WORK_CLAIMS
from tests.preparation_intake_helpers import payload, release, run, setup
from tests.source_reader.conftest import saved_catalog as saved_catalog  # noqa: PLC0414


@pytest.mark.parametrize("after", [False, True])
def test_finalization_crash_boundary(saved_catalog, tmp_path, monkeypatch, after):
    seq = release(saved_catalog)

    async def check():
        reader, persistence, scope, service = await setup(saved_catalog, tmp_path)
        original = persistence.finalize_preparation_intake
        saved_refs = []

        async def crash(result, workset, *, claim):
            saved_refs.extend(workset.selection_refs)
            if after:
                await original(result, workset, claim=claim)
            raise RuntimeError("injected finalization crash")

        monkeypatch.setattr(persistence, "finalize_preparation_intake", crash)
        try:
            with pytest.raises(RuntimeError, match="injected"):
                await run(service, scope)
            cursor = await persistence.get_preparation_intake_cursor(scope)
            pending = await persistence.list_preparation_intake_worksets(scope)
            if cursor.last_release_entry_seq != (seq if after else 0):
                pytest.fail("Crash crossed the atomic cursor boundary")
            if len(pending) != int(after):
                pytest.fail("Committed workset is not discoverable after crash")
            monkeypatch.setattr(persistence, "finalize_preparation_intake", original)
            if not after:
                before = await persistence.get_result(saved_refs[0].result_id)
                retry = await payload(
                    persistence, await run(service, scope, identity="retry")
                )
                if retry.selection_refs != tuple(saved_refs):
                    pytest.fail("Retry did not reuse deterministic selection identity")
                if await persistence.get_result(saved_refs[0].result_id) != before:
                    pytest.fail("Retry overwrote immutable selection provenance")
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())


def test_held_entry_advances_only_with_durable_disposition(saved_catalog, tmp_path):
    import hashlib

    from tests.source_reader.release_nonmail_helpers import fact, publish, save_evidence

    save_evidence(saved_catalog, "missing", {"id": "missing-task"})
    digest = hashlib.sha256(b'{"id":"missing-task"}').hexdigest()
    (saved_catalog["evidence_root"] / f"{digest}.bin").unlink()

    seq = publish(
        saved_catalog,
        [
            fact(
                "todo",
                "todo_task",
                '["list","missing-task"]',
                "missing",
                scope_kind="todo_list",
                scope_identity="list",
            )
        ],
    )
    later = release(saved_catalog, suffix="after-held")

    async def check():
        reader, persistence, scope, service = await setup(saved_catalog, tmp_path)
        try:
            value = await payload(persistence, await run(service, scope))
            held = await persistence.list_preparation_intake_held_entries(scope)
            if len(value.held) != 1 or len(held) != 1:
                pytest.fail("Bad evidence advanced without durable held disposition")
            if value.held[0].reason != "materialization_failed":
                pytest.fail("Generic evidence failure was misclassified as corruption")
            if (
                value.held[0].entry.release_entry_seq != seq
                or len(value.selections) != 1
            ):
                pytest.fail("Held entry lost its anchor or poisoned later input")
            if (
                await persistence.get_preparation_intake_cursor(scope)
            ).last_release_entry_seq != later:
                pytest.fail("Held entry blocked accounted cursor progress")
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())


def test_transaction_rollback_and_expired_owner(saved_catalog, tmp_path, monkeypatch):
    from msgloom.persistence import StaleClaimError

    release(saved_catalog)

    async def check():
        reader, persistence, scope, service = await setup(saved_catalog, tmp_path)
        original = persistence.finalize_preparation_intake

        async def expire(result, workset, *, claim):
            with persistence._store.engine.begin() as connection:
                connection.execute(
                    update(WORK_CLAIMS).values(expires_at="2000-01-01T00:00:00+00:00")
                )
            await original(result, workset, claim=claim)

        monkeypatch.setattr(persistence, "finalize_preparation_intake", expire)
        try:
            with pytest.raises(StaleClaimError):
                await run(service, scope)
            if (
                await persistence.get_preparation_intake_cursor(scope)
            ).last_release_entry_seq:
                pytest.fail("Expired owner advanced cursor")
            if await persistence.list_preparation_intake_worksets(scope):
                pytest.fail("Expired owner published workset")
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())


def test_cancelled_finalization_drains_committed_work(
    saved_catalog, tmp_path, monkeypatch
):
    import threading

    release(saved_catalog)

    async def check():
        reader, persistence, scope, service = await setup(saved_catalog, tmp_path)
        entered = asyncio.Event()
        release_write = threading.Event()
        loop = asyncio.get_running_loop()
        original = persistence._store.finalize_preparation_intake

        def blocked(result, workset, *, claim):
            loop.call_soon_threadsafe(entered.set)
            if not release_write.wait(5):
                raise RuntimeError("Test did not release accepted database work")
            original(result, workset, claim=claim)

        monkeypatch.setattr(persistence._store, "finalize_preparation_intake", blocked)
        task = asyncio.create_task(run(service, scope))
        try:
            await asyncio.wait_for(entered.wait(), timeout=5)
            task.cancel()
            release_write.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            if len(await persistence.list_preparation_intake_worksets(scope)) != 1:
                pytest.fail("Cancellation returned before accepted commit drained")
            if not (
                await persistence.get_preparation_intake_cursor(scope)
            ).last_release_entry_seq:
                pytest.fail("Drained finalization lost its cursor")
        finally:
            release_write.set()
            await reader.close()
            await persistence.close()

    asyncio.run(check())


def test_cursor_insert_failure_rolls_back_entire_admission(saved_catalog, tmp_path):
    from sqlalchemy import event

    from msgloom.persistence.records import INTAKE_CURSORS

    release(saved_catalog)

    async def check():
        reader, persistence, scope, service = await setup(saved_catalog, tmp_path)

        def fail_cursor(connection, cursor, statement, parameters, context, many):
            if statement.startswith("INSERT INTO " + INTAKE_CURSORS.name):
                raise RuntimeError("injected cursor insert failure")

        event.listen(persistence._store.engine, "before_cursor_execute", fail_cursor)
        try:
            with pytest.raises(RuntimeError, match="injected cursor"):
                await run(service, scope)
            if await persistence.list_preparation_intake_worksets(scope):
                pytest.fail("Rolled-back admission left a pending workset")
            if (
                await persistence.get_preparation_intake_cursor(scope)
            ).last_release_entry_seq:
                pytest.fail("Rolled-back admission advanced cursor")
        finally:
            event.remove(
                persistence._store.engine, "before_cursor_execute", fail_cursor
            )
            await reader.close()
            await persistence.close()

    asyncio.run(check())


def test_replaced_owner_cannot_finalize_or_finish_successor(
    saved_catalog, tmp_path, monkeypatch
):
    from msgloom.contracts import AttemptIdentity, ClaimKind, ExecutionIdentity
    from msgloom.persistence import StaleClaimError

    release(saved_catalog)

    async def check():
        reader, persistence, scope, service = await setup(saved_catalog, tmp_path)
        original = persistence.finalize_preparation_intake
        successor = None

        async def replace_owner(result, workset, *, claim):
            nonlocal successor
            with persistence._store.engine.begin() as connection:
                connection.execute(
                    update(WORK_CLAIMS)
                    .where(WORK_CLAIMS.c.claim_key == scope.claim_key())
                    .values(expires_at="2000-01-01T00:00:00+00:00")
                )
            successor = await persistence.acquire_claim(
                scope.claim_key(),
                ClaimKind.PREPARE_INTAKE,
                ExecutionIdentity("successor"),
                AttemptIdentity("successor"),
            )
            await original(result, workset, claim=claim)

        monkeypatch.setattr(persistence, "finalize_preparation_intake", replace_owner)
        try:
            with pytest.raises(StaleClaimError):
                await run(service, scope)
            if (
                (
                    await persistence.get_preparation_intake_cursor(scope)
                ).last_release_entry_seq
                or await persistence.list_preparation_intake_worksets(scope)
            ):
                pytest.fail("Replaced owner committed admission")
            inspection = await persistence.inspect_claim(scope.claim_key())
            if successor is None or inspection.current_token != successor:
                pytest.fail("Stale owner cleanup changed successor ownership")
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())


def test_corrupt_prior_anchor_fails_before_next_admission(saved_catalog, tmp_path):
    from msgloom.persistence.records import INTAKE_CURSORS
    from msgloom.sources.models import SourceReferenceError

    release(saved_catalog)

    async def check():
        reader, persistence, scope, service = await setup(saved_catalog, tmp_path)
        try:
            await run(service, scope)
            release(saved_catalog, suffix="later")
            with persistence._store.engine.begin() as connection:
                connection.execute(
                    update(INTAKE_CURSORS).values(last_release_entry_digest="0" * 64)
                )
            before = await persistence.get_preparation_intake_cursor(scope)
            pending = await persistence.list_preparation_intake_worksets(scope)
            with pytest.raises(SourceReferenceError, match="anchor mismatch"):
                await run(service, scope, identity="after-restore")
            if await persistence.get_preparation_intake_cursor(scope) != before:
                pytest.fail("Anchor mismatch changed the saved cursor")
            if await persistence.list_preparation_intake_worksets(scope) != pending:
                pytest.fail("Anchor mismatch admitted later work")
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())
