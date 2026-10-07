"""Terminal intake requires accepted preparation of every frozen input."""

from dataclasses import replace

import pytest
from sqlalchemy import event

from msgloom.contracts import TerminalStatus, VersionRef
from msgloom.persistence import DependencyNotReadyError
from tests.phase1_foundation import intake_completion_helpers as c
from tests.phase1_foundation import intake_helpers as h


@pytest.mark.parametrize("kind", ["selection", "intake", "unrelated"])
@pytest.mark.parametrize("status", [TerminalStatus.COMPLETE, TerminalStatus.INCOMPLETE])
def test_original_input_or_unrelated_result_is_not_completion_proof(
    tmp_path, kind, status
):
    store = h.store(tmp_path / "neutral.db")
    value, saved, owner, selections = c.admit(store)
    output = c.ref(selections[0]) if kind == "selection" else c.ref(saved)
    if kind == "unrelated":
        output = h.output(store, saved, owner)
    try:
        with pytest.raises((ValueError, DependencyNotReadyError)):
            store.finalize_preparation_intake_workset(
                saved.result_id,
                status,
                (output,),
                claim=owner,
            )
        if len(store.list_preparation_intake_worksets(value.scope)) != 1:
            pytest.fail("Original input or unrelated result consumed pending work")
    finally:
        store.close()


@pytest.mark.parametrize(
    "damage",
    [
        "missing_input",
        "wrong_selection",
        "wrong_source",
        "incomplete_coverage",
        "unrelated_filter",
        "unrelated_group",
        "mixed_unrelated",
    ],
)
def test_preparation_outputs_require_exact_frozen_lineage(tmp_path, damage):
    store = h.store(tmp_path / "neutral.db")
    value, saved, owner, selections = c.admit(store, count=2)
    outcome = c.replay(store, owner, selections)
    prepared_ref = next(ref for ref in outcome.result_refs if ref.kind == "prepared")
    prepared = store.get_result(prepared_ref.result_id)
    output_refs = (prepared_ref,)
    other_prepared = tuple(
        ref
        for ref in outcome.result_refs
        if ref.kind == "prepared" and ref != prepared_ref
    )
    if damage == "missing_input":
        output_refs = (c.clone(store, prepared, input_refs=()), *other_prepared)
    elif damage == "wrong_selection":
        original = selections[0]
        if original.semantic_data_ref is None:
            pytest.fail("Saved selection lacks semantic data")
        alias = replace(original, result_id="selection-alias")
        store.append_result_with_data(
            alias,
            store.load_semantic_data(original.semantic_data_ref),
        )
        output_refs = (
            c.clone(store, prepared, input_refs=(c.ref(alias),)),
            *other_prepared,
        )
    elif damage == "wrong_source":
        output_refs = (
            c.clone(
                store,
                prepared,
                source_versions=(VersionRef("outlook_email", "wrong", "1"),),
            ),
            *other_prepared,
        )
    elif damage in {"unrelated_filter", "unrelated_group"}:
        kind = "filter_result" if damage == "unrelated_filter" else "group_result"
        original_ref = next(ref for ref in outcome.result_refs if ref.kind == kind)
        original = store.get_result(original_ref.result_id)
        forged = c.clone(store, original, input_refs=(c.ref(selections[0]),))
        output_refs = tuple(
            forged if ref == original_ref else ref for ref in outcome.result_refs
        )
    elif damage == "mixed_unrelated":
        output_refs = outcome.result_refs + (h.output(store, saved, owner),)
    try:
        with pytest.raises((ValueError, DependencyNotReadyError)):
            store.finalize_preparation_intake_workset(
                saved.result_id,
                TerminalStatus.INCOMPLETE,
                output_refs,
                claim=owner,
            )
        if not store.list_preparation_intake_worksets(value.scope):
            pytest.fail("Unrelated or incomplete lineage consumed pending work")
    finally:
        store.close()


@pytest.mark.parametrize("selected", [False, True])
def test_unproven_transitions_remain_pending_even_with_prepared_records(
    tmp_path, selected
):
    store = h.store(tmp_path / "neutral.db")
    value, saved, owner, selections = c.admit(
        store,
        count=int(selected),
        transition=True,
    )
    refs = c.replay(store, owner, selections).result_refs if selected else ()
    try:
        with pytest.raises((ValueError, DependencyNotReadyError)):
            store.finalize_preparation_intake_workset(
                saved.result_id,
                TerminalStatus.INCOMPLETE,
                refs,
                claim=owner,
            )
        if not store.list_preparation_intake_worksets(value.scope):
            pytest.fail("Selection processing erased an unprocessed transition")
    finally:
        store.close()


