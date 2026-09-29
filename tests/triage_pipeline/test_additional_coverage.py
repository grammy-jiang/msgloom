"""Additional finite A3 coverage for identity and context limitations."""

from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from msgloom.ai import AnalysisResponse, AttemptStatus
from msgloom.contracts import (
    ExecutionIdentity,
    OperationRequest,
    PhaseCapability,
    TerminalStatus,
    VersionRef,
)
from msgloom.triage import (
    Priority,
    TopicAllocation,
    TopicCandidate,
    TriageCandidate,
    TriageData,
)
from msgloom.triage_pipeline import TriageHandler
from msgloom.working_context import MemoryFileSelection
from tests.triage_input.helpers import record, selection
from tests.triage_pipeline.helpers import FakeRunner, open_store, save_selection, setup


def request(producer, execution):
    """Return the exact synthetic operation request."""
    return OperationRequest(
        execution=ExecutionIdentity(execution),
        caller="synthetic-app",
        capability=PhaseCapability.TRIAGE,
        target_inputs=producer.plan.expected_targets,
        authority_ref="synthetic-authority",
        parameters=producer.expected_parameters,
    )


def test_same_subject_distinct_groups_keep_distinct_allocations(tmp_path):
    """Display subject equality never merges independent source groups."""
    asyncio.run(_distinct_groups(tmp_path))


