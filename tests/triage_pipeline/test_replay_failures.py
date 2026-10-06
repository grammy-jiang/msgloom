"""Replay, malformed-output, duplicate, and stale-owner A3 regressions."""

from __future__ import annotations

import asyncio
import time
from dataclasses import replace
from datetime import timedelta

import pytest

from msgloom.ai import AnalysisResponse, AttemptStatus, TrustedPolicy
from msgloom.ai_evidence import TerminalEvidence
from msgloom.contracts import (
    ExecutionIdentity,
    ExternalEffectState,
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
from tests.triage_pipeline.test_deadline_boundaries import (
    DeadlineRunner,
    deadline_clock,
    saved_result_kinds,
)


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


class BlockingLateRunner(DeadlineRunner):
    """Return valid COMPLETE after blocking past the attempt deadline."""

    blocked_seconds = 0.0

    async def run(self, attempt, trace_sink):
        """Block the loop before advancing the controlled clocks by 30 ms."""
        started = time.perf_counter()
        time.sleep(0.03)  # noqa: ASYNC251 - deliberately starve the loop.
        self.blocked_seconds = time.perf_counter() - started
        return await super().run(attempt, trace_sink)


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
    """Prevent repeated plan execution through the terminal durable claim."""
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


def test_finite_deadline_precedes_claim_expiry(tmp_path, monkeypatch):
    """Acceptance closes before the configured durable claim can expire."""
    asyncio.run(_stale(tmp_path, monkeypatch))


def test_late_complete_response_is_rejected_after_event_loop_starvation(
    tmp_path, monkeypatch
):
    """A runner cannot win by blocking the loop past semantic acceptance."""
    asyncio.run(_blocking_late(tmp_path, monkeypatch))


async def _blocking_late(tmp_path, monkeypatch):
    path = tmp_path / "blocking-late.sqlite"
    store = await open_store(path)
    try:
        selected, producer, candidate = setup()
        await save_selection(store, selected)
        producer = replace(
            producer,
            attempt_limits=replace(producer.attempt_limits, timeout_seconds=0.01),
            lease_seconds=3.0,
            operation_timeout_seconds=2.0,
            cleanup_margin_seconds=0.005,
        )
        # Keep host scheduling outside this attempt-deadline invariant. The
        # runner still blocks synchronously before advancing both clocks.
        with deadline_clock(monkeypatch) as clock:
            runner = BlockingLateRunner(clock, candidate, 0.03)
            triage = TriageHandler(store, producer, runner)
            outcome = await triage.run(request(producer, "blocking-late-exec"))
            inspection = await store.inspect_claim(producer.claim_key)

        if (
            outcome.status is not TerminalStatus.INCOMPLETE
            or tuple(item.code for item in outcome.limitations)
            != ("triage_part_incomplete",)
            or outcome.failures
            or outcome.external_effect is not ExternalEffectState.NONE
        ):
            pytest.fail(f"late COMPLETE response was not rejected: {outcome}")
        if runner.calls != 1 or runner.blocked_seconds < 0.03:
            pytest.fail(f"runner did not exercise synchronous starvation: {outcome}")
        if "triage" in saved_result_kinds(path, "blocking-late-exec"):
            pytest.fail(f"late response published durable final triage: {outcome}")
        terminals = [ref for ref in outcome.result_refs if ref.kind == "ai_response"]
        if len(terminals) != 1:
            pytest.fail(f"missing exact terminal AI evidence: {outcome}")
        saved = await store.get_result(terminals[0].result_id)
        if saved is None or saved.semantic_data_ref is None:
            pytest.fail(f"terminal AI evidence was not durable: {outcome}")
        evidence = await store.load_semantic_data(saved.semantic_data_ref)
        if (
            not isinstance(evidence, TerminalEvidence)
            or evidence.response.failure_code != "attempt_deadline"
            or evidence.transport_eligible
        ):
            pytest.fail(f"late response was not fenced by attempt deadline: {outcome}")
        if inspection.current_token is not None or len(inspection.attempts) != 1:
            pytest.fail(f"live claim was not released: {inspection}; {outcome}")
        attempt = inspection.attempts[0]
        if (
            attempt.token.execution != outcome.execution
            or attempt.terminal_status is not TerminalStatus.INCOMPLETE
            or attempt.external_effect is not ExternalEffectState.NONE
            or attempt.finished_at != attempt.started_at + timedelta(seconds=0.03)
        ):
            pytest.fail(
                f"unexpected live-owner terminal state: {inspection}; {outcome}"
            )
    finally:
        await store.close()


async def _stale(tmp_path, monkeypatch):
    path = tmp_path / "stale.sqlite"
    store = await open_store(path)
    try:
        selected, producer, candidate = setup()
        await save_selection(store, selected)
        tiny_limits = replace(producer.attempt_limits, timeout_seconds=0.01)
        producer = replace(
            producer,
            attempt_limits=tiny_limits,
            lease_seconds=0.04,
            operation_timeout_seconds=0.03,
            cleanup_margin_seconds=0.005,
        )
        # Isolate acceptance expiry from host scheduling during durable drain.
        # A genuinely expired lease must still fail, as boundary tests verify.
        with deadline_clock(monkeypatch) as clock:
            runner = DeadlineRunner(clock, candidate, 0.026)
            triage = TriageHandler(store, producer, runner)
            outcome = await triage.run(request(producer, "stale-exec"))
            inspection = await store.inspect_claim(producer.claim_key)

        if outcome.status is not TerminalStatus.INCOMPLETE:
            pytest.fail(f"finite deadline did not remain incomplete: {outcome}")
        if (
            tuple(item.code for item in outcome.limitations)
            != ("triage_operation_deadline",)
            or outcome.failures
        ):
            pytest.fail(f"finite acceptance deadline was not explicit: {outcome}")
        if runner.calls != 1 or "triage" in saved_result_kinds(path, "stale-exec"):
            pytest.fail("late valid COMPLETE response escaped deadline rejection")
        if inspection.current_token is not None or len(inspection.attempts) != 1:
            pytest.fail(
                f"finite operation did not release its live claim: {inspection}"
            )
        attempt = inspection.attempts[0]
        if (
            attempt.terminal_status is not TerminalStatus.INCOMPLETE
            or attempt.finished_at is None
            or not attempt.started_at
            < attempt.finished_at
            < attempt.started_at + timedelta(seconds=0.04)
        ):
            pytest.fail(f"deadline did not finish before claim expiry: {inspection}")
    finally:
        await store.close()


def test_changed_prompt_replay_reuses_saved_context_and_prior_topic(tmp_path):
    """Replay saved context and preserve supported topic identity."""
    asyncio.run(_changed_prompt(tmp_path))


async def _changed_prompt(tmp_path):
    store = await open_store(tmp_path / "replay.sqlite")
    selected, first_config, first_candidate = setup()
    await save_selection(store, selected)
    first_runner = FakeRunner(store, [first_candidate])
    first = TriageHandler(store, first_config, first_runner)
    first_outcome = await first.run(request(first_config, "first-exec"))
    first_context_text = first_runner.attempts[0].context_text
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
        assessment_ref=VersionRef("topic-assessment", "topic-0", "v2"),
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
    if runner.attempts[0].context_text != first_context_text:
        pytest.fail("replay recaptured or changed the saved time/context snapshot")
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
    """Preserve repeated cancellation and prevent silent restart."""
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
