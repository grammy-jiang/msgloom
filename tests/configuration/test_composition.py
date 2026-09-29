"""Finite Phase 1 composition and redacted snapshot tests."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from msgloom.configuration import (
    ConfigurationError,
    ConfigurationErrorCode,
    PreparationOperationData,
    ReportOperationData,
    ReportSubmitOperationData,
    TriageOperationData,
    load_operator_configuration,
)
from msgloom.contracts import PhaseCapability


def test_full_configuration_resolves_relative_paths_and_operations(
    minimal_toml: Path,
    full_options: dict[str, object],
) -> None:
    configured = load_operator_configuration(minimal_toml, command_options=full_options)

    source = configured.source_reader_config()
    expected_catalog = minimal_toml.parent / "saved" / "catalog.sqlite3"
    if source.catalog_path != expected_catalog:
        pytest.fail("source catalog was not resolved against explicit TOML")
    expected_root = minimal_toml.parent / "saved" / "raw"
    if source.evidence_roots != (expected_root,):
        pytest.fail("evidence root was not resolved against explicit TOML")
    expected_database = minimal_toml.parent / "state" / "phase1.sqlite3"
    parsed_url = make_url(configured.database_url)
    if parsed_url.database != f"file:{expected_database}":
        pytest.fail("persistence path was not resolved against explicit TOML")
    if parsed_url.query.get("uri") != "true":
        pytest.fail("persistence URL did not preserve filesystem URI semantics")

    prepare = configured.operation(PhaseCapability.PREPARE)
    triage = configured.operation(PhaseCapability.TRIAGE)
    report = configured.operation(PhaseCapability.REPORT_BUILD)
    submit = configured.operation(PhaseCapability.REPORT_SUBMIT)
    if not isinstance(prepare, PreparationOperationData):
        pytest.fail("A2 operation data is unavailable")
    if not isinstance(triage, TriageOperationData):
        pytest.fail("A3 operation data is unavailable")
    if not isinstance(report, ReportOperationData):
        pytest.fail("A5 build operation data is unavailable")
    if not isinstance(submit, ReportSubmitOperationData):
        pytest.fail("A5 submit operation data is unavailable")

    context = triage.working_context_config
    selected = context.selected_files[0].path
    if selected != str(minimal_toml.parent / "memory" / "daily.md"):
        pytest.fail("working-context selection did not resolve relative to TOML")
    if triage.input_config.version.version != configured.version:
        pytest.fail("triage input did not bind exact configuration version")
    if prepare.configuration_version != configured.version:
        pytest.fail("A2 did not bind exact configuration version")
    if report.configuration_version != configured.version:
        pytest.fail("A5 did not bind exact configuration version")


def test_snapshot_is_frozen_deterministic_redacted_and_change_sensitive(
    minimal_toml: Path,
    full_options: dict[str, object],
) -> None:
    first = load_operator_configuration(minimal_toml, command_options=full_options)
    second = load_operator_configuration(minimal_toml, command_options=full_options)
    if first.snapshot() != second.snapshot():
        pytest.fail("unchanged configuration did not produce an exact snapshot")

    payload = first.snapshot().payload
    forbidden = (
        "private-owner",
        "private-owner@example.invalid",
        "SYNTHETIC_AI_REGION",
        "report-token",
        str(minimal_toml.parent),
        "daily.md",
    )
    if any(value in payload for value in forbidden):
        pytest.fail("inspection snapshot exposed private configuration")

    report = dict(cast(dict[str, object], full_options["report"]))
    policy = dict(cast(dict[str, object], report["policy"]))
    destination = dict(cast(dict[str, object], policy["destination"]))
    destination["destination_identity"] = "changed@example.invalid"
    policy["destination"] = destination
    report["policy"] = policy
    changed_options = dict(full_options)
    changed_options["report"] = report
    changed = load_operator_configuration(minimal_toml, command_options=changed_options)
    if changed.version == first.version:
        pytest.fail("redacted private change did not change configuration version")

    with pytest.raises(FrozenInstanceError):
        first.snapshot().version = "mutated"  # type: ignore[misc]


def test_phase2_capability_and_missing_phase1_config_are_unavailable(
    minimal_toml: Path,
) -> None:
    configured = load_operator_configuration(minimal_toml)
    with pytest.raises(ConfigurationError) as caught:
        configured.operation(PhaseCapability.INVESTIGATE)
    if caught.value.code is not ConfigurationErrorCode.CONFIG_UNAVAILABLE:
        pytest.fail("Phase 2 capability did not fail at configuration gate")

    with pytest.raises(ConfigurationError) as caught:
        configured.operation(PhaseCapability.TRIAGE)
    if caught.value.code is not ConfigurationErrorCode.CONFIG_UNAVAILABLE:
        pytest.fail("missing Phase 1 configuration did not expose unavailable gate")


def test_phase2_admission_is_rejected_before_composition(
    minimal_toml: Path,
) -> None:
    admissions = [
        {
            "caller": "operator-cli",
            "authority_ref": "owner-approved",
            "capabilities": ["a4_investigate"],
        }
    ]
    with pytest.raises(ConfigurationError) as caught:
        load_operator_configuration(
            minimal_toml, command_options={"admissions": admissions}
        )
    if caught.value.code is not ConfigurationErrorCode.INVALID_INPUT:
        pytest.fail("unsupported admission was not rejected")


def test_loading_does_not_construct_adapters(
    minimal_toml: Path,
    full_options: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inspection validates composition without starting execution adapters."""
    from msgloom.ai.runner import AIRunner
    from msgloom.reporting.handler import ReportBuildHandler
    from msgloom.sources.reader import SavedSourceReader

    def forbidden(*_args: object, **_kwargs: object) -> None:
        pytest.fail("configuration inspection started an execution adapter")

    monkeypatch.setattr(AIRunner, "__init__", forbidden)
    monkeypatch.setattr(ReportBuildHandler, "__init__", forbidden)
    monkeypatch.setattr(SavedSourceReader, "__init__", forbidden)

    configured = load_operator_configuration(minimal_toml, command_options=full_options)
    if not configured.version:
        pytest.fail("configuration did not load after adapter guards")


