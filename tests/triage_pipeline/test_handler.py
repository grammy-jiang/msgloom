"""Core A3 producer acceptance tests using real Phase1Persistence."""

from __future__ import annotations

import asyncio

import pytest

from msgloom.application import Application
from msgloom.contracts import (
    ExecutionIdentity,
    OperationRequest,
    PhaseCapability,
    TerminalStatus,
    TrustedAdmission,
)
from msgloom.triage import TriageData
from tests.triage_pipeline.helpers import handler, open_store, save_selection, setup


def request(producer, execution="triage-exec"):
    """Build the exact non-CLI operation request admitted by the plan."""
    return OperationRequest(
        execution=ExecutionIdentity(execution),
        caller="synthetic-app",
        capability=PhaseCapability.TRIAGE,
        target_inputs=producer.plan.expected_targets,
        authority_ref="synthetic-authority",
        parameters=producer.expected_parameters,
    )


def test_success_saves_evidence_before_semantics_and_multiple_topics(tmp_path):
    """A3 saves request evidence first and retains several topics per group."""
    asyncio.run(_success(tmp_path))


async def _success(tmp_path):
    store = await open_store(tmp_path / "a3.sqlite")
    selected, producer, candidate = setup(allocations=2)
    await save_selection(store, selected)
    triage, runner = handler(store, producer, candidate)

    outcome = await triage.run(request(producer))

    if outcome.status is not TerminalStatus.COMPLETE:
        pytest.fail(f"unexpected status: {outcome.status} {outcome.failures}")
    if runner.calls != 1 or runner.request_was_saved != [True]:
        pytest.fail("fake runner did not observe durable request evidence")
    final = await store.get_result(outcome.result_refs[0].result_id)
    if final is None or final.semantic_data_ref is None:
        pytest.fail("final triage result was not persisted")
    data = await store.load_semantic_data(final.semantic_data_ref)
    if not isinstance(data, TriageData):
        pytest.fail("held-source semantic type is invalid")
    if not isinstance(data, TriageData) or len(data.topics) != 2:
        pytest.fail("multiple synthetic topics were not retained")
    if final.acceptable is not True:
        pytest.fail("final semantics were not acceptable")
    await store.close()


def test_non_cli_application_caller_owns_terminal_outcome(tmp_path):
    """Application admission composes the handler without another event loop."""
    asyncio.run(_application(tmp_path))


async def _application(tmp_path):
    store = await open_store(tmp_path / "application.sqlite")
    selected, producer, candidate = setup()
    await save_selection(store, selected)
    triage, runner = handler(store, producer, candidate)
    app = Application(
        store,
        trusted_admissions=(
            TrustedAdmission(
                caller="synthetic-app",
                authority_ref="synthetic-authority",
                capabilities=frozenset({PhaseCapability.TRIAGE}),
            ),
        ),
        triage_factory=lambda: triage,
    )

    outcome = await app.run(request(producer, "application-exec"))

    if outcome.status is not TerminalStatus.COMPLETE or runner.calls != 1:
        pytest.fail(f"Application A3 failed: {outcome.failures}")
    saved = await store.get_outcome(outcome.execution)
    if saved != outcome:
        pytest.fail("Application did not own terminal outcome persistence")
    await store.close()


def test_request_mismatch_is_rejected_before_semantic_load_or_runner(tmp_path):
    """Duplicate or changed request parameters cannot widen the trusted plan."""
    asyncio.run(_mismatch(tmp_path))


async def _mismatch(tmp_path):
    store = await open_store(tmp_path / "mismatch.sqlite")
    selected, producer, candidate = setup()
    await save_selection(store, selected)
    triage, runner = handler(store, producer, candidate)
    bad = OperationRequest(
        execution=ExecutionIdentity("bad-exec"),
        caller="synthetic-app",
        capability=PhaseCapability.TRIAGE,
        target_inputs=producer.plan.expected_targets,
        authority_ref="synthetic-authority",
        parameters=(("mode", "synthetic"), ("mode", "changed")),
    )

    outcome = await triage.run(bad)

    if outcome.status is not TerminalStatus.FAILED or runner.calls:
        pytest.fail("invalid request reached semantic execution")
    await store.close()


def test_deterministic_exclusion_skips_runner_and_remains_replayable(tmp_path):
    """Held deterministic sources publish exclusion without an AI call."""
    asyncio.run(_exclusion(tmp_path))


async def _exclusion(tmp_path):
    from dataclasses import replace

    from msgloom.triage import TriageCandidate
    from msgloom.triage_input import TrustedInputVersions
    from msgloom.triage_pipeline import TriageHandler
    from tests.triage_input.helpers import exclusion_filter, record, selection
    from tests.triage_pipeline.helpers import FakeRunner

    store = await open_store(tmp_path / "excluded.sqlite")
    source = record("source-1", body="Synthetic excluded body.")
    selected = selection((source,), filter_config=exclusion_filter("source-1"))
    _base_selected, base, _candidate = setup()
    versions = TrustedInputVersions(
        prompt=base.versions.prompt,
        model=base.versions.model,
        output_schema=base.versions.output_schema,
        configuration=base.versions.configuration,
    )
    selected = selected.model_copy(update={"versions": versions})
    await save_selection(store, selected)
    plan = replace(
        base.plan,
        expected_targets=(source.source,),
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
    runner = FakeRunner(store, [TriageCandidate(topics=(), dispositions=())])
    triage = TriageHandler(store, producer, runner)

    outcome = await triage.run(request(producer, "excluded-exec"))

    if outcome.status is not TerminalStatus.COMPLETE or runner.calls != 0:
        pytest.fail(f"deterministic exclusion invoked AI: {outcome.failures}")
    final = await store.get_result(outcome.result_refs[0].result_id)
    if final is None or final.semantic_data_ref is None:
        pytest.fail("held-source triage was not persisted")
    data = await store.load_semantic_data(final.semantic_data_ref)
    if not isinstance(data, TriageData):
        pytest.fail("held-source semantic type is invalid")
    if len(data.dispositions) != 1 or data.dispositions[0].kind.value != "excluded":
        pytest.fail("deterministic exclusion was not retained")
    await store.close()
