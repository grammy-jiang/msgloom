"""Real-persistence REPORT_BUILD handler and replay tests."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from msgloom.application import Application
from msgloom.contracts import (
    AttemptIdentity,
    ExecutionIdentity,
    OperationRequest,
    PhaseCapability,
    ResultRef,
    TerminalStatus,
    TrustedAdmission,
)
from msgloom.reporting import (
    PendingAssessmentWarning,
    RendererConfig,
    ReportBuildHandler,
    ReportHandlerConfig,
    SavedReport,
)
from msgloom.reporting.models import ReportSelectionPlan
from tests.reporting.helpers import (
    open_store,
    plan,
    policy,
    ref,
    save_triage,
    topic,
    triage_data,
)


def _config(identity: str = "report-result") -> ReportHandlerConfig:
    return ReportHandlerConfig(
        report_ref=ref("report", identity),
        result_id=identity,
        semantic_data_id=f"data-{identity}",
        selection_result_id=f"selection-{identity}",
        selection_semantic_data_id=f"selection-data-{identity}",
        max_input_bytes=4 * 1024 * 1024,
        attempt=AttemptIdentity(f"attempt-{identity}"),
        code_version="report-build-test",
        expected_parameters=(("mode", "scheduled"),),
        timeout_seconds=5.0,
        claim_lease_seconds=10.0,
    )


def _request(
    selection: ReportSelectionPlan,
    identity: str = "report-execution",
) -> OperationRequest:
    return OperationRequest(
        execution=ExecutionIdentity(identity),
        caller="synthetic-owner",
        capability=PhaseCapability.REPORT_BUILD,
        target_inputs=selection.request_targets,
        authority_ref="trusted-report-build",
        parameters=(("mode", "scheduled"),),
    )


def _handler(
    store: object, selection: ReportSelectionPlan, identity: str = "report-result"
) -> ReportBuildHandler:
    return ReportBuildHandler(
        policy=policy(),
        selection_plan=selection,
        persistence=store,  # type: ignore[arg-type]
        renderer_config=RendererConfig(
            max_part_bytes=100_000,
            max_total_bytes=300_000,
            max_parts=8,
        ),
        config=_config(identity),
    )


def test_application_builds_saved_report_and_restart_replays_exact_outputs(
    tmp_path: Path,
) -> None:
    """Application saves exact report output that survives persistence restart."""

    async def exercise() -> None:
        path = tmp_path / "phase1.sqlite3"
        store = await open_store(path)
        item = topic()
        triage_ref = await save_triage(store, triage_data(item))
        warning = PendingAssessmentWarning(
            topic_ref=item.topic_ref,
            selected_assessment_ref=item.assessment_ref,
            pending_ref=ref("topic-assessment", "pending-newer"),
            detail="Newer source work remains pending.",
        )
        selection = plan(triage_ref).model_copy(update={"pending_warnings": (warning,)})
        app = Application(
            store,
            trusted_admissions=(
                TrustedAdmission(
                    caller="synthetic-owner",
                    authority_ref="trusted-report-build",
                    capabilities=frozenset({PhaseCapability.REPORT_BUILD}),
                ),
            ),
            report_build_factory=lambda: _handler(store, selection),
        )
        outcome = await app.run(_request(selection))
        if outcome.status is not TerminalStatus.INCOMPLETE:
            pytest.fail("pending warning did not produce an honest incomplete outcome")
        if len(outcome.result_refs) != 1:
            pytest.fail("report build did not return the exact saved result reference")
        saved_result = await store.get_result("report-result")
        if saved_result is None or saved_result.semantic_data_ref is None:
            pytest.fail("saved report stage result is missing")
        saved = await store.load_semantic_data(saved_result.semantic_data_ref)
        if not isinstance(saved, SavedReport):
            pytest.fail("saved report semantic payload has the wrong type")
        expected_parts = saved.parts
        await store.close()

        reopened = await open_store(path)
        try:
            replay_result = await reopened.get_result("report-result")
            if replay_result is None or replay_result.semantic_data_ref is None:
                pytest.fail("report result did not survive restart")
            replay = await reopened.load_semantic_data(replay_result.semantic_data_ref)
            if not isinstance(replay, SavedReport):
                pytest.fail("replayed report semantic payload has the wrong type")
            if replay.parts != expected_parts:
                pytest.fail("restart changed exact saved report output")
            if replay.pending_warnings != (warning,):
                pytest.fail("pending-newer warning was not frozen in the report")
        finally:
            await reopened.close()

    asyncio.run(exercise())


def test_handler_rejects_request_mismatch_before_persistence_access(
    tmp_path: Path,
) -> None:
    """Capability, targets, and parameters must exactly match trusted config."""

    async def exercise() -> None:
        store = await open_store(tmp_path / "mismatch.sqlite3")
        try:
            selection = plan(ResultRef("missing", "triage", "1"))
            handler = _handler(store, selection)
            request = _request(selection)
            wrong = OperationRequest(
                execution=request.execution,
                caller=request.caller,
                capability=request.capability,
                target_inputs=(ref("report-target", "wrong"),),
                authority_ref=request.authority_ref,
                parameters=request.parameters,
            )
            outcome = await handler.run(wrong)
            if outcome.status is not TerminalStatus.FAILED:
                pytest.fail("mismatched target was not rejected")
            duplicate = OperationRequest(
                execution=request.execution,
                caller=request.caller,
                capability=request.capability,
                target_inputs=request.target_inputs,
                authority_ref=request.authority_ref,
                parameters=(("mode", "scheduled"), ("mode", "scheduled")),
            )
            outcome = await handler.run(duplicate)
            if outcome.status is not TerminalStatus.FAILED:
                pytest.fail("duplicate request parameters were not rejected")
        finally:
            await store.close()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "selected_ref",
    (
        ResultRef("missing", "triage", "1"),
        ResultRef("wrong-schema", "triage", "999"),
    ),
)
def test_handler_fails_closed_for_missing_or_schema_invalid_input(
    tmp_path: Path,
    selected_ref: ResultRef,
) -> None:
    """Missing or unregistered declared dependencies never reach rendering."""

    async def exercise() -> None:
        store = await open_store(tmp_path / f"{selected_ref.result_id}.sqlite3")
        try:
            selection = plan(selected_ref)
            outcome = await _handler(store, selection).run(_request(selection))
            if outcome.status is not TerminalStatus.FAILED:
                pytest.fail("invalid declared input did not fail report build")
            if outcome.result_refs:
                pytest.fail("invalid input unexpectedly published a report result")
        finally:
            await store.close()

    asyncio.run(exercise())


def test_handler_failed_write_returns_failure_and_releases_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed report write cannot produce a successful operation outcome."""

    async def exercise() -> None:
        store = await open_store(tmp_path / "failed-write.sqlite3")
        triage_ref = await save_triage(store, triage_data(topic()))
        selection = plan(triage_ref)
        original = store.append_result_with_data

        async def fail_write(result: object, value: object) -> None:
            del result, value
            from msgloom.persistence import ImmutableRecordError

            raise ImmutableRecordError("synthetic write failure")

        monkeypatch.setattr(store, "append_result_with_data", fail_write)
        first = await _handler(store, selection).run(_request(selection))
        if first.status is not TerminalStatus.FAILED or first.result_refs:
            pytest.fail("failed write produced a successful report outcome")

        monkeypatch.setattr(store, "append_result_with_data", original)
        second = await _handler(store, selection, "report-result-retry").run(
            _request(selection, "retry-execution")
        )
        if second.status is not TerminalStatus.COMPLETE:
            pytest.fail("failed write left the report claim unavailable")
        await store.close()

    asyncio.run(exercise())


