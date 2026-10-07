"""Require exact scoped facts and normally accepted transition publications."""

import asyncio
from dataclasses import replace

import pytest
from pydantic import ValidationError

from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ExternalEffectState,
    OperationRequest,
    PhaseCapability,
    TerminalStatus,
)
from msgloom.persistence import DependencyNotReadyError, Phase1Persistence
from msgloom.preparation_pipeline.transitions import (
    PreparedTransitions,
    PreparedTransitionsCodec,
    prepare_transitions,
)
from tests.phase1_foundation import intake_completion_helpers as c
from tests.phase1_foundation import intake_helpers as h


def publish(store, saved, owner, *, attempt="transition-plan", persistence=None):
    """Run the real finite producer independently of selection replay."""
    return asyncio.run(
        prepare_transitions(
            persistence or Phase1Persistence(store),
            c.ref(saved),
            OperationRequest(owner.execution, "test", PhaseCapability.PREPARE),
            AttemptIdentity(attempt),
            configuration_version="transition-config",
            code_version="transition-code",
            lease_seconds=60,
        )
    )


@pytest.mark.parametrize(
    "damage", ["scope", "fact", "kind", "extra", "foreign_root", "unbound"]
)
def test_accepted_transition_output_cannot_substitute_frozen_facts(tmp_path, damage):
    """Even genuinely accepted publications need exact semantic workset proof."""
    store = h.store(tmp_path / "neutral.db")
    value, saved, owner, _ = c.admit(store, count=0, transition=True)
    try:
        refs = publish(store, saved, owner)
        original = store.get_result(refs[0].result_id)
        if original is None:
            pytest.fail("Real producer did not publish its result")
        transition = value.transitions[0]
        facts = value.transitions
        if damage in {"scope", "fact", "kind"}:
            change = {
                "scope": {"scope_identity": "different-folder"},
                "fact": {"fact_id": "b" * 64},
                "kind": {"transition_kind": "deletion"},
            }[damage]
            facts = (transition.model_copy(update=change),)
        if damage == "extra":
            facts += (transition.model_copy(update={"fact_id": "b" * 64}),)
        root = c.ref(saved)
        if damage == "foreign_root":
            alias = replace(saved, result_id="foreign-workset")
            store.append_result_with_data(alias, value)
            root = c.ref(alias)
        payload = PreparedTransitions(transitions=facts)
        token = store.acquire_claim(
            "prepare:probe:" + damage,
            ClaimKind.PREPARE,
            owner.execution,
            AttemptIdentity("probe"),
            required_inputs=(root,),
            lease_seconds=60,
        )
        result = replace(
            original,
            result_id="probe-result",
            attempt=token.attempt,
            input_refs=(root,),
            semantic_data_ref=store.semantic_reference(
                "probe-data",
                "prepared_transitions",
                "1",
                payload,
            ),
        )
        store.append_result_with_data(
            result, payload, claim=None if damage == "unbound" else token
        )
        refs = (c.ref(result),)
        if damage != "unbound":
            store.finish_claim(
                token,
                TerminalStatus.COMPLETE,
                ExternalEffectState.NONE,
                accepted_preparation_results=refs,
            )
        with pytest.raises(DependencyNotReadyError):
            store.finalize_preparation_intake_workset(
                saved.result_id,
                TerminalStatus.COMPLETE,
                refs,
                claim=owner,
            )
        if not store.list_preparation_intake_worksets(value.scope):
            pytest.fail("Invalid transition proof consumed pending work")
    finally:
        store.close()


@pytest.mark.parametrize("failure", [RuntimeError, asyncio.CancelledError])
def test_cancelled_publication_stays_pending_and_retry_uses_saved_workset(
    tmp_path, monkeypatch, failure
):
    """Published facts without normal acceptance cannot discharge the workset."""
    store = h.store(tmp_path / "neutral.db")
    value, saved, owner, _ = c.admit(store, count=0, transition=True)
    persistence = Phase1Persistence(store)
    finish = persistence.finish_claim
    append = persistence.append_result_with_data
    published = []

    async def observed(result, payload, **kwargs):
        await append(result, payload, **kwargs)
        published.append(c.ref(result))

    async def cancel_before_acceptance(*args, **kwargs):
        if kwargs.get("accepted_preparation_results") is not None:
            raise failure
        return await finish(*args, **kwargs)

    monkeypatch.setattr(persistence, "append_result_with_data", observed)
    monkeypatch.setattr(persistence, "finish_claim", cancel_before_acceptance)
    try:
        with pytest.raises(failure):
            publish(store, saved, owner, persistence=persistence)
        if len(published) != 1:
            pytest.fail("Cancellation fixture did not publish its real result")
        with pytest.raises(DependencyNotReadyError):
            store.finalize_preparation_intake_workset(
                saved.result_id,
                TerminalStatus.COMPLETE,
                tuple(published),
                claim=owner,
            )
        if not store.list_preparation_intake_worksets(value.scope):
            pytest.fail("Cancelled producer consumed pending work")
        refs = publish(store, saved, owner, attempt="retry")
        store.finalize_preparation_intake_workset(
            saved.result_id,
            TerminalStatus.COMPLETE,
            refs,
            claim=owner,
        )
        if store.list_preparation_intake_worksets(value.scope):
            pytest.fail("Real accepted retry did not discharge saved work")
    finally:
        store.close()


def test_transition_tuple_codec_retains_supported_bound(tmp_path):
    """One output supports 1024 exact facts and rejects empty or larger tuples."""
    store = h.store(tmp_path / "neutral.db")
    try:
        value, _, _, _ = c.admit(store, count=0, transition=True)
        facts = tuple(
            value.transitions[0].model_copy(update={"fact_id": f"{i:064x}"})
            for i in range(1024)
        )
        payload = PreparedTransitions(transitions=facts)
        codec = PreparedTransitionsCodec()
        if codec.decode(codec.encode(payload)) != payload:
            pytest.fail("Canonical codec lost a transition at the supported bound")
        for invalid in ((), facts + (facts[0],)):
            with pytest.raises(ValidationError):
                codec.encode(PreparedTransitions.model_construct(transitions=invalid))
    finally:
        store.close()
