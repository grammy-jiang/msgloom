"""Semantic-data persistence integrity, atomicity, and lifecycle tests."""

from __future__ import annotations

import asyncio
import sqlite3
import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest

from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ExecutionIdentity,
    ResultRef,
    SemanticDataRef,
    StageResult,
    TerminalStatus,
)
from msgloom.persistence import (
    DependencyNotReadyError,
    ImmutableRecordError,
    IncompatibleSchemaError,
    Phase1Persistence,
    SemanticDataIntegrityError,
    SemanticDataReferenceError,
    SemanticDataTooLargeError,
    SemanticDataTypeError,
    UnknownSemanticDataSchemaError,
)
from tests.prepared_contract_fixtures import (
    phase1_url,
    prepared_record,
    prepared_result,
)


def test_semantic_schema_type_and_reference_mismatches_are_rejected(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        persistence = await Phase1Persistence.open(
            phase1_url(tmp_path / "phase1.sqlite3")
        )
        prepared = prepared_record()
        try:
            with pytest.raises(UnknownSemanticDataSchemaError):
                persistence.semantic_reference("data-x", "triage", "1", prepared)
            with pytest.raises(SemanticDataTypeError):
                persistence.semantic_reference(
                    "data-x", "prepared", "1", {"body": "not validated"}
                )
            reference = persistence.semantic_reference(
                "data-x", "prepared", "1", prepared
            )
            forged = replace(reference, sha256="cd" * 32)
            with pytest.raises(SemanticDataReferenceError):
                await persistence.append_result_with_data(
                    prepared_result(forged), prepared
                )
            with pytest.raises(SemanticDataReferenceError):
                await persistence.append_result(prepared_result(reference))
        finally:
            await persistence.close()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "kind",
    [
        "prepared",
        "filter_result",
        "group_result",
        "working_context",
        "triage",
        "report",
    ],
)
def test_acceptable_product_result_requires_semantic_data(
    tmp_path: Path,
    kind: str,
) -> None:
    async def exercise() -> None:
        persistence = await Phase1Persistence.open(
            phase1_url(tmp_path / f"{kind}.sqlite3")
        )
        try:
            missing = replace(
                prepared_result(None, result_id=f"{kind}-missing"),
                kind=kind,
            )
            with pytest.raises(SemanticDataReferenceError):
                await persistence.append_result(missing)

            diagnostic = replace(
                missing,
                result_id=f"{kind}-failed",
                status=TerminalStatus.FAILED,
                acceptable=False,
            )
            await persistence.append_result(diagnostic)
            if await persistence.get_result(diagnostic.result_id) != diagnostic:
                pytest.fail("Failed diagnostic metadata did not remain durable")
            with pytest.raises(DependencyNotReadyError):
                await persistence.acquire_claim(
                    f"dependent:{kind}",
                    ClaimKind.TRIAGE,
                    ExecutionIdentity(f"execution-{kind}"),
                    AttemptIdentity(f"attempt-{kind}"),
                    required_inputs=(
                        ResultRef(
                            diagnostic.result_id, kind, diagnostic.schema_version
                        ),
                    ),
                )
        finally:
            await persistence.close()

    asyncio.run(exercise())


def test_missing_required_semantic_reference_is_rejected_after_storage_tamper(
    tmp_path: Path,
) -> None:
    path = tmp_path / "phase1.sqlite3"

    async def seed() -> None:
        persistence = await Phase1Persistence.open(phase1_url(path))
        try:
            prepared = prepared_record()
            reference = persistence.semantic_reference(
                "tamper-data", "prepared", "1", prepared
            )
            await persistence.append_result_with_data(
                prepared_result(reference, result_id="tampered"), prepared
            )
        finally:
            await persistence.close()

    asyncio.run(seed())
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "UPDATE phase1_stage_results SET semantic_data_ref = NULL "
            "WHERE result_id = 'tampered'"
        )
        connection.commit()
    finally:
        connection.close()

    async def verify() -> None:
        persistence = await Phase1Persistence.open(phase1_url(path))
        try:
            with pytest.raises(SemanticDataReferenceError):
                await persistence.get_result("tampered")
            with pytest.raises(DependencyNotReadyError):
                await persistence.acquire_claim(
                    "triage:tampered",
                    ClaimKind.TRIAGE,
                    ExecutionIdentity("execution-tampered"),
                    AttemptIdentity("attempt-tampered"),
                    required_inputs=(ResultRef("tampered", "prepared", "1"),),
                )
        finally:
            await persistence.close()

    asyncio.run(verify())


