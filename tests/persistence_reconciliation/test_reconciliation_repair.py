"""Adversarial reconciliation recovery and snapshot regressions."""

from __future__ import annotations

import asyncio
import sqlite3
import threading
from pathlib import Path

import pytest

import msgloom.persistence.store as persistence_store
from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ClaimToken,
    ExecutionIdentity,
    ExternalEffectState,
    ResultRef,
    ResultSchemaRegistry,
    StageResult,
    TerminalStatus,
    VersionRef,
)
from msgloom.persistence import (
    ExternalEffectReconciliationRequired,
    Phase1Persistence,
    ReconciliationIdentity,
    ReconciliationRequest,
    StaleClaimError,
)


def _registry() -> ResultSchemaRegistry:
    return ResultSchemaRegistry.phase1().with_schema("reconcile_evidence", "1")


def _evidence(result_id: str) -> StageResult:
    return StageResult(
        result_id=result_id,
        kind="reconcile_evidence",
        schema_version="1",
        execution=ExecutionIdentity(f"evidence-execution-{result_id}"),
        attempt=AttemptIdentity(f"evidence-attempt-{result_id}"),
        input_refs=(),
        source_versions=(VersionRef("source", "synthetic", "v1"),),
        prepared_versions=(),
        topic_versions=(),
        configuration_version="config-v1",
        code_version="build-v1",
        status=TerminalStatus.COMPLETE,
        acceptable=True,
    )


async def _open(path: Path) -> Phase1Persistence:
    return await Phase1Persistence.open(f"sqlite:///{path}", registry=_registry())


async def _unknown(
    store: Phase1Persistence,
    *,
    claim_key: str = "submit:synthetic",
    suffix: str = "one",
) -> ClaimToken:
    token = await store.acquire_claim(
        claim_key,
        ClaimKind.REPORT_SUBMIT,
        ExecutionIdentity(f"execution-{suffix}"),
        AttemptIdentity(f"attempt-{suffix}"),
        lease_seconds=60,
    )
    await store.mark_external_effect(token, ExternalEffectState.PENDING)
    await store.finish_claim(token, TerminalStatus.FAILED, ExternalEffectState.UNKNOWN)
    return token


def _set_expiry(path: Path, token: str, value: str) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "UPDATE phase1_work_claims SET expires_at = ? WHERE claim_token = ?",
            (value, token),
        )
        connection.commit()
    finally:
        connection.close()


def _ref(result: StageResult) -> ResultRef:
    return ResultRef(result.result_id, result.kind, result.schema_version)


