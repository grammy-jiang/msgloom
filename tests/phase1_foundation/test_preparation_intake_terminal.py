"""Pending work remains discoverable until a live exact owner completes it."""

from dataclasses import replace

import pytest

from msgloom.contracts import TerminalStatus
from msgloom.persistence import ImmutableRecordError, StaleClaimError


def test_exact_pending_owner_can_mark_terminal_after_saved_output(tmp_path):
    from tests.phase1_foundation import intake_helpers as h

    store = h.store(tmp_path / "neutral.db")
    from tests.phase1_foundation import intake_completion_helpers as c

    value, saved, owner, selections = c.admit(store)
    outcome = c.replay(store, owner, selections)
    refs = outcome.result_refs
    try:
        store.finalize_preparation_intake_workset(
            saved.result_id,
            TerminalStatus.INCOMPLETE,
            refs,
            claim=owner,
        )
        if store.list_preparation_intake_worksets(value.scope):
            pytest.fail("Terminal workset remains pending")
        states = store.list_preparation_intake_worksets(value.scope, pending_only=False)
        if states[0].result_refs != refs or states[0].state != "terminal":
            pytest.fail("Terminal processing lost exact result references")
        store.finalize_preparation_intake_workset(
            saved.result_id,
            TerminalStatus.INCOMPLETE,
            refs,
            claim=owner,
        )
        with pytest.raises(ImmutableRecordError):
            store.finalize_preparation_intake_workset(
                saved.result_id,
                TerminalStatus.COMPLETE,
                refs,
                claim=owner,
            )
    finally:
        store.close()


@pytest.mark.parametrize(
    "invalid",
    [
        "expired",
        "superseded",
        "unrelated",
        "missing_input",
        "intake",
        "wrong_attempt",
    ],
)
def test_invalid_processing_owner_leaves_work_pending(tmp_path, invalid):
    from msgloom.contracts import AttemptIdentity, ClaimKind, ExecutionIdentity
    from msgloom.preparation_pipeline.intake_models import workset_claim_key
    from tests.phase1_foundation import intake_helpers as h

    store = h.store(tmp_path / "neutral.db")
    value = h.workset()
    token = h.claim(store, value)
    saved = h.result(store, value, token)
    store.finalize_preparation_intake(saved, value, claim=token)
    if invalid == "intake":
        owner = token
    elif invalid == "missing_input":
        owner = store.acquire_claim(
            workset_claim_key(saved.result_id),
            ClaimKind.PREPARE,
            ExecutionIdentity("processor"),
            AttemptIdentity("processor"),
            (),
            60,
        )
    else:
        owner = h.processing_claim(
            store,
            saved,
            lease=0 if invalid in {"expired", "superseded"} else 60,
            key="unrelated" if invalid == "unrelated" else None,
        )
        if invalid == "superseded":
            h.processing_claim(store, saved, identity="replacement")
        elif invalid == "wrong_attempt":
            owner = replace(owner, attempt=AttemptIdentity("forged"))
    try:
        with pytest.raises(StaleClaimError):
            store.finalize_preparation_intake_workset(
                saved.result_id,
                TerminalStatus.COMPLETE,
                (),
                claim=owner,
            )
        if len(store.list_preparation_intake_worksets(value.scope)) != 1:
            pytest.fail("An invalid owner consumed pending work")
    finally:
        store.close()


@pytest.mark.parametrize(
    "status",
    [
        TerminalStatus.FAILED,
        TerminalStatus.CANCELLED,
        TerminalStatus.BLOCKED,
    ],
)
def test_unsuccessful_processing_keeps_work_pending(tmp_path, status):
    from tests.phase1_foundation import intake_helpers as h

    store = h.store(tmp_path / "neutral.db")
    value = h.workset()
    token = h.claim(store, value)
    saved = h.result(store, value, token)
    store.finalize_preparation_intake(saved, value, claim=token)
    owner = h.processing_claim(store, saved)
    try:
        with pytest.raises(ValueError):
            store.finalize_preparation_intake_workset(
                saved.result_id,
                status,
                (),
                claim=owner,
            )
        if not store.list_preparation_intake_worksets(value.scope):
            pytest.fail("Unsuccessful processing orphaned admitted work")
    finally:
        store.close()
