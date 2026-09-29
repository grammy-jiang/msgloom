"""Trusted limitation propagation regressions for the A3 producer."""

from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from msgloom.contracts import (
    ExecutionIdentity,
    Limitation,
    OperationRequest,
    PhaseCapability,
    TerminalStatus,
    VersionRef,
)
from msgloom.triage import (
    Priority,
    SourceDisposition,
    SourceDispositionKind,
    TopicAllocation,
    TopicCandidate,
    TriageCandidate,
    TriageData,
)
from msgloom.triage_pipeline import TriageHandler, TriageMode
from msgloom.working_context import MemoryFileSelection
from tests.triage_input.helpers import record, selection
from tests.triage_pipeline.helpers import FakeRunner, open_store, save_selection, setup


def _request(producer, execution: str) -> OperationRequest:
    """Build the exact synthetic request for one producer configuration."""
    return OperationRequest(
        execution=ExecutionIdentity(execution),
        caller="synthetic-app",
        capability=PhaseCapability.TRIAGE,
        target_inputs=producer.plan.expected_targets,
        authority_ref="synthetic-authority",
        parameters=producer.expected_parameters,
    )


async def _final_data(store, outcome) -> tuple[object, TriageData]:
    """Load the exact saved triage result and semantic product."""
    final = await store.get_result(outcome.result_refs[0].result_id)
    if final is None or final.semantic_data_ref is None:
        pytest.fail("saved triage result is missing")
    data = await store.load_semantic_data(final.semantic_data_ref)
    if not isinstance(data, TriageData):
        pytest.fail("saved triage semantic product has an unexpected type")
    return final, data


def test_source_limitations_are_scoped_to_affected_topics(tmp_path) -> None:
    """A saved source gap does not contaminate an unrelated topic."""
    asyncio.run(_source_scoping(tmp_path))


async def _source_scoping(tmp_path) -> None:
    store = await open_store(tmp_path / "source-scoping.sqlite")
    _selected, base, _candidate = setup()
    affected = record("source-1")
    unaffected = record("source-2").model_copy(update={"limitations": ()})
    selected = selection((affected, unaffected)).model_copy(
        update={"versions": base.versions}
    )
    await save_selection(store, selected)
    allocations = (
        TopicAllocation(
            allocation_key="affected",
            topic_ref=VersionRef("topic", "affected", "v1"),
            assessment_ref=VersionRef("topic-assessment", "affected", "v1"),
        ),
        TopicAllocation(
            allocation_key="unaffected",
            topic_ref=VersionRef("topic", "unaffected", "v1"),
            assessment_ref=VersionRef("topic-assessment", "unaffected", "v1"),
        ),
    )
    candidates = [
        TriageCandidate(
            topics=(
                TopicCandidate(
                    allocation_key=allocation.allocation_key,
                    title=allocation.allocation_key,
                    source_refs=(source.source,),
                    priority=Priority.NORMAL,
                    reason="Synthetic scoped topic",
                ),
            ),
            dispositions=(),
        )
        for allocation, source in zip(allocations, (affected, unaffected), strict=True)
    ]
    plan = replace(
        base.plan,
        expected_targets=(affected.source, unaffected.source),
        prepared_results=tuple(item.result_ref for item in selected.prepared),
        filter_results=tuple(item.result_ref for item in selected.filters),
        group_results=tuple(item.result_ref for item in selected.groups),
        roles=selected.roles,
        topic_allocations=allocations,
    )
    producer = replace(
        base,
        plan=plan,
        filter_config=selected.filter_config,
        rule_config=selected.rules.evaluation.config,
    )
    runner = FakeRunner(store, candidates)
    outcome = await TriageHandler(store, producer, runner).run(
        _request(producer, "source-scoping")
    )
    if outcome.status is not TerminalStatus.COMPLETE:
        pytest.fail(f"source-scoped triage failed: {outcome}")
    _final, data = await _final_data(store, outcome)
    by_identity = {topic.topic_ref.identity: topic for topic in data.topics}
    if [item.code for item in by_identity["affected"].limitations] != ["synthetic"]:
        pytest.fail("affected topic did not inherit its saved source limitation")
    if by_identity["unaffected"].limitations:
        pytest.fail("source-specific limitation leaked into an unrelated topic")
    await store.close()