@pytest.mark.parametrize(
    ("effect", "decision"),
    [
        (ExternalEffectState.PENDING, ExternalEffectState.REJECTED),
        (ExternalEffectState.UNKNOWN, ExternalEffectState.REJECTED),
        (ExternalEffectState.ACCEPTED, ExternalEffectState.CONFIRMED),
    ],
)
def test_live_unfinished_exact_owner_cannot_be_reconciled(
    tmp_path: Path,
    effect: ExternalEffectState,
    decision: ExternalEffectState,
) -> None:
    async def exercise() -> None:
        store = await _open(tmp_path / f"active-{effect.value}.sqlite3")
        try:
            token = await store.acquire_claim(
                f"submit:active-{effect.value}",
                ClaimKind.REPORT_SUBMIT,
                ExecutionIdentity(f"active-{effect.value}"),
                AttemptIdentity(f"active-{effect.value}"),
                lease_seconds=60,
            )
            await store.mark_external_effect(token, ExternalEffectState.PENDING)
            if effect is not ExternalEffectState.PENDING:
                await store.mark_external_effect(token, effect)
            proof = _evidence(f"active-proof-{effect.value}")
            await store.append_result(proof)
            with pytest.raises(
                StaleClaimError, match="active claim owner cannot be reconciled"
            ):
                await store.reconcile_external_effect(
                    ReconciliationRequest(
                        ReconciliationIdentity(f"active-{effect.value}"),
                        token,
                        decision,
                        (_ref(proof),),
                    )
                )
            snapshot = await store.inspect_claim(token.claim_key)
            if snapshot.current_token != token or snapshot.current_effect is not effect:
                pytest.fail("Active-owner rejection changed the durable claim gate")
            if snapshot.reconciliations:
                pytest.fail("Active-owner rejection appended reconciliation proof")
        finally:
            await store.close()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "decision",
    [ExternalEffectState.ACCEPTED, ExternalEffectState.CONFIRMED],
)
def test_reconciled_expired_owner_cannot_publish_mark_or_finish_late(
    tmp_path: Path, decision: ExternalEffectState
) -> None:
    async def exercise() -> None:
        path = tmp_path / f"late-{decision.value}.sqlite3"
        store = await _open(path)
        try:
            token = await store.acquire_claim(
                f"submit:late-{decision.value}",
                ClaimKind.REPORT_SUBMIT,
                ExecutionIdentity(f"late-{decision.value}"),
                AttemptIdentity(f"late-{decision.value}"),
                lease_seconds=60,
            )
            await store.mark_external_effect(token, ExternalEffectState.PENDING)
            _set_expiry(path, token.token, "2000-01-01T00:00:00+00:00")
            proof = _evidence(f"late-proof-{decision.value}")
            await store.append_result(proof)
            await store.reconcile_external_effect(
                ReconciliationRequest(
                    ReconciliationIdentity(f"late-resolution-{decision.value}"),
                    token,
                    decision,
                    (_ref(proof),),
                )
            )

            late_result = StageResult(
                result_id=f"late-result-{decision.value}",
                kind="reconcile_evidence",
                schema_version="1",
                execution=token.execution,
                attempt=token.attempt,
                input_refs=(),
                source_versions=(VersionRef("source", "synthetic", "v1"),),
                prepared_versions=(),
                topic_versions=(),
                configuration_version="config-v1",
                code_version="build-v1",
                status=TerminalStatus.COMPLETE,
                acceptable=True,
            )
            with pytest.raises(StaleClaimError):
                await store.append_result(late_result, claim=token)
            with pytest.raises(StaleClaimError, match="resolved by reconciliation"):
                await store.mark_external_effect(token, ExternalEffectState.UNKNOWN)
            with pytest.raises(StaleClaimError, match="resolved by reconciliation"):
                await store.finish_claim(
                    token, TerminalStatus.FAILED, ExternalEffectState.REJECTED
                )

            snapshot = await store.inspect_claim(token.claim_key)
            if snapshot.current_effect is not decision:
                pytest.fail("Late old-owner call overwrote the reconciled retry gate")
            if len(snapshot.reconciliations) != 1:
                pytest.fail("Late old-owner call changed reconciliation history")
            if snapshot.attempts[0].finished_at is not None:
                pytest.fail("Reconciliation rewrote the unfinished original attempt")
            with pytest.raises(ExternalEffectReconciliationRequired):
                await store.acquire_claim(
                    token.claim_key,
                    ClaimKind.REPORT_SUBMIT,
                    ExecutionIdentity("unsafe-retry"),
                    AttemptIdentity("unsafe-retry"),
                )
        finally:
            await store.close()

    asyncio.run(exercise())


