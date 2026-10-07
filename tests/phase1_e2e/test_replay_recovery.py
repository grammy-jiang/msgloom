"""Replay and cancellation recovery acceptance."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from msgloom.ai import AnalysisResponse, AttemptStatus, TrustedPolicy
from msgloom.contracts import (
    ExecutionIdentity,
    PhaseCapability,
    ResultRef,
    TerminalStatus,
    VersionRef,
)
from msgloom.preparation_pipeline import PreparationHandler
from msgloom.sources import CollectedSourceReader
from msgloom.triage import (
    Development,
    EvidenceKind,
    Priority,
    RelationshipStatus,
    TopicAllocation,
    TopicCandidate,
    TopicContinuation,
    TriageCandidate,
    TriageEvidence,
)
from msgloom.triage_input import TrustedInputVersions
from msgloom.triage_pipeline import TriageHandler, TriageMode
from tests.reporting.helpers import plan as report_plan
from tests.triage_pipeline.helpers import FakeRunner

from .helpers import (
    app_for,
    collected_record,
    open_store,
    preparation_plan,
    prepared_records,
    request,
    require_status,
    run_report,
    static_reader,
    triage_config,
)


def _allocation(version: str) -> TopicAllocation:
    return TopicAllocation(
        allocation_key="allocation-replay",
        topic_ref=VersionRef("topic", "replay", "v1"),
        assessment_ref=VersionRef("topic-assessment", "replay", version),
    )


def _candidate(
    allocation: TopicAllocation,
    source: VersionRef,
    *,
    continuation: TopicContinuation | None = None,
) -> TriageCandidate:
    evidence = TriageEvidence(
        kind=EvidenceKind.SOURCE_STATEMENT,
        source_ref=source,
        statement="Synthetic replay source statement.",
    )
    return TriageCandidate(
        topics=(
            TopicCandidate(
                allocation_key=allocation.allocation_key,
                title="Synthetic replay topic",
                source_refs=(source,),
                priority=Priority.IMPORTANT,
                reason="Synthetic replay acceptance evidence.",
                developments=(
                    Development(
                        text="Synthetic replay source statement.",
                        evidence=(evidence,),
                    ),
                ),
                continuation=continuation,
            ),
        ),
        dispositions=(),
    )


class BarrierRunner:
    """Hold the model boundary until the cancellation test releases it."""

    def __init__(self, candidate: TriageCandidate) -> None:
        self.candidate = candidate
        self.entered = asyncio.Event()
        self.release = asyncio.Event()

    async def run(self, attempt, trace_sink):
        """Expose a deterministic ownership barrier, then return the candidate."""
        self.entered.set()
        await self.release.wait()
        return AnalysisResponse(
            attempt=attempt.attempt,
            status=AttemptStatus.COMPLETE,
            structured_output=self.candidate.model_dump(mode="json"),
            trace_count=0,
        )


def test_changed_prompt_replay_uses_saved_context_and_preserves_old_result(
    tmp_path: Path,
) -> None:
    """Prompt replay creates new lineage without recollecting A2 or context."""

    async def exercise() -> None:
        record = collected_record(
            "replay",
            subject="Synthetic replay",
            body="Synthetic replay source statement.",
        )
        store = await open_store(tmp_path / "replay.sqlite3")
        preparation = preparation_plan((record.source,), attempt="replay-prepare")
        prepared = await app_for(
            store,
            PhaseCapability.PREPARE,
            lambda: PreparationHandler(
                store,
                cast(CollectedSourceReader, static_reader(record)),
                preparation,
            ),
        ).run(request(PhaseCapability.PREPARE, "replay-prepare", (record.source,)))
        require_status(prepared, TerminalStatus.COMPLETE, "A2 replay setup failed")
        records = await prepared_records(store, prepared.result_refs)

        first_allocation = _allocation("v1")
        first_config = triage_config(
            records,
            prepared.result_refs,
            preparation,
            (first_allocation,),
            key="replay-v1",
        )
        first_runner = FakeRunner(store, [_candidate(first_allocation, record.source)])
        first = await app_for(
            store,
            PhaseCapability.TRIAGE,
            lambda: TriageHandler(store, first_config, first_runner),
        ).run(
            request(
                PhaseCapability.TRIAGE,
                "replay-triage-v1",
                first_config.plan.expected_targets,
                parameters=first_config.expected_parameters,
            )
        )
        require_status(first, TerminalStatus.COMPLETE, "first A3 replay pass failed")
        old_saved = await store.get_result(first.result_refs[0].result_id)
        if old_saved is None:
            pytest.fail("first A3 result is missing")
        context_ref = next(
            ref for ref in old_saved.input_refs if ref.kind == "working_context"
        )
        first_context = first_runner.attempts[0].context_text

        versions = TrustedInputVersions(
            prompt=VersionRef("prompt", "triage", "v2"),
            model=first_config.versions.model,
            output_schema=first_config.versions.output_schema,
            configuration=first_config.versions.configuration,
        )
        second_allocation = _allocation("v2")
        evidence = TriageEvidence(
            kind=EvidenceKind.SOURCE_STATEMENT,
            source_ref=record.source,
            statement="Synthetic replay source statement.",
        )
        continuation = TopicContinuation(
            prior_topic_ref=first_allocation.topic_ref,
            prior_assessment_ref=first_allocation.assessment_ref,
            status=RelationshipStatus.CONFIRMED,
            reason="Same exact saved source supports continuity.",
            evidence=(evidence,),
        )
        replay_plan = replace(
            first_config.plan,
            prior_triage_results=(first.result_refs[0],),
            topic_allocations=(second_allocation,),
            mode=TriageMode.REPLAY,
            replay_context_result=context_ref,
        )
        replay_config = replace(
            first_config,
            plan=replay_plan,
            versions=versions,
            working_context_config=None,
            capture_time=None,
            prompt_text="Changed synthetic prompt.",
            trusted_policy=TrustedPolicy(
                schemas={versions.output_schema: {"type": "object"}},
                models={versions.model: "synthetic-model"},
            ),
            claim_key="triage:phase1-e2e:replay-v2",
            configuration_version="phase1-e2e-replay-v2",
        )
        replay_runner = FakeRunner(
            store,
            [_candidate(second_allocation, record.source, continuation=continuation)],
        )
        replay = await app_for(
            store,
            PhaseCapability.TRIAGE,
            lambda: TriageHandler(store, replay_config, replay_runner),
        ).run(
            request(
                PhaseCapability.TRIAGE,
                "replay-triage-v2",
                replay_config.plan.expected_targets,
                parameters=replay_config.expected_parameters,
            )
        )
        require_status(replay, TerminalStatus.COMPLETE, "changed-prompt replay failed")
        new_saved = await store.get_result(replay.result_refs[0].result_id)
        if new_saved is None or new_saved.prompt_version != "v2":
            pytest.fail("changed prompt did not create new saved lineage")
        if await store.get_result(first.result_refs[0].result_id) != old_saved:
            pytest.fail("changed prompt mutated the prior accepted result")
        if replay_runner.attempts[0].context_text != first_context:
            pytest.fail("replay recaptured mutable working context")
        if context_ref not in new_saved.input_refs:
            pytest.fail("replay omitted exact saved context dependency")
        await store.close()

    asyncio.run(exercise())


def test_application_cancellation_is_persisted_and_blocks_downstream_complete(
    tmp_path: Path,
) -> None:
    """Cancellation drains owned A3 work before a dependent A5 attempt can pass."""

    async def exercise() -> None:
        record = collected_record(
            "cancel",
            subject="Synthetic cancellation",
            body="Synthetic cancellation source statement.",
        )
        store = await open_store(tmp_path / "cancel.sqlite3")
        preparation = preparation_plan((record.source,), attempt="cancel-prepare")
        prepared = await app_for(
            store,
            PhaseCapability.PREPARE,
            lambda: PreparationHandler(
                store,
                cast(CollectedSourceReader, static_reader(record)),
                preparation,
            ),
        ).run(request(PhaseCapability.PREPARE, "cancel-prepare", (record.source,)))
        require_status(
            prepared, TerminalStatus.COMPLETE, "A2 cancellation setup failed"
        )
        records = await prepared_records(store, prepared.result_refs)
        allocation = TopicAllocation(
            allocation_key="allocation-cancel",
            topic_ref=VersionRef("topic", "cancel", "v1"),
            assessment_ref=VersionRef("topic-assessment", "cancel", "v1"),
        )
        config = triage_config(
            records,
            prepared.result_refs,
            preparation,
            (allocation,),
            key="cancel",
        )
        barrier = BarrierRunner(_candidate(allocation, record.source))
        application = app_for(
            store,
            PhaseCapability.TRIAGE,
            lambda: TriageHandler(store, config, barrier),
        )
        task = asyncio.create_task(
            application.run(
                request(
                    PhaseCapability.TRIAGE,
                    "cancel-triage",
                    config.plan.expected_targets,
                    parameters=config.expected_parameters,
                )
            )
        )
        await asyncio.wait_for(barrier.entered.wait(), timeout=5.0)
        task.cancel()
        barrier.release.set()
        with pytest.raises(asyncio.CancelledError):
            await task

        saved = await store.get_outcome(ExecutionIdentity("cancel-triage"))
        if saved is None or saved.status is not TerminalStatus.CANCELLED:
            pytest.fail("Application did not persist the cancelled terminal outcome")

        missing = ResultRef("cancelled-triage-result", "triage", "1")
        downstream = await run_report(
            store,
            report_plan(missing),
            identity="cancel-downstream-report",
        )
        require_status(
            downstream,
            TerminalStatus.FAILED,
            "stopped A3 work allowed downstream A5 COMPLETE",
        )
        persisted = await store.get_outcome(
            ExecutionIdentity("cancel-downstream-report-execution")
        )
        if persisted is None or persisted.status is not TerminalStatus.FAILED:
            pytest.fail("dependent failure outcome was not durably saved")
        await store.close()

    asyncio.run(exercise())
