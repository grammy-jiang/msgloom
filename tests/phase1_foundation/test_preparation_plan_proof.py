"""Atomic exact-plan publication and producer acceptance receipts."""

from dataclasses import replace

import pytest
from sqlalchemy import event, text

from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ExecutionIdentity,
    ExternalEffectState,
    ResultRef,
    TerminalStatus,
)
from msgloom.persistence import DependencyNotReadyError, ImmutableRecordError
from msgloom.persistence.errors import StaleClaimError
from tests.phase1_foundation import intake_completion_helpers as c
from tests.phase1_foundation import intake_helpers as h


def rows(store, table):
    """Read synthetic proof fixtures without semantic payload access."""
    with store.engine.connect() as connection:
        return tuple(connection.execute(text(f"SELECT * FROM {table}")).mappings())


def semantic(store, saved):
    """Require the real fixture's semantic payload before replaying a write."""
    if saved.semantic_data_ref is None:
        pytest.fail("Publication fixture lacks semantic data")
    return store.load_semantic_data(saved.semantic_data_ref)


def plan_publication(store):
    """Publish a semantic selection under a real finite producer claim."""
    token = store.acquire_claim(
        "prepare:fixture",
        ClaimKind.PREPARE,
        ExecutionIdentity("producer"),
        AttemptIdentity("producer-attempt"),
        (),
        60,
    )
    saved = h.selection(store, token)
    return token, saved


def finish(store, token, refs, status=TerminalStatus.COMPLETE):
    """Exercise the explicit producer acceptance handoff."""
    store.finish_claim(
        token,
        status,
        ExternalEffectState.NONE,
        accepted_preparation_results=refs,
    )


def test_exact_publication_and_receipt_survive_restart(tmp_path):
    path = tmp_path / "neutral.db"
    store = h.store(path)
    token, saved = plan_publication(store)
    refs = (c.ref(saved),)
    proof = rows(store, "phase1_preparation_plan_proofs")[0]
    binding = rows(store, "phase1_preparation_result_bindings")[0]
    if (
        (proof["claim_token"], proof["attempt_id"], proof["required_inputs"])
        != (
            token.token,
            token.attempt.value,
            "[]",
        )
        or binding["claim_token"] != token.token
        or proof["accepted_status"] is not None
    ):
        pytest.fail("Publication lost exact producer identity or accepted early")
    store.append_result_with_data(
        saved,
        semantic(store, saved),
        claim=token,
    )
    finish(store, token, refs)
    before = rows(store, "phase1_preparation_plan_proofs")
    store.close()
    store = h.store(path)
    finish(store, token, refs)
    if rows(store, "phase1_preparation_plan_proofs") != before:
        pytest.fail("Exact accepted retry mutated its immutable receipt")
    with pytest.raises((ImmutableRecordError, StaleClaimError)):
        finish(store, token, refs, TerminalStatus.INCOMPLETE)
    with pytest.raises((ImmutableRecordError, StaleClaimError)):
        store.finish_claim(token, TerminalStatus.CANCELLED, ExternalEffectState.NONE)
    if rows(store, "phase1_work_claims"):
        pytest.fail("Accepted replay reopened a closed claim")
    store.close()


