"""Freeze approved pre-ledger history and continue from the release anchor."""

import asyncio
import importlib
from dataclasses import replace

import pytest

from message_ingest.acquisition.handoff import source_state_key
from msgloom.preparation.records import PreparedSourceType
from tests.preparation_intake_helpers import payload, release, run, setup
from tests.source_reader.release_nonmail_helpers import fact, publish


@pytest.mark.parametrize("existing_release", [False, True])
def test_historical_baseline_is_immutable_and_future_intake_continues(
    saved_catalog, tmp_path, existing_release
):
    """Catch duplicated history, fabricated releases, and a lost genesis cut."""

    initial = release(saved_catalog) if existing_release else 0

    async def check():
        reader, persistence, scope, incremental = await setup(saved_catalog, tmp_path)
        try:
            try:
                module = importlib.import_module(
                    "msgloom.preparation_pipeline.historical_baseline"
                )
            except ModuleNotFoundError:
                pytest.fail("Historical baseline operation is missing")
            versions = await reader.list_versions(
                PreparedSourceType.TODO, source_id=scope.source_id, limit=10
            )
            approved = tuple(v for v in versions if "todo-old" in v.version)
            baseline = module.HistoricalBaselineService(persistence, reader)
            result = await run(
                baseline, scope, sources=approved, approval_id="operator-approval"
            )
            workset = await payload(persistence, result)
            if workset.cutoff.last_release_entry_seq != initial or workset.entries:
                pytest.fail("Baseline fabricated a release chronology")
            if workset.baseline_sources != approved:
                pytest.fail("Baseline widened the approved scope")
            selection = await persistence.get_result(
                workset.selection_refs[0].result_id
            )
            if (await payload(persistence, selection)).record.subject != "Old task":
                pytest.fail("Baseline did not freeze exact historical evidence")
            pending = await persistence.select_preparation_intake_worksets(scope)
            if len(pending) != 1 or pending[0].workset.result_id != result.result_id:
                pytest.fail("Genesis baseline is not discoverable")
            first_page = await persistence.list_preparation_intake_worksets(
                scope, limit=1
            )
            if len(first_page) != 1:
                pytest.fail("Baseline missing from first workset page")
            if await persistence.list_preparation_intake_worksets(
                scope, after_seq=initial
            ):
                pytest.fail("Workset paging repeats consumed baseline")
            with pytest.raises(ValueError, match="already"):
                await run(
                    baseline,
                    scope,
                    identity="repeat",
                    sources=approved,
                    approval_id="operator-approval",
                )
            if await run(incremental, scope, identity="empty") is not None:
                pytest.fail("Historical baseline invented incremental work")
            sequence = publish(
                saved_catalog,
                [
                    replace(
                        fact(
                            "todo",
                            "todo_task",
                            '["list","task"]',
                            "ev-todo-new",
                            scope_kind="todo_list",
                            scope_identity="list",
                        ),
                        source_state_key=source_state_key({"version": "future"}),
                    )
                ],
            )
            later = await payload(
                persistence, await run(incremental, scope, identity="future")
            )
            if later.previous != workset.cutoff or len(later.entries) != 1:
                pytest.fail("Future intake did not continue at the baseline anchor")
            if later.cutoff.last_release_entry_seq != sequence:
                pytest.fail("Future release was lost")
            if await payload(persistence, result) != workset:
                pytest.fail("Incremental admission mutated the baseline")
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())


@pytest.mark.parametrize("invalid", ["empty", "approval", "duplicate", "foreign"])
def test_baseline_requires_explicit_approved_scope(saved_catalog, tmp_path, invalid):
    """Reject invalid approval and scope before workset or cursor admission."""
    from msgloom.preparation_pipeline.historical_baseline import (
        HistoricalBaselineService,
    )
    from msgloom.sources.models import SourceReferenceError

    async def check():
        reader, persistence, scope, _ = await setup(saved_catalog, tmp_path)
        try:
            versions = await reader.list_versions(
                PreparedSourceType.TODO, source_id=scope.source_id, limit=10
            )
            sources = versions[:1]
            approval = "approved"
            if invalid == "empty":
                sources = ()
            elif invalid == "approval":
                approval = ""
            elif invalid == "duplicate":
                sources = sources * 2
            else:
                scope = scope.model_copy(update={"stream": "contacts"})
            with pytest.raises((ValueError, SourceReferenceError)):
                await run(
                    HistoricalBaselineService(persistence, reader),
                    scope,
                    sources=sources,
                    approval_id=approval,
                )
            if await persistence.list_preparation_intake_worksets(scope):
                pytest.fail("Rejected approval created a workset")
            if (
                await persistence.get_preparation_intake_cursor(scope)
            ).last_release_entry_seq:
                pytest.fail("Rejected approval advanced the cursor")
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())