def test_repeated_model_limitation_is_deduplicated(tmp_path) -> None:
    """A model echo of a trusted saved limitation remains one limitation."""
    asyncio.run(_repeated_limitation(tmp_path))


async def _repeated_limitation(tmp_path) -> None:
    store = await open_store(tmp_path / "repeated.sqlite")
    selected, producer, candidate = setup()
    await save_selection(store, selected)
    known = selected.prepared[0].record.limitations[0]
    topic = candidate.topics[0].model_copy(update={"limitations": (known,)})
    runner = FakeRunner(
        store,
        [candidate.model_copy(update={"topics": (topic,)})],
    )
    outcome = await TriageHandler(store, producer, runner).run(
        _request(producer, "repeated")
    )
    if outcome.status is not TerminalStatus.COMPLETE:
        pytest.fail("model repetition incorrectly blocked triage")
    _final, data = await _final_data(store, outcome)
    if data.topics[0].limitations != (known,):
        pytest.fail("trusted and model-repeated limitations were not deduplicated")
    await store.close()


def test_no_reportable_disposition_with_known_gap_requires_review(tmp_path) -> None:
    """Incomplete saved evidence cannot become no-reportable-content."""
    asyncio.run(_no_reportable(tmp_path))


async def _no_reportable(tmp_path) -> None:
    store = await open_store(tmp_path / "no-reportable.sqlite")
    selected, producer, _candidate = setup()
    await save_selection(store, selected)
    source = selected.prepared[0].record.source
    plan = replace(producer.plan, topic_allocations=())
    producer = replace(producer, plan=plan)
    candidate = TriageCandidate(
        topics=(),
        dispositions=(
            SourceDisposition(
                source_ref=source,
                kind=SourceDispositionKind.NO_REPORTABLE_CONTENT,
                reason="Synthetic model found no reportable content",
            ),
        ),
    )
    runner = FakeRunner(store, [candidate])
    outcome = await TriageHandler(store, producer, runner).run(
        _request(producer, "no-reportable")
    )
    if outcome.status is not TerminalStatus.COMPLETE:
        pytest.fail(f"review-required disposition was not saved: {outcome}")
    final, data = await _final_data(store, outcome)
    if data.dispositions[0].kind is not SourceDispositionKind.REVIEW_REQUIRED:
        pytest.fail("known incomplete evidence remained no-reportable-content")
    if not final.limitations or final.limitations[0].code != "synthetic":
        pytest.fail("no-topic source limitation was not retained operation-wide")
    await store.close()


def test_low_value_with_known_gap_is_incomplete(tmp_path) -> None:
    """Known incomplete evidence cannot be finalized as low-value."""
    asyncio.run(_low_value(tmp_path))


async def _low_value(tmp_path) -> None:
    store = await open_store(tmp_path / "low-value.sqlite")
    selected, producer, candidate = setup()
    await save_selection(store, selected)
    low = candidate.topics[0].model_copy(update={"priority": Priority.LOW_VALUE})
    runner = FakeRunner(store, [candidate.model_copy(update={"topics": (low,)})])
    outcome = await TriageHandler(store, producer, runner).run(
        _request(producer, "low-value")
    )
    if outcome.status is not TerminalStatus.INCOMPLETE:
        pytest.fail("known incomplete evidence was accepted as low-value")
    if not outcome.limitations or (
        outcome.limitations[-1].detail != "incomplete-source-low-value"
    ):
        pytest.fail("low-value limitation rejection was not explicit")
    if any(ref.kind == "triage" for ref in outcome.result_refs):
        pytest.fail("low-value rejection published final triage semantics")
    await store.close()


def test_limitation_overflow_is_explicit_and_not_truncated(tmp_path) -> None:
    """More than the bounded topic limitation count remains incomplete."""
    asyncio.run(_overflow(tmp_path))


