"""Frozen selections and real replay outcomes for terminal-proof tests."""

import asyncio
from dataclasses import replace
from typing import cast

from msgloom.contracts import (
    AttemptIdentity,
    OperationRequest,
    PhaseCapability,
    ResultRef,
    VersionRef,
)
from msgloom.persistence import Phase1Persistence
from msgloom.preparation_pipeline import (
    PreparationHandler,
    PreparationMode,
    PreparationPlan,
    SelectionPlan,
)
from msgloom.preparation_pipeline.intake_models import (
    HeldIntakeEntry,
    IntakeAnchor,
    IntakeSelection,
    IntakeTransition,
    PreparationIntakeWorkset,
)
from msgloom.sources import CollectedSourceReader
from tests.phase1_foundation import intake_helpers as h
from tests.preparation_pipeline.helpers import filter_config


def ref(result):
    """Return the exact saved result identity."""
    return ResultRef(result.result_id, result.kind, result.schema_version)


def admit(store, *, count=1, transition=False, held=False, same_source=False):
    """Admit real immutable selections and optional mixed dispositions."""
    token = h.claim(store, identity="same-execution")
    selections = tuple(
        h.selection(
            store,
            token,
            result_id=f"selection-{index}",
            source=VersionRef(
                "outlook_email",
                f"mail-{0 if same_source else index}",
                "observation-one",
            ),
        )
        for index in range(count)
    )
    entries = tuple(h.entry(index + 1) for index in range(count + transition + held))
    transitions = ()
    if transition:
        transitions = (
            IntakeTransition(
                entry=entries[count],
                fact_id="a" * 64,
                transition_kind="membership_removal",
                resource_kind="message",
                resource_identity="mail-transition",
                scope_kind="folder",
                scope_identity="inbox",
            ),
        )
    value = PreparationIntakeWorkset(
        scope=h.scope(),
        previous=IntakeAnchor(),
        cutoff=IntakeAnchor(
            last_release_entry_seq=entries[-1].release_entry_seq,
            last_release_entry_digest=entries[-1].entry_digest,
        ),
        entries=entries,
        selections=tuple(
            IntakeSelection(entry=entries[index], result=ref(saved))
            for index, saved in enumerate(selections)
        ),
        transitions=transitions,
        held=(HeldIntakeEntry(entry=entries[-1], reason="missing_evidence"),)
        if held
        else (),
        configuration_version="config-1",
        code_version="code-1",
    )
    saved = h.result(store, value, token)
    store.finalize_preparation_intake(saved, value, claim=token)
    owner = h.processing_claim(store, saved, identity=token.execution.value)
    return value, saved, owner, selections


class NoLiveReader:
    """Fail any attempt to consult mutable A1 or external evidence."""

    def __getattr__(self, name):
        raise RuntimeError(f"Unexpected source read: {name}")


def replay(store, owner, selections, *, parser_profiles=(), attempt="plan-attempt"):
    """Run the existing handler under its separate exact plan claim."""

    async def run():
        plans = []
        for selected in selections:
            payload = store.load_semantic_data(selected.semantic_data_ref)
            plans.append(
                SelectionPlan(
                    source=payload.source,
                    replay_result=ref(selected),
                    replay_selection=payload.selection,
                )
            )
        plan = PreparationPlan(
            mode=PreparationMode.REPLAY,
            attempt=AttemptIdentity(attempt),
            selections=tuple(plans),
            filter_config=filter_config(),
            parser_profiles=parser_profiles,
            configuration_version="replay-config",
            code_version="replay-code",
        )
        handler = PreparationHandler(
            Phase1Persistence(store),
            cast(CollectedSourceReader, NoLiveReader()),
            plan,
        )
        outcome = await handler.run(
            OperationRequest(
                execution=owner.execution,
                caller="test",
                capability=PhaseCapability.PREPARE,
                target_inputs=tuple(item.source for item in plans),
                authority_ref="test",
            )
        )
        return outcome

    return asyncio.run(run())


def clone(store, original, **changes):
    """Save a distinct immutable metadata variant for rejection probes."""
    saved = replace(original, result_id="forged-output", **changes)
    store.append_result_with_data(
        saved,
        store.load_semantic_data(saved.semantic_data_ref),
    )
    return ref(saved)
