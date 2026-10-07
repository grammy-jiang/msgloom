"""Atomic admission, durable pending state, and claim fencing regressions."""

from dataclasses import replace

import pytest
from sqlalchemy import event, text

from msgloom.contracts import ClaimKind, ExternalEffectState, TerminalStatus
from msgloom.persistence import DependencyNotReadyError, StaleClaimError


def test_workset_cursor_pending_and_held_survive_restart(tmp_path):
    from tests.phase1_foundation import intake_helpers as h

    path = tmp_path / "neutral.db"
    store = h.store(path)
    value = h.workset()
    token = h.claim(store, value)
    saved = h.result(store, value, token)
    store.finalize_preparation_intake(saved, value, claim=token)
    store.finish_claim(token, TerminalStatus.COMPLETE, ExternalEffectState.NONE)
    store.close()
    store = h.store(path)
    try:
        if store.get_preparation_intake_cursor(value.scope) != value.cutoff:
            pytest.fail("Cursor was not advanced with its durable workset")
        states = store.list_preparation_intake_worksets(value.scope)
        if len(states) != 1 or states[0].state != "pending":
            pytest.fail("Restart lost pending admitted work")
        if store.get_result("workset") != saved:
            pytest.fail("Workset StageResult changed across restart")
        if saved.semantic_data_ref is None:
            pytest.fail("Intake workset has no semantic payload")
        if store.load_semantic_data(saved.semantic_data_ref) != value:
            pytest.fail("Workset payload changed across restart")
        held = store.list_preparation_intake_held_entries(value.scope)
        if len(held) != 1 or held[0].disposition != value.held[0]:
            pytest.fail("Held entry was lost from bounded operator index")
    finally:
        store.close()


