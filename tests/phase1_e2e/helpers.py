"""Shared synthetic helpers for composed Phase 1 acceptance tests."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

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
    VersionRef,
)
from msgloom.persistence import Phase1Persistence
from msgloom.preparation import (
    DocumentFormat,
    DocumentLocation,
    NativeRelationship,
    PreparedRecord,
    PreparedSourceType,
)
from msgloom.preparation.filtering import FilterConfig
from msgloom.preparation_pipeline import (
    PreparationMode,
    PreparationPlan,
    SelectionPlan,
)
from msgloom.reporting import (
    RendererConfig,
    ReportBuildHandler,
    ReportHandlerConfig,
    ReportSelectionPlan,
)
from msgloom.sources import (
    CollectedBody,
    CollectedRecord,
    CollectedSelection,
    ContentKind,
    SavedSourceReader,
    SavedSourceReaderConfig,
)
from msgloom.sources._snapshot import capture_selection
from msgloom.triage import TopicAllocation, TriageCandidate, TriageRuleConfig
from msgloom.triage_pipeline import TriageHandler, TriageProducerConfig
from tests.preparation_pipeline.helpers import filter_config, profiles
from tests.reporting.helpers import policy as report_policy
from tests.triage_input.helpers import selection as triage_selection
from tests.triage_pipeline.helpers import FakeRunner
from tests.triage_pipeline.helpers import setup as triage_setup

CALLER = "phase1-e2e"
AUTHORITY = "phase1-e2e-authority"


async def open_store(path: Path) -> Phase1Persistence:
    """Open the reviewed default Phase 1 persistence composition."""
    return await Phase1Persistence.open(f"sqlite:///{path}")


def saved_reader(saved_catalog: dict[str, object]) -> SavedSourceReader:
    """Open the actual saved-source adapter over the synthetic A1 fixture."""
    return SavedSourceReader(
        SavedSourceReaderConfig(
            catalog_path=cast(Path, saved_catalog["database"]),
            evidence_roots=(cast(Path, saved_catalog["evidence_root"]),),
        )
    )


def request(
    capability: PhaseCapability,
    execution: str,
    targets: tuple[VersionRef, ...],
    *,
    parameters: tuple[tuple[str, str], ...] = (),
) -> OperationRequest:
    """Build one exact finite Application request."""
    return OperationRequest(
        execution=ExecutionIdentity(execution),
        caller=CALLER,
        capability=capability,
        target_inputs=targets,
        authority_ref=AUTHORITY,
        parameters=parameters,
    )


def app_for(
    store: Phase1Persistence,
    capability: PhaseCapability,
    factory,
) -> Application:
    """Return an Application admitting exactly one configured capability."""
    kwargs = {
        PhaseCapability.PREPARE: {"prepare_factory": factory},
        PhaseCapability.TRIAGE: {"triage_factory": factory},
        PhaseCapability.REPORT_BUILD: {"report_build_factory": factory},
    }[capability]
    return Application(
        store,
        trusted_admissions=(
            TrustedAdmission(CALLER, AUTHORITY, frozenset({capability})),
        ),
        **kwargs,
    )


def preparation_plan(
    sources: tuple[VersionRef, ...],
    *,
    attempt: str,
    config: FilterConfig | None = None,
) -> PreparationPlan:
    """Build a finite live plan using reviewed native parser identities."""
    return PreparationPlan(
        mode=PreparationMode.LIVE,
        attempt=AttemptIdentity(attempt),
        selections=tuple(SelectionPlan(source=source) for source in sources),
        filter_config=config or filter_config(),
        parser_profiles=profiles(
            DocumentFormat.HTML,
            DocumentFormat.TEXT,
            DocumentFormat.JSON,
            DocumentFormat.MIME,
        ),
        configuration_version="phase1-e2e-prepare-v1",
        code_version="phase1-e2e",
        execution_timeout_seconds=30.0,
        claim_lease_seconds=35.0,
    )


async def semantic_values(
    store: Phase1Persistence,
    refs: tuple[ResultRef, ...],
    kind: str,
) -> tuple[object, ...]:
    """Load exact semantic values for one result kind."""
    values: list[object] = []
    for ref in refs:
        if ref.kind != kind:
            continue
        saved = await store.get_result(ref.result_id)
        if saved is None or saved.semantic_data_ref is None:
            pytest.fail(f"{kind} result omitted durable semantic data")
        values.append(await store.load_semantic_data(saved.semantic_data_ref))
    return tuple(values)


async def prepared_records(
    store: Phase1Persistence, refs: tuple[ResultRef, ...]
) -> tuple[PreparedRecord, ...]:
    """Load only actually produced A2 prepared records."""
    values = await semantic_values(store, refs, "prepared")
    if not values or any(not isinstance(value, PreparedRecord) for value in values):
        pytest.fail("A2 did not persist prepared records")
    return cast(tuple[PreparedRecord, ...], values)


def triage_config(
    records: tuple[PreparedRecord, ...],
    prepared_outcome_refs: tuple[ResultRef, ...],
    preparation: PreparationPlan,
    allocations: tuple[TopicAllocation, ...],
    *,
    key: str,
    prompt_version: str = "v1",
    rules: TriageRuleConfig | None = None,
) -> TriageProducerConfig:
    """Bind A3 to exact A2 results while keeping the model boundary fake."""
    chosen = triage_selection(
        records,
        filter_config=preparation.filter_config,
        triage_config=rules,
    )
    _unused, base, _candidate = triage_setup(prompt_version=prompt_version)
    plan = replace(
        base.plan,
        expected_targets=tuple(record.source for record in records),
        prepared_results=tuple(
            ref for ref in prepared_outcome_refs if ref.kind == "prepared"
        ),
        filter_results=tuple(
            ref for ref in prepared_outcome_refs if ref.kind == "filter_result"
        ),
        group_results=tuple(
            ref for ref in prepared_outcome_refs if ref.kind == "group_result"
        ),
        roles=chosen.roles,
        topic_allocations=allocations,
    )
    return replace(
        base,
        plan=plan,
        filter_config=preparation.filter_config,
        rule_config=chosen.rules.evaluation.config,
        claim_key=f"triage:phase1-e2e:{key}",
        configuration_version=f"phase1-e2e-{key}",
    )


async def run_triage(
    store: Phase1Persistence,
    config: TriageProducerConfig,
    candidate: TriageCandidate,
    execution: str,
) -> tuple[object, FakeRunner]:
    """Run A3 through Application with deterministic model output only."""
    runner = FakeRunner(store, [candidate] * config.max_parts)
    handler = TriageHandler(store, config, runner)
    outcome = await app_for(store, PhaseCapability.TRIAGE, lambda: handler).run(
        request(
            PhaseCapability.TRIAGE,
            execution,
            config.plan.expected_targets,
            parameters=config.expected_parameters,
        )
    )
    return outcome, runner


def report_handler(
    store: Phase1Persistence,
    selection: ReportSelectionPlan,
    *,
    identity: str,
    max_part_bytes: int = 100_000,
) -> ReportBuildHandler:
    """Build the actual A5 handler over exact accepted A3 references."""
    return ReportBuildHandler(
        policy=report_policy(),
        selection_plan=selection,
        persistence=store,
        renderer_config=RendererConfig(
            max_part_bytes=max_part_bytes,
            max_total_bytes=300_000,
            max_parts=64,
        ),
        config=ReportHandlerConfig(
            report_ref=VersionRef("report", identity, "v1"),
            result_id=identity,
            semantic_data_id=f"data-{identity}",
            selection_result_id=f"selection-{identity}",
            selection_semantic_data_id=f"selection-data-{identity}",
            max_input_bytes=8 * 1024 * 1024,
            attempt=AttemptIdentity(f"attempt-{identity}"),
            code_version="phase1-e2e",
            expected_parameters=(("mode", "acceptance"),),
            timeout_seconds=10.0,
            claim_lease_seconds=15.0,
        ),
    )


async def run_report(
    store: Phase1Persistence,
    selection: ReportSelectionPlan,
    *,
    identity: str,
    max_part_bytes: int = 100_000,
):
    """Run A5 through Application and persist its terminal outcome."""
    handler = report_handler(
        store,
        selection,
        identity=identity,
        max_part_bytes=max_part_bytes,
    )
    return await app_for(store, PhaseCapability.REPORT_BUILD, lambda: handler).run(
        request(
            PhaseCapability.REPORT_BUILD,
            f"{identity}-execution",
            selection.request_targets,
            parameters=(("mode", "acceptance"),),
        )
    )


class StaticReader:
    """Serve captured synthetic A1-like selections without semantic shortcuts."""

    def __init__(self, selections: tuple[CollectedSelection, ...]) -> None:
        self._values = {item.record.source: item for item in selections}

    async def read_selection(self, requested: VersionRef) -> CollectedSelection:
        """Return the exact captured source selection."""
        return self._values[requested]

    async def load_saved_bytes(self, _reference) -> bytes:
        """Reject unexpected byte loads for body-only fixtures."""
        pytest.fail("body-only acceptance fixture requested saved bytes")


def collected_record(
    identity: str,
    *,
    subject: str,
    body: str,
    relationships: tuple[NativeRelationship, ...] = (),
) -> CollectedRecord:
    """Build one pre-semantics synthetic source record."""
    source = VersionRef("outlook_message", identity, "v1")
    scope = VersionRef("source_scope", f"scope-{identity}", "v1")
    return CollectedRecord(
        source=source,
        source_scope=scope,
        source_type=PreparedSourceType.OUTLOOK_EMAIL,
        semantic_identity=f"outlook:{identity}",
        observed_at=datetime(2026, 9, 29, tzinfo=UTC),
        source_time=datetime(2026, 9, 29, tzinfo=UTC),
        subject=subject,
        sender=None,
        author=None,
        recipients=(),
        source_content_kind=ContentKind.JSON,
        source_bytes=None,
        body=CollectedBody(
            kind=ContentKind.PLAIN,
            content=body,
            saved_bytes=None,
            location=DocumentLocation(part="graph-json"),
        ),
        alternate_bodies=(),
        attachments=(),
        relationships=(
            NativeRelationship(kind="source_scope", target=scope),
            *relationships,
        ),
        metadata=(),
        source_locations=(DocumentLocation(part="graph-json"),),
        limitations=(),
    )


def static_reader(*records: CollectedRecord) -> StaticReader:
    """Capture exact source selections before A2 begins."""
    return StaticReader(tuple(capture_selection(record) for record in records))


def require_status(outcome, expected: TerminalStatus, detail: str) -> None:
    """Fail with the complete safe outcome when a stage status is unexpected."""
    if outcome.status is not expected:
        pytest.fail(f"{detail}: {outcome}")
