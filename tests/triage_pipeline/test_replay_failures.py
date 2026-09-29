"""Replay, malformed-output, duplicate, and stale-owner A3 regressions."""

from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from msgloom.ai import AnalysisResponse, AttemptStatus, TrustedPolicy
from msgloom.contracts import (
    ExecutionIdentity,
    OperationRequest,
    PhaseCapability,
    TerminalStatus,
    VersionRef,
)
from msgloom.triage import (
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
from tests.triage_pipeline.helpers import FakeRunner, open_store, save_selection, setup


def request(producer, execution):
    """Build an exact synthetic request."""
    return OperationRequest(
        execution=ExecutionIdentity(execution),
        caller="synthetic-app",
        capability=PhaseCapability.TRIAGE,
        target_inputs=producer.plan.expected_targets,
        authority_ref="synthetic-authority",
        parameters=producer.expected_parameters,
    )


class MalformedRunner:
    """Return transport-complete but schema-invalid structured output."""

    calls = 0

    async def run(self, attempt, trace_sink):
        """Return an unsupported model claim without provider access."""
        self.calls += 1
        return AnalysisResponse(
            attempt=attempt.attempt,
            status=AttemptStatus.COMPLETE,
            structured_output={"invented": "claim"},
            trace_count=0,
        )


class SlowRunner:
    """Delay beyond the deliberately tiny synthetic claim lease."""

    async def run(self, attempt, trace_sink):
        """Return only after claim ownership has expired."""
        await asyncio.sleep(0.08)
        return AnalysisResponse(
            attempt=attempt.attempt,
            status=AttemptStatus.COMPLETE,
            structured_output={"topics": [], "dispositions": []},
            trace_count=0,
        )


def test_malformed_output_never_becomes_complete_triage(tmp_path):
    """Unsupported model structure remains explicit incomplete work."""
    asyncio.run(_malformed(tmp_path))


async def _malformed(tmp_path):
    store = await open_store(tmp_path / "malformed.sqlite")
    selected, producer, _candidate = setup()
    await save_selection(store, selected)
    runner = MalformedRunner()
    triage = TriageHandler(store, producer, runner)

    outcome = await triage.run(request(producer, "malformed-exec"))

    if outcome.status is not TerminalStatus.INCOMPLETE or runner.calls != 1:
        pytest.fail("malformed structured output was not retained as incomplete")
    if any(ref.kind == "triage" for ref in outcome.result_refs):
        pytest.fail("malformed output published complete triage semantics")
    await store.close()


def test_duplicate_admission_does_not_repeat_model_work(tmp_path):
    """A terminal durable claim prevents a second execution of the same plan."""
    asyncio.run(_duplicate(tmp_path))


async def _duplicate(tmp_path):
    store = await open_store(tmp_path / "duplicate.sqlite")
    selected, producer, candidate = setup()
    await save_selection(store, selected)
    runner = FakeRunner(store, [candidate, candidate])
    triage = TriageHandler(store, producer, runner)
    req = request(producer, "duplicate-exec")

    first = await triage.run(req)
    second = await triage.run(req)

    if first.status is not TerminalStatus.COMPLETE:
        pytest.fail("first synthetic triage did not complete")
    if second.status is not TerminalStatus.FAILED or runner.calls != 1:
        pytest.fail("duplicate admission repeated paid/model work")
    await store.close()


def test_expired_claim_cannot_publish_semantics(tmp_path):
    """A stale owner fails rather than bypassing the publication fence."""
    asyncio.run(_stale(tmp_path))


async def _stale(tmp_path):
    store = await open_store(tmp_path / "stale.sqlite")
    selected, producer, _candidate = setup()
    await save_selection(store, selected)
    tiny_limits = replace(producer.attempt_limits, timeout_seconds=0.01)
    producer = replace(
        producer,
        attempt_limits=tiny_limits,
        lease_seconds=0.04,
    )
    triage = TriageHandler(store, producer, SlowRunner())

    outcome = await triage.run(request(producer, "stale-exec"))

    if outcome.status is not TerminalStatus.FAILED:
        pytest.fail("expired claim was allowed to complete")
    if not outcome.failures or outcome.failures[0].code != "stale_triage_claim":
        pytest.fail("stale ownership was not surfaced explicitly")
    await store.close()


def test_changed_prompt_replay_reuses_saved_context_and_prior_topic(tmp_path):
    """Replay loads exact saved context and can preserve supported topic identity."""
    asyncio.run(_changed_prompt(tmp_path))


async def _changed_prompt(tmp_path):
    store = await open_store(tmp_path / "replay.sqlite")
    selected, first_config, first_candidate = setup()
    await save_selection(store, selected)
    first_runner = FakeRunner(store, [first_candidate])
    first = TriageHandler(store, first_config, first_runner)
    first_outcome = await first.run(request(first_config, "first-exec"))
    if first_outcome.status is not TerminalStatus.COMPLETE:
        pytest.fail("first triage did not complete")
    final = await store.get_result(first_outcome.result_refs[0].result_id)
    if final is None:
        pytest.fail("first final result is missing")
    context_ref = next(ref for ref in final.input_refs if ref.kind == "working_context")

    old_allocation = first_config.plan.topic_allocations[0]
    versions = TrustedInputVersions(
        prompt=VersionRef("prompt", "triage", "v2"),
        model=first_config.versions.model,
        output_schema=first_config.versions.output_schema,
        configuration=first_config.versions.configuration,
    )
    allocation = TopicAllocation(
        allocation_key=old_allocation.allocation_key,
        topic_ref=old_allocation.topic_ref,
        assessment_ref=VersionRef("assessment", "topic-0", "v2"),
    )
    source = first_config.plan.expected_targets[0]
    evidence = TriageEvidence(
        kind=EvidenceKind.SOURCE_STATEMENT,
        source_ref=source,
        statement="Synthetic approval is requested.",
    )
    replay_candidate = TriageCandidate(
        topics=(
            TopicCandidate(
                allocation_key=allocation.allocation_key,
                title="Synthetic topic replay",
                source_refs=(source,),
                priority=Priority.NORMAL,
                reason="Changed prompt replay with supported continuity",
                continuation=TopicContinuation(
                    prior_topic_ref=old_allocation.topic_ref,
                    prior_assessment_ref=old_allocation.assessment_ref,
                    status=RelationshipStatus.CONFIRMED,
                    reason="Same exact saved source supports continuity",
                    evidence=(evidence,),
                ),
            ),
        ),
        dispositions=(),
    )
    plan = replace(
        first_config.plan,
        prior_triage_results=(first_outcome.result_refs[0],),
        topic_allocations=(allocation,),
        mode=TriageMode.REPLAY,
        replay_context_result=context_ref,
    )
    policy = TrustedPolicy(
        schemas={versions.output_schema: {"type": "object"}},
        models={versions.model: "synthetic-model"},
    )
    replay_config = replace(
        first_config,
        plan=plan,
        versions=versions,
        working_context_config=None,
        capture_time=None,
        prompt_text="Changed synthetic prompt.",
        trusted_policy=policy,
        claim_key="triage:source-1:v2",
        configuration_version="producer-v2",
    )
    runner = FakeRunner(store, [replay_candidate])
    replay = TriageHandler(store, replay_config, runner)

    outcome = await replay.run(request(replay_config, "replay-exec"))

    if outcome.status is not TerminalStatus.COMPLETE or runner.calls != 1:
        pytest.fail(
            f"changed-prompt replay failed: {outcome.failures} {outcome.limitations}"
        )
    replay_final = await store.get_result(outcome.result_refs[0].result_id)
    if replay_final is None or replay_final.prompt_version != "v2":
        pytest.fail("changed prompt did not create a new saved assessment result")
    await store.close()


class FailSecondRunner:
    """Complete one part, then expose a deterministic failed middle part."""

    def __init__(self, candidate):
        self.candidate = candidate
        self.calls = 0

    async def run(self, attempt, trace_sink):
        """Fail exactly the second accepted part attempt."""
        self.calls += 1
        if self.calls == 2:
            return AnalysisResponse(
                attempt=attempt.attempt,
                status=AttemptStatus.FAILED,
                structured_output=None,
                trace_count=0,
                failure_code="synthetic_middle_failure",
                failure_detail="synthetic middle part failed",
            )
        return AnalysisResponse(
            attempt=attempt.attempt,
            status=AttemptStatus.COMPLETE,
            structured_output=self.candidate.model_dump(mode="json"),
            trace_count=0,
        )


def test_split_input_failed_middle_part_never_disposes_parent(tmp_path):
    """A failed middle part leaves the parent incomplete, not low-value."""
    asyncio.run(_split_failure(tmp_path))


async def _split_failure(tmp_path):
    from tests.triage_input.helpers import config, record, selection, with_large_cell

    store = await open_store(tmp_path / "split.sqlite")
    base_selected, base, candidate = setup()
    source = with_large_cell(record("source-1"), "x" * 20_000)
    selected = selection((source,)).model_copy(
        update={"versions": base_selected.versions}
    )
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
        input_config=config(max_part_bytes=4096, max_parts=64),
        max_parts=64,
        lease_seconds=128.0,
    )
    runner = FailSecondRunner(candidate)
    triage = TriageHandler(store, producer, runner)

    outcome = await triage.run(request(producer, "split-exec"))

    if outcome.status is not TerminalStatus.INCOMPLETE or runner.calls != 2:
        pytest.fail(f"split failure did not stop parent completion: {outcome}")
    if any(ref.kind == "triage" for ref in outcome.result_refs):
        pytest.fail("partial fragment incorrectly published complete parent triage")
    await store.close()


