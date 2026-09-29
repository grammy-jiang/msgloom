"""Focused R2 finite-contract regressions for the A3 producer."""

from __future__ import annotations

import asyncio
import json
from dataclasses import replace

import pytest

from msgloom.ai import AnalysisResponse, AttemptStatus, TraceEvent, TraceKind
from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ExecutionIdentity,
    ExternalEffectState,
    ResultRef,
    SemanticDataRef,
    TerminalStatus,
)
from msgloom.persistence import StaleClaimError
from msgloom.triage import TriageCandidate
from msgloom.triage_input import PartState
from msgloom.triage_pipeline import TriageHandler
from msgloom.triage_pipeline.codecs import TriagePartState, TriagePartStateCodec
from msgloom.triage_pipeline.common import RUN_STATE, RunState
from tests.triage_input.helpers import config, record, selection, with_large_cell
from tests.triage_pipeline.helpers import (
    FakeRunner,
    open_store,
    save_selection,
    setup,
)
from tests.triage_pipeline.test_handler import request


class TraceRunner(FakeRunner):
    """Emit one exposed trace before a successful terminal response."""

    async def run(self, attempt, trace_sink):
        self.attempts.append(attempt)
        self.calls += 1
        await trace_sink.write(
            TraceEvent(
                attempt=attempt.attempt,
                sequence=0,
                kind=TraceKind.DIAGNOSTIC,
                name="synthetic-trace",
                text="Synthetic trace before terminal response.",
                data={"synthetic": True},
            )
        )
        candidate = self.candidates[self.calls - 1]
        return AnalysisResponse(
            attempt=attempt.attempt,
            status=AttemptStatus.COMPLETE,
            structured_output=candidate.model_dump(mode="json"),
            trace_count=1,
        )


class BarrierRunner:
    """Block until the handler-enforced attempt deadline cancels this runner."""

    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.calls = 0

    async def run(self, attempt, trace_sink):
        """Expose a controlled barrier without implementing a private timeout."""
        self.calls += 1
        self.started.set()
        await asyncio.Event().wait()
        raise RuntimeError("unreachable synthetic barrier state")


def test_injected_runner_deadline_keeps_event_loop_responsive(tmp_path):
    """The handler enforces attempt time and pure work does not starve the loop."""
    asyncio.run(_deadline(tmp_path))


async def _deadline(tmp_path):
    store = await open_store(tmp_path / "deadline.sqlite")
    selected, producer, _candidate = setup()
    await save_selection(store, selected)
    limits = replace(producer.attempt_limits, timeout_seconds=0.05)
    producer = replace(producer, attempt_limits=limits)
    runner = BarrierRunner()
    triage = TriageHandler(store, producer, runner)
    beats = 0
    stop = asyncio.Event()

    async def heartbeat() -> None:
        nonlocal beats
        while not stop.is_set():
            beats += 1
            await asyncio.sleep(0.005)

    pulse = asyncio.create_task(heartbeat())
    outcome = await triage.run(request(producer, "deadline-exec"))
    stop.set()
    await pulse

    if outcome.status is not TerminalStatus.INCOMPLETE or runner.calls != 1:
        pytest.fail(f"attempt deadline did not stop injected runner: {outcome}")
    if beats < 3:
        pytest.fail("caller event loop was starved during bounded A3 work")
    kinds = tuple(ref.kind for ref in outcome.result_refs)
    if "ai_request" not in kinds or "ai_response" not in kinds:
        pytest.fail("deadline outcome lost its exact durable evidence prefix")
    if "triage" in kinds:
        pytest.fail("deadline published acceptable final triage semantics")
    await store.close()


def test_trace_and_terminal_prefix_preserve_durable_order(tmp_path):
    """Incomplete/success evidence ordering is request, trace, then terminal."""
    asyncio.run(_trace_order(tmp_path))


