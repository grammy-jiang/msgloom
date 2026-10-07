"""Claim-fenced publication regressions for real SQLite persistence."""

from __future__ import annotations

import asyncio
import sqlite3
import threading
from dataclasses import replace
from pathlib import Path

import pytest

from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ExecutionIdentity,
    ExternalEffectState,
    ResultSchemaRegistry,
    SemanticDataRef,
    StageResult,
    TerminalStatus,
    VersionRef,
)
from msgloom.persistence import (
    DependencyNotReadyError,
    ExternalEffectReconciliationRequired,
    Phase1Persistence,
    StaleClaimError,
)
from msgloom.persistence.errors import DuplicateResultError
from msgloom.persistence.semantic import SemanticDataRegistry


class _TextCodec:
    kind = "fenced_data"
    schema_version = "1"
    max_bytes = 1024

    def encode(self, value: object) -> bytes:
        if not isinstance(value, str):
            raise TypeError("fenced data must be text")
        return value.encode()

    def decode(self, payload: bytes) -> object:
        return payload.decode()


def _url(path: Path) -> str:
    return f"sqlite:///{path}"


def _result(
    result_id: str,
    execution: ExecutionIdentity,
    *,
    attempt: AttemptIdentity | None = None,
    kind: str = "fenced_result",
    semantic_data_ref: SemanticDataRef | None = None,
) -> StageResult:
    return StageResult(
        result_id=result_id,
        kind=kind,
        schema_version="1",
        execution=execution,
        attempt=attempt or AttemptIdentity(f"child-{result_id}"),
        input_refs=(),
        source_versions=(VersionRef("source", "synthetic", "v1"),),
        prepared_versions=(),
        topic_versions=(),
        configuration_version="config-v1",
        code_version="build-v1",
        status=TerminalStatus.COMPLETE,
        acceptable=True,
        semantic_data_ref=semantic_data_ref,
    )


def _registries() -> tuple[ResultSchemaRegistry, SemanticDataRegistry]:
    schemas = frozenset({("fenced_result", "1"), ("fenced_data", "1")})
    return (
        ResultSchemaRegistry(schemas, frozenset({("fenced_data", "1")})),
        SemanticDataRegistry((_TextCodec(),)),
    )


async def _open(path: Path) -> Phase1Persistence:
    result_registry, semantic_registry = _registries()
    return await Phase1Persistence.open(
        _url(path),
        registry=result_registry,
        semantic_registry=semantic_registry,
    )


def _expire(path: Path, token: str) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "UPDATE phase1_work_claims "
            "SET expires_at = '2000-01-01T00:00:00+00:00' "
            "WHERE claim_token = ?",
            (token,),
        )
        connection.commit()
    finally:
        connection.close()


def _unexpire(path: Path, token: str) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "UPDATE phase1_work_claims "
            "SET expires_at = '2999-01-01T00:00:00+00:00' "
            "WHERE claim_token = ?",
            (token,),
        )
        connection.commit()
    finally:
        connection.close()


