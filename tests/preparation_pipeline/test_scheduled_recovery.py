"""Exercise scheduled recovery against real release and persistence stores."""

import asyncio
from dataclasses import replace
from typing import cast

import pytest

from message_ingest.acquisition.handoff import source_state_key
from msgloom.configuration import PreparationOperationData
from msgloom.contracts import (
    AttemptIdentity,
    ExecutionIdentity,
    OperationRequest,
    PhaseCapability,
    TerminalStatus,
)
from msgloom.persistence import Phase1Persistence
from msgloom.preparation_pipeline.intake import PreparationIntakeService
from msgloom.preparation_pipeline.intake_models import IntakeScope
from msgloom.preparation_pipeline.scheduled import ScheduledPreparationHandler
from msgloom.sources.release_reader import ReleaseSourceReader
from tests.application_cli.test_scheduled_prepare import configuration
from tests.preparation_intake_helpers import release, run
from tests.source_reader.release_nonmail_helpers import fact, publish


def repeated_release(saved, suffix):
    """Publish a changed source state that retains the same saved version."""
    item = fact(
        "todo",
        "todo_task",
        '["list","task"]',
        "ev-todo-old",
        scope_kind="todo_list",
        scope_identity="list",
    )
    return publish(
        saved,
        [
            replace(
                item,
                source_state_key=source_state_key({"revision": suffix}),
                run_id="run-" + suffix,
            )
        ],
    )


async def context(saved, tmp_path, *, budget=2, entries=1, intake_limit=1):
    """Open real stores and seed exact durable pending worksets."""
    config = configuration(saved, tmp_path)
    operation = cast(
        PreparationOperationData, config.operation(PhaseCapability.PREPARE)
    )
    operation = replace(
        operation,
        intake_targets=(
            operation.intake_targets[0].model_copy(
                update={"max_pending_worksets": budget}
            ),
        ),
    )
    persistence = await Phase1Persistence.open(config.database_url)
    reader = ReleaseSourceReader(config.source_reader_config())
    scope = IntakeScope(
        catalog=await reader.catalog.catalog_identity(),
        source_id="synthetic-source",
        stream="todo",
        consumer_id="stable",
    )
    service = PreparationIntakeService(persistence, reader)
    for index in range(entries):
        await run(service, scope, identity=f"seed-{index}", limit=intake_limit)
    await reader.close()
    request = OperationRequest(
        ExecutionIdentity("scheduled"),
        "operator",
        PhaseCapability.PREPARE,
    )
    handler = ScheduledPreparationHandler(
        persistence,
        config.source_reader_config(),
        operation,
        AttemptIdentity("scheduled"),
    )
    return persistence, scope, handler, request


def test_incomplete_output_remains_incomplete(saved_catalog, tmp_path):
    """Accepted incomplete preparation must not become aggregate complete."""
    release(saved_catalog)

    async def check():
        persistence, scope, handler, request = await context(saved_catalog, tmp_path)
        try:
            outcome = await handler.run(request)
            states = await persistence.list_preparation_intake_worksets(
                scope,
                pending_only=False,
            )
            if states[0].terminal_status is not TerminalStatus.INCOMPLETE:
                pytest.fail("fixture did not produce accepted incomplete work")
            if outcome.status is not TerminalStatus.INCOMPLETE:
                pytest.fail("aggregate erased accepted INCOMPLETE status")
        finally:
            await persistence.close()

    asyncio.run(check())


def test_failed_workset_does_not_skip_later_pending(
    saved_catalog, tmp_path, monkeypatch
):
    """One corrupt pending item cannot skip a later item in the same budget."""
    repeated_release(saved_catalog, "one")
    repeated_release(saved_catalog, "two")

    async def check():
        persistence, scope, handler, request = await context(
            saved_catalog,
            tmp_path,
            entries=2,
        )
        original = handler._process
        states = await persistence.list_preparation_intake_worksets(scope)
        if len(states) != 2:
            pytest.fail("fixture needs two distinct pending worksets")

        async def fail_first(reference, reader, request):
            if reference == states[0].workset:
                raise ValueError("injected corrupt workset")
            return await original(reference, reader, request)

        monkeypatch.setattr(handler, "_process", fail_first)
        try:
            await handler.run(request)
            remaining = await persistence.list_preparation_intake_worksets(scope)
            if tuple(s.workset for s in remaining) != (states[0].workset,):
                pytest.fail("one failed workset skipped later pending work")
        finally:
            await persistence.close()

    asyncio.run(check())