def test_concurrent_claim_and_cancellation_use_deterministic_barrier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only one policy build owns work; cancellation releases after its barrier."""

    async def exercise() -> None:
        store = await open_store(tmp_path / "concurrent.sqlite3")
        triage_ref = await save_triage(store, triage_data(topic()))
        selection = plan(triage_ref)
        first_handler = _handler(store, selection, "report-first")
        entered = asyncio.Event()
        release = asyncio.Event()
        original_load = first_handler._load_inputs

        async def blocked_load() -> object:
            entered.set()
            await release.wait()
            return await original_load()

        monkeypatch.setattr(first_handler, "_load_inputs", blocked_load)
        first_task = asyncio.create_task(
            first_handler.run(_request(selection, "first-execution"))
        )
        await entered.wait()

        second = await _handler(store, selection, "report-second").run(
            _request(selection, "second-execution")
        )
        if second.status is not TerminalStatus.FAILED:
            pytest.fail("concurrent policy build bypassed the durable claim")

        first_task.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await first_task

        third = await _handler(store, selection, "report-third").run(
            _request(selection, "third-execution")
        )
        if third.status is not TerminalStatus.COMPLETE:
            pytest.fail("cancelled owner did not release the report build claim")
        await store.close()

    asyncio.run(exercise())


def test_handler_rejects_saved_unacceptable_triage_input(tmp_path: Path) -> None:
    """A durable but unacceptable triage result cannot supply report topics."""

    async def exercise() -> None:
        store = await open_store(tmp_path / "unacceptable.sqlite3")
        try:
            triage_ref = await save_triage(
                store,
                triage_data(topic()),
                result_id="unacceptable-triage",
                acceptable=False,
            )
            selection = plan(triage_ref)
            outcome = await _handler(store, selection).run(_request(selection))
            if outcome.status is not TerminalStatus.FAILED or outcome.result_refs:
                pytest.fail("unacceptable triage input published a report")
        finally:
            await store.close()

    asyncio.run(exercise())


def test_failed_render_keeps_frozen_selection_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Selection is durable before rendering and survives a render failure."""

    async def exercise() -> None:
        store = await open_store(tmp_path / "render-failure.sqlite3")
        triage_ref = await save_triage(store, triage_data(topic()))
        selection = plan(triage_ref)

        def fail_render(*args: object, **kwargs: object) -> object:
            del args, kwargs
            from msgloom.reporting import ReportBuildError

            raise ReportBuildError("synthetic render failure")

        monkeypatch.setattr("msgloom.reporting.handler.render_report", fail_render)
        outcome = await _handler(store, selection).run(_request(selection))
        if outcome.status is not TerminalStatus.FAILED:
            pytest.fail("render failure did not fail the operation")
        frozen_result = await store.get_result("selection-report-result")
        if frozen_result is None or frozen_result.semantic_data_ref is None:
            pytest.fail("render failure lost the pre-render selection snapshot")
        frozen = await store.load_semantic_data(frozen_result.semantic_data_ref)
        from msgloom.reporting import FrozenReportSelection

        if not isinstance(frozen, FrozenReportSelection):
            pytest.fail("saved pre-render evidence has the wrong semantic type")
        if frozen.inputs[0].result_ref != triage_ref:
            pytest.fail("frozen selection lost its exact triage result reference")
        await store.close()

    asyncio.run(exercise())


