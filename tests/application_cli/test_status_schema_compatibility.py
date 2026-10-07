"""Read-only status compatibility across explicit neutral schema versions."""

import json
import sqlite3
from pathlib import Path

import pytest

from msgloom.cli.status import StatusError, read_saved_status
from msgloom.contracts import (
    ExecutionIdentity,
    Failure,
    Limitation,
    OperationOutcome,
    PhaseCapability,
    ResultRef,
    ResultSchemaRegistry,
    TerminalStatus,
)
from msgloom.persistence.store import Phase1Store
from tests.application_cli.helpers import invoke, minimal_config


def _seed(path: Path, version: str) -> None:
    """Save an outcome and build an exact legacy schema if requested."""
    store = Phase1Store(f"sqlite:///{path}", ResultSchemaRegistry.phase1())
    try:
        store.save_outcome(
            OperationOutcome(
                execution=ExecutionIdentity("execution-one"),
                capability=PhaseCapability.PREPARE,
                status=TerminalStatus.INCOMPLETE,
                result_refs=(
                    ResultRef("prepared-one", "prepared", "1"),
                    ResultRef("group-two", "group_result", "1"),
                ),
                limitations=(Limitation("held-input", "Safe limitation"),),
                failures=(Failure("unavailable", "Safe failure"),),
            )
        )
    finally:
        store.close()
    if version == "4":
        return
    with sqlite3.connect(path) as connection:
        for table in (
            "phase1_preparation_intake_held_entries",
            "phase1_preparation_intake_worksets",
            "phase1_preparation_intake_cursors",
        ):
            connection.execute(f"DROP TABLE {table}")
        connection.execute(
            "UPDATE phase1_schema_metadata SET value=? WHERE key='schema_version'",
            (version,),
        )


def _snapshot(path: Path) -> tuple:
    """Capture bytes, mtime, and siblings to detect writes or created files."""
    return (
        path.read_bytes(),
        path.stat().st_mtime_ns,
        tuple(sorted(item.name for item in path.parent.iterdir())),
    )


@pytest.mark.parametrize("version", ["3", "4"])
def test_cli_reads_known_schema_without_writes_or_migration(
    tmp_path: Path, version: str
) -> None:
    """Preserve exact refs and storage for both known schema versions."""
    root = Path(__file__).parents[2]
    config = minimal_config(tmp_path / "operator.toml")
    database = tmp_path / "state" / "phase1.sqlite3"
    _seed(database, version)
    before = _snapshot(database)
    result = invoke(root, "status", str(config), "execution-one")
    if _snapshot(database) != before:
        pytest.fail("Status created, migrated, or rewrote persistent storage")
    if result.returncode != 0:
        pytest.fail(f"Known schema {version} was rejected: {result.stdout}")
    expected = {
        "execution": "execution-one",
        "capability": "a2_prepare",
        "status": "incomplete",
        "result_refs": [
            {"result_id": "prepared-one", "kind": "prepared", "schema_version": "1"},
            {"result_id": "group-two", "kind": "group_result", "schema_version": "1"},
        ],
        "limitation_codes": ["held-input"],
        "failure_codes": ["unavailable"],
        "external_effect": "none",
    }
    if json.loads(result.stdout)["saved"] != expected:
        pytest.fail("Status changed exact saved references or outcome metadata")
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
        row = connection.execute(
            "SELECT value FROM phase1_schema_metadata WHERE key='schema_version'"
        ).fetchone()
    if row != (version,):
        pytest.fail("Read-only status migrated the schema")


@pytest.mark.parametrize("version", ["2", "0", "5", "999", "04", "future"])
def test_status_rejects_unsupported_versions_without_writing(
    tmp_path: Path, version: str
) -> None:
    """A populated but unsupported database remains byte-for-byte unchanged."""
    database = tmp_path / "state" / "phase1.sqlite3"
    _seed(database, "3")
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE phase1_schema_metadata SET value=? WHERE key='schema_version'",
            (version,),
        )
    before = _snapshot(database)
    with pytest.raises(StatusError, match="^status_store_incompatible$"):
        read_saved_status(f"sqlite:///{database}", "execution-one")
    if _snapshot(database) != before:
        pytest.fail("Unsupported status storage was changed")


def test_missing_status_database_does_not_create_parent_or_file(tmp_path: Path) -> None:
    """Keep missing status storage absent."""
    database = tmp_path / "missing" / "phase1.sqlite3"
    with pytest.raises(StatusError, match="^status_store_unavailable$"):
        read_saved_status(f"sqlite:///{database}", "execution-one")
    if database.parent.exists():
        pytest.fail("Status created a missing storage directory")


@pytest.mark.parametrize(
    "damage",
    [
        "not_sqlite",
        "empty",
        "missing_metadata",
        "missing_version",
        "missing_outcomes",
        "malformed_refs",
    ],
)
def test_corrupt_status_database_fails_closed_without_writes(
    tmp_path: Path, damage: str
) -> None:
    """Return only safe errors for corrupt status storage."""
    database = tmp_path / "state" / "phase1.sqlite3"
    _seed(database, "4")
    if damage == "not_sqlite":
        database.write_bytes(b"synthetic corrupt database")
    elif damage == "empty":
        database.write_bytes(b"")
    else:
        with sqlite3.connect(database) as connection:
            if damage == "missing_metadata":
                connection.execute("DROP TABLE phase1_schema_metadata")
            elif damage == "missing_version":
                connection.execute("DELETE FROM phase1_schema_metadata")
            elif damage == "missing_outcomes":
                connection.execute("DROP TABLE phase1_operation_outcomes")
            else:
                connection.execute(
                    "UPDATE phase1_operation_outcomes SET result_refs='invalid-json'"
                )
    before = _snapshot(database)
    with pytest.raises(StatusError, match="^status_store_incompatible$"):
        read_saved_status(f"sqlite:///{database}", "execution-one")
    if _snapshot(database) != before:
        pytest.fail("Corrupt status storage was rewritten")


@pytest.mark.parametrize("version", ["3", "4"])
def test_missing_outcome_in_known_schema_remains_read_only(
    tmp_path: Path, version: str
) -> None:
    """Known schemas distinguish absent outcomes from incompatible storage."""
    database = tmp_path / "state" / "phase1.sqlite3"
    _seed(database, version)
    before = _snapshot(database)
    with pytest.raises(StatusError, match="^status_not_found$"):
        read_saved_status(f"sqlite:///{database}", "missing-execution")
    if _snapshot(database) != before:
        pytest.fail("Missing outcome inspection changed storage")
