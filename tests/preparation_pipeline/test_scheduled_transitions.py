"""Schedule exact frozen transitions without consulting mutable source state."""

import asyncio
from dataclasses import replace
from typing import cast

import pytest

from msgloom.configuration import PreparationOperationData
from msgloom.contracts import (
    AttemptIdentity,
    ExternalEffectState,
    OperationRequest,
    PhaseCapability,
    TerminalStatus,
)
from msgloom.persistence import Phase1Persistence
from msgloom.preparation_pipeline.scheduled import ScheduledPreparationHandler
from msgloom.preparation_pipeline.transitions import PreparedTransitions
from tests.application_cli.test_scheduled_prepare import configuration
from tests.phase1_foundation import intake_completion_helpers as c
from tests.phase1_foundation import intake_helpers as h


@pytest.mark.parametrize("selected", [False, True])
@pytest.mark.parametrize("scope_kind", ["folder", "calendar_window"])
def test_scheduled_exact_scoped_transitions_finish(
    saved_catalog, tmp_path, monkeypatch, selected, scope_kind
):
    """Real accepted output preserves every fact and the removal's scope."""
    original = c.IntakeTransition

    def transition(**values):
        values.update(scope_kind=scope_kind, scope_identity="exact-scope")
        if scope_kind == "calendar_window":
            values.update(resource_kind="event", resource_identity="event-one")
        return original(**values)

    monkeypatch.setattr(c, "IntakeTransition", transition)
    store = h.store(tmp_path / "neutral.db")
    value, saved, owner, _ = c.admit(store, count=int(selected), transition=True)
    store.finish_claim(owner, TerminalStatus.CANCELLED, ExternalEffectState.NONE)
    config = configuration(saved_catalog, tmp_path)
    operation = cast(
        PreparationOperationData, config.operation(PhaseCapability.PREPARE)
    )

    async def check():
        handler = ScheduledPreparationHandler(
            Phase1Persistence(store),
            config.source_reader_config(),
            operation,
            AttemptIdentity("scheduled-transition"),
        )
        outputs, accepted, status = await handler._process(
            c.ref(saved),
            c.NoLiveReader(),
            OperationRequest(owner.execution, "test", PhaseCapability.PREPARE),
        )
        if not accepted:
            pytest.fail("Scheduled frozen transitions did not obtain accepted proof")
        transition_refs = tuple(
            ref for ref in outputs if ref.kind == "prepared_transitions"
        )
        if len(transition_refs) != 1:
            pytest.fail("One bounded transition tuple needs one genuine output")
        result = store.get_result(transition_refs[0].result_id)
        if result is None or result.semantic_data_ref is None:
            pytest.fail("Accepted transition publication is missing")
        payload = store.load_semantic_data(result.semantic_data_ref)
        if not isinstance(payload, PreparedTransitions):
            pytest.fail("Accepted output has the wrong semantic schema")
        if payload.transitions != value.transitions or result.input_refs != (
            c.ref(saved),
        ):
            pytest.fail("Transition output changed the frozen facts or workset root")
        if any(
            item.transition_kind != "membership_removal" for item in payload.transitions
        ):
            pytest.fail("Scoped removal became a global deletion")
        states = store.list_preparation_intake_worksets(value.scope, pending_only=False)
        if states[0].state != "terminal" or states[0].result_refs != outputs:
            pytest.fail("Accepted transition manifest did not close exact work")
        expected = TerminalStatus.INCOMPLETE if selected else TerminalStatus.COMPLETE
        if status is not expected:
            pytest.fail("Mixed preparation status was not preserved")

    try:
        asyncio.run(check())
    finally:
        store.close()