def test_operation_builders_reuse_integrated_domain_contracts(
    minimal_toml: Path,
    full_options: dict[str, object],
) -> None:
    """Build reviewed A2/A3/A5 configs without constructing their handlers."""
    from msgloom.contracts import AttemptIdentity, ResultRef, VersionRef
    from msgloom.preparation_pipeline import PreparationMode, SelectionPlan
    from msgloom.triage import TopicAllocation
    from msgloom.triage_input import SourceRole, SourceRoleBinding
    from msgloom.triage_pipeline import TriageMode, TriageReplayPlan

    configured = load_operator_configuration(minimal_toml, command_options=full_options)
    source = VersionRef("source", "synthetic", "1")
    attempt = AttemptIdentity("attempt-1")

    prepare = configured.operation(PhaseCapability.PREPARE)
    if not isinstance(prepare, PreparationOperationData):
        pytest.fail("A2 operation data has the wrong type")
    plan = prepare.plan(
        mode=PreparationMode.LIVE,
        attempt=attempt,
        selections=(SelectionPlan(source=source),),
    )
    if plan.configuration_version != configured.version:
        pytest.fail("A2 plan lost configuration provenance")

    triage = configured.operation(PhaseCapability.TRIAGE)
    if not isinstance(triage, TriageOperationData):
        pytest.fail("A3 operation data has the wrong type")
    replay = TriageReplayPlan(
        expected_targets=(source,),
        prepared_results=(ResultRef("prepared-1", "prepared_record", "1"),),
        filter_results=(ResultRef("filter-1", "filter_result", "1"),),
        group_results=(ResultRef("group-1", "group_result", "1"),),
        prior_triage_results=(),
        roles=(SourceRoleBinding(source_ref=source, role=SourceRole.NEW_SOURCE),),
        topic_allocations=(
            TopicAllocation(
                allocation_key="topic-1",
                topic_ref=VersionRef("topic", "topic-1", "1"),
                assessment_ref=VersionRef("topic-assessment", "assessment-1", "1"),
            ),
        ),
        mode=TriageMode.REPLAY,
        replay_context_result=ResultRef("context-1", "working_context_snapshot", "1"),
    )
    producer = triage.producer_config(
        plan=replay,
        capture_time=None,
        expected_parameters=(),
        claim_key="triage-claim",
    )
    if producer.configuration_version != configured.version:
        pytest.fail("A3 producer lost configuration provenance")

    report = configured.operation(PhaseCapability.REPORT_BUILD)
    if not isinstance(report, ReportOperationData):
        pytest.fail("A5 operation data has the wrong type")
    handler = report.handler_config(
        report_ref=VersionRef("report", "daily", "1"),
        result_id="report-result-1",
        semantic_data_id="report-data-1",
        selection_result_id="selection-result-1",
        selection_semantic_data_id="selection-data-1",
        attempt=attempt,
        expected_parameters=(),
    )
    if handler.code_version != configured.code_version:
        pytest.fail("A5 handler config lost code provenance")


def test_database_url_preserves_reserved_filename_identity(
    minimal_toml: Path,
) -> None:
    reserved = Path("state") / "phase1?reserved #%.sqlite3"
    configured = load_operator_configuration(
        minimal_toml,
        command_options={"storage": {"sqlite_path": str(reserved)}},
    )
    exact_path = minimal_toml.parent / reserved
    exact_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(configured.database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE identity_probe (value INTEGER)"))
    finally:
        engine.dispose()

    if not exact_path.is_file():
        pytest.fail("SQLite URL did not open the exact reserved-character path")
    rewritten = minimal_toml.parent / "state" / "phase1"
    if rewritten.exists():
        pytest.fail("SQLite URL rewrote '?' into URI query semantics")