def test_expired_unfinished_rejected_resolution_releases_atomically(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        path = tmp_path / "rejected-release.sqlite3"
        store = await _open(path)
        try:
            token = await store.acquire_claim(
                "submit:rejected-release",
                ClaimKind.REPORT_SUBMIT,
                ExecutionIdentity("rejected-release"),
                AttemptIdentity("rejected-release"),
                lease_seconds=60,
            )
            await store.mark_external_effect(token, ExternalEffectState.PENDING)
            _set_expiry(path, token.token, "2000-01-01T00:00:00+00:00")
            proof = _evidence("rejected-release-proof")
            await store.append_result(proof)
            await store.reconcile_external_effect(
                ReconciliationRequest(
                    ReconciliationIdentity("rejected-release"),
                    token,
                    ExternalEffectState.REJECTED,
                    (_ref(proof),),
                )
            )
            snapshot = await store.inspect_claim(token.claim_key)
            if snapshot.current_token is not None or len(snapshot.reconciliations) != 1:
                pytest.fail("Rejected proof and retry release were not atomic")
            replacement = await store.acquire_claim(
                token.claim_key,
                ClaimKind.REPORT_SUBMIT,
                ExecutionIdentity("replacement-after-proof"),
                AttemptIdentity("replacement-after-proof"),
            )
            if replacement.token == token.token:
                pytest.fail("Released scope reused old ownership")
            with pytest.raises(StaleClaimError):
                await store.finish_claim(
                    token, TerminalStatus.FAILED, ExternalEffectState.REJECTED
                )
        finally:
            await store.close()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "proven", [ExternalEffectState.ACCEPTED, ExternalEffectState.CONFIRMED]
)
def test_proven_effect_cannot_be_downgraded_by_ordinary_late_owner(
    tmp_path: Path, proven: ExternalEffectState
) -> None:
    async def exercise() -> None:
        path = tmp_path / f"proven-{proven.value}.sqlite3"
        store = await _open(path)
        try:
            token = await store.acquire_claim(
                f"submit:proven-{proven.value}",
                ClaimKind.REPORT_SUBMIT,
                ExecutionIdentity(f"proven-{proven.value}"),
                AttemptIdentity(f"proven-{proven.value}"),
                lease_seconds=60,
            )
            await store.mark_external_effect(token, ExternalEffectState.PENDING)
            await store.mark_external_effect(token, proven)
            _set_expiry(path, token.token, "2000-01-01T00:00:00+00:00")
            with pytest.raises(StaleClaimError, match="cannot be downgraded"):
                await store.mark_external_effect(token, ExternalEffectState.REJECTED)
            with pytest.raises(StaleClaimError, match="cannot be downgraded"):
                await store.finish_claim(
                    token, TerminalStatus.FAILED, ExternalEffectState.NOT_STARTED
                )
            snapshot = await store.inspect_claim(token.claim_key)
            if snapshot.current_effect is not proven:
                pytest.fail("Ordinary late owner downgraded proven acceptance")
            with pytest.raises(ExternalEffectReconciliationRequired):
                await store.acquire_claim(
                    token.claim_key,
                    ClaimKind.REPORT_SUBMIT,
                    ExecutionIdentity("blocked-after-proof"),
                    AttemptIdentity("blocked-after-proof"),
                )
        finally:
            await store.close()

    asyncio.run(exercise())


def test_finish_and_reconcile_race_never_resolves_a_live_sender(tmp_path: Path) -> None:
    async def exercise() -> None:
        path = tmp_path / "finish-reconcile-race.sqlite3"
        first = await _open(path)
        second = await _open(path)
        try:
            token = await first.acquire_claim(
                "submit:finish-race",
                ClaimKind.REPORT_SUBMIT,
                ExecutionIdentity("finish-race"),
                AttemptIdentity("finish-race"),
                lease_seconds=60,
            )
            await first.mark_external_effect(token, ExternalEffectState.PENDING)
            proof = _evidence("finish-race-proof")
            await first.append_result(proof)
            request = ReconciliationRequest(
                ReconciliationIdentity("finish-race"),
                token,
                ExternalEffectState.ACCEPTED,
                (_ref(proof),),
            )
            reconciled, finished = await asyncio.gather(
                second.reconcile_external_effect(request),
                first.finish_claim(
                    token, TerminalStatus.FAILED, ExternalEffectState.UNKNOWN
                ),
                return_exceptions=True,
            )
            if isinstance(finished, BaseException):
                pytest.fail(
                    f"Terminal owner publication lost the race: {type(finished)}"
                )
            if isinstance(reconciled, BaseException):
                if not isinstance(reconciled, StaleClaimError):
                    pytest.fail("Race loser was not fenced as an active owner")
                reconciled = await second.reconcile_external_effect(request)
            if reconciled.decision is not ExternalEffectState.ACCEPTED:
                pytest.fail("Post-terminal reconciliation did not retain proof")
            snapshot = await first.inspect_claim(token.claim_key)
            if snapshot.current_effect is not ExternalEffectState.ACCEPTED:
                pytest.fail("Race reopened retry after accepted proof")
        finally:
            await first.close()
            await second.close()

    asyncio.run(exercise())