@pytest.mark.parametrize(
    "table",
    [
        "phase1_semantic_data",
        "phase1_stage_results",
        "phase1_preparation_plan_proofs",
        "phase1_preparation_result_bindings",
    ],
)
def test_publication_failure_rolls_back_entire_pair_and_proof(tmp_path, table):
    store = h.store(tmp_path / "neutral.db")
    token = store.acquire_claim(
        "prepare:fixture",
        ClaimKind.PREPARE,
        ExecutionIdentity("producer"),
        AttemptIdentity("producer-attempt"),
        (),
        60,
    )

    def fail(_connection, _cursor, statement, _params, _context, _many):
        if statement.startswith(f"INSERT INTO {table}"):
            raise RuntimeError("injected publication failure")

    event.listen(store.engine, "after_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="injected publication failure"):
            h.selection(store, token)
    finally:
        event.remove(store.engine, "after_cursor_execute", fail)
    for name in (
        "phase1_stage_results",
        "phase1_semantic_data",
        "phase1_preparation_plan_proofs",
        "phase1_preparation_result_bindings",
    ):
        if rows(store, name):
            pytest.fail(f"Failed publication leaked rows in {name}")
    store.close()


@pytest.mark.parametrize("point", ["receipt", "history", "release"])
def test_acceptance_failure_rolls_back_receipt_history_and_release(tmp_path, point):
    store = h.store(tmp_path / "neutral.db")
    token, saved = plan_publication(store)
    before = {
        name: rows(store, name)
        for name in (
            "phase1_preparation_plan_proofs",
            "phase1_claim_attempts",
            "phase1_work_claims",
        )
    }
    prefix = {
        "receipt": "UPDATE phase1_preparation_plan_proofs",
        "history": "UPDATE phase1_claim_attempts",
        "release": "DELETE FROM phase1_work_claims",
    }[point]

    def fail(_connection, _cursor, statement, _params, _context, _many):
        if statement.startswith(prefix):
            raise RuntimeError("injected acceptance failure")

    event.listen(store.engine, "after_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="injected acceptance failure"):
            finish(store, token, (c.ref(saved),))
    finally:
        event.remove(store.engine, "after_cursor_execute", fail)
    if any(rows(store, name) != values for name, values in before.items()):
        pytest.fail("Failed acceptance changed receipt, history, or ownership")
    finish(store, token, (c.ref(saved),))
    store.close()


@pytest.mark.parametrize(
    "mutation",
    [
        "omit",
        "extra",
        "duplicate",
        "kind",
        "schema",
        "token",
        "attempt",
        "failed",
        "cancelled",
        "blocked",
        "expired",
        "effect",
    ],
)
def test_invalid_acceptance_never_manufactures_receipt(tmp_path, mutation):
    store = h.store(tmp_path / "neutral.db")
    token, saved = plan_publication(store)
    refs = (c.ref(saved),)
    status, effect = TerminalStatus.COMPLETE, ExternalEffectState.NONE
    if mutation == "omit":
        refs = ()
    elif mutation == "extra":
        refs += (ResultRef("foreign", "prepared", "1"),)
    elif mutation == "duplicate":
        refs += refs
    elif mutation in {"kind", "schema"}:
        refs = (
            replace(
                refs[0], **{"kind" if mutation == "kind" else "schema_version": "wrong"}
            ),
        )
    elif mutation == "token":
        token = replace(token, token="foreign")
    elif mutation == "attempt":
        token = replace(token, attempt=AttemptIdentity("foreign"))
    elif mutation in {"failed", "cancelled", "blocked"}:
        status = TerminalStatus(mutation)
    elif mutation == "effect":
        effect = ExternalEffectState.NOT_STARTED
    else:
        with store._write_transaction() as connection:
            connection.execute(
                text(
                    "UPDATE phase1_work_claims SET expires_at='2000-01-01T00:00:00+00:00'"
                )
            )
    with pytest.raises((ValueError, DependencyNotReadyError, StaleClaimError)):
        store.finish_claim(
            token,
            status,
            effect,
            accepted_preparation_results=refs,
        )
    if rows(store, "phase1_preparation_plan_proofs")[0]["accepted_status"] is not None:
        pytest.fail("Invalid completion manufactured acceptance")
    if rows(store, "phase1_claim_attempts")[0]["finished_at"] is not None:
        pytest.fail("Invalid completion finished the attempt")
    store.close()


@pytest.mark.parametrize("historical", [False, True])
def test_no_adoption_or_rebinding_of_existing_results(tmp_path, historical):
    store = h.store(tmp_path / "neutral.db")
    old, saved = plan_publication(store)
    store.finish_claim(old, TerminalStatus.FAILED, ExternalEffectState.NONE)
    if historical:
        with store._write_transaction() as connection:
            connection.execute(text("DELETE FROM phase1_preparation_result_bindings"))
            connection.execute(text("DELETE FROM phase1_preparation_plan_proofs"))
    replacement = store.acquire_claim(
        old.claim_key,
        old.kind,
        old.execution,
        old.attempt,
        (),
        60,
    )
    with pytest.raises(ImmutableRecordError):
        store.append_result_with_data(
            saved,
            semantic(store, saved),
            claim=replacement,
        )
    if store.get_result(saved.result_id) != saved:
        pytest.fail("Rejected adoption altered historical metadata")
    store.close()


def test_prepare_publication_requires_exact_attempt_and_consistent_versions(tmp_path):
    store = h.store(tmp_path / "neutral.db")
    token, saved = plan_publication(store)
    payload = semantic(store, saved)
    for changes in (
        {"attempt": AttemptIdentity("child")},
        {"configuration_version": "other"},
        {"code_version": "other"},
    ):
        forged = replace(saved, result_id="forged", **changes)
        with pytest.raises((ImmutableRecordError, StaleClaimError)):
            store.append_result_with_data(forged, payload, claim=token)
        if store.get_result("forged") is not None:
            pytest.fail("Invalid publication committed result metadata")
    store.close()


def test_complete_disjoint_plans_cover_workset_without_execution_uniqueness(tmp_path):
    store = h.store(tmp_path / "neutral.db")
    value, saved, owner, selections = c.admit(store, count=2)
    first = c.replay(store, owner, selections[:1])
    second = c.replay(store, owner, selections[1:])
    for refs in (first.result_refs, first.result_refs + second.result_refs[:-1]):
        with pytest.raises(DependencyNotReadyError):
            store.finalize_preparation_intake_workset(
                saved.result_id,
                TerminalStatus.INCOMPLETE,
                refs,
                claim=owner,
            )
    store.finalize_preparation_intake_workset(
        saved.result_id,
        TerminalStatus.INCOMPLETE,
        first.result_refs + second.result_refs,
        claim=owner,
    )
    if store.list_preparation_intake_worksets(value.scope):
        pytest.fail("Full exact disjoint manifests did not complete work")
    store.close()


@pytest.mark.parametrize("target", ["inputs", "binding", "result", "receipt"])
def test_receipt_rechecks_exact_publication_before_commit(tmp_path, target):
    store = h.store(tmp_path / "neutral.db")
    token, saved = plan_publication(store)
    names = (
        "phase1_preparation_plan_proofs",
        "phase1_preparation_result_bindings",
        "phase1_stage_results",
        "phase1_claim_attempts",
        "phase1_work_claims",
    )
    before = {name: rows(store, name) for name in names}
    fired = False

    def alter(connection, _cursor, statement, _params, _context, _many):
        nonlocal fired
        if fired or not statement.startswith("UPDATE phase1_preparation_plan_proofs"):
            return
        fired = True
        sql = {
            "inputs": "UPDATE phase1_work_claims SET required_inputs='[{}]'",
            "binding": "UPDATE phase1_preparation_result_bindings SET claim_token='foreign'",
            "result": "UPDATE phase1_stage_results SET code_version='foreign'",
            "receipt": "UPDATE phase1_preparation_plan_proofs SET accepted_result_refs='[]'",
        }[target]
        connection.exec_driver_sql(sql)

    event.listen(store.engine, "after_cursor_execute", alter)
    try:
        with pytest.raises(
            (DependencyNotReadyError, ImmutableRecordError, StaleClaimError)
        ):
            finish(store, token, (c.ref(saved),))
    finally:
        event.remove(store.engine, "after_cursor_execute", alter)
    if not fired or any(rows(store, name) != value for name, value in before.items()):
        pytest.fail("Acceptance failed to fence and roll back changed proof")
    store.close()


@pytest.mark.parametrize("target", ["receipt", "binding", "root", "owner"])
def test_terminal_transaction_rechecks_proof_after_update(tmp_path, target):
    store = h.store(tmp_path / "neutral.db")
    value, saved, owner, selections = c.admit(store)
    outcome = c.replay(store, owner, selections)
    names = (
        "phase1_preparation_plan_proofs",
        "phase1_preparation_result_bindings",
        "phase1_stage_results",
        "phase1_preparation_intake_worksets",
        "phase1_preparation_intake_cursors",
        "phase1_work_claims",
    )
    before = {name: rows(store, name) for name in names}
    fired = False

    def alter(connection, _cursor, statement, _params, _context, _many):
        nonlocal fired
        if fired or not statement.startswith(
            "UPDATE phase1_preparation_intake_worksets"
        ):
            return
        fired = True
        if target == "receipt":
            connection.exec_driver_sql(
                "UPDATE phase1_preparation_plan_proofs SET accepted_status='complete'"
            )
        elif target == "binding":
            connection.exec_driver_sql(
                "UPDATE phase1_preparation_result_bindings SET claim_token='foreign'"
            )
        elif target == "root":
            connection.exec_driver_sql(
                "UPDATE phase1_stage_results SET code_version='foreign' "
                "WHERE result_id=?",
                (selections[0].result_id,),
            )
        else:
            connection.exec_driver_sql(
                "UPDATE phase1_work_claims SET expires_at='2000-01-01T00:00:00+00:00' "
                "WHERE claim_token=?",
                (owner.token,),
            )

    event.listen(store.engine, "after_cursor_execute", alter)
    try:
        with pytest.raises(
            (DependencyNotReadyError, ImmutableRecordError, StaleClaimError)
        ):
            store.finalize_preparation_intake_workset(
                saved.result_id,
                outcome.status,
                outcome.result_refs,
                claim=owner,
            )
    finally:
        event.remove(store.engine, "after_cursor_execute", alter)
    if not fired or any(rows(store, name) != values for name, values in before.items()):
        pytest.fail("Terminal transaction did not roll back inconsistent proof")
    if len(store.list_preparation_intake_worksets(value.scope)) != 1:
        pytest.fail("Rejected terminal proof lost pending work")
    store.close()


@pytest.mark.parametrize("case", ["downgrade", "overlap", "foreign"])
def test_exact_receipts_cannot_certify_wrong_status_or_input_partition(tmp_path, case):
    from msgloom.preparation import DocumentFormat
    from tests.preparation_pipeline.helpers import profiles

    store = h.store(tmp_path / "neutral.db")
    value, saved, owner, selections = c.admit(store)
    outcome = c.replay(
        store,
        owner,
        selections,
        parser_profiles=profiles(DocumentFormat.JSON) if case == "downgrade" else (),
    )
    refs = outcome.result_refs
    if case == "overlap":
        duplicate = c.replay(store, owner, selections, attempt="another-plan")
        refs += duplicate.result_refs
    elif case == "foreign":
        other = h.selection(
            store,
            owner,
            result_id="foreign-selection",
        )
        foreign = c.replay(store, owner, (other,), attempt="foreign-plan")
        refs += foreign.result_refs
    elif outcome.status is not TerminalStatus.COMPLETE:
        pytest.fail("Downgrade probe lacks real complete preparation")
    before = rows(store, "phase1_preparation_intake_worksets")
    with pytest.raises(DependencyNotReadyError):
        store.finalize_preparation_intake_workset(
            saved.result_id,
            TerminalStatus.INCOMPLETE,
            refs,
            claim=owner,
        )
    if rows(store, "phase1_preparation_intake_worksets") != before:
        pytest.fail("Wrong status or input partition altered durable work")
    if store.get_preparation_intake_cursor(value.scope) != value.cutoff:
        pytest.fail("Rejected proof changed the admitted cursor")
    store.close()
