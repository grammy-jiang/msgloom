"""SQLite reconciliation regressions for uncertain external effects."""

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
    ImmutableRecordError,
    Phase1Persistence,
    ReconciliationIdentity,
    ReconciliationRequest,
    StaleClaimError,
    reconciliation_store,
)


def _url(path: Path) -> str:
    return f"sqlite:///{path}"


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
    return await Phase1Persistence.open(_url(path), registry=_registry())


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


def test_unknown_reopens_with_history_and_preserves_attempt(tmp_path: Path) -> None:
    async def exercise() -> None:
        path = tmp_path / "phase1.sqlite3"
        first = await _open(path)
        token = await _unknown(first)
        await first.close()
        second = await _open(path)
        try:
            snapshot = await second.inspect_claim(token.claim_key)
            if snapshot.current_token != token:
                pytest.fail("Restart inspection lost exact current ownership")
            if snapshot.current_effect is not ExternalEffectState.UNKNOWN:
                pytest.fail("Restart inspection did not retain unknown effect")
            if len(snapshot.attempts) != 1:
                pytest.fail("Restart inspection lost claim attempt history")
            attempt = snapshot.attempts[0]
            if attempt.external_effect is not ExternalEffectState.UNKNOWN:
                pytest.fail("Original unknown attempt was not retained")
            if attempt.terminal_status is not TerminalStatus.FAILED:
                pytest.fail("Original terminal status was not retained")
        finally:
            await second.close()

    asyncio.run(exercise())


def test_inconclusive_stays_unknown_and_definite_requires_evidence(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        store = await _open(tmp_path / "phase1.sqlite3")
        try:
            token = await _unknown(store)
            with pytest.raises(ValueError, match="requires durable evidence"):
                ReconciliationRequest(
                    ReconciliationIdentity("definite-without-proof"),
                    token,
                    ExternalEffectState.REJECTED,
                )
            result = await store.reconcile_external_effect(
                ReconciliationRequest(
                    ReconciliationIdentity("still-unknown"),
                    token,
                    ExternalEffectState.UNKNOWN,
                )
            )
            if result.decision is not ExternalEffectState.UNKNOWN:
                pytest.fail("Inconclusive reconciliation changed the decision")
            with pytest.raises(ExternalEffectReconciliationRequired):
                await store.acquire_claim(
                    token.claim_key,
                    ClaimKind.REPORT_SUBMIT,
                    ExecutionIdentity("retry-blocked"),
                    AttemptIdentity("retry-blocked"),
                )
        finally:
            await store.close()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    ("decision", "retry_allowed"),
    [
        (ExternalEffectState.REJECTED, True),
        (ExternalEffectState.ACCEPTED, False),
        (ExternalEffectState.CONFIRMED, False),
    ],
)
def test_definite_resolution_controls_retry_without_rewriting_attempt(
    tmp_path: Path,
    decision: ExternalEffectState,
    retry_allowed: bool,
) -> None:
    async def exercise() -> None:
        store = await _open(tmp_path / f"{decision.value}.sqlite3")
        try:
            token = await _unknown(store)
            evidence = _evidence(f"proof-{decision.value}")
            await store.append_result(evidence)
            result = await store.reconcile_external_effect(
                ReconciliationRequest(
                    ReconciliationIdentity(f"resolution-{decision.value}"),
                    token,
                    decision,
                    (_ref(evidence),),
                )
            )
            if result.decision is not decision:
                pytest.fail("Saved reconciliation decision changed")
            snapshot = await store.inspect_claim(token.claim_key)
            if snapshot.attempts[0].external_effect is not ExternalEffectState.UNKNOWN:
                pytest.fail("Reconciliation rewrote immutable attempt history")
            if retry_allowed:
                replacement = await store.acquire_claim(
                    token.claim_key,
                    ClaimKind.REPORT_SUBMIT,
                    ExecutionIdentity("replacement"),
                    AttemptIdentity("replacement"),
                )
                if replacement.token == token.token:
                    pytest.fail("Released scope reused the old claim token")
            else:
                with pytest.raises(ExternalEffectReconciliationRequired):
                    await store.acquire_claim(
                        token.claim_key,
                        ClaimKind.REPORT_SUBMIT,
                        ExecutionIdentity("blocked"),
                        AttemptIdentity("blocked"),
                    )
        finally:
            await store.close()

    asyncio.run(exercise())


