"""Require the producing plan's exact accepted output and terminal status."""

import pytest
from sqlalchemy import select

from msgloom.contracts import TerminalStatus, VersionRef
from msgloom.persistence import DependencyNotReadyError
from msgloom.persistence.records import CLAIM_ATTEMPTS
from msgloom.preparation_pipeline import PreparationHandler
from tests.phase1_foundation import intake_completion_helpers as c
from tests.phase1_foundation import intake_helpers as h


def test_successful_sibling_cannot_accept_failed_plan_output(tmp_path, monkeypatch):
    store = h.store(tmp_path / "neutral.db")
    value, saved, owner, selections = c.admit(store)

    async def fail_filter(*_args, **_kwargs):
        raise RuntimeError("injected failure after prepared output")

    try:
        with monkeypatch.context() as patch:
            patch.setattr(PreparationHandler, "_filter_all", fail_filter)
            failed = c.replay(store, owner, selections)
        if failed.status is not TerminalStatus.FAILED:
            pytest.fail("Original preparation plan did not fail")
        if tuple(ref.kind for ref in failed.result_refs) != ("prepared",):
            pytest.fail("Original plan did not retain its partial prepared output")

        unrelated = h.selection(
            store,
            owner,
            result_id="unrelated-selection",
            source=VersionRef("outlook_email", "unrelated", "observation-other"),
        )
        sibling = c.replay(store, owner, (unrelated,))
        if sibling.status is not TerminalStatus.INCOMPLETE:
            pytest.fail("Sibling plan did not finish successfully")
        with store.engine.connect() as connection:
            plans = tuple(
                connection.execute(
                    select(
                        CLAIM_ATTEMPTS.c.claim_key,
                        CLAIM_ATTEMPTS.c.execution_id,
                        CLAIM_ATTEMPTS.c.attempt_id,
                        CLAIM_ATTEMPTS.c.terminal_status,
                    ).where(CLAIM_ATTEMPTS.c.claim_key.startswith("prepare:"))
                )
            )
        if (
            len(plans) != 2
            or len({plan.claim_key for plan in plans}) != 2
            or len({(plan.execution_id, plan.attempt_id) for plan in plans}) != 1
            or {plan.terminal_status for plan in plans} != {"failed", "incomplete"}
        ):
            pytest.fail("Regression did not create distinct sibling plan histories")
        with pytest.raises(DependencyNotReadyError):
            store.finalize_preparation_intake_workset(
                saved.result_id,
                TerminalStatus.COMPLETE,
                failed.result_refs,
                claim=owner,
            )
        if len(store.list_preparation_intake_worksets(value.scope)) != 1:
            pytest.fail("Successful sibling discharged the failed producing plan")
    finally:
        store.close()


def test_incomplete_plan_cannot_be_escalated_to_complete(tmp_path):
    store = h.store(tmp_path / "neutral.db")
    value, saved, owner, selections = c.admit(store)
    outcome = c.replay(store, owner, selections)
    if outcome.status is not TerminalStatus.INCOMPLETE:
        pytest.fail("Fixture requires an accepted limited preparation outcome")
    try:
        with pytest.raises(DependencyNotReadyError):
            store.finalize_preparation_intake_workset(
                saved.result_id,
                TerminalStatus.COMPLETE,
                outcome.result_refs,
                claim=owner,
            )
        if len(store.list_preparation_intake_worksets(value.scope)) != 1:
            pytest.fail("Caller escalated the saved preparation status")
    finally:
        store.close()


@pytest.mark.parametrize("omitted", ["filter_result", "group_result"])
def test_terminal_requires_the_full_producing_plan_result_set(tmp_path, omitted):
    store = h.store(tmp_path / "neutral.db")
    value, saved, owner, selections = c.admit(store)
    outcome = c.replay(store, owner, selections)
    if outcome.status is not TerminalStatus.INCOMPLETE:
        pytest.fail("Fixture requires an accepted preparation outcome")
    refs = tuple(ref for ref in outcome.result_refs if ref.kind == "prepared")
    if omitted == "group_result":
        refs = tuple(ref for ref in outcome.result_refs if ref.kind != "group_result")
    try:
        with pytest.raises(DependencyNotReadyError):
            store.finalize_preparation_intake_workset(
                saved.result_id,
                outcome.status,
                refs,
                claim=owner,
            )
        if len(store.list_preparation_intake_worksets(value.scope)) != 1:
            pytest.fail("Partial results erased pending preparation work")
    finally:
        store.close()