async def _trace_order(tmp_path):
    store = await open_store(tmp_path / "trace-order.sqlite")
    selected, producer, candidate = setup()
    await save_selection(store, selected)
    runner = TraceRunner(store, [candidate])
    triage = TriageHandler(store, producer, runner)

    outcome = await triage.run(request(producer, "trace-order-exec"))

    if outcome.status is not TerminalStatus.COMPLETE:
        pytest.fail("trace-order synthetic triage did not complete")
    final = await store.get_result(outcome.result_refs[0].result_id)
    if final is None:
        pytest.fail("trace-order final result is missing")
    part_state_ref = next(
        ref for ref in final.input_refs if ref.kind == "triage_part_state"
    )
    part_state = await store.get_result(part_state_ref.result_id)
    if part_state is None:
        pytest.fail("trace-order part state is missing")
    response_ref = next(
        ref for ref in part_state.input_refs if ref.kind == "ai_response"
    )
    response = await store.get_result(response_ref.result_id)
    if response is None:
        pytest.fail("trace-order terminal response is missing")
    kinds = tuple(ref.kind for ref in response.input_refs)
    if kinds != ("ai_request", "ai_trace"):
        pytest.fail(f"unexpected request/trace order: {kinds}")
    await store.close()


def test_empty_context_still_carries_time_timezone_and_snapshot_basis(tmp_path):
    """An empty selected-file set still gives the model captured time context."""
    asyncio.run(_context_basis(tmp_path))


async def _context_basis(tmp_path):
    store = await open_store(tmp_path / "context.sqlite")
    selected, producer, candidate = setup()
    await save_selection(store, selected)
    runner = FakeRunner(store, [candidate])
    triage = TriageHandler(store, producer, runner)

    outcome = await triage.run(request(producer, "context-exec"))

    if outcome.status is not TerminalStatus.COMPLETE or not runner.attempts:
        pytest.fail("synthetic context operation did not complete")
    payload = json.loads(runner.attempts[0].context_text)
    if payload["timezone"] != "Australia/Sydney":
        pytest.fail("captured timezone was not supplied to analysis")
    if not payload["capture_time"].startswith("2026-09-29T12:00:00"):
        pytest.fail("captured current-time basis was not supplied to analysis")
    if payload["files"] != [] or "snapshot_sha256" not in payload:
        pytest.fail("empty-file snapshot metadata was not preserved")
    if "/tmp" in runner.attempts[0].context_text:
        pytest.fail("private configured roots leaked into model context")
    await store.close()


def test_two_facade_reclaim_fences_old_a3_publication(tmp_path):
    """A reclaimed real-SQLite claim fences the old A3 publication path."""
    asyncio.run(_two_facade_reclaim(tmp_path))


async def _two_facade_reclaim(tmp_path):
    path = tmp_path / "two-facade.sqlite"
    first = await open_store(path)
    second = await open_store(path)
    selected, producer, candidate = setup()
    await save_selection(first, selected)
    handler = TriageHandler(first, producer, FakeRunner(first, [candidate]))
    required = (
        *producer.plan.prepared_results,
        *producer.plan.filter_results,
        *producer.plan.group_results,
    )
    old_attempt = AttemptIdentity("old-attempt")
    old = await first.acquire_claim(
        producer.claim_key,
        ClaimKind.TRIAGE,
        ExecutionIdentity("old-exec"),
        old_attempt,
        required_inputs=required,
        lease_seconds=0.01,
    )
    await asyncio.sleep(0.03)
    new = await second.acquire_claim(
        producer.claim_key,
        ClaimKind.TRIAGE,
        ExecutionIdentity("new-exec"),
        AttemptIdentity("new-attempt"),
        required_inputs=required,
        lease_seconds=1.0,
    )
    upstream_values = []
    for reference in required:
        saved = await first.get_result(reference.result_id)
        if saved is not None:
            upstream_values.append(saved)
    upstream = tuple(upstream_values)
    prepared_versions = tuple(
        dict.fromkeys(
            version for saved in upstream for version in saved.prepared_versions
        )
    )
    state_token = RUN_STATE.set(
        RunState(
            asyncio.get_running_loop().time() + 1.0,
            prepared_versions=prepared_versions,
        )
    )
    try:
        with pytest.raises(StaleClaimError):
            await handler._save_rules(
                request(producer, "old-exec"),
                old_attempt,
                old,
                selected.rules.evaluation,
                upstream,
            )
    finally:
        RUN_STATE.reset(state_token)
    await second.finish_claim(new, TerminalStatus.FAILED, ExternalEffectState.NONE)
    await first.close()
    await second.close()


def test_nested_model_copy_mutation_is_rejected_before_io(tmp_path, monkeypatch):
    """Strict operation-boundary reconstruction catches nested model-copy bypass."""
    asyncio.run(_bad_nested_config(tmp_path, monkeypatch))