async def _distinct_groups(tmp_path):
    store = await open_store(tmp_path / "groups.sqlite")
    _base_selected, base, _candidate = setup()
    first = record("source-1")
    second = record("source-2")
    selected = selection((first, second)).model_copy(update={"versions": base.versions})
    await save_selection(store, selected)
    allocations = (
        TopicAllocation(
            allocation_key="allocation-a",
            topic_ref=VersionRef("topic", "topic-a", "v1"),
            assessment_ref=VersionRef("topic-assessment", "topic-a", "v1"),
        ),
        TopicAllocation(
            allocation_key="allocation-b",
            topic_ref=VersionRef("topic", "topic-b", "v1"),
            assessment_ref=VersionRef("topic-assessment", "topic-b", "v1"),
        ),
    )
    candidates = [
        TriageCandidate(
            topics=(
                TopicCandidate(
                    allocation_key=allocation.allocation_key,
                    title="Same display title",
                    source_refs=(source.source,),
                    priority=Priority.NORMAL,
                    reason="Distinct saved group identity",
                ),
            ),
            dispositions=(),
        )
        for allocation, source in zip(allocations, (first, second), strict=True)
    ]
    plan = replace(
        base.plan,
        expected_targets=(first.source, second.source),
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
    triage = TriageHandler(store, producer, runner)

    outcome = await triage.run(request(producer, "groups-exec"))

    if outcome.status is not TerminalStatus.COMPLETE or runner.calls != 2:
        pytest.fail(f"distinct groups were not independently triaged: {outcome}")
    final = await store.get_result(outcome.result_refs[0].result_id)
    if final is None or final.semantic_data_ref is None:
        pytest.fail("final grouped triage is missing")
    data = await store.load_semantic_data(final.semantic_data_ref)
    if not isinstance(data, TriageData):
        pytest.fail("final grouped semantic type is invalid")
    if not hasattr(data, "topics") or len(data.topics) != 2:
        pytest.fail("same-subject groups were silently merged")
    await store.close()


class ContextRunner(FakeRunner):
    """Record exact context text exposed to the deterministic runner."""

    def __init__(self, store, candidates):
        super().__init__(store, candidates)
        self.context_texts = []

    async def run(self, attempt, trace_sink):
        """Record context then delegate to the deterministic response."""
        self.context_texts.append(attempt.context_text)
        return await super().run(attempt, trace_sink)


def test_missing_selected_memory_is_explicit_context_limitation(tmp_path):
    """A configured missing memory file is retained without blocking triage."""
    asyncio.run(_missing_context(tmp_path))


async def _missing_context(tmp_path):
    store = await open_store(tmp_path / "missing-context.sqlite")
    selected, producer, candidate = setup()
    await save_selection(store, selected)
    if producer.working_context_config is None:
        pytest.fail("synthetic live context configuration is missing")
    context_config = producer.working_context_config.model_copy(
        update={
            "selected_files": (
                MemoryFileSelection(
                    selection_id="missing-synthetic",
                    path="/tmp/msgloom-a3-synthetic-missing.txt",
                ),
            )
        }
    )
    producer = replace(producer, working_context_config=context_config)
    runner = ContextRunner(store, [candidate])
    triage = TriageHandler(store, producer, runner)

    outcome = await triage.run(request(producer, "missing-context-exec"))

    if outcome.status is not TerminalStatus.COMPLETE or runner.calls != 1:
        pytest.fail("missing optional context incorrectly blocked triage")
    if '"state":"missing"' not in runner.context_texts[0]:
        pytest.fail("missing memory limitation was not exposed to the AI request")
    await store.close()


class TimeoutRunner:
    """Return the same transport timeout shape produced by the reviewed runner."""

    async def run(self, attempt, trace_sink):
        """Return a terminal timeout without semantic output."""
        return AnalysisResponse(
            attempt=attempt.attempt,
            status=AttemptStatus.TIMED_OUT,
            structured_output=None,
            trace_count=0,
            failure_code="attempt_timeout",
            failure_detail="synthetic timeout",
        )


def test_runner_timeout_is_incomplete_not_no_reportable_content(tmp_path):
    """A timed-out part cannot become a semantic low-value decision."""
    asyncio.run(_timeout(tmp_path))


async def _timeout(tmp_path):
    store = await open_store(tmp_path / "timeout.sqlite")
    selected, producer, _candidate = setup()
    await save_selection(store, selected)
    if producer.working_context_config is None:
        pytest.fail("synthetic live context configuration is missing")
    triage = TriageHandler(store, producer, TimeoutRunner())

    outcome = await triage.run(request(producer, "timeout-exec"))

    if outcome.status is not TerminalStatus.INCOMPLETE:
        pytest.fail("runner timeout was not retained as incomplete")
    if any(ref.kind == "triage" for ref in outcome.result_refs):
        pytest.fail("runner timeout published semantic triage")
    await store.close()


def test_filter_conflict_is_review_required_without_ai(tmp_path):
    """Contradictory deterministic filter effects are held for review."""
    asyncio.run(_filter_conflict(tmp_path))


async def _filter_conflict(tmp_path):
    from msgloom.preparation.filtering import (
        AddressNormalization,
        FilterConfig,
        FilterEffect,
        FilterRule,
        SubjectMatchMode,
        SubjectPattern,
    )

    store = await open_store(tmp_path / "conflict.sqlite")
    _base_selected, base, _candidate = setup()
    source = record("source-1")
    pattern = SubjectPattern(
        mode=SubjectMatchMode.EXACT,
        value="Shared synthetic subject",
    )
    filter_config = FilterConfig(
        reference=VersionRef("filter_config", "conflict", "v1"),
        address_normalization=AddressNormalization.EXACT,
        rules=(
            FilterRule(
                reference=VersionRef("filter_rule", "include", "v1"),
                effect=FilterEffect.INCLUDE,
                subject_patterns=(pattern,),
            ),
            FilterRule(
                reference=VersionRef("filter_rule", "exclude", "v1"),
                effect=FilterEffect.EXCLUDE,
                subject_patterns=(pattern,),
            ),
        ),
    )
    selected = selection((source,), filter_config=filter_config).model_copy(
        update={"versions": base.versions}
    )
    await save_selection(store, selected)
    plan = replace(
        base.plan,
        prepared_results=tuple(item.result_ref for item in selected.prepared),
        filter_results=tuple(item.result_ref for item in selected.filters),
        group_results=tuple(item.result_ref for item in selected.groups),
        roles=selected.roles,
        topic_allocations=(),
    )
    producer = replace(
        base,
        plan=plan,
        filter_config=selected.filter_config,
        rule_config=selected.rules.evaluation.config,
    )
    runner = FakeRunner(store, [])
    triage = TriageHandler(store, producer, runner)

    outcome = await triage.run(request(producer, "conflict-exec"))

    if outcome.status is not TerminalStatus.COMPLETE or runner.calls != 0:
        pytest.fail("deterministic conflict invoked AI or failed")
    final = await store.get_result(outcome.result_refs[0].result_id)
    if final is None or final.semantic_data_ref is None:
        pytest.fail("conflict triage result is missing")
    data = await store.load_semantic_data(final.semantic_data_ref)
    if not isinstance(data, TriageData):
        pytest.fail("conflict triage semantic type is invalid")
    if data.dispositions[0].kind.value != "review-required":
        pytest.fail("filter conflict was not retained for review")
    await store.close()


def test_failed_claim_owned_write_stops_before_runner(tmp_path, monkeypatch):
    """A failed durable write cannot be skipped to reach model execution."""
    asyncio.run(_failed_write(tmp_path, monkeypatch))


async def _failed_write(tmp_path, monkeypatch):
    store = await open_store(tmp_path / "write-failure.sqlite")
    selected, producer, candidate = setup()
    await save_selection(store, selected)
    runner = FakeRunner(store, [candidate])
    triage = TriageHandler(store, producer, runner)

    async def fail_write(*args, **kwargs):
        raise RuntimeError("synthetic durable write failure")

    monkeypatch.setattr(store, "append_result_with_data", fail_write)
    outcome = await triage.run(request(producer, "write-failure-exec"))

    if outcome.status is not TerminalStatus.FAILED or runner.calls != 0:
        pytest.fail("failed durable write was bypassed")
    await store.close()