def test_semantic_data_is_bounded_before_persistence(tmp_path: Path) -> None:
    async def exercise() -> None:
        persistence = await Phase1Persistence.open(
            phase1_url(tmp_path / "phase1.sqlite3")
        )
        try:
            oversized = prepared_record(body="x" * (16 * 1024 * 1024))
            with pytest.raises(SemanticDataTooLargeError):
                persistence.semantic_reference("oversized", "prepared", "1", oversized)
        finally:
            await persistence.close()

    asyncio.run(exercise())


def test_conflicting_semantic_replay_preserves_accepted_history(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        persistence = await Phase1Persistence.open(
            phase1_url(tmp_path / "phase1.sqlite3")
        )
        first = prepared_record()
        try:
            first_ref = persistence.semantic_reference(
                "stable-data", "prepared", "1", first
            )
            first_result = prepared_result(first_ref)
            await persistence.append_result_with_data(first_result, first)
            await persistence.append_result_with_data(first_result, first)

            changed = prepared_record(body="Changed semantic content.")
            changed_ref = persistence.semantic_reference(
                "stable-data", "prepared", "1", changed
            )
            with pytest.raises(ImmutableRecordError):
                await persistence.append_result_with_data(
                    replace(first_result, semantic_data_ref=changed_ref), changed
                )
            if await persistence.load_semantic_data(first_ref) != first:
                pytest.fail("Conflicting replay mutated accepted semantic history")
        finally:
            await persistence.close()

    asyncio.run(exercise())


def test_missing_and_corrupt_semantic_data_block_dependent_claims(
    tmp_path: Path,
) -> None:
    path = tmp_path / "phase1.sqlite3"

    async def seed(result_id: str, data_id: str) -> SemanticDataRef:
        persistence = await Phase1Persistence.open(phase1_url(path))
        try:
            prepared = prepared_record()
            reference = persistence.semantic_reference(
                data_id, "prepared", "1", prepared
            )
            await persistence.append_result_with_data(
                prepared_result(reference, result_id=result_id), prepared
            )
            return reference
        finally:
            await persistence.close()

    missing_ref = asyncio.run(seed("prepared-missing", "data-missing"))
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "DELETE FROM phase1_semantic_data WHERE data_id = ?",
            (missing_ref.data_id,),
        )
        connection.commit()
    finally:
        connection.close()

    async def check_missing() -> None:
        persistence = await Phase1Persistence.open(phase1_url(path))
        try:
            with pytest.raises(DependencyNotReadyError):
                await persistence.acquire_claim(
                    "triage:missing",
                    ClaimKind.TRIAGE,
                    ExecutionIdentity("execution-missing"),
                    AttemptIdentity("attempt-missing"),
                    required_inputs=(ResultRef("prepared-missing", "prepared", "1"),),
                )
        finally:
            await persistence.close()

    asyncio.run(check_missing())

    corrupt_ref = asyncio.run(seed("prepared-corrupt", "data-corrupt"))
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "UPDATE phase1_semantic_data SET payload = ? WHERE data_id = ?",
            (b"{}", corrupt_ref.data_id),
        )
        connection.commit()
    finally:
        connection.close()

    async def check_corrupt() -> None:
        persistence = await Phase1Persistence.open(phase1_url(path))
        try:
            with pytest.raises(SemanticDataIntegrityError):
                await persistence.acquire_claim(
                    "triage:corrupt",
                    ClaimKind.TRIAGE,
                    ExecutionIdentity("execution-corrupt"),
                    AttemptIdentity("attempt-corrupt"),
                    required_inputs=(ResultRef("prepared-corrupt", "prepared", "1"),),
                )
        finally:
            await persistence.close()

    asyncio.run(check_corrupt())

    digest_ref = asyncio.run(seed("prepared-digest", "data-digest"))
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "UPDATE phase1_semantic_data SET sha256 = ? WHERE data_id = ?",
            ("ef" * 32, digest_ref.data_id),
        )
        connection.commit()
    finally:
        connection.close()

    async def check_digest() -> None:
        persistence = await Phase1Persistence.open(phase1_url(path))
        try:
            with pytest.raises(SemanticDataReferenceError):
                await persistence.acquire_claim(
                    "triage:digest",
                    ClaimKind.TRIAGE,
                    ExecutionIdentity("execution-digest"),
                    AttemptIdentity("attempt-digest"),
                    required_inputs=(ResultRef("prepared-digest", "prepared", "1"),),
                )
        finally:
            await persistence.close()

    asyncio.run(check_digest())