async def _bad_nested_config(tmp_path, monkeypatch):
    store = await open_store(tmp_path / "bad-config.sqlite")
    _selected, producer, candidate = setup()
    triage = TriageHandler(store, producer, FakeRunner(store, [candidate]))
    bad_split = producer.input_config.split.model_copy(update={"max_part_bytes": 1})
    bad_input = producer.input_config.model_copy(update={"split": bad_split})
    object.__setattr__(producer, "input_config", bad_input)

    async def forbidden_read(*args, **kwargs):
        pytest.fail("invalid trusted configuration reached persistence I/O")

    monkeypatch.setattr(store, "get_result", forbidden_read)
    outcome = await triage.run(request(producer, "bad-config-exec"))

    if outcome.status is not TerminalStatus.FAILED:
        pytest.fail("invalid nested trusted configuration was accepted")
    if not outcome.failures or outcome.failures[0].code != "triage_config_invalid":
        pytest.fail("invalid configuration did not fail at the public boundary")
    await store.close()


def test_changed_trusted_policy_is_rejected_before_io(tmp_path, monkeypatch):
    """A handler snapshots trusted maps and rejects later semantic mutation."""
    asyncio.run(_changed_policy(tmp_path, monkeypatch))


async def _changed_policy(tmp_path, monkeypatch):
    store = await open_store(tmp_path / "changed-policy.sqlite")
    _selected, producer, candidate = setup()
    runner = FakeRunner(store, [candidate])
    triage = TriageHandler(store, producer, runner)
    object.__setattr__(
        producer.trusted_policy,
        "models",
        {producer.versions.model: "changed-synthetic-model"},
    )

    async def forbidden_read(*args, **kwargs):
        pytest.fail("changed trusted policy reached persistence I/O")

    monkeypatch.setattr(store, "get_result", forbidden_read)
    outcome = await triage.run(request(producer, "changed-policy-exec"))

    if outcome.status is not TerminalStatus.FAILED or runner.calls:
        pytest.fail("changed trusted policy reached semantic execution")
    await store.close()


def test_part_state_codec_rejects_incoherent_model_copy():
    """Closed part-state codec rejects a bypassed complete/failure combination."""
    value = TriagePartState(
        part_ref=SemanticDataRef(
            "part",
            "triage_input_part",
            "1",
            "0" * 64,
            1,
        ),
        attempt=AttemptIdentity("attempt"),
        state=PartState.COMPLETE,
        ai_response_ref=ResultRef("response", "ai_response", "1"),
    )
    malformed = value.model_copy(update={"failure_code": "impossible"})
    with pytest.raises(TypeError, match="failed validation"):
        TriagePartStateCodec().encode(malformed)


def test_split_input_success_requires_each_part_to_cover_its_source(tmp_path):
    """A successful split can complete only when every part is explicitly covered."""
    asyncio.run(_split_success(tmp_path))


async def _split_success(tmp_path):
    store = await open_store(tmp_path / "split-success.sqlite")
    base_selected, base, candidate = setup()
    source = with_large_cell(
        record("source-1", body="Synthetic approval is requested."),
        "x" * 6_000,
    )
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
    )
    runner = FakeRunner(store, [candidate] * 64)
    triage = TriageHandler(store, producer, runner)

    outcome = await triage.run(request(producer, "split-success-exec"))

    if outcome.status is not TerminalStatus.COMPLETE or runner.calls < 2:
        pytest.fail(f"fully covered split input did not complete: {outcome}")
    await store.close()


def test_empty_part_candidate_cannot_borrow_coverage_from_other_part(tmp_path):
    """An empty split response cannot be completed by another part using its source."""
    asyncio.run(_empty_part(tmp_path))


async def _empty_part(tmp_path):
    store = await open_store(tmp_path / "split-empty.sqlite")
    base_selected, base, candidate = setup()
    source = with_large_cell(
        record("source-1", body="Synthetic approval is requested."),
        "x" * 6_000,
    )
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
    )
    empty = TriageCandidate(topics=(), dispositions=())
    runner = FakeRunner(store, [empty, candidate])
    triage = TriageHandler(store, producer, runner)

    outcome = await triage.run(request(producer, "split-empty-exec"))

    if outcome.status is not TerminalStatus.INCOMPLETE or runner.calls != 1:
        pytest.fail("empty split part borrowed source coverage from another part")
    if any(ref.kind == "triage" for ref in outcome.result_refs):
        pytest.fail("missing part disposition published final triage semantics")
    await store.close()
