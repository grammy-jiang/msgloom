"""Explicit additive schema migration regression."""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

import pytest

from msgloom.contracts import (
    AttemptIdentity,
    ExecutionIdentity,
    ResultSchemaRegistry,
    StageResult,
    TerminalStatus,
    VersionRef,
)
from msgloom.persistence import Phase1Persistence


def _evidence() -> StageResult:
    return StageResult(
        result_id="migration-preserved",
        kind="reconcile_evidence",
        schema_version="1",
        execution=ExecutionIdentity("migration-execution"),
        attempt=AttemptIdentity("migration-attempt"),
        input_refs=(),
        source_versions=(VersionRef("source", "synthetic", "v1"),),
        prepared_versions=(),
        topic_versions=(),
        configuration_version="config-v1",
        code_version="build-v1",
        status=TerminalStatus.COMPLETE,
        acceptable=True,
    )


def test_schema_v2_migrates_additively_without_losing_data(tmp_path: Path) -> None:
    async def exercise() -> None:
        path = tmp_path / "phase1.sqlite3"
        registry = ResultSchemaRegistry.phase1().with_schema("reconcile_evidence", "1")
        store = await Phase1Persistence.open(f"sqlite:///{path}", registry=registry)
        evidence = _evidence()
        await store.append_result(evidence)
        await store.close()

        connection = sqlite3.connect(path)
        try:
            connection.execute("DROP TABLE phase1_reconciliations")
            connection.execute(
                "UPDATE phase1_schema_metadata SET value = '2' "
                "WHERE key = 'schema_version'"
            )
            connection.commit()
        finally:
            connection.close()

        reopened = await Phase1Persistence.open(f"sqlite:///{path}", registry=registry)
        try:
            if await reopened.get_result(evidence.result_id) != evidence:
                pytest.fail("Explicit v2 migration lost existing durable data")
        finally:
            await reopened.close()

    asyncio.run(exercise())
