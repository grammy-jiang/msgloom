"""Scheduled PREPARE uses exact durable intake with finite ownership."""

import asyncio

import pytest
from pydantic import ValidationError

from msgloom.cli import models
from msgloom.cli.composition import execute_invocation
from msgloom.configuration import load_operator_configuration
from msgloom.configuration import models as config_models
from msgloom.contracts import TerminalStatus
from tests.application_cli.helpers import minimal_config
from tests.preparation_intake_helpers import release
from tests.preparation_pipeline.helpers import filter_config


def scheduled_api():
    """Fail explicitly when the scheduled public envelope is absent."""
    if not hasattr(models, "ScheduledPrepareInvocation"):
        pytest.fail("separate scheduled PREPARE invocation is missing")
    return models.ScheduledPrepareInvocation


def configuration(saved, tmp_path):
    """Load real strict configuration with one stable consumer."""
    return load_operator_configuration(
        minimal_config(tmp_path / "operator.toml"),
        command_options={
            "source": {
                "catalog_path": str(saved["database"]),
                "evidence_roots": [str(saved["evidence_root"])],
            },
            "preparation": {
                "filter_config": filter_config().model_dump(mode="json"),
                "parser_profiles": [],
                "intake_targets": [
                    {
                        "source_id": "synthetic-source",
                        "stream": "todo",
                        "consumer_id": "stable",
                        "max_entries": 1,
                        "max_pending_worksets": 2,
                    }
                ],
            },
        },
    )


def test_target_rejects_credentials_coercion_and_empty_consumer():
    """Reject unsafe and ambiguous trusted target identity."""
    if not hasattr(config_models, "PreparationIntakeTarget"):
        pytest.fail("closed intake target configuration is missing")
    model = config_models.PreparationIntakeTarget
    valid = {"source_id": "source", "stream": "todo", "consumer_id": "stable"}
    for change in (
        {"password": "secret"},
        {"max_entries": "2"},
        {"consumer_id": " "},
        {"max_pending_worksets": 0},
    ):
        with pytest.raises(ValidationError):
            model(**(valid | change))


@pytest.mark.parametrize("new_work", [False, True])
def test_scheduled_no_work_and_new_exact_replay(saved_catalog, tmp_path, new_work):
    """Return finite accepted outcomes and durable terminal workset state."""
    model = scheduled_api()
    if new_work:
        release(saved_catalog)
    else:
        # Initialize an authentic empty ledger using the fixture catalog.
        from message_ingest.catalog import Catalog
        from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore

        catalog = Catalog(f"sqlite:///{saved_catalog['database']}")
        AcquisitionHandoffStore(catalog)
        catalog.close()
    config = configuration(saved_catalog, tmp_path)
    invocation = model(
        configuration_version=config.version,
        execution="scheduled",
        attempt="attempt",
        caller="operator-cli",
        authority_ref="owner-approved",
    )
    outcome = asyncio.run(execute_invocation(config, invocation))
    if outcome.status not in {TerminalStatus.COMPLETE, TerminalStatus.INCOMPLETE}:
        pytest.fail(f"scheduled preparation failed: {outcome}")
    if new_work and not any(ref.kind == "prepared" for ref in outcome.result_refs):
        pytest.fail("scheduled intake did not replay its frozen selection")
    if not new_work and outcome.result_refs:
        pytest.fail("empty ledger fabricated outputs")


def test_scheduled_denied_before_intake(saved_catalog, tmp_path):
    """An untrusted caller cannot create source or cursor progress."""
    model = scheduled_api()
    config = configuration(saved_catalog, tmp_path)
    invocation = model(
        configuration_version=config.version,
        execution="denied",
        attempt="attempt",
        caller="stranger",
        authority_ref="owner-approved",
    )
    outcome = asyncio.run(execute_invocation(config, invocation))
    if outcome.status is not TerminalStatus.BLOCKED:
        pytest.fail("scheduled intake bypassed trusted PREPARE admission")