def test_atomic_result_data_rollback_leaves_no_orphan_semantic_row(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        persistence = await Phase1Persistence.open(
            phase1_url(tmp_path / "phase1.sqlite3")
        )
        prepared = prepared_record()
        try:
            metadata_only = replace(
                prepared_result(None, result_id="atomic"),
                status=TerminalStatus.FAILED,
                acceptable=False,
            )
            await persistence.append_result(metadata_only)
            reference = persistence.semantic_reference(
                "atomic-data", "prepared", "1", prepared
            )
            with pytest.raises(ImmutableRecordError):
                await persistence.append_result_with_data(
                    prepared_result(reference, result_id="atomic"), prepared
                )
            with pytest.raises(DependencyNotReadyError):
                await persistence.load_semantic_data(reference)
        finally:
            await persistence.close()

    asyncio.run(exercise())


def test_cancelled_semantic_write_drains_before_close_and_remains_durable(
    tmp_path: Path,
) -> None:
    path = tmp_path / "phase1.sqlite3"

    async def exercise() -> SemanticDataRef:
        persistence = await Phase1Persistence.open(phase1_url(path))
        prepared = prepared_record()
        reference = persistence.semantic_reference(
            "cancel-data", "prepared", "1", prepared
        )
        result = prepared_result(reference, result_id="cancelled")
        started = threading.Event()
        release = threading.Event()
        original = persistence._store.append_result_with_data

        def slow_write(stage_result: StageResult, value: object) -> None:
            started.set()
            release.wait(timeout=2)
            time.sleep(0.02)
            original(stage_result, value)

        persistence._store.append_result_with_data = slow_write  # type: ignore[method-assign]
        write_task = asyncio.create_task(
            persistence.append_result_with_data(result, prepared)
        )
        await asyncio.to_thread(started.wait, 2)
        write_task.cancel()
        close_task = asyncio.create_task(persistence.close())
        await asyncio.sleep(0)
        if close_task.done():
            pytest.fail("Close returned before the accepted semantic write drained")
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await write_task
        await close_task
        return reference

    reference = asyncio.run(exercise())

    async def verify() -> None:
        persistence = await Phase1Persistence.open(phase1_url(path))
        try:
            if await persistence.load_semantic_data(reference) != prepared_record():
                pytest.fail(
                    "Cancelled caller returned before semantic write durability"
                )
        finally:
            await persistence.close()

    asyncio.run(verify())


def test_unknown_neutral_schema_version_requires_explicit_migration(
    tmp_path: Path,
) -> None:
    path = tmp_path / "phase1.sqlite3"

    async def initialize() -> None:
        persistence = await Phase1Persistence.open(phase1_url(path))
        await persistence.close()

    asyncio.run(initialize())
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "UPDATE phase1_schema_metadata SET value = '999' "
            "WHERE key = 'schema_version'"
        )
        connection.commit()
    finally:
        connection.close()

    async def reopen() -> None:
        with pytest.raises(IncompatibleSchemaError):
            await Phase1Persistence.open(phase1_url(path))

    asyncio.run(reopen())
