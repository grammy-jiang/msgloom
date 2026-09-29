"""Help, configuration, and read-only saved-status CLI coverage."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from msgloom.contracts import (
    ExecutionIdentity,
    OperationOutcome,
    PhaseCapability,
    ResultRef,
    TerminalStatus,
)
from msgloom.persistence import Phase1Persistence
from tests.application_cli.helpers import invoke, minimal_config


def test_help_and_config_do_not_create_storage_or_require_credentials(
    tmp_path: Path,
) -> None:
    """Help and config inspection stay outside runtime adapter construction."""
    root = Path(__file__).parents[2]
    config = minimal_config(tmp_path / "operator.toml")

    help_result = invoke(root, "--help")
    if help_result.returncode != 0 or "report" not in help_result.stdout:
        pytest.fail("installed command surface help was not ready")

    result = invoke(root, "config", "validate", str(config))
    if result.returncode != 0:
        pytest.fail(f"config validation failed: {result.stdout}")
    payload = json.loads(result.stdout)
    if payload.get("status") != "ok":
        pytest.fail("config validation did not return the fixed success contract")
    if (tmp_path / "state" / "phase1.sqlite3").exists():
        pytest.fail("config validation constructed persistence")

    inspected = invoke(root, "config", "inspect", str(config))
    if inspected.returncode != 0:
        pytest.fail("redacted config inspection failed")
    if str(tmp_path) in inspected.stdout:
        pytest.fail("config inspection exposed a private filesystem path")


def test_status_is_read_only_and_reports_exact_saved_refs(tmp_path: Path) -> None:
    """Status never creates missing storage and reads exact terminal references."""
    root = Path(__file__).parents[2]
    config = minimal_config(tmp_path / "operator.toml")
    database = tmp_path / "state" / "phase1.sqlite3"

    missing = invoke(root, "status", str(config), "execution-one")
    if missing.returncode != 2:
        pytest.fail("missing status storage did not fail closed")
    if database.exists():
        pytest.fail("status silently created a missing database")

    async def seed() -> None:
        persistence = await Phase1Persistence.open(f"sqlite:///{database}")
        try:
            await persistence.save_outcome(
                OperationOutcome(
                    execution=ExecutionIdentity("execution-one"),
                    capability=PhaseCapability.PREPARE,
                    status=TerminalStatus.COMPLETE,
                    result_refs=(ResultRef("prepared-one", "prepared", "1"),),
                )
            )
        finally:
            await persistence.close()

    asyncio.run(seed())
    before = database.stat().st_mtime_ns
    result = invoke(root, "status", str(config), "execution-one")
    after = database.stat().st_mtime_ns
    if result.returncode != 0:
        pytest.fail(f"saved status failed: {result.stdout}")
    payload = json.loads(result.stdout)["saved"]
    if payload["execution"] != "execution-one":
        pytest.fail("status returned the wrong execution")
    if payload["result_refs"][0]["result_id"] != "prepared-one":
        pytest.fail("status did not preserve the exact saved result reference")
    if before != after:
        pytest.fail("read-only status rewrote the SQLite database")


def test_status_refuses_legacy_schema_without_migrating(tmp_path: Path) -> None:
    """Legacy storage is reported incompatible and remains byte-for-byte v2."""
    import sqlite3

    root = Path(__file__).parents[2]
    config = minimal_config(tmp_path / "operator.toml")
    database = tmp_path / "state" / "phase1.sqlite3"
    database.parent.mkdir()
    connection = sqlite3.connect(database)
    try:
        connection.execute(
            "CREATE TABLE phase1_schema_metadata "
            "(key VARCHAR PRIMARY KEY, value VARCHAR NOT NULL)"
        )
        connection.execute(
            "INSERT INTO phase1_schema_metadata(key, value) VALUES(?, ?)",
            ("schema_version", "2"),
        )
        connection.commit()
    finally:
        connection.close()
    before = database.read_bytes()
    result = invoke(root, "status", str(config), "execution-one")
    after = database.read_bytes()
    if result.returncode != 2:
        pytest.fail("legacy status schema did not fail closed")
    if json.loads(result.stdout).get("code") != "status_store_incompatible":
        pytest.fail("legacy schema used the wrong fixed failure code")
    if before != after:
        pytest.fail("status migrated or rewrote legacy storage")