class BlockingRunner:
    """Expose a barrier so cancellation can interrupt accepted model work."""

    def __init__(self):
        self.started = asyncio.Event()
        self.calls = 0

    async def run(self, attempt, trace_sink):
        """Wait forever until the owning handler is cancelled."""
        self.calls += 1
        self.started.set()
        await asyncio.Event().wait()
        raise RuntimeError("unreachable synthetic runner state")


def test_repeated_cancellation_drains_evidence_and_releases_claim(tmp_path):
    """Repeated cancellation preserves cancellation and prevents silent restart."""
    asyncio.run(_cancelled(tmp_path))


async def _cancelled(tmp_path):
    store = await open_store(tmp_path / "cancelled.sqlite")
    selected, producer, _candidate = setup()
    await save_selection(store, selected)
    runner = BlockingRunner()
    triage = TriageHandler(store, producer, runner)
    req = request(producer, "cancelled-exec")
    task = asyncio.create_task(triage.run(req))
    await runner.started.wait()

    task.cancel()
    await asyncio.sleep(0)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    else:
        pytest.fail("handler erased caller cancellation")

    retry = await triage.run(req)
    if retry.status is not TerminalStatus.FAILED or runner.calls != 1:
        pytest.fail("cancelled claim silently restarted model work")
    await store.close()
