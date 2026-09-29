"""Explicit additive schema migration regression."""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

import pytest

from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ExecutionIdentity,
    ResultSchemaRegistry,
    StageResult,
    TerminalStatus,
    VersionRef,
)
from msgloom.persistence import IncompatibleSchemaError, Phase1Persistence


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
        claim = await store.acquire_claim(
            "migration:claim",
            ClaimKind.REPORT_SUBMIT,
            ExecutionIdentity("migration-claim-execution"),
            AttemptIdentity("migration-claim-attempt"),
            lease_seconds=60,
        )
        await store.close()

        connection = sqlite3.connect(path)
        try:
            connection.execute("DROP TABLE phase1_reconciliations")
            connection.execute(
                "UPDATE phase1_schema_metadata SET value = '2' "
                "WHERE key = 'schema_version'"
            )
            connection.execute(
                "INSERT INTO phase1_schema_metadata(key, value) VALUES (?, ?)",
                ("migration_sentinel", "preserve-me"),
            )
            connection.commit()
        finally:
            connection.close()

        reopened = await Phase1Persistence.open(f"sqlite:///{path}", registry=registry)
        try:
            if await reopened.get_result(evidence.result_id) != evidence:
                pytest.fail("Explicit v2 migration lost existing durable data")
            snapshot = await reopened.inspect_claim(claim.claim_key)
            if snapshot.current_token != claim:
                pytest.fail("Explicit v2 migration lost existing claim ownership")
            connection = sqlite3.connect(path)
            try:
                metadata = dict(
                    connection.execute(
                        "SELECT key, value FROM phase1_schema_metadata"
                    ).fetchall()
                )
            finally:
                connection.close()
            if metadata.get("schema_version") != "3":
                pytest.fail("Explicit migration did not persist exact v3 metadata")
            if metadata.get("migration_sentinel") != "preserve-me":
                pytest.fail("Explicit migration changed unrelated metadata")
        finally:
            await reopened.close()

    asyncio.run(exercise())


@pytest.mark.parametrize("mutation", ["missing_metadata", "partial", "unknown_version"])
def test_malformed_schema_fails_closed_without_partial_changes(
    tmp_path: Path, mutation: str
) -> None:
    async def exercise() -> None:
        path = tmp_path / f"{mutation}.sqlite3"
        store = await Phase1Persistence.open(f"sqlite:///{path}")
        await store.close()

        connection = sqlite3.connect(path)
        try:
            connection.execute("DROP TABLE phase1_reconciliations")
            connection.execute(
                "UPDATE phase1_schema_metadata SET value = '2' "
                "WHERE key = 'schema_version'"
            )
            if mutation == "missing_metadata":
                connection.execute("DROP TABLE phase1_schema_metadata")
            elif mutation == "partial":
                connection.execute("DROP TABLE phase1_stage_results")
            else:
                connection.execute(
                    "UPDATE phase1_schema_metadata SET value = '999' "
                    "WHERE key = 'schema_version'"
                )
            connection.commit()
            before = tuple(
                connection.execute(
                    "SELECT type, name, sql FROM sqlite_master "
                    "WHERE name LIKE 'phase1_%' ORDER BY type, name"
                ).fetchall()
            )
        finally:
            connection.close()

        with pytest.raises(IncompatibleSchemaError):
            await Phase1Persistence.open(f"sqlite:///{path}")

        connection = sqlite3.connect(path)
        try:
            after = tuple(
                connection.execute(
                    "SELECT type, name, sql FROM sqlite_master "
                    "WHERE name LIKE 'phase1_%' ORDER BY type, name"
                ).fetchall()
            )
        finally:
            connection.close()
        if after != before:
            pytest.fail("Failed schema validation partially changed the database")

    asyncio.run(exercise())