def test_successful_page_does_not_hide_backlog(saved_catalog, tmp_path, monkeypatch):
    """A terminal first page does not establish that pending queue is empty."""
    repeated_release(saved_catalog, "one")
    repeated_release(saved_catalog, "two")

    async def check():
        persistence, scope, handler, request = await context(
            saved_catalog,
            tmp_path,
            entries=2,
            budget=1,
        )
        # Suppress only aggregation of the known incomplete parser fixture.
        # Real preparation and exact terminal proof still execute unchanged.
        original = handler._process

        async def complete(reference, reader, request):
            result = await original(reference, reader, request)
            if len(result) == 3:
                return result[0], result[1], TerminalStatus.COMPLETE
            return result

        monkeypatch.setattr(handler, "_process", complete)
        try:
            outcome = await handler.run(request)
            if not await persistence.list_preparation_intake_worksets(scope):
                pytest.fail("fixture must retain a second pending workset")
            if outcome.status is not TerminalStatus.INCOMPLETE:
                pytest.fail("successful first page hid pending backlog")
        finally:
            await persistence.close()

    asyncio.run(check())


def test_restart_after_plan_acceptance_before_finalization(
    saved_catalog,
    tmp_path,
    monkeypatch,
):
    """A new execution rebuilds exact proof after the pre-finalization crash."""
    release(saved_catalog)

    async def check():
        persistence, scope, handler, request = await context(saved_catalog, tmp_path)
        finalize = persistence.finalize_preparation_intake_workset

        async def crash(*args, **kwargs):
            raise RuntimeError("crash after accepted preparation")

        monkeypatch.setattr(persistence, "finalize_preparation_intake_workset", crash)
        try:
            await handler.run(request)
            if not await persistence.list_preparation_intake_worksets(scope):
                pytest.fail("crash lost durable pending work")
            monkeypatch.setattr(
                persistence, "finalize_preparation_intake_workset", finalize
            )
            await handler.run(replace(request, execution=ExecutionIdentity("restart")))
            if await persistence.list_preparation_intake_worksets(scope):
                pytest.fail("new execution could not rebuild exact completion proof")
        finally:
            await persistence.close()

    asyncio.run(check())


def test_intake_deadline_cancels_and_drains(saved_catalog, tmp_path, monkeypatch):
    """Finite intake timeout cancels awaited work and leaves no detached task."""
    release(saved_catalog)

    async def check():
        persistence, _scope, handler, request = await context(saved_catalog, tmp_path)
        handler._operation = replace(handler._operation, execution_timeout_seconds=0.02)
        cancelled = asyncio.Event()

        async def stalled(*args, **kwargs):
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        monkeypatch.setattr(PreparationIntakeService, "run", stalled)
        try:
            # The outer watchdog fails the old unbounded code rather than
            # allowing the regression itself to hang indefinitely.
            try:
                async with asyncio.timeout(2):
                    outcome = await handler.run(request)
            except TimeoutError:
                pytest.fail("scheduled intake exceeded finite invocation budget")
            if (
                not cancelled.is_set()
                or outcome.status is not TerminalStatus.INCOMPLETE
            ):
                pytest.fail("intake timeout did not drain and report incomplete")
        finally:
            await persistence.close()

    asyncio.run(check())


def test_duplicate_versions_and_record_bound_use_exact_multiple_plans(
    saved_catalog,
    tmp_path,
):
    """Two frozen inputs for the same version need disjoint exact plans."""
    repeated_release(saved_catalog, "one")
    repeated_release(saved_catalog, "two")

    async def check():
        persistence, scope, handler, request = await context(
            saved_catalog,
            tmp_path,
            intake_limit=2,
        )
        handler._operation = replace(handler._operation, max_records=1)
        try:
            await handler.run(request)
            if await persistence.list_preparation_intake_worksets(scope):
                pytest.fail("bounded exact replay did not finish duplicate versions")
            states = await persistence.list_preparation_intake_worksets(
                scope,
                pending_only=False,
            )
            if len([r for r in states[0].result_refs if r.kind == "prepared"]) != 2:
                pytest.fail("completion proof did not cover both frozen selections")
        finally:
            await persistence.close()

    asyncio.run(check())