@pytest.mark.parametrize(
    "stream,resource,scope_kind,scope_identity,reason,want",
    [
        (
            "outlook_mail",
            "message",
            "mail_folder",
            "exact-scope",
            "folder_delta_removed",
            "membership_removal",
        ),
        (
            "outlook_mail",
            "mail_folder",
            "mail_folder",
            "resource",
            "inventory_present",
            "presence",
        ),
        (
            "outlook_calendar",
            "calendar_event",
            "calendar_window",
            "exact-scope",
            '{"kind":"removed","removed_reason":"deleted"}',
            "membership_removal",
        ),
        (
            "outlook_calendar",
            "calendar_event",
            "calendar_window",
            '["default","2026-01-01T00:00:00Z","2026-02-01T00:00:00Z"]',
            '{"attempt":1,"kind":"rebaseline_absence","removed_reason":null}',
            "absence",
        ),
    ],
)
def test_real_release_is_prepared_in_original_scope(
    saved_catalog, tmp_path, stream, resource, scope_kind, scope_identity, reason, want
):
    """The adapter and scheduler retain exact producer transition semantics."""
    from message_ingest.acquisition.handoff import AcquisitionFactKind
    from msgloom.preparation_pipeline.intake_models import (
        IntakeScope,
        PreparationIntakeWorkset,
    )
    from msgloom.sources.release_reader import ReleaseSourceReader
    from tests.source_reader.release_nonmail_helpers import fact, publish

    item = replace(
        fact(
            stream,
            resource,
            "resource",
            "unused",
            scope_kind=scope_kind,
            scope_identity=scope_identity,
        ),
        fact_kind=AcquisitionFactKind.SCOPED_STATE_TRANSITION,
        source_version_locator=None,
        evidence_id=None,
        transition_reason=reason,
    )
    seq = publish(saved_catalog, [item], roles=("transition",), entry_kind="transition")
    config = configuration(saved_catalog, tmp_path)
    operation = cast(
        PreparationOperationData, config.operation(PhaseCapability.PREPARE)
    )
    operation = replace(
        operation,
        intake_targets=(
            operation.intake_targets[0].model_copy(update={"stream": stream}),
        ),
    )

    async def check():
        persistence = await Phase1Persistence.open(config.database_url)
        reader = ReleaseSourceReader(config.source_reader_config())
        try:
            entry = await reader.catalog.get_release_entry(seq)
            if entry is None:
                pytest.fail("Real transition release is missing")
            facts = await reader.catalog.get_release_facts(entry.reference)
            scope = IntakeScope(
                catalog=entry.reference.catalog,
                source_id="synthetic-source",
                stream=stream,
                consumer_id="stable",
            )
            handler = ScheduledPreparationHandler(
                persistence,
                config.source_reader_config(),
                operation,
                AttemptIdentity("real-transition"),
            )
            from msgloom.contracts import ExecutionIdentity

            outcome = await handler.run(
                OperationRequest(
                    ExecutionIdentity("real-transition"),
                    "test",
                    PhaseCapability.PREPARE,
                )
            )
            if outcome.status is not TerminalStatus.COMPLETE:
                pytest.fail("Real scoped transition was not prepared completely")
            states = await persistence.list_preparation_intake_worksets(
                scope, pending_only=False
            )
            if len(states) != 1 or states[0].state != "terminal":
                pytest.fail("Real transition intake did not become terminal")
            saved = await persistence.get_result(states[0].workset.result_id)
            if saved is None or saved.semantic_data_ref is None:
                pytest.fail("Frozen workset is missing")
            workset = await persistence.load_semantic_data(saved.semantic_data_ref)
            if not isinstance(workset, PreparationIntakeWorkset):
                pytest.fail("Frozen workset schema changed")
            if workset.held or len(workset.transitions) != 1:
                pytest.fail("Legitimate producer transition became held work")
            result = await persistence.get_result(outcome.result_refs[0].result_id)
            if result is None or result.semantic_data_ref is None:
                pytest.fail("Accepted scoped output is missing")
            value = await persistence.load_semantic_data(result.semantic_data_ref)
            if (
                not isinstance(value, PreparedTransitions)
                or value.transitions != workset.transitions
            ):
                pytest.fail("Processing substituted frozen transition facts")
            transition = value.transitions[0]
            if (
                transition.entry != entry.reference
                or transition.fact_id != facts[0].fact_id
                or transition.scope_kind != scope_kind
                or transition.scope_identity != scope_identity
                or transition.transition_kind != want
            ):
                pytest.fail("Scoped Mail/Calendar removal became a global deletion")
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())
