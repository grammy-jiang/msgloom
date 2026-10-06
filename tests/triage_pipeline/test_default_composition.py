"""Check default producer composition and owned stage cancellation."""

import asyncio
from dataclasses import replace
from pathlib import Path
from threading import Event
from typing import cast

import pytest

from msgloom.contracts import AttemptIdentity, TerminalStatus
from msgloom.persistence import Phase1Persistence
from msgloom.preparation import DocumentFormat
from msgloom.preparation_pipeline import PreparationHandler
from msgloom.reporting import SavedReport
from msgloom.reporting import handler as reporting_handler
from msgloom.sources import CollectedSourceReader
from msgloom.triage import Development, EvidenceKind, Priority, TriageEvidence
from msgloom.triage_pipeline import TriageHandler
from tests.preparation_pipeline.helpers import plan as preparation_plan
from tests.preparation_pipeline.helpers import profiles
from tests.preparation_pipeline.test_lifecycle import _fixture
from tests.preparation_pipeline.test_lifecycle import _request as preparation_request
from tests.reporting.helpers import plan as report_plan
from tests.reporting.test_handler import _handler as report_handler
from tests.reporting.test_handler import _request as report_request
from tests.triage_pipeline.helpers import FakeRunner, save_selection, setup
from tests.triage_pipeline.test_deadline_boundaries import deadline_clock
from tests.triage_pipeline.test_handler import request as triage_request


def test_default_prepare_triage_report_chain_survives_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Compose real producers and parsers with an injected AI runner."""

    async def exercise() -> None:
        url = f"sqlite:///{tmp_path / 'composed.db'}"
        store = await Phase1Persistence.open(url)
        source, reader = _fixture()
        preparation = preparation_plan(
            source,
            attempt=AttemptIdentity("composed-prepare"),
            parser_profiles=profiles(DocumentFormat.TEXT, DocumentFormat.JSON),
        )
        try:
            prepared = await PreparationHandler(
                store, cast(CollectedSourceReader, reader), preparation
            ).run(preparation_request("composed-prepare", source))
            if prepared.status is not TerminalStatus.COMPLETE:
                pytest.fail("Actual preparation did not complete")
            _selected, base, candidate = setup()
            chosen = replace(
                base.plan,
                expected_targets=(source,),
                prepared_results=tuple(
                    ref for ref in prepared.result_refs if ref.kind == "prepared"
                ),
                filter_results=tuple(
                    ref for ref in prepared.result_refs if ref.kind == "filter_result"
                ),
                group_results=tuple(
                    ref for ref in prepared.result_refs if ref.kind == "group_result"
                ),
                roles=(base.plan.roles[0].model_copy(update={"source_ref": source}),),
            )
            config = replace(base, plan=chosen, filter_config=preparation.filter_config)
            topic = candidate.topics[0].model_copy(
                update={
                    "source_refs": (source,),
                    "priority": Priority.IMPORTANT,
                    "developments": (
                        Development(
                            text="Synthetic body",
                            evidence=(
                                TriageEvidence(
                                    kind=EvidenceKind.SOURCE_STATEMENT,
                                    source_ref=source,
                                    statement="Synthetic body",
                                ),
                            ),
                        ),
                    ),
                }
            )
            candidate = candidate.model_copy(update={"topics": (topic,)})
            runner = FakeRunner(store, [candidate])
            triaged = await TriageHandler(store, config, runner).run(
                triage_request(config, "composed-triage")
            )
            if triaged.status is not TerminalStatus.COMPLETE or runner.calls != 1:
                pytest.fail(
                    f"Default A3 did not consume the actual A2 chain: {triaged}"
                )
            plan = report_plan(*triaged.result_refs)
            # Isolate semantic reporting/restart checks from host scheduling.
            # Keep the real five-second timeout and ten-second claim lease.
            with (
                deadline_clock(monkeypatch) as clock,
                monkeypatch.context() as scoped,
            ):
                scoped.setattr(reporting_handler, "monotonic", clock.time)
                reported = await report_handler(store, plan).run(report_request(plan))
            if reported.status is not TerminalStatus.COMPLETE:
                pytest.fail(
                    f"Default reporting did not consume actual A3 output: {reported}"
                )
            values = {}
            for ref in (
                *prepared.result_refs,
                *triaged.result_refs,
                *reported.result_refs,
            ):
                saved = await store.get_result(ref.result_id)
                if saved is None or saved.semantic_data_ref is None:
                    pytest.fail("A produced result lacks durable semantic data")
                values[ref] = (
                    saved,
                    await store.load_semantic_data(saved.semantic_data_ref),
                )
            report = values[reported.result_refs[0]][1]
            if not isinstance(report, SavedReport):
                pytest.fail("Default report codec returned the wrong product")
            for part in report.parts:
                if (
                    "Synthetic body" not in part.plain_text
                    or "Synthetic body" not in part.html
                ):
                    pytest.fail("Cross-stage evidence was lost during rendering")
            triage = values[triaged.result_refs[0]][0]
            if not triage.prepared_versions or any(
                ref.kind != "prepared" for ref in triage.prepared_versions
            ):
                pytest.fail("A3 confused source and prepared lineage")
        finally:
            await store.close()
        reopened = await Phase1Persistence.open(url)
        try:
            for ref, (expected, data) in values.items():
                saved = await reopened.get_result(ref.result_id)
                if (
                    saved != expected
                    or saved is None
                    or saved.semantic_data_ref is None
                ):
                    pytest.fail("Restart changed a produced stage result")
                if await reopened.load_semantic_data(saved.semantic_data_ref) != data:
                    pytest.fail("Restart changed immutable cross-stage semantics")
        finally:
            await reopened.close()

    asyncio.run(exercise())


def test_cancelled_rule_work_keeps_cancellation_after_late_validation_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Preserve cancellation and release the claim after late rule failure."""

    async def exercise() -> None:
        store = await Phase1Persistence.open(f"sqlite:///{tmp_path / 'cancel.db'}")
        selected, config, candidate = setup()
        await save_selection(store, selected)
        runner = FakeRunner(store, [candidate])
        entered = asyncio.Event()
        release = Event()
        loop = asyncio.get_running_loop()

        def blocked_rules(*args):
            loop.call_soon_threadsafe(entered.set)
            if not release.wait(timeout=2.0):
                raise RuntimeError("Owned rule work blocked the event loop")
            raise ValueError("Synthetic late rule rejection")

        monkeypatch.setattr(
            "msgloom.triage_pipeline.handler.evaluate_rule_set", blocked_rules
        )
        task = asyncio.create_task(
            TriageHandler(store, config, runner).run(triage_request(config))
        )
        try:
            await asyncio.wait_for(entered.wait(), timeout=5.0)
            task.cancel()
            await asyncio.sleep(0)
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            if runner.calls:
                pytest.fail("Cancelled rule work reached the model boundary")
            snapshot = await store.inspect_claim(config.claim_key)
            if snapshot.current_token is not None:
                pytest.fail("Cancelled owned work retained its safe claim")
        finally:
            release.set()
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            await store.close()

    asyncio.run(exercise())
