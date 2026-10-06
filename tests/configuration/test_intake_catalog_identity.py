"""Require explicit scheduled catalog authority and version its whole target."""

import copy

import pytest
from pydantic import ValidationError

from msgloom.configuration import load_operator_configuration
from msgloom.configuration.models import PreparationIntakeTarget


def test_scheduled_target_requires_catalog_pin():
    """An old unpinned operator target must fail closed during loading."""
    with pytest.raises(ValidationError):
        PreparationIntakeTarget.model_validate(
            {"source_id": "source", "stream": "todo", "consumer_id": "consumer"}
        )


@pytest.mark.parametrize(
    "pin",
    [
        None,
        {},
        {"catalog_identity": "", "schema_version": 1},
        {"catalog_identity": " ", "schema_version": 1},
        {"catalog_identity": "catalog", "schema_version": 2},
    ],
)
def test_scheduled_target_rejects_invalid_catalog_pin(pin):
    """Reject missing, blank, and unsupported catalog authority."""
    with pytest.raises(ValidationError):
        PreparationIntakeTarget.model_validate(
            {
                "source_id": "source",
                "stream": "todo",
                "consumer_id": "consumer",
                "expected_catalog": pin,
            }
        )


def test_scheduled_catalog_pin_changes_configuration_version(
    minimal_toml, full_options
):
    """Changing trusted catalog selection invalidates an earlier invocation."""
    options = copy.deepcopy(full_options)
    target = {
        "source_id": "source",
        "stream": "todo",
        "consumer_id": "consumer",
        "max_entries": 1,
        "expected_catalog": {"catalog_identity": "approved-one", "schema_version": 1},
    }
    options["preparation"]["intake_targets"] = [target]
    first = load_operator_configuration(minimal_toml, command_options=options)
    target["expected_catalog"]["catalog_identity"] = "approved-two"
    second = load_operator_configuration(minimal_toml, command_options=options)
    if first.version == second.version:
        pytest.fail("Catalog pin did not change configuration authority")
    if "approved-one" in first.snapshot().payload:
        pytest.fail("Snapshot exposed the private catalog identity")