def test_expired_and_reclaimed_claims_cannot_publish_across_facades(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        path = tmp_path / "phase1.sqlite3"
        first = await _open(path)
        second = await _open(path)
        try:
            old_execution = ExecutionIdentity("execution-old")
            old = await first.acquire_claim(
                "prepare:synthetic",
                ClaimKind.PREPARE,
                old_execution,
                AttemptIdentity("attempt-old"),
                lease_seconds=0,
            )
            with pytest.raises(StaleClaimError):
                await first.append_result(
                    _result("expired", old_execution),
                    claim=old,
                )
            if await first.get_result("expired") is not None:
                pytest.fail("Expired owner published before a competing reclaim")

            new_execution = ExecutionIdentity("execution-new")
            new = await second.acquire_claim(
                "prepare:synthetic",
                ClaimKind.PREPARE,
                new_execution,
                AttemptIdentity("attempt-new"),
                lease_seconds=60,
            )
            with pytest.raises(StaleClaimError):
                await first.append_result(
                    _result("reclaimed", old_execution),
                    claim=old,
                )
            child_attempt = AttemptIdentity("child-ai-attempt")
            accepted = _result(
                "new-owner",
                new_execution,
                attempt=child_attempt,
            )
            await second.append_result(accepted, claim=new)
            if await first.get_result("new-owner") != accepted:
                pytest.fail("Current owner could not publish a child-attempt result")
        finally:
            await first.close()
            await second.close()

    asyncio.run(exercise())


def test_claim_metadata_execution_and_terminal_attempt_are_fenced(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        path = tmp_path / "phase1.sqlite3"
        store = await _open(path)
        try:
            execution = ExecutionIdentity("execution-owner")
            token = await store.acquire_claim(
                "triage:synthetic",
                ClaimKind.TRIAGE,
                execution,
                AttemptIdentity("attempt-owner"),
                lease_seconds=60,
            )
            forged = replace(token, attempt=AttemptIdentity("attempt-forged"))
            with pytest.raises(StaleClaimError):
                await store.append_result(_result("forged", execution), claim=forged)
            with pytest.raises(StaleClaimError):
                await store.append_result(
                    _result("wrong-execution", ExecutionIdentity("other")),
                    claim=token,
                )

            submit = await store.acquire_claim(
                "submit:synthetic",
                ClaimKind.REPORT_SUBMIT,
                execution,
                AttemptIdentity("attempt-submit"),
                lease_seconds=60,
            )
            await store.mark_external_effect(submit, ExternalEffectState.PENDING)
            await store.finish_claim(
                submit,
                TerminalStatus.FAILED,
                ExternalEffectState.UNKNOWN,
            )
            _unexpire(path, submit.token)
            with pytest.raises(StaleClaimError):
                await store.append_result(_result("terminal", execution), claim=submit)
        finally:
            await store.close()

    asyncio.run(exercise())


@pytest.mark.parametrize("lease", [True, float("nan"), float("inf"), -float("inf"), -1])
def test_claim_lease_rejects_invalid_values(tmp_path: Path, lease: float) -> None:
    async def exercise() -> None:
        store = await _open(tmp_path / "phase1.sqlite3")
        try:
            with pytest.raises((TypeError, ValueError), match="finite non-negative"):
                await store.acquire_claim(
                    "prepare:lease",
                    ClaimKind.PREPARE,
                    ExecutionIdentity("execution-lease"),
                    AttemptIdentity("attempt-lease"),
                    lease_seconds=lease,
                )
        finally:
            await store.close()

    asyncio.run(exercise())


def test_zero_lease_remains_explicit_immediate_expiry(tmp_path: Path) -> None:
    async def exercise() -> None:
        store = await _open(tmp_path / "phase1.sqlite3")
        try:
            execution = ExecutionIdentity("execution-zero")
            token = await store.acquire_claim(
                "prepare:zero",
                ClaimKind.PREPARE,
                execution,
                AttemptIdentity("attempt-zero"),
                lease_seconds=0,
            )
            with pytest.raises(StaleClaimError):
                await store.append_result(_result("zero", execution), claim=token)
        finally:
            await store.close()

    asyncio.run(exercise())


def test_stale_semantic_write_rolls_back_new_payload(tmp_path: Path) -> None:
    async def exercise() -> None:
        path = tmp_path / "phase1.sqlite3"
        store = await _open(path)
        try:
            execution = ExecutionIdentity("execution-semantic")
            token = await store.acquire_claim(
                "triage:semantic",
                ClaimKind.TRIAGE,
                execution,
                AttemptIdentity("attempt-semantic"),
                lease_seconds=0,
            )
            value = "synthetic semantic payload"
            reference = store.semantic_reference(
                "stale-data", "fenced_data", "1", value
            )
            result = _result(
                "stale-semantic",
                execution,
                kind="fenced_data",
                semantic_data_ref=reference,
            )
            with pytest.raises(StaleClaimError):
                await store.append_result_with_data(result, value, claim=token)
            with pytest.raises(DependencyNotReadyError):
                await store.load_semantic_data(reference)
            if await store.get_result(result.result_id) is not None:
                pytest.fail("Stale semantic transaction left a stage result")
        finally:
            await store.close()

    asyncio.run(exercise())


def test_require_new_duplicate_rolls_back_new_semantic_bytes(tmp_path: Path) -> None:
    async def exercise() -> None:
        path = tmp_path / "phase1.sqlite3"
        store = await _open(path)
        try:
            execution = ExecutionIdentity("execution-duplicate")
            first_value = "first payload"
            first_ref = store.semantic_reference(
                "first-data", "fenced_data", "1", first_value
            )
            first = _result(
                "duplicate-id",
                execution,
                kind="fenced_data",
                semantic_data_ref=first_ref,
            )
            await store.append_result_with_data(first, first_value)

            token = await store.acquire_claim(
                "triage:duplicate",
                ClaimKind.TRIAGE,
                execution,
                AttemptIdentity("attempt-duplicate"),
                lease_seconds=60,
            )
            second_value = "second payload"
            second_ref = store.semantic_reference(
                "rolled-back-data", "fenced_data", "1", second_value
            )
            duplicate = replace(first, semantic_data_ref=second_ref)
            with pytest.raises(DuplicateResultError):
                await store.append_result_with_data(
                    duplicate,
                    second_value,
                    require_new=True,
                    claim=token,
                )
            with pytest.raises(DependencyNotReadyError):
                await store.load_semantic_data(second_ref)
        finally:
            await store.close()

    asyncio.run(exercise())


def test_repeated_cancellation_drains_claim_bound_publication(tmp_path: Path) -> None:
    async def exercise() -> None:
        path = tmp_path / "phase1.sqlite3"
        store = await _open(path)
        started = threading.Event()
        release = threading.Event()
        original = store._store.append_result
        try:
            execution = ExecutionIdentity("execution-cancel")
            token = await store.acquire_claim(
                "prepare:cancel",
                ClaimKind.PREPARE,
                execution,
                AttemptIdentity("attempt-cancel"),
                lease_seconds=60,
            )
            result = _result("cancelled-fenced-write", execution)

            def slow_append(
                stage_result: StageResult,
                *,
                claim=None,
            ) -> None:
                started.set()
                release.wait(timeout=2)
                original(stage_result, claim=claim)

            store._store.append_result = slow_append  # type: ignore[method-assign]
            task = asyncio.create_task(store.append_result(result, claim=token))
            await asyncio.to_thread(started.wait, 2)
            task.cancel()
            task.cancel()
            await asyncio.sleep(0)
            if task.done():
                pytest.fail("Cancellation returned before accepted publication drained")
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            if await store.get_result(result.result_id) != result:
                pytest.fail("Drained claim-bound publication did not commit")
        finally:
            release.set()
            await store.close()

    asyncio.run(exercise())


def test_expired_submission_cannot_start_effect_but_can_reconcile_pending(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        path = tmp_path / "phase1.sqlite3"
        store = await _open(path)
        try:
            expired = await store.acquire_claim(
                "submit:not-started",
                ClaimKind.REPORT_SUBMIT,
                ExecutionIdentity("execution-not-started"),
                AttemptIdentity("attempt-not-started"),
                lease_seconds=0,
            )
            with pytest.raises(StaleClaimError):
                await store.mark_external_effect(expired, ExternalEffectState.PENDING)

            pending = await store.acquire_claim(
                "submit:pending",
                ClaimKind.REPORT_SUBMIT,
                ExecutionIdentity("execution-pending"),
                AttemptIdentity("attempt-pending"),
                lease_seconds=60,
            )
            await store.mark_external_effect(pending, ExternalEffectState.PENDING)
            _expire(path, pending.token)
            await store.mark_external_effect(pending, ExternalEffectState.UNKNOWN)
            await store.finish_claim(
                pending,
                TerminalStatus.FAILED,
                ExternalEffectState.UNKNOWN,
            )
            with pytest.raises(ExternalEffectReconciliationRequired):
                await store.acquire_claim(
                    "submit:pending",
                    ClaimKind.REPORT_SUBMIT,
                    ExecutionIdentity("execution-retry"),
                    AttemptIdentity("attempt-retry"),
                )
        finally:
            await store.close()

    asyncio.run(exercise())