def test_selection_write_failure_prevents_render(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rendering cannot start before the frozen selection write commits."""

    async def exercise() -> None:
        store = await open_store(tmp_path / "selection-write-failure.sqlite3")
        triage_ref = await save_triage(store, triage_data(topic()))
        selection = plan(triage_ref)
        rendered = False

        def observe_render(*args: object, **kwargs: object) -> object:
            nonlocal rendered
            del args, kwargs
            rendered = True
            raise RuntimeError("render should not run")

        async def fail_write(result: object, value: object) -> None:
            del result, value
            from msgloom.persistence import ImmutableRecordError

            raise ImmutableRecordError("synthetic write failure")

        monkeypatch.setattr("msgloom.reporting.handler.render_report", observe_render)
        monkeypatch.setattr(store, "append_result_with_data", fail_write)
        outcome = await _handler(store, selection).run(_request(selection))
        if outcome.status is not TerminalStatus.FAILED:
            pytest.fail("selection write failure did not fail the operation")
        if rendered:
            pytest.fail("rendering started before selection persistence")
        await store.close()

    asyncio.run(exercise())


def test_slow_render_drains_deadline_and_keeps_event_loop_responsive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Synchronous rendering runs off-loop and cannot publish after its deadline."""

    async def exercise() -> None:
        from time import sleep

        import msgloom.reporting.handler as handler_module

        store = await open_store(tmp_path / "slow-render.sqlite3")
        triage_ref = await save_triage(store, triage_data(topic()))
        selection = plan(triage_ref)
        original = handler_module.render_report

        def slow_render(*args: object, **kwargs: object) -> object:
            sleep(0.30)
            return original(*args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(handler_module, "render_report", slow_render)
        config = _config("slow-report").model_copy(
            update={"timeout_seconds": 0.20, "claim_lease_seconds": 2.0}
        )
        handler = ReportBuildHandler(
            policy=policy(),
            selection_plan=selection,
            persistence=store,
            renderer_config=RendererConfig(
                max_part_bytes=100_000,
                max_total_bytes=300_000,
                max_parts=8,
            ),
            config=config,
        )
        ticks = 0
        running = True

        async def ticker() -> None:
            nonlocal ticks
            while running:
                ticks += 1
                await asyncio.sleep(0.01)

        tick_task = asyncio.create_task(ticker())
        outcome = await handler.run(_request(selection, "slow-execution"))
        running = False
        await tick_task
        if outcome.status is not TerminalStatus.FAILED:
            pytest.fail("expired slow render published an acceptable report")
        if ticks < 3:
            pytest.fail("synchronous rendering blocked the event loop")
        if await store.get_result("slow-report") is not None:
            pytest.fail("expired render persisted an acceptable report")
        if await store.get_result("selection-slow-report") is None:
            pytest.fail("expired render lost its frozen selection evidence")
        await store.close()

    asyncio.run(exercise())