def test_baseline_retry_reuses_saved_selections(saved_catalog, tmp_path, monkeypatch):
    """A crash before atomic admission leaves no cursor and reuses exact data."""
    from msgloom.preparation_pipeline.historical_baseline import (
        HistoricalBaselineService,
    )

    async def check():
        reader, persistence, scope, _ = await setup(saved_catalog, tmp_path)
        try:
            sources = (
                await reader.list_versions(
                    PreparedSourceType.TODO, source_id=scope.source_id, limit=10
                )
            )[:1]
            baseline = HistoricalBaselineService(persistence, reader)
            finalize = persistence.finalize_preparation_intake
            saved = []

            async def interrupted(result, workset, *, claim):
                saved.extend(workset.selection_refs)
                raise RuntimeError("before admission")

            monkeypatch.setattr(persistence, "finalize_preparation_intake", interrupted)
            with pytest.raises(RuntimeError, match="before admission"):
                await run(baseline, scope, sources=sources, approval_id="approved")
            if await persistence.list_preparation_intake_worksets(scope):
                pytest.fail("Interrupted baseline became pending")
            if (
                await persistence.get_preparation_intake_cursor(scope)
            ).last_release_entry_seq:
                pytest.fail("Interrupted baseline moved its cursor")
            original = await persistence.get_result(saved[0].result_id)
            monkeypatch.setattr(persistence, "finalize_preparation_intake", finalize)
            result = await run(
                baseline,
                scope,
                identity="retry",
                sources=sources,
                approval_id="approved",
            )
            if (await payload(persistence, result)).selection_refs != tuple(saved):
                pytest.fail("Retry replaced the exact saved selection")
            if await persistence.get_result(saved[0].result_id) != original:
                pytest.fail("Retry changed immutable selection provenance")
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())


@pytest.mark.parametrize("existing_release", [False, True])
def test_matching_pin_schedules_explicit_historical_baseline(
    saved_catalog, tmp_path, existing_release
):
    """Replay only approved history, then continue after its captured anchor."""
    from msgloom.contracts import AttemptIdentity, ExecutionIdentity, TerminalStatus
    from msgloom.preparation_pipeline.historical_baseline import (
        HistoricalBaselineService,
    )
    from msgloom.preparation_pipeline.scheduled import ScheduledPreparationHandler
    from msgloom.sources.release_reader import ReleaseSourceReader
    from tests.preparation_pipeline.test_scheduled_recovery import context

    initial = release(saved_catalog) if existing_release else 0

    async def check():
        persistence, scope, handler, request = await context(
            saved_catalog, tmp_path, entries=0
        )
        reader = ReleaseSourceReader(handler._source)
        try:
            target = handler._operation.intake_targets[0]
            if target.expected_catalog != scope.catalog:
                pytest.fail("Fixture lacks the matching trusted catalog pin")
            versions = await reader.list_versions(
                PreparedSourceType.TODO, source_id=scope.source_id, limit=10
            )
            approved = tuple(v for v in versions if "todo-old" in v.version)
            baseline = await run(
                HistoricalBaselineService(persistence, reader),
                scope,
                sources=approved,
                approval_id="explicit-operator-approval",
            )
            frozen = await payload(persistence, baseline)
            await reader.close()
            outcome = await handler.run(request)
            states = await persistence.list_preparation_intake_worksets(
                scope, pending_only=False
            )
            if (
                len(states) != 1
                or states[0].workset.result_id != baseline.result_id
                or states[0].state != "terminal"
                or states[0].terminal_status
                not in {TerminalStatus.COMPLETE, TerminalStatus.INCOMPLETE}
                or not any(ref.kind == "prepared" for ref in outcome.result_refs)
            ):
                pytest.fail("Scheduled handler did not accept baseline replay")
            prepared = [ref for ref in outcome.result_refs if ref.kind == "prepared"]
            if len(prepared) != 1:
                pytest.fail("Scheduled baseline widened the approved history")
            result = await persistence.get_result(prepared[0].result_id)
            if (await payload(persistence, result)).source != approved[0]:
                pytest.fail("Scheduled baseline prepared an unapproved version")
            cursor = await persistence.get_preparation_intake_cursor(scope)
            if cursor != frozen.cutoff or cursor.last_release_entry_seq != initial:
                pytest.fail("Scheduled replay changed the baseline cursor")
            sequence = publish(
                saved_catalog,
                [
                    replace(
                        fact(
                            "todo",
                            "todo_task",
                            '["list","task"]',
                            "ev-todo-new",
                            scope_kind="todo_list",
                            scope_identity="list",
                        ),
                        source_state_key=source_state_key({"version": "future"}),
                    )
                ],
            )
            successor = ScheduledPreparationHandler(
                persistence,
                handler._source,
                handler._operation,
                AttemptIdentity("future-scheduled"),
            )
            await successor.run(
                replace(request, execution=ExecutionIdentity("future-scheduled"))
            )
            states = await persistence.list_preparation_intake_worksets(
                scope, pending_only=False
            )
            cursor = await persistence.get_preparation_intake_cursor(scope)
            if (
                len(states) != 2
                or any(state.state != "terminal" for state in states)
                or cursor.last_release_entry_seq != sequence
            ):
                pytest.fail("Scheduled successor lost or duplicated release work")
            if await payload(persistence, baseline) != frozen:
                pytest.fail("Scheduled replay mutated the explicit baseline")
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())