@pytest.mark.parametrize(
    "failed_table",
    [
        "phase1_semantic_data",
        "phase1_stage_results",
        "phase1_preparation_intake_worksets",
        "phase1_preparation_intake_held_entries",
        "phase1_preparation_intake_cursors",
    ],
)
def test_any_final_write_failure_rolls_back_every_admission_row(tmp_path, failed_table):
    from tests.phase1_foundation import intake_helpers as h

    store = h.store(tmp_path / "neutral.db")
    value = h.workset()
    token = h.claim(store, value)
    saved = h.result(store, value, token)

    def reject(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.startswith("INSERT INTO " + failed_table):
            raise RuntimeError("injected intake write failure")

    event.listen(store.engine, "before_cursor_execute", reject)
    try:
        with pytest.raises(RuntimeError, match="injected intake write"):
            store.finalize_preparation_intake(saved, value, claim=token)
    finally:
        event.remove(store.engine, "before_cursor_execute", reject)
    try:
        if store.get_result(saved.result_id) is not None:
            pytest.fail("Failed finalization leaked its StageResult")
        if store.get_preparation_intake_cursor(value.scope) != value.previous:
            pytest.fail("Failed finalization advanced the source cursor")
        if store.list_preparation_intake_worksets(value.scope):
            pytest.fail("Failed finalization leaked pending work")
        if store.list_preparation_intake_held_entries(value.scope):
            pytest.fail("Failed finalization leaked held entry")
        with store.engine.connect() as connection:
            count = connection.execute(
                text("SELECT count(*) FROM phase1_semantic_data")
            ).scalar_one()
        if count:
            pytest.fail("Failed finalization leaked semantic bytes")
        store.finalize_preparation_intake(saved, value, claim=token)
    finally:
        store.close()


def test_selection_must_be_durable_before_finalization(tmp_path):
    from tests.phase1_foundation import intake_helpers as h

    store = h.store(tmp_path / "neutral.db")
    value = h.workset(selected=True)
    token = h.claim(store, value)
    saved = h.result(store, value, token)
    try:
        with pytest.raises(DependencyNotReadyError):
            store.finalize_preparation_intake(saved, value, claim=token)
        h.selection(store, token)
        store.finalize_preparation_intake(saved, value, claim=token)
        if store.get_preparation_intake_cursor(value.scope) != value.cutoff:
            pytest.fail("Durable exact selection was not admitted")
    finally:
        store.close()


@pytest.mark.parametrize("bad_owner", ["expired", "superseded", "wrong_key", "prepare"])
def test_invalid_intake_owner_cannot_publish(tmp_path, bad_owner):
    from tests.phase1_foundation import intake_helpers as h

    store = h.store(tmp_path / "neutral.db")
    value = h.workset()
    token = h.claim(
        store,
        value,
        lease=0 if bad_owner in {"expired", "superseded"} else 60,
        key="unrelated" if bad_owner == "wrong_key" else None,
        kind=ClaimKind.PREPARE if bad_owner == "prepare" else None,
    )
    if bad_owner == "superseded":
        h.claim(store, value, identity="new")
    saved = h.result(store, value, token)
    try:
        with pytest.raises(StaleClaimError):
            store.finalize_preparation_intake(saved, value, claim=token)
        if store.get_preparation_intake_cursor(value.scope) != value.previous:
            pytest.fail("Invalid owner advanced intake")
    finally:
        store.close()


def test_prior_cursor_cas_and_consumer_stream_isolation(tmp_path):
    from tests.phase1_foundation import intake_helpers as h

    store = h.store(tmp_path / "neutral.db")
    first = h.workset()
    token = h.claim(store, first)
    saved = h.result(store, first, token)
    try:
        store.finalize_preparation_intake(saved, first, claim=token)
        stale = h.workset(seq=9)
        with pytest.raises(StaleClaimError):
            store.finalize_preparation_intake(
                h.result(store, stale, token, "stale"),
                stale,
                claim=token,
            )
        next_value = h.workset(previous=first.cutoff, seq=9).model_copy(
            update={
                "configuration_version": "config-2",
                "code_version": "code-2",
            }
        )
        store.finalize_preparation_intake(
            h.result(store, next_value, token, "next"),
            next_value,
            claim=token,
        )
        for other in (h.scope("outlook_calendar"), h.scope(consumer="other")):
            if store.get_preparation_intake_cursor(other) != first.previous:
                pytest.fail("Independent cursor scope advanced")
        if store.get_preparation_intake_cursor(first.scope) != next_value.cutoff:
            pytest.fail("Ordinary version change created a fresh consumer cursor")
    finally:
        store.close()


def test_final_fence_rolls_back_if_lease_expires_during_write(tmp_path):
    from tests.phase1_foundation import intake_helpers as h

    store = h.store(tmp_path / "neutral.db")
    value = h.workset()
    token = h.claim(store, value)
    saved = h.result(store, value, token)

    def expire(connection, _cursor, statement, _parameters, _context, _many):
        if statement.startswith("INSERT INTO phase1_preparation_intake_cursors"):
            connection.execute(
                text(
                    "UPDATE phase1_work_claims SET expires_at='2000-01-01T00:00:00+00:00'"
                )
            )

    event.listen(store.engine, "after_cursor_execute", expire)
    try:
        with pytest.raises(StaleClaimError):
            store.finalize_preparation_intake(saved, value, claim=token)
    finally:
        event.remove(store.engine, "after_cursor_execute", expire)
    try:
        if store.get_result(saved.result_id) is not None:
            pytest.fail("Lease expiry at commit leaked the workset")
    finally:
        store.close()


@pytest.mark.parametrize("mismatch", ["execution", "attempt", "inputs", "config"])
def test_workset_result_must_match_claim_payload_and_lineage(tmp_path, mismatch):
    from msgloom.contracts import AttemptIdentity, ExecutionIdentity, ResultRef
    from tests.phase1_foundation import intake_helpers as h

    store = h.store(tmp_path / "neutral.db")
    value = h.workset()
    token = h.claim(store, value)
    saved = h.result(store, value, token)
    updates = {
        "execution": {"execution": ExecutionIdentity("unowned")},
        "attempt": {"attempt": AttemptIdentity("unowned")},
        "inputs": {"input_refs": (ResultRef("missing", "collected_selection", "1"),)},
        "config": {"configuration_version": "unbound"},
    }
    try:
        with pytest.raises((ValueError, StaleClaimError)):
            store.finalize_preparation_intake(
                replace(saved, **updates[mismatch]),
                value,
                claim=token,
            )
    finally:
        store.close()