async def _overflow(tmp_path) -> None:
    store = await open_store(tmp_path / "overflow.sqlite")
    _selected, base, candidate = setup()
    source = record("source-1").model_copy(
        update={
            "limitations": tuple(
                Limitation(f"gap-{index}", "Synthetic bounded gap")
                for index in range(65)
            )
        }
    )
    selected = selection((source,)).model_copy(update={"versions": base.versions})
    await save_selection(store, selected)
    plan = replace(
        base.plan,
        prepared_results=tuple(item.result_ref for item in selected.prepared),
        filter_results=tuple(item.result_ref for item in selected.filters),
        group_results=tuple(item.result_ref for item in selected.groups),
        roles=selected.roles,
    )
    producer = replace(
        base,
        plan=plan,
        filter_config=selected.filter_config,
        rule_config=selected.rules.evaluation.config,
    )
    runner = FakeRunner(store, [candidate])
    outcome = await TriageHandler(store, producer, runner).run(
        _request(producer, "overflow")
    )
    if outcome.status is not TerminalStatus.INCOMPLETE:
        pytest.fail("limitation overflow was silently accepted")
    if not outcome.limitations or (
        outcome.limitations[-1].detail != "topic-limitation-overflow"
    ):
        pytest.fail("limitation overflow did not expose a bounded classification")
    if any(ref.kind == "triage" for ref in outcome.result_refs):
        pytest.fail("limitation overflow published truncated final semantics")
    await store.close()


def test_replay_reuses_saved_context_gap_after_reopen(tmp_path) -> None:
    """Replay retains the saved gap even after the current file appears."""
    asyncio.run(_replay_saved_context(tmp_path))


async def _replay_saved_context(tmp_path) -> None:
    database = tmp_path / "replay-gap.sqlite"
    context_path = tmp_path / "memory.txt"
    store = await open_store(database)
    selected, producer, candidate = setup()
    await save_selection(store, selected)
    if producer.working_context_config is None:
        pytest.fail("live context configuration is missing")
    context_config = producer.working_context_config.model_copy(
        update={
            "selected_files": (
                MemoryFileSelection(
                    selection_id="synthetic-memory",
                    path=str(context_path),
                ),
            ),
            "allowed_roots": (str(tmp_path),),
        }
    )
    producer = replace(producer, working_context_config=context_config)
    first_runner = FakeRunner(store, [candidate])
    first = await TriageHandler(store, producer, first_runner).run(
        _request(producer, "replay-gap-live")
    )
    if first.status is not TerminalStatus.COMPLETE:
        pytest.fail(f"live missing-context triage failed: {first}")
    first_final, _data = await _final_data(store, first)
    context_ref = next(
        ref for ref in first_final.input_refs if ref.kind == "working_context"
    )
    if not any(
        item.code == "working-context-missing" for item in first_final.limitations
    ):
        pytest.fail("live triage did not retain the saved missing-context gap")
    await store.close()

    context_path.write_text("Current content must not affect replay.")
    store = await open_store(database)
    replay_plan = replace(
        producer.plan,
        mode=TriageMode.REPLAY,
        replay_context_result=context_ref,
    )
    replay_config = replace(
        producer,
        plan=replay_plan,
        working_context_config=None,
        capture_time=None,
        claim_key="triage:source-1:replay-gap",
        configuration_version="producer-replay-gap",
    )
    replay_runner = FakeRunner(store, [candidate])
    replay = await TriageHandler(store, replay_config, replay_runner).run(
        _request(replay_config, "replay-gap-saved")
    )
    if replay.status is not TerminalStatus.COMPLETE:
        pytest.fail(f"saved-context replay failed: {replay}")
    replay_final, _replay_data = await _final_data(store, replay)
    if not any(
        item.code == "working-context-missing" for item in replay_final.limitations
    ):
        pytest.fail("replay lost the exact saved working-context gap")
    if '"state":"missing"' not in replay_runner.attempts[0].context_text:
        pytest.fail("replay consulted current context instead of the saved snapshot")
    if str(context_path) in replay_runner.attempts[0].context_text:
        pytest.fail("working-context replay exposed a local file path")
    await store.close()
