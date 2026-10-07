"""Integration checks for neutral schema ownership and Application outcomes."""

from __future__ import annotations

import ast
import asyncio
import sqlite3
from pathlib import Path

import pytest

from msgloom.application import Application
from msgloom.contracts import (
    ExecutionIdentity,
    OperationRequest,
    PhaseCapability,
    TerminalStatus,
)
from msgloom.persistence import IncompatibleSchemaError, Phase1Persistence


def _url(path: Path) -> str:
    return f"sqlite:///{path}"


def test_blocked_application_outcome_is_saved_in_real_persistence(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        persistence = await Phase1Persistence.open(_url(tmp_path / "phase1.sqlite3"))
        try:
            application = Application(persistence)
            request = OperationRequest(
                execution=ExecutionIdentity("blocked-execution"),
                caller="synthetic-caller",
                capability=PhaseCapability.EXECUTE_ACTION,
            )
            outcome = await application.run(request)
            saved = await persistence.get_outcome(request.execution)
            if outcome.status is not TerminalStatus.BLOCKED:
                pytest.fail("Expected later capability to be blocked")
            if saved != outcome:
                pytest.fail("Blocked outcome was not durable before return")
        finally:
            await persistence.close()

    asyncio.run(exercise())


def test_neutral_schema_reopens_without_recreating_or_losing_outcomes(
    tmp_path: Path,
) -> None:
    path = tmp_path / "phase1.sqlite3"

    async def first_open() -> None:
        persistence = await Phase1Persistence.open(_url(path))
        application = Application(persistence)
        await application.run(
            OperationRequest(
                execution=ExecutionIdentity("reopen-execution"),
                caller="synthetic-caller",
                capability=PhaseCapability.INVESTIGATE,
            )
        )
        await persistence.close()

    async def second_open() -> None:
        persistence = await Phase1Persistence.open(_url(path))
        try:
            saved = await persistence.get_outcome(ExecutionIdentity("reopen-execution"))
            if saved is None or saved.status is not TerminalStatus.BLOCKED:
                pytest.fail("Reopening lost the immutable terminal outcome")
        finally:
            await persistence.close()

    asyncio.run(first_open())
    asyncio.run(second_open())


def test_partial_neutral_schema_requires_explicit_migration(tmp_path: Path) -> None:
    path = tmp_path / "partial.sqlite3"
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "CREATE TABLE phase1_schema_metadata "
            "(key TEXT PRIMARY KEY NOT NULL, value TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO phase1_schema_metadata(key, value) "
            "VALUES ('schema_version', '1')"
        )
        connection.commit()
    finally:
        connection.close()

    async def exercise() -> None:
        with pytest.raises(IncompatibleSchemaError):
            await Phase1Persistence.open(_url(path))

    asyncio.run(exercise())


def test_contract_modules_import_no_cli_sdk_or_orm_packages() -> None:
    root = Path("msgloom/contracts")
    forbidden = {"sqlalchemy", "scrapy", "cyclopts", "fastmcp", "msal"}
    imported: set[str] = set()
    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
    overlap = imported & forbidden
    if overlap:
        pytest.fail(f"Transport or ORM dependency leaked into contracts: {overlap!r}")
