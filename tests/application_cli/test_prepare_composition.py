"""Actual A2 construction through the awaited operator composition API."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import cast

import pytest

from msgloom.cli.composition import execute_invocation
from msgloom.cli.models import PrepareInvocation
from msgloom.configuration import load_operator_configuration
from msgloom.contracts import TerminalStatus, VersionRef
from msgloom.preparation import DocumentFormat, PreparedSourceType
from msgloom.preparation_pipeline import PreparationMode, SelectionPlan
from tests.application_cli.helpers import minimal_config
from tests.preparation_pipeline.helpers import filter_config, profiles


def test_actual_prepare_uses_saved_reader_and_reviewed_parser_profiles(
    saved_catalog: dict[str, object],
    tmp_path: Path,
) -> None:
    """Construct A2 lazily and persist durable results from synthetic A1 bytes."""
    config_path = minimal_config(tmp_path / "operator.toml", ("a2_prepare",))
    parser_profiles = profiles(
        DocumentFormat.HTML,
        DocumentFormat.TEXT,
        DocumentFormat.JSON,
        DocumentFormat.MIME,
    )
    configuration = load_operator_configuration(
        config_path,
        command_options={
            "source": {
                "catalog_path": str(cast(Path, saved_catalog["database"])),
                "evidence_roots": [str(cast(Path, saved_catalog["evidence_root"]))],
                "limits": {"max_selected_records": 8},
            },
            "preparation": {
                "filter_config": filter_config().model_dump(mode="json"),
                "parser_profiles": [
                    item.model_dump(mode="json") for item in parser_profiles
                ],
                "execution_timeout_seconds": 30.0,
                "claim_lease_seconds": 35.0,
                "max_records": 8,
            },
        },
    )
    source = VersionRef(
        PreparedSourceType.OUTLOOK_EMAIL.value,
        cast(str, saved_catalog["source_id"]) + "/message",
        "obs-current",
    )
    invocation = PrepareInvocation(
        configuration_version=configuration.version,
        execution="prepare-cli-execution",
        attempt="prepare-cli-attempt",
        caller="operator-cli",
        authority_ref="owner-approved",
        mode=PreparationMode.LIVE,
        selections=(SelectionPlan(source=source),),
    )
    outcome = asyncio.run(execute_invocation(configuration, invocation))
    if outcome.status not in {TerminalStatus.COMPLETE, TerminalStatus.INCOMPLETE}:
        pytest.fail(f"actual preparation composition failed: {outcome}")
    kinds = {item.kind for item in outcome.result_refs}
    if (
        not {"collected_selection", "prepared", "filter_result", "group_result"}
        <= kinds
    ):
        pytest.fail("actual preparation did not persist the reviewed durable stages")