@pytest.mark.parametrize("status", [TerminalStatus.FAILED, TerminalStatus.BLOCKED])
def test_unaccepted_plan_keeps_work_pending(
    saved_catalog,
    tmp_path,
    monkeypatch,
    status,
):
    """Neither failure nor duplicate admission constitutes output proof."""
    from msgloom.contracts import OperationOutcome
    from msgloom.preparation_pipeline.handler import PreparationHandler

    release(saved_catalog)

    async def unaccepted(self, request):
        return OperationOutcome(request.execution, request.capability, status)

    original = PreparationHandler.run
    monkeypatch.setattr(PreparationHandler, "run", unaccepted)

    async def check():
        persistence, scope, handler, request = await context(saved_catalog, tmp_path)
        try:
            before = await persistence.get_preparation_intake_cursor(scope)
            committed = await persistence.list_preparation_intake_worksets(scope)
            if len(committed) != 1 or before.last_release_entry_seq == 0:
                pytest.fail("Fixture needs one committed workset and cursor")
            outcome = await handler.run(request)
            pending = await persistence.list_preparation_intake_worksets(scope)
            if tuple(s.workset for s in pending) != (committed[0].workset,):
                pytest.fail("unaccepted plan discharged or replaced pending work")
            if await persistence.get_preparation_intake_cursor(scope) != before:
                pytest.fail("failed preparation rewound the committed cursor")
            if outcome.status is not TerminalStatus.INCOMPLETE:
                pytest.fail("unaccepted plan did not report remaining work")
            monkeypatch.setattr(PreparationHandler, "run", original)
            retry = ScheduledPreparationHandler(
                persistence,
                handler._source,
                handler._operation,
                AttemptIdentity("fresh-retry"),
            )
            await retry.run(
                replace(request, execution=ExecutionIdentity("fresh-retry"))
            )
            states = await persistence.list_preparation_intake_worksets(
                scope, pending_only=False
            )
            if (
                len(states) != 1
                or states[0].workset != committed[0].workset
                or states[0].state != "terminal"
                or states[0].terminal_status
                not in (TerminalStatus.COMPLETE, TerminalStatus.INCOMPLETE)
                or not any(ref.kind == "prepared" for ref in states[0].result_refs)
            ):
                pytest.fail("Fresh retry did not prepare the same committed workset")
            if (
                await persistence.list_preparation_intake_worksets(scope)
                or await persistence.get_preparation_intake_cursor(scope) != before
            ):
                pytest.fail("Successful retry left pending work or rewound cursor")
        finally:
            await persistence.close()

    asyncio.run(check())


def test_external_cancellation_drains_reader_and_keeps_work(
    saved_catalog,
    tmp_path,
    monkeypatch,
):
    """Cancellation drains owned resources without dropping durable work."""
    from msgloom.preparation_pipeline.handler import PreparationHandler

    release(saved_catalog)

    async def check():
        persistence, scope, handler, request = await context(saved_catalog, tmp_path)
        entered = asyncio.Event()
        drained = asyncio.Event()
        closed = asyncio.Event()
        original_close = ReleaseSourceReader.close

        async def stalled(self, request):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                drained.set()

        async def close(self):
            await original_close(self)
            closed.set()

        monkeypatch.setattr(PreparationHandler, "run", stalled)
        monkeypatch.setattr(ReleaseSourceReader, "close", close)
        task = asyncio.create_task(handler.run(request))
        try:
            async with asyncio.timeout(2):
                await entered.wait()
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
            if not drained.is_set() or not closed.is_set():
                pytest.fail("cancelled scheduled command left owned work alive")
            if not await persistence.list_preparation_intake_worksets(scope):
                pytest.fail("cancelled plan dropped pending work")
        finally:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            await persistence.close()

    asyncio.run(check())


def test_configuration_change_preserves_cursor(saved_catalog, tmp_path):
    """Parser and code versions cannot create a new consumer admission scope."""
    release(saved_catalog)

    async def check():
        persistence, scope, handler, request = await context(saved_catalog, tmp_path)
        try:
            before = await persistence.get_preparation_intake_cursor(scope)
            handler._operation = replace(
                handler._operation,
                configuration_version="changed-config",
                code_version="changed-code",
            )
            await handler.run(request)
            after = await persistence.get_preparation_intake_cursor(scope)
            states = await persistence.list_preparation_intake_worksets(
                scope,
                pending_only=False,
            )
            if after != before or len(states) != 1:
                pytest.fail("ordinary configuration change reset consumer progress")
        finally:
            await persistence.close()

    asyncio.run(check())