def test_accepted_can_refine_to_confirmed_with_distinct_proof(tmp_path: Path) -> None:
    async def exercise() -> None:
        store = await _open(tmp_path / "phase1.sqlite3")
        try:
            token = await _unknown(store)
            accepted = _evidence("accepted-proof")
            confirmed = _evidence("confirmed-proof")
            await store.append_result(accepted)
            await store.append_result(confirmed)
            await store.reconcile_external_effect(
                ReconciliationRequest(
                    ReconciliationIdentity("accepted"),
                    token,
                    ExternalEffectState.ACCEPTED,
                    (_ref(accepted),),
                )
            )
            await store.reconcile_external_effect(
                ReconciliationRequest(
                    ReconciliationIdentity("confirmed"),
                    token,
                    ExternalEffectState.CONFIRMED,
                    (_ref(confirmed),),
                )
            )
            snapshot = await store.inspect_claim(token.claim_key)
            if snapshot.current_effect is not ExternalEffectState.CONFIRMED:
                pytest.fail("Accepted submission did not refine to confirmed")
            if len(snapshot.reconciliations) != 2:
                pytest.fail("Refinement did not retain both proof records")
        finally:
            await store.close()

    asyncio.run(exercise())


def test_exact_replay_survives_release_and_conflicting_reuse_fails(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        store = await _open(tmp_path / "phase1.sqlite3")
        try:
            token = await _unknown(store)
            proof = _evidence("proof")
            await store.append_result(proof)
            request = ReconciliationRequest(
                ReconciliationIdentity("stable-id"),
                token,
                ExternalEffectState.REJECTED,
                (_ref(proof),),
            )
            first = await store.reconcile_external_effect(request)
            second = await store.reconcile_external_effect(request)
            if first != second:
                pytest.fail("Exact reconciliation replay was not idempotent")
            with pytest.raises(ImmutableRecordError):
                await store.reconcile_external_effect(
                    replace(request, decision=ExternalEffectState.ACCEPTED)
                )
        finally:
            await store.close()

    asyncio.run(exercise())


def test_old_token_cannot_mutate_replacement_owner(tmp_path: Path) -> None:
    async def exercise() -> None:
        store = await _open(tmp_path / "phase1.sqlite3")
        try:
            old = await _unknown(store)
            proof = _evidence("reject-old")
            await store.append_result(proof)
            await store.reconcile_external_effect(
                ReconciliationRequest(
                    ReconciliationIdentity("release-old"),
                    old,
                    ExternalEffectState.REJECTED,
                    (_ref(proof),),
                )
            )
            new = await store.acquire_claim(
                old.claim_key,
                ClaimKind.REPORT_SUBMIT,
                ExecutionIdentity("new-execution"),
                AttemptIdentity("new-attempt"),
            )
            with pytest.raises(StaleClaimError):
                await store.reconcile_external_effect(
                    ReconciliationRequest(
                        ReconciliationIdentity("stale-old"),
                        old,
                        ExternalEffectState.ACCEPTED,
                        (_ref(proof),),
                    )
                )
            snapshot = await store.inspect_claim(old.claim_key)
            if snapshot.current_token != new:
                pytest.fail("Stale reconciliation mutated replacement ownership")
        finally:
            await store.close()

    asyncio.run(exercise())


def test_two_facades_cannot_overwrite_opposed_resolution(tmp_path: Path) -> None:
    async def exercise() -> None:
        path = tmp_path / "phase1.sqlite3"
        first = await _open(path)
        second = await _open(path)
        try:
            token = await _unknown(first)
            accepted = _evidence("accepted-race")
            rejected = _evidence("rejected-race")
            await first.append_result(accepted)
            await first.append_result(rejected)
            requests = (
                ReconciliationRequest(
                    ReconciliationIdentity("race-accepted"),
                    token,
                    ExternalEffectState.ACCEPTED,
                    (_ref(accepted),),
                ),
                ReconciliationRequest(
                    ReconciliationIdentity("race-rejected"),
                    token,
                    ExternalEffectState.REJECTED,
                    (_ref(rejected),),
                ),
            )
            results = await asyncio.gather(
                first.reconcile_external_effect(requests[0]),
                second.reconcile_external_effect(requests[1]),
                return_exceptions=True,
            )
            winners = [item for item in results if not isinstance(item, BaseException)]
            losers = [item for item in results if isinstance(item, BaseException)]
            if len(winners) != 1 or len(losers) != 1:
                pytest.fail("Opposed reconciliation race lacked one winner")
            if not isinstance(losers[0], StaleClaimError):
                pytest.fail("Opposed reconciliation loser was not fenced")
        finally:
            await first.close()
            await second.close()

    asyncio.run(exercise())


def test_transaction_failure_rolls_back_proof_and_claim_update(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def exercise() -> None:
        store = await _open(tmp_path / "phase1.sqlite3")
        original = reconciliation_store.append_reconciliation
        try:
            token = await _unknown(store)
            proof = _evidence("rollback-proof")
            await store.append_result(proof)

            def fail_after_append(connection, request, resolved_at) -> None:
                original(connection, request, resolved_at)
                raise RuntimeError("synthetic transaction failure")

            monkeypatch.setattr(
                reconciliation_store, "append_reconciliation", fail_after_append
            )
            with pytest.raises(RuntimeError, match="synthetic transaction failure"):
                await store.reconcile_external_effect(
                    ReconciliationRequest(
                        ReconciliationIdentity("rolled-back"),
                        token,
                        ExternalEffectState.REJECTED,
                        (_ref(proof),),
                    )
                )
            snapshot = await store.inspect_claim(token.claim_key)
            if snapshot.current_effect is not ExternalEffectState.UNKNOWN:
                pytest.fail("Failed transaction changed retry gating")
            if snapshot.reconciliations:
                pytest.fail("Failed transaction retained reconciliation proof")
        finally:
            await store.close()

    asyncio.run(exercise())


def test_active_expired_and_terminal_pending_ownership_is_exact(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        path = tmp_path / "phase1.sqlite3"
        store = await _open(path)
        try:
            active = await store.acquire_claim(
                "submit:active",
                ClaimKind.REPORT_SUBMIT,
                ExecutionIdentity("active-execution"),
                AttemptIdentity("active-attempt"),
                lease_seconds=60,
            )
            await store.mark_external_effect(active, ExternalEffectState.PENDING)
            proof = _evidence("ownership-proof")
            await store.append_result(proof)
            forged = replace(active, token="competing-token")
            with pytest.raises(StaleClaimError):
                await store.reconcile_external_effect(
                    ReconciliationRequest(
                        ReconciliationIdentity("competing"),
                        forged,
                        ExternalEffectState.ACCEPTED,
                        (_ref(proof),),
                    )
                )
            _set_expiry(path, active.token, "2000-01-01T00:00:00+00:00")
            await store.reconcile_external_effect(
                ReconciliationRequest(
                    ReconciliationIdentity("expired-owner"),
                    active,
                    ExternalEffectState.ACCEPTED,
                    (_ref(proof),),
                )
            )

            terminal = await _unknown(
                store, claim_key="submit:terminal", suffix="terminal"
            )
            _set_expiry(path, terminal.token, "2999-01-01T00:00:00+00:00")
            await store.reconcile_external_effect(
                ReconciliationRequest(
                    ReconciliationIdentity("terminal-owner"),
                    terminal,
                    ExternalEffectState.UNKNOWN,
                )
            )
        finally:
            await store.close()

    asyncio.run(exercise())


def test_repeated_cancellation_drains_reconciliation_before_return(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        store = await _open(tmp_path / "phase1.sqlite3")
        started = threading.Event()
        release = threading.Event()
        original = store._store.reconcile_external_effect
        try:
            token = await _unknown(store)
            proof = _evidence("cancel-proof")
            await store.append_result(proof)
            request = ReconciliationRequest(
                ReconciliationIdentity("cancelled-resolution"),
                token,
                ExternalEffectState.REJECTED,
                (_ref(proof),),
            )

            def slow_reconcile(value):
                started.set()
                release.wait(timeout=2)
                return original(value)

            store._store.reconcile_external_effect = slow_reconcile  # type: ignore[method-assign]
            task = asyncio.create_task(store.reconcile_external_effect(request))
            await asyncio.to_thread(started.wait, 2)
            task.cancel()
            task.cancel()
            await asyncio.sleep(0)
            if task.done():
                pytest.fail("Cancellation returned before accepted write drained")
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            snapshot = await store.inspect_claim(token.claim_key)
            if snapshot.current_token is not None:
                pytest.fail("Drained rejected reconciliation did not release scope")
            if len(snapshot.reconciliations) != 1:
                pytest.fail("Drained reconciliation proof was not committed")
        finally:
            release.set()
            await store.close()

    asyncio.run(exercise())
