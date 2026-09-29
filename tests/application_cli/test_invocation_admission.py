"""Closed invocation-file and configuration-version admission tests."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from msgloom.cli.codecs import InvocationError, load_invocation
from msgloom.cli.models import CliRequest, StageName
from msgloom.cli.runner import run_request
from msgloom.configuration import load_operator_configuration
from tests.application_cli.helpers import minimal_config


def _prepare_payload(version: str) -> dict[str, object]:
    return {
        "schema_version": "1",
        "configuration_version": version,
        "execution": "execution-one",
        "attempt": "attempt-one",
        "caller": "operator-cli",
        "authority_ref": "owner-approved",
        "parameters": [],
        "mode": "live",
        "selections": [
            {
                "source": {
                    "kind": "outlook-email",
                    "identity": "synthetic-source",
                    "version": "one",
                },
                "replay_result": None,
                "replay_selection": None,
            }
        ],
    }


def test_duplicate_unknown_and_oversized_invocation_inputs_fail_closed(
    tmp_path: Path,
) -> None:
    """Invocation decoding rejects ambiguous or unbounded caller content."""
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(
        '{"schema_version":"1","schema_version":"1"}',
        encoding="utf-8",
    )
    try:
        load_invocation(duplicate, StageName.PREPARE)
    except InvocationError as error:
        if error.code != "invocation_duplicate_key":
            pytest.fail("duplicate key used the wrong safe failure code")
    else:
        pytest.fail("duplicate invocation key was accepted")

    unknown = tmp_path / "unknown.json"
    payload = _prepare_payload("version")
    payload["unexpected"] = True
    unknown.write_text(json.dumps(payload), encoding="utf-8")
    try:
        load_invocation(unknown, StageName.PREPARE)
    except InvocationError as error:
        if error.code != "invocation_invalid":
            pytest.fail("unknown field used the wrong safe failure code")
    else:
        pytest.fail("unknown invocation field was accepted")

    large = tmp_path / "large.json"
    large.write_bytes(b"x" * (2 * 1024 * 1024 + 1))
    try:
        load_invocation(large, StageName.PREPARE)
    except InvocationError as error:
        if error.code != "invocation_too_large":
            pytest.fail("oversized invocation used the wrong safe failure code")
    else:
        pytest.fail("oversized invocation was accepted")


def test_configuration_version_mismatch_precedes_persistence(tmp_path: Path) -> None:
    """A stale invocation fails before source/parser/persistence construction."""
    config = minimal_config(tmp_path / "operator.toml")
    current = load_operator_configuration(config)
    invocation = tmp_path / "prepare.json"
    invocation.write_text(
        json.dumps(_prepare_payload(current.version + "-stale")),
        encoding="utf-8",
    )
    request = CliRequest(
        action="execute",
        config_file=str(config),
        invocation_file=str(invocation),
        stage=StageName.PREPARE,
    )
    result = asyncio.run(run_request(request))
    if result.exit_code != 2 or result.payload.get("code") != "invocation_invalid":
        pytest.fail("configuration-version mismatch did not fail closed")
    if (tmp_path / "state" / "phase1.sqlite3").exists():
        pytest.fail("rejected invocation constructed persistence")


def test_selected_replay_requires_explicit_replay_mode(tmp_path: Path) -> None:
    """Replay rejects a live A2 plan before constructing persistence or adapters."""
    config = minimal_config(tmp_path / "operator.toml")
    current = load_operator_configuration(config)
    invocation = tmp_path / "prepare-live.json"
    invocation.write_text(
        json.dumps(_prepare_payload(current.version)),
        encoding="utf-8",
    )
    result = asyncio.run(
        run_request(
            CliRequest(
                action="replay",
                config_file=str(config),
                invocation_file=str(invocation),
                stage=StageName.PREPARE,
            )
        )
    )
    if result.payload.get("code") != "replay_mode_required":
        pytest.fail("selected replay accepted a live preparation plan")
    if (tmp_path / "state" / "phase1.sqlite3").exists():
        pytest.fail("rejected replay constructed persistence")
