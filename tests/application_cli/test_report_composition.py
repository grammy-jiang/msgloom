"""Actual report-build construction from exact saved triage input."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from msgloom.cli.composition import execute_invocation
from msgloom.cli.models import ReportBuildInvocation
from msgloom.cli.registry import full_semantic_registry
from msgloom.configuration import load_operator_configuration
from msgloom.contracts import ResultSchemaRegistry, TerminalStatus, VersionRef
from msgloom.persistence import Phase1Persistence
from tests.application_cli.helpers import minimal_config
from tests.reporting.helpers import plan, policy, save_triage, topic, triage_data


def test_actual_report_build_persists_new_report_identity(tmp_path: Path) -> None:
    """Build a report from one exact saved triage result without any send."""
    config_path = minimal_config(tmp_path / "operator.toml", ("a5_report_build",))
    report_policy = policy()
    configuration = load_operator_configuration(
        config_path,
        command_options={
            "report": {
                "policy": report_policy.model_dump(mode="json"),
                "renderer": {
                    "max_part_bytes": 65536,
                    "max_total_bytes": 262144,
                    "max_parts": 8,
                },
                "max_input_bytes": 4 * 1024 * 1024,
                "timeout_seconds": 20.0,
                "claim_lease_seconds": 30.0,
            }
        },
    )

    async def exercise() -> None:
        seed = await Phase1Persistence.open(
            configuration.database_url,
            registry=ResultSchemaRegistry.phase1(),
            semantic_registry=full_semantic_registry(),
        )
        try:
            triage_ref = await save_triage(seed, triage_data(topic()))
        finally:
            await seed.close()
        selection = plan(triage_ref)
        invocation = ReportBuildInvocation(
            configuration_version=configuration.version,
            execution="report-cli-execution",
            attempt="report-cli-attempt",
            caller="operator-cli",
            authority_ref="owner-approved",
            parameters=(),
            selection_plan=selection,
            report_ref=VersionRef("report", "owner-daily", "cli-1"),
            result_id="report-cli-result",
            semantic_data_id="report-cli-data",
            selection_result_id="report-cli-selection",
            selection_semantic_data_id="report-cli-selection-data",
        )
        outcome = await execute_invocation(configuration, invocation)
        if outcome.status is not TerminalStatus.COMPLETE:
            pytest.fail(f"actual report build failed: {outcome}")
        reports = tuple(item for item in outcome.result_refs if item.kind == "report")
        if len(reports) != 1 or reports[0].result_id != "report-cli-result":
            pytest.fail("report build did not preserve the new downstream identity")

    asyncio.run(exercise())
