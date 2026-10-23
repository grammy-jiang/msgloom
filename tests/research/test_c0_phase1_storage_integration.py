"""C0: actual Phase1Persistence / SQLite storage facts, no production mutations.

Each test uses an isolated pytest tmp_path SQLite DB. These are behavioral
qualification tests for existing APIs, NOT the new A2 acceptance store.
"""

from __future__ import annotations

import asyncio
import json
import threading
from dataclasses import dataclass, replace
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
)
from msgloom.persistence import Phase1Persistence, SemanticDataRegistry
from msgloom.persistence.errors import (
    ClaimUnavailableError,
    DependencyNotReadyError,
    ImmutableRecordError,
    SemanticDataReferenceError,
    StaleClaimError,
)


@dataclass(frozen=True, slots=True)
class C0TestPayload:
    """Only a test-only sentinel, not the future prepared@2 contract."""

    content: str


class C0TestCodec:
    kind = "c0_storage_probe"
    schema_version = "1"
    max_bytes = 4096

    def encode(self, value: object) -> bytes:
        if not isinstance(value, C0TestPayload):
            raise TypeError("c0 test requires an exact payload")
        if not value.content or len(value.content.encode("utf-8")) > 1024:
            raise ValueError("c0 test payload exceeds bound")
        return json.dumps(
            {"content": value.content},
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")

    def decode(self, payload: bytes) -> object:
        data = json.loads(payload)
        if (
            not isinstance(data, dict)
            or set(data) != {"content"}
            or not isinstance(data["content"], str)
        ):
            raise ValueError("invalid c0 test payload")
        return C0TestPayload(content=data["content"])


class C0PreparedV2TestCodec(C0TestCodec):
    kind = "prepared"
    schema_version = "2"


def registries(
    *, prepared_v2: bool = False
) -> tuple[ResultSchemaRegistry, SemanticDataRegistry]:
    schema = ResultSchemaRegistry.phase1().with_schema(
        "c0_storage_probe", "1", semantic_data_required=True
    )
    codecs = [C0TestCodec()]
    if prepared_v2:
        schema = schema.with_schema("prepared", "2", semantic_data_required=True)
        codecs.append(C0PreparedV2TestCodec())
    return schema, SemanticDataRegistry(tuple(codecs))


def required_semantic_ref(result: StageResult) -> SemanticDataRef:
    """A semantic persistence result must have a typed, usable reference."""
    ref = result.semantic_data_ref
    if ref is None:
        pytest.fail("Expected a fully materialized semantic result reference")
    return ref


async def open_store(path: Path, *, prepared_v2: bool = False) -> Phase1Persistence:
    schema, semantic = registries(prepared_v2=prepared_v2)
    return await Phase1Persistence.open(
        f"sqlite:///{path}", registry=schema, semantic_registry=semantic
    )


def make_stage(
    store: Phase1Persistence,
    *,
    result_id: str,
    execution: str,
    attempt: str,
    value: C0TestPayload,
    kind: str = "c0_storage_probe",
    schema: str = "1",
) -> StageResult:
    ref = store.semantic_reference("c0-payload:" + result_id, kind, schema, value)
    return StageResult(
        result_id=result_id,
        kind=kind,
        schema_version=schema,
        execution=ExecutionIdentity(execution),
        attempt=AttemptIdentity(attempt),
        input_refs=(),
        source_versions=(),
        prepared_versions=(),
        topic_versions=(),
        configuration_version="frozen-c0-config-v1",
        code_version="frozen-c0-code-v1",
        status=TerminalStatus.COMPLETE,
        acceptable=True,
        semantic_data_ref=ref,
    )


async def create_claim(
    store: Phase1Persistence,
    key: str,
    execution: str,
    attempt: str,
    *,
    lease: float = 120,
):
    return await store.acquire_claim(
        key,
        ClaimKind.PREPARE,
        ExecutionIdentity(execution),
        AttemptIdentity(attempt),
        required_inputs=(),
        lease_seconds=lease,
    )


def test_claim_fenced_semantic_persists_after_reopen_and_different_attempt_conflicts(
    tmp_path: Path,
) -> None:
    """True SQL transaction; same logical key/new attempt is not idempotent."""

    async def scenario() -> None:
        db = tmp_path / "actual-storage.sqlite3"
        store = await open_store(db)
        value = C0TestPayload("synthetic A2 body #1")
        result_id = "c0-input-deterministic-key"
        first = make_stage(
            store,
            result_id=result_id,
            execution="c0-execution-1",
            attempt="c0-attempt-1",
            value=value,
        )
        try:
            claim1 = await create_claim(
                store, "c0-probe:one-input", "c0-execution-1", "c0-attempt-1"
            )
            await store.append_result_with_data(first, value, claim=claim1)
            if await store.get_result(result_id) != first:
                pytest.fail(
                    "first accepted StageResult was not readable after the claim-fenced append"
                )
            if await store.load_semantic_data(required_semantic_ref(first)) != value:
                pytest.fail(
                    "first semantic bytes were not readable after the claim-fenced append"
                )
            await store.finish_claim(
                claim1, TerminalStatus.COMPLETE, ExternalEffectState.NONE
            )
        finally:
            await store.close()

        store = await open_store(db)
        try:
            if await store.get_result(result_id) != first:
                pytest.fail(
                    "first StageResult changed after reopening the SQLite database"
                )
            if await store.load_semantic_data(required_semantic_ref(first)) != value:
                pytest.fail(
                    "first semantic bytes changed after reopening the SQLite database"
                )
            claim2 = await create_claim(
                store, "c0-probe:one-input", "c0-execution-2", "c0-attempt-2"
            )
            replay = replace(
                first,
                execution=ExecutionIdentity("c0-execution-2"),
                attempt=AttemptIdentity("c0-attempt-2"),
            )
            with pytest.raises(ImmutableRecordError):
                await store.append_result_with_data(replay, value, claim=claim2)
            changed = C0TestPayload("synthetic A2 body CHANGED")
            changed_stage = make_stage(
                store,
                result_id=result_id,
                execution="c0-execution-2",
                attempt="c0-attempt-2",
                value=changed,
            )
            with pytest.raises(ImmutableRecordError):
                await store.append_result_with_data(
                    changed_stage, changed, claim=claim2
                )
            # Published first result is not changed by either rollback.
            if await store.get_result(result_id) != first:
                pytest.fail(
                    "first StageResult changed after a rejected equal-byte or changed-byte replay"
                )
            if await store.load_semantic_data(required_semantic_ref(first)) != value:
                pytest.fail(
                    "first semantic bytes changed after a rejected equal-byte or changed-byte replay"
                )
            await store.finish_claim(
                claim2, TerminalStatus.INCOMPLETE, ExternalEffectState.NONE
            )
        finally:
            await store.close()

    asyncio.run(scenario())


def test_durable_claim_busy_and_expiry_fence_real_sqlite(tmp_path: Path) -> None:
    """Busy, expired, and already-terminal owner cannot publish."""

    async def scenario() -> None:
        store = await open_store(tmp_path / "claims.sqlite3")
        try:
            active = await create_claim(
                store, "c0-probe:busy", "first-exec", "first-attempt"
            )
            with pytest.raises(ClaimUnavailableError):
                await create_claim(
                    store, "c0-probe:busy", "second-exec", "second-attempt"
                )
            value = C0TestPayload("prohibited after finish")
            terminal_stage = make_stage(
                store,
                result_id="after-finish",
                execution="first-exec",
                attempt="first-attempt",
                value=value,
            )
            await store.finish_claim(
                active, TerminalStatus.INCOMPLETE, ExternalEffectState.NONE
            )
            with pytest.raises(StaleClaimError):
                await store.append_result_with_data(terminal_stage, value, claim=active)
            if not (await store.get_result("after-finish") is None):
                pytest.fail(
                    "result was published although its claim was already finished"
                )

            expired = await create_claim(
                store,
                "c0-probe:expired",
                "expired-exec",
                "expired-attempt",
                lease=0,
            )
            expired_stage = make_stage(
                store,
                result_id="expired-result",
                execution="expired-exec",
                attempt="expired-attempt",
                value=value,
            )
            with pytest.raises(StaleClaimError):
                await store.append_result_with_data(expired_stage, value, claim=expired)
            if not (await store.get_result("expired-result") is None):
                pytest.fail(
                    "result was published although its claim lease was already expired"
                )
        finally:
            await store.close()

    asyncio.run(scenario())


def test_cancellation_after_real_sqlite_commit_requires_readback(
    tmp_path: Path,
) -> None:
    """Delay acknowledgement *after* a real SQLite COMMIT, then cancel caller."""

    async def scenario() -> None:
        db = tmp_path / "postcommit.sqlite3"
        store = await open_store(db)
        value = C0TestPayload("already durably accepted")
        result = make_stage(
            store,
            result_id="postcommit-result",
            execution="publish-exec",
            attempt="publish-attempt",
            value=value,
        )
        try:
            claim = await create_claim(
                store, "c0-probe:postcommit", "publish-exec", "publish-attempt"
            )
            saved = store._store.append_result_with_data
            committed = threading.Event()
            allow_return = threading.Event()

            def delayed_after_commit(*args, **kwargs):
                saved(*args, **kwargs)  # REAL Phase1Store transaction, COMMIT done
                committed.set()
                if not allow_return.wait(timeout=30):
                    raise RuntimeError("test acknowledgement barrier timed out")

            store._store.append_result_with_data = delayed_after_commit
            publishing = asyncio.create_task(
                store.append_result_with_data(result, value, claim=claim)
            )
            if not (await asyncio.to_thread(committed.wait, 30)):
                pytest.fail(
                    "worker never reached the post-COMMIT barrier before the timeout"
                )
            if not (publishing.cancel()):
                pytest.fail(
                    "caller task was already done, so cancellation could not be tested"
                )
            allow_return.set()
            with pytest.raises(asyncio.CancelledError):
                await publishing
            # Successful SQLite commit is still visible, despite CANCELLED.
            if await store.get_result(result.result_id) != result:
                pytest.fail(
                    "committed StageResult was not visible after the caller was cancelled"
                )
            if await store.load_semantic_data(required_semantic_ref(result)) != value:
                pytest.fail(
                    "committed semantic bytes were not visible after the caller was cancelled"
                )
            store._store.append_result_with_data = saved
            await store.finish_claim(
                claim, TerminalStatus.INCOMPLETE, ExternalEffectState.NONE
            )
        finally:
            await store.close()
        reopened = await open_store(db)
        try:
            if await reopened.get_result(result.result_id) != result:
                pytest.fail(
                    "committed StageResult was not visible after reopening the database"
                )
            if (
                await reopened.load_semantic_data(required_semantic_ref(result))
                != value
            ):
                pytest.fail(
                    "committed semantic bytes were not visible after reopening the database"
                )
        finally:
            await reopened.close()

    asyncio.run(scenario())


def test_legacy_preparation_proof_explicitly_rejects_prepared_v2(
    tmp_path: Path,
) -> None:
    """Even an opt-in registry cannot bypass the V1 plan-proof whitelist."""

    async def scenario() -> None:
        store = await open_store(tmp_path / "legacy-proof.sqlite3", prepared_v2=True)
        value = C0TestPayload("v2 synthetic example")
        try:
            claim = await create_claim(
                store, "prepare:c0-test-v2", "v2-exec", "v2-attempt"
            )
            prepared_v2 = make_stage(
                store,
                result_id="new-prepared-v2",
                kind="prepared",
                schema="2",
                execution="v2-exec",
                attempt="v2-attempt",
                value=value,
            )
            with pytest.raises(DependencyNotReadyError):
                await store.append_result_with_data(prepared_v2, value, claim=claim)
            if not (await store.get_result(prepared_v2.result_id) is None):
                pytest.fail(
                    "prepared@2 result was stored although the legacy plan proof rejected it"
                )
            await store.finish_claim(
                claim, TerminalStatus.INCOMPLETE, ExternalEffectState.NONE
            )
        finally:
            await store.close()

    asyncio.run(scenario())


def test_codec_integrity_failure_does_not_create_result(tmp_path: Path) -> None:
    async def scenario() -> None:
        store = await open_store(tmp_path / "corrupt.sqlite3")
        first = C0TestPayload("accepted bytes")
        mismatch = C0TestPayload("different bytes")
        try:
            claim = await create_claim(
                store, "c0-probe:integrity", "integrity-exec", "integrity-attempt"
            )
            stage = make_stage(
                store,
                result_id="integrity-proof",
                execution="integrity-exec",
                attempt="integrity-attempt",
                value=first,
            )
            with pytest.raises(SemanticDataReferenceError):
                await store.append_result_with_data(stage, mismatch, claim=claim)
            if not (await store.get_result(stage.result_id) is None):
                pytest.fail(
                    "StageResult was stored although the semantic codec check failed"
                )
            await store.finish_claim(
                claim, TerminalStatus.INCOMPLETE, ExternalEffectState.NONE
            )
        finally:
            await store.close()

    asyncio.run(scenario())
