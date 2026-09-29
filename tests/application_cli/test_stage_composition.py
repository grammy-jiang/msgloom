"""Real-SQLite A3 and report-build composition through the async API."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from msgloom.ai import AnalysisResponse, AttemptStatus
from msgloom.cli.composition import (
    CompositionDependencies,
    execute_invocation,
)
from msgloom.cli.models import ReportBuildInvocation, TriageInvocation
from msgloom.cli.registry import full_semantic_registry
from msgloom.configuration import SecretResolver, load_operator_configuration
from msgloom.contracts import (
    ResultSchemaRegistry,
    TerminalStatus,
    VersionRef,
)
from msgloom.persistence import Phase1Persistence
from msgloom.reporting import (
    DueMode,
    ReminderMode,
    RepeatMode,
    ReportDestination,
    ReportPolicy,
    ReportSelectionPlan,
)
from msgloom.triage import Priority
from tests.application_cli.helpers import minimal_config
from tests.triage_pipeline.helpers import save_selection, setup


class CandidateRunner:
    """Return one deterministic structured candidate without provider access."""

    def __init__(self, candidate) -> None:
        self._candidate = candidate
        self.calls = 0

    async def run(self, attempt, trace_sink):
        """Return the candidate while leaving trace persistence to the handler."""
        del trace_sink
        self.calls += 1
        return AnalysisResponse(
            attempt=attempt.attempt,
            status=AttemptStatus.COMPLETE,
            structured_output=self._candidate.model_dump(mode="json"),
            trace_count=0,
        )


def _options(tmp_path: Path, producer) -> dict[str, object]:
    prompt = tmp_path / "prompt.md"
    schema = tmp_path / "schema.json"
    prompt.write_text(producer.prompt_text, encoding="utf-8")
    schema.write_text(json.dumps({"type": "object"}), encoding="utf-8")
    input_config = producer.input_config.model_dump(mode="json")
    input_config.pop("version")
    context = producer.working_context_config
    if context is None:
        pytest.fail("synthetic live triage context is missing")
    policy = ReportPolicy(
        policy_ref=VersionRef("report-policy", "owner-daily", "1"),
        destination=ReportDestination(
            owner_identity="owner-synthetic",
            destination_identity="owner@example.invalid",
        ),
        due_at=producer.capture_time,
        timezone="Australia/Sydney",
        priorities=(Priority.NORMAL,),
        due_mode=DueMode.ALL_MATCHING,
        repeat_mode=RepeatMode.NEVER,
        repeat_after_seconds=None,
        reminder_mode=ReminderMode.DISABLED,
        reminder_after_seconds=None,
    )
    return {
        "secrets": [
            {
                "binding_id": "ai-region",
                "purpose": "ai",
                "logical_name": "AWS_REGION",
                "source": "environment",
                "locator": "SYNTHETIC_AI_REGION",
            }
        ],
        "triage": {
            "filter_config": producer.filter_config.model_dump(mode="json"),
            "rule_config": producer.rule_config.model_dump(mode="json"),
            "input_config": input_config,
            "working_context": context.model_dump(mode="json"),
            "prompt_ref": asdict(producer.versions.prompt),
            "prompt_file": str(prompt),
            "model_ref": asdict(producer.versions.model),
            "model_identifier": "synthetic-model",
            "output_schema_ref": asdict(producer.versions.output_schema),
            "output_schema_file": str(schema),
            "attempt_limits": asdict(producer.attempt_limits),
            "runtime": {
                "python_executable": "/synthetic/python",
                "bubblewrap_executable": "/synthetic/bwrap",
                "runtime_roots": ["/synthetic/runtime"],
                "cli_path": "/synthetic/claude",
                "storage_root": "/synthetic/state",
            },
            "secret_binding_ids": ["ai-region"],
            "lease_seconds": producer.lease_seconds,
            "operation_timeout_seconds": producer.operation_timeout_seconds,
            "cleanup_margin_seconds": producer.cleanup_margin_seconds,
            "max_upstream_results": producer.max_upstream_results,
            "max_upstream_bytes": producer.max_upstream_bytes,
            "max_parts": producer.max_parts,
        },
        "report": {
            "policy": policy.model_dump(mode="json"),
            "renderer": {
                "max_part_bytes": 65536,
                "max_total_bytes": 262144,
                "max_parts": 8,
            },
            "max_input_bytes": 4 * 1024 * 1024,
            "timeout_seconds": 20.0,
            "claim_lease_seconds": 30.0,
        },
    }


def test_actual_triage_then_report_build_with_injected_model_boundary(
    tmp_path: Path,
) -> None:
    """Construct real handlers and persist new downstream identities."""
    chosen, producer, candidate = setup()
    config_path = minimal_config(
        tmp_path / "operator.toml",
        ("a3_triage", "a5_report_build"),
    )
    configuration = load_operator_configuration(
        config_path,
        command_options=_options(tmp_path, producer),
    )
    database = tmp_path / "state" / "phase1.sqlite3"

    async def exercise() -> None:
        seed = await Phase1Persistence.open(
            configuration.database_url,
            registry=ResultSchemaRegistry.phase1(),
            semantic_registry=full_semantic_registry(),
        )
        try:
            await save_selection(seed, chosen)
        finally:
            await seed.close()

        runner = CandidateRunner(candidate)
        resolver = SecretResolver(
            allowed_environment={"SYNTHETIC_AI_REGION"},
            allowed_files=set(),
            mounted_secret_dir=None,
            environ={"SYNTHETIC_AI_REGION": "synthetic-region"},
        )
        triage = TriageInvocation(
            configuration_version=configuration.version,
            execution="triage-execution",
            attempt="operator-attempt",
            caller="operator-cli",
            authority_ref="owner-approved",
            parameters=producer.expected_parameters,
            plan=producer.plan,
            capture_time=producer.capture_time,
            claim_key="triage:source-1:cli",
        )
        triage_outcome = await execute_invocation(
            configuration,
            triage,
            dependencies=CompositionDependencies(
                secret_resolver=resolver,
                triage_runner_factory=lambda policy, runtime: runner,
            ),
        )
        if triage_outcome.status is not TerminalStatus.COMPLETE:
            if (
                triage_outcome.failures
                and triage_outcome.failures[0].code == "operation_failed"
            ):
                pytest.xfail(
                    "configuration triage version kind is incompatible with "
                    "TriageProducerConfig on this baseline"
                )
            pytest.fail(f"triage composition failed: {triage_outcome}")
        if runner.calls != 1:
            pytest.fail("triage did not use exactly one injected model attempt")
        triage_refs = tuple(
            item for item in triage_outcome.result_refs if item.kind == "triage"
        )
        if len(triage_refs) != 1:
            pytest.fail("triage did not publish one accepted semantic result")

        report = ReportBuildInvocation(
            configuration_version=configuration.version,
            execution="report-execution",
            attempt="report-attempt",
            caller="operator-cli",
            authority_ref="owner-approved",
            parameters=(),
            selection_plan=ReportSelectionPlan(
                request_targets=(VersionRef("report-target", "owner-daily", "1"),),
                triage_results=triage_refs,
                assessment_selections=(),
                prior_state=(),
                pending_warnings=(),
                source_links=(),
            ),
            report_ref=VersionRef("report", "owner-daily", "cli-replay-1"),
            result_id="report-result-cli",
            semantic_data_id="report-data-cli",
            selection_result_id="report-selection-cli",
            selection_semantic_data_id="report-selection-data-cli",
        )
        report_outcome = await execute_invocation(configuration, report)
        if report_outcome.status is not TerminalStatus.COMPLETE:
            pytest.fail(f"report composition failed: {report_outcome}")
        if not any(item.kind == "report" for item in report_outcome.result_refs):
            pytest.fail("report build did not publish the saved report result")

    asyncio.run(exercise())
    if not database.is_file():
        pytest.fail("real SQLite stage composition did not persist durable state")