def test_nested_reconciliation_fields_are_revalidated_privately(tmp_path: Path) -> None:
    async def exercise() -> None:
        store = await _open(tmp_path / "nested-validation.sqlite3")
        try:
            token = await _unknown(store)
            proof = _evidence("nested-validation-proof")
            await store.append_result(proof)

            bad_execution = ExecutionIdentity("temporary-valid")
            object.__setattr__(bad_execution, "value", "")
            bad_token = ClaimToken(
                token.claim_key,
                token.token,
                token.kind,
                bad_execution,
                token.attempt,
            )
            bad_request = ReconciliationRequest(
                ReconciliationIdentity("bad-token"),
                bad_token,
                ExternalEffectState.ACCEPTED,
                (_ref(proof),),
            )
            with pytest.raises(ValueError, match="^reconciliation request is invalid$"):
                await store.reconcile_external_effect(bad_request)

            bad_ref = _ref(proof)
            object.__setattr__(bad_ref, "result_id", "")
            ref_request = ReconciliationRequest(
                ReconciliationIdentity("bad-ref"),
                token,
                ExternalEffectState.ACCEPTED,
                (bad_ref,),
            )
            with pytest.raises(ValueError, match="^reconciliation request is invalid$"):
                await store.reconcile_external_effect(ref_request)

            bad_identity = ReconciliationIdentity("bad-identity")
            object.__setattr__(bad_identity, "value", "")
            identity_request = ReconciliationRequest(
                bad_identity,
                token,
                ExternalEffectState.ACCEPTED,
                (_ref(proof),),
            )
            with pytest.raises(ValueError, match="^reconciliation request is invalid$"):
                await store.reconcile_external_effect(identity_request)

            snapshot = await store.inspect_claim(token.claim_key)
            if snapshot.reconciliations:
                pytest.fail(
                    "Invalid nested request changed durable reconciliation state"
                )
        finally:
            await store.close()

    asyncio.run(exercise())


def test_inspection_is_one_snapshot_while_another_facade_commits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def exercise() -> None:
        path = tmp_path / "inspection-snapshot.sqlite3"
        reader = await _open(path)
        writer = await _open(path)
        entered = threading.Event()
        release = threading.Event()
        original = persistence_store.inspect_claim
        try:
            token = await _unknown(
                reader, claim_key="submit:snapshot", suffix="snapshot"
            )
            proof = _evidence("snapshot-proof")
            await reader.append_result(proof)
            request = ReconciliationRequest(
                ReconciliationIdentity("snapshot-resolution"),
                token,
                ExternalEffectState.ACCEPTED,
                (_ref(proof),),
            )

            def paused_inspection(connection, claim_key, history_limit):
                connection.exec_driver_sql(
                    "SELECT claim_token FROM phase1_work_claims WHERE claim_key = ?",
                    (claim_key,),
                ).first()
                entered.set()
                if not release.wait(timeout=2):
                    raise RuntimeError("synthetic inspection barrier timed out")
                return original(connection, claim_key, history_limit)

            monkeypatch.setattr(persistence_store, "inspect_claim", paused_inspection)
            inspection = asyncio.create_task(reader.inspect_claim(token.claim_key))
            if not await asyncio.to_thread(entered.wait, 2):
                pytest.fail("Inspection did not reach the synthetic snapshot barrier")
            reconciliation = asyncio.create_task(
                writer.reconcile_external_effect(request)
            )
            await asyncio.sleep(0.05)
            if reconciliation.done():
                pytest.fail("Writer committed through an active inspection snapshot")
            release.set()
            before = await inspection
            resolved = await reconciliation
            if before.current_effect is not ExternalEffectState.UNKNOWN:
                pytest.fail(
                    "Inspection mixed post-commit claim state into old snapshot"
                )
            if before.reconciliations:
                pytest.fail(
                    "Inspection mixed post-commit reconciliation into old snapshot"
                )
            if resolved.decision is not ExternalEffectState.ACCEPTED:
                pytest.fail("Blocked writer did not commit after inspection completed")
            after = await reader.inspect_claim(token.claim_key)
            if (
                after.current_effect is not ExternalEffectState.ACCEPTED
                or len(after.reconciliations) != 1
            ):
                pytest.fail(
                    "Post-commit inspection did not observe one coherent new state"
                )
        finally:
            release.set()
            await reader.close()
            await writer.close()

    asyncio.run(exercise())