@pytest.mark.parametrize("with_derived", [False, True])
def test_real_replay_outputs_complete_mixed_readable_and_held_workset(
    tmp_path, with_derived
):
    store = h.store(tmp_path / "neutral.db")
    value, saved, owner, selections = c.admit(store, count=2, held=True)
    from msgloom.preparation import DocumentFormat
    from tests.preparation_pipeline.helpers import profiles

    outcome = c.replay(
        store,
        owner,
        selections,
        parser_profiles=profiles(DocumentFormat.JSON) if with_derived else (),
    )
    expected_status = (
        TerminalStatus.COMPLETE if with_derived else TerminalStatus.INCOMPLETE
    )
    if outcome.status is not expected_status:
        pytest.fail(f"Real replay did not preserve its accepted outcome: {outcome}")
    expected_kinds = {"prepared", "filter_result", "group_result"}
    if with_derived:
        expected_kinds.add("derived_bytes")
    if {ref.kind for ref in outcome.result_refs} != expected_kinds:
        pytest.fail("Replay fixture did not exercise all preparation outputs")
    reads = []

    def observe(connection, _cursor, statement, _params, _context, _many):
        if (
            statement.startswith("SELECT")
            and "phase1_semantic_data.payload" in statement
        ):
            reads.append(connection.connection.driver_connection.in_transaction)

    event.listen(store.engine, "before_cursor_execute", observe)
    try:
        store.finalize_preparation_intake_workset(
            saved.result_id,
            outcome.status,
            outcome.result_refs,
            claim=owner,
        )
        if not reads or any(reads):
            pytest.fail("Semantic proof was not checked outside final writer ownership")
        states = store.list_preparation_intake_worksets(value.scope, pending_only=False)
        if (
            states[0].result_refs != outcome.result_refs
            or states[0].state != "terminal"
        ):
            pytest.fail("Legitimate replay lost exact saved result references")
        if not store.list_preparation_intake_held_entries(value.scope):
            pytest.fail("Completion erased held repair evidence")
        store.finalize_preparation_intake_workset(
            saved.result_id,
            outcome.status,
            outcome.result_refs,
            claim=owner,
        )
    finally:
        event.remove(store.engine, "before_cursor_execute", observe)
        store.close()


@pytest.mark.parametrize("terminal", ["failed", "cancelled", "blocked", None])
def test_unaccepted_plan_attempt_cannot_supply_completion_proof(tmp_path, terminal):
    from sqlalchemy import update

    from msgloom.persistence.records import CLAIM_ATTEMPTS

    store = h.store(tmp_path / "neutral.db")
    value, saved, owner, selections = c.admit(store)
    outcome = c.replay(store, owner, selections)
    with store.engine.begin() as connection:
        connection.execute(
            update(CLAIM_ATTEMPTS)
            .where(CLAIM_ATTEMPTS.c.attempt_id == "plan-attempt")
            .values(terminal_status=terminal)
        )
    try:
        with pytest.raises((ValueError, DependencyNotReadyError)):
            store.finalize_preparation_intake_workset(
                saved.result_id,
                TerminalStatus.COMPLETE,
                outcome.result_refs,
                claim=owner,
            )
        if not store.list_preparation_intake_worksets(value.scope):
            pytest.fail("An unaccepted preparation attempt consumed pending work")
    finally:
        store.close()


def test_equal_semantic_versions_do_not_replace_exact_derived_lineage(tmp_path):
    from msgloom.preparation import DocumentFormat
    from tests.preparation_pipeline.helpers import profiles

    store = h.store(tmp_path / "neutral.db")
    value, saved, owner, selections = c.admit(store, count=2, same_source=True)
    first, second = (
        c.replay(
            store,
            owner,
            (selected,),
            parser_profiles=profiles(DocumentFormat.JSON),
        )
        for selected in selections
    )
    prepared_ref = next(ref for ref in first.result_refs if ref.kind == "prepared")
    prepared = store.get_result(prepared_ref.result_id)
    derived_ref = next(ref for ref in second.result_refs if ref.kind == "derived_bytes")
    replacement = c.clone(
        store,
        prepared,
        input_refs=(c.ref(selections[0]), derived_ref),
    )
    refs = tuple(ref for ref in first.result_refs if ref.kind == "derived_bytes") + (
        replacement,
        *(
            ref
            for ref in second.result_refs
            if ref.kind in {"derived_bytes", "prepared"}
        ),
    )
    try:
        with pytest.raises(DependencyNotReadyError):
            store.finalize_preparation_intake_workset(
                saved.result_id,
                TerminalStatus.COMPLETE,
                refs,
                claim=owner,
            )
        if not store.list_preparation_intake_worksets(value.scope):
            pytest.fail("Equal semantic versions hid a different exact selection ref")
    finally:
        store.close()
