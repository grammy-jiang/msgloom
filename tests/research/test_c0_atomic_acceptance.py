"""
C0: experimental acceptance table with real Phase1 claim and SQLite writes.

Never touches production schema. The new table exists only under pytest
``tmp_path``.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from msgloom.contracts import ExternalEffectState, TerminalStatus
from msgloom.persistence.errors import StaleClaimError
from scripts.research.c0_atomic_acceptance_prototype import (
    ExperimentalA2AcceptanceStore,
)
from scripts.research.c0_contract_prototype import (
    C0ContractError,
    FrozenRoot,
    StageIdentity,
)
from tests.research.test_c0_contract_prototype import (
    digest,
    fixture_workset,
)
from tests.research.test_c0_phase1_storage_integration import (
    C0TestPayload,
    create_claim,
    make_stage,
    open_store,
    required_semantic_ref,
)


def input_identity() -> StageIdentity:
    workset, workset_ref = fixture_workset()
    selected = workset.selections[0]
    root = FrozenRoot(
        entry=selected.entry,
        selected=selected.result,
        role="primary",
        occurrence=0,
        selection_sha256=digest("exact-selected-content"),
        a1_ordinal_proof=digest("verified-ordinal-proof"),
    )
    return StageIdentity(
        scope_key=digest(workset.scope.claim_key()),
        workset=workset_ref,
        partition_ordinal=0,
        selected=(root,),
        stage_kind="prepared",
        schema_version="2",
        configuration_version="c0-config-v1",
        code_version="c0-code-v1",
        parser_version="c0-parser-v1",
        rule_version="c0-rule-v1",
        partition_policy_version="c0-partition-v1",
    )


def test_atomic_acceptance_replays_same_key_across_attempts(tmp_path: Path) -> None:
    """Legacy StageResult metadata stays; the index returns the old ref."""

    async def scenario() -> None:
        db = tmp_path / "a2-acceptance.sqlite3"
        identity = input_identity()
        accepted_key = identity.logical_acceptance_key()
        value = C0TestPayload("original bytes accepted")
        store = await open_store(db, prepared_v2=True)
        try:
            prototype = ExperimentalA2AcceptanceStore(store._store)
            first = make_stage(
                store,
                result_id=accepted_key,
                execution="first-exec",
                attempt="first-attempt",
                kind="prepared",
                schema="2",
                value=value,
            )
            c1 = await create_claim(
                store, "c0-a2:partition", "first-exec", "first-attempt"
            )
            ref = await asyncio.to_thread(
                prototype.publish, identity, first, value, claim=c1
            )
            if prototype.count() != 1 or ref.result_id != accepted_key:
                pytest.fail("C0 transaction did not persist one accepted logical key")
            await store.finish_claim(
                c1, TerminalStatus.COMPLETE, ExternalEffectState.NONE
            )
        finally:
            await store.close()
        reopened = await open_store(db, prepared_v2=True)
        try:
            prototype = ExperimentalA2AcceptanceStore(reopened._store)
            c2 = await create_claim(
                reopened, "c0-a2:partition", "second-exec", "second-attempt"
            )
            replay = make_stage(
                reopened,
                result_id=accepted_key,
                execution="second-exec",
                attempt="second-attempt",
                kind="prepared",
                schema="2",
                value=value,
            )
            recovered_ref = await asyncio.to_thread(
                prototype.publish, identity, replay, value, claim=c2
            )
            if recovered_ref != ref or prototype.count() != 1:
                pytest.fail("C0 replay duplicated the same semantic acceptance")
            saved = await reopened.get_result(accepted_key)
            if saved != first:
                pytest.fail("C0 replay rewrote first accepted StageResult metadata")
            if await reopened.load_semantic_data(required_semantic_ref(first)) != value:
                pytest.fail("C0 replay lost original canonical semantic bytes")

            changed = C0TestPayload("CONFLICTING nondeterministic parser bytes")
            conflicting = make_stage(
                reopened,
                result_id=accepted_key,
                execution="second-exec",
                attempt="second-attempt",
                kind="prepared",
                schema="2",
                value=changed,
            )
            with pytest.raises(C0ContractError, match="integrity-conflict"):
                await asyncio.to_thread(
                    prototype.publish, identity, conflicting, changed, claim=c2
                )
            if prototype.count() != 1:
                pytest.fail("C0 conflict created a second durable accepted record")
            if await reopened.get_result(accepted_key) != first:
                pytest.fail("C0 conflict changed original immutable StageResult")
            await reopened.finish_claim(
                c2, TerminalStatus.INCOMPLETE, ExternalEffectState.NONE
            )
        finally:
            await reopened.close()

    asyncio.run(scenario())


def test_atomic_acceptance_checks_real_expired_claim_before_lookup(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        store = await open_store(tmp_path / "a2-stale.sqlite3", prepared_v2=True)
        value = C0TestPayload("no late publish")
        identity = input_identity()
        try:
            prototype = ExperimentalA2AcceptanceStore(store._store)
            claim = await create_claim(
                store, "c0-a2:stale", "stale-exec", "stale-attempt", lease=0
            )
            stage = make_stage(
                store,
                result_id=identity.logical_acceptance_key(),
                execution="stale-exec",
                attempt="stale-attempt",
                kind="prepared",
                schema="2",
                value=value,
            )
            with pytest.raises(StaleClaimError):
                await asyncio.to_thread(
                    prototype.publish, identity, stage, value, claim=claim
                )
            if prototype.count() != 0:
                pytest.fail("C0 expired claim performed a late write")
        finally:
            await store.close()

    asyncio.run(scenario())


def test_concurrent_claims_publish_single_logical_key(tmp_path: Path) -> None:
    """
    BEGIN IMMEDIATE serializes two owners of one accepted input key.

    The owners hold two different claim keys. That is a research shortcut.
    A production deterministic partition claim key would make the second
    owner fail with ``ClaimUnavailableError`` before it could publish. The
    test starts both threads without a barrier, so it shows SQLite
    serialization of the compare-and-insert, not proven overlap.
    """

    async def scenario() -> None:
        db = tmp_path / "a2-race.sqlite3"
        left = await open_store(db, prepared_v2=True)
        right = await open_store(db, prepared_v2=True)
        identity = input_identity()
        value = C0TestPayload("same canonical output")
        try:
            l = ExperimentalA2AcceptanceStore(left._store)
            r = ExperimentalA2AcceptanceStore(right._store)
            c1 = await create_claim(left, "c0-a2:left", "exec-left", "try-left")
            c2 = await create_claim(right, "c0-a2:right", "exec-right", "try-right")
            stage1 = make_stage(
                left,
                result_id=identity.logical_acceptance_key(),
                execution="exec-left",
                attempt="try-left",
                kind="prepared",
                schema="2",
                value=value,
            )
            stage2 = make_stage(
                right,
                result_id=identity.logical_acceptance_key(),
                execution="exec-right",
                attempt="try-right",
                kind="prepared",
                schema="2",
                value=value,
            )
            outputs = await asyncio.gather(
                asyncio.to_thread(l.publish, identity, stage1, value, claim=c1),
                asyncio.to_thread(r.publish, identity, stage2, value, claim=c2),
            )
            if outputs[0] != outputs[1] or l.count() != 1 or r.count() != 1:
                pytest.fail("concurrent partitions duplicated logical acceptance")
            stored = await left.get_result(identity.logical_acceptance_key())
            if stored not in (stage1, stage2):
                pytest.fail("concurrent accepted metadata changed original owner")
            await left.finish_claim(
                c1, TerminalStatus.COMPLETE, ExternalEffectState.NONE
            )
            await right.finish_claim(
                c2, TerminalStatus.COMPLETE, ExternalEffectState.NONE
            )
        finally:
            await left.close()
            await right.close()

    asyncio.run(scenario())


def test_concurrent_conflicting_output_has_one_winner_and_no_second_commit(
    tmp_path: Path,
) -> None:
    """
    Racing owners cannot insert two digests for one input key.

    The owners hold two different claim keys, so the claim fence cannot
    separate them. Only the acceptance table decides the winner. A
    production partition claim key would normally stop the second owner
    earlier. There is no start barrier, so overlap is not proven.
    """

    async def scenario() -> None:
        db = tmp_path / "a2-race-conflict.sqlite3"
        left = await open_store(db, prepared_v2=True)
        right = await open_store(db, prepared_v2=True)
        identity = input_identity()
        before = C0TestPayload("winning payload A")
        after = C0TestPayload("competing payload B")
        try:
            l = ExperimentalA2AcceptanceStore(left._store)
            r = ExperimentalA2AcceptanceStore(right._store)
            c1 = await create_claim(left, "c0-a2:left-conflict", "exec-a", "try-a")
            c2 = await create_claim(right, "c0-a2:right-conflict", "exec-b", "try-b")
            stage1 = make_stage(
                left,
                result_id=identity.logical_acceptance_key(),
                execution="exec-a",
                attempt="try-a",
                kind="prepared",
                schema="2",
                value=before,
            )
            stage2 = make_stage(
                right,
                result_id=identity.logical_acceptance_key(),
                execution="exec-b",
                attempt="try-b",
                kind="prepared",
                schema="2",
                value=after,
            )
            outputs = await asyncio.gather(
                asyncio.to_thread(l.publish, identity, stage1, before, claim=c1),
                asyncio.to_thread(r.publish, identity, stage2, after, claim=c2),
                return_exceptions=True,
            )
            success = [item for item in outputs if not isinstance(item, Exception)]
            failures = [item for item in outputs if isinstance(item, Exception)]
            if len(success) != 1 or len(failures) != 1:
                pytest.fail("conflicting writers did not produce one winner")
            if not isinstance(failures[0], C0ContractError):
                pytest.fail("concurrent conflicting writer did not fail closed")
            if l.count() != 1 or r.count() != 1:
                pytest.fail("two simultaneous accepted digests for one key")
            saved = await left.get_result(identity.logical_acceptance_key())
            if saved not in (stage1, stage2):
                pytest.fail("winning StageResult metadata is not the immutable owner")
            await left.finish_claim(
                c1, TerminalStatus.INCOMPLETE, ExternalEffectState.NONE
            )
            await right.finish_claim(
                c2, TerminalStatus.INCOMPLETE, ExternalEffectState.NONE
            )
        finally:
            await left.close()
            await right.close()

    asyncio.run(scenario())
