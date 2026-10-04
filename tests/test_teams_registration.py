"""Qualify automatic additive Teams schema registration in a fresh process."""

import json
import sqlite3
import subprocess
import sys

import pytest


def test_catalog_import_registers_teams_and_preserves_legacy_binding(tmp_path):
    """Opening a pre-Teams catalog must register models without a lane import."""
    database = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE source_bindings (source_id VARCHAR(200) PRIMARY KEY, "
            "provider VARCHAR(64) NOT NULL, key_scheme VARCHAR(96) NOT NULL, "
            "account_key_sha256 VARCHAR(64) NOT NULL, "
            "binding_method VARCHAR(32) NOT NULL, bound_at VARCHAR(40) NOT NULL)"
        )
        connection.execute(
            "INSERT INTO source_bindings VALUES (?, ?, ?, ?, ?, ?)",
            ("legacy", "microsoft", "scheme", "a" * 64, "test", "2026-01-01"),
        )
    script = """
import json
import sys
from message_ingest.catalog import Catalog
catalog = Catalog('sqlite:///' + sys.argv[1])
with catalog.engine.connect() as connection:
    tables = connection.exec_driver_sql(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).scalars().all()
    binding = connection.exec_driver_sql(
        "SELECT source_id, account_key_sha256 FROM source_bindings"
    ).all()
print(json.dumps({'tables': tables, 'binding': [list(row) for row in binding]}))
catalog.close()
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(database)],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    data = json.loads(result.stdout)
    expected = {
        "teams_message_observations",
        "teams_message_current",
        "teams_message_deletions",
        "teams_message_attachments",
        "teams_topology_observations",
        "teams_topology_current",
        "teams_reference_resolution_observations",
        "teams_reference_resolution_current",
        "teams_hosted_content_observations",
        "teams_coverage_observations",
        "teams_coverage_current",
    }
    if missing := expected - set(data["tables"]):
        pytest.fail(
            f"Catalog-only import did not register Teams tables: {sorted(missing)}"
        )
    if data["binding"] != [["legacy", "a" * 64]]:
        pytest.fail("Additive registration changed an existing source binding")
