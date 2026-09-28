"""Verify Mail delta execution-state serialization remains provider-cursor free."""

from __future__ import annotations

import pytest

from message_ingest.spiders.microsoft.outlook.email._delta_state import (
    MailDeltaExecutionState,
    execution_payload,
)


def test_mail_delta_execution_state_round_trips_plain_facts() -> None:
    payload = execution_payload(
        run_id="run-1",
        seen_folder_ids={"folder-b", "folder-a"},
        started_folder_ids={"folder-a"},
        completed_folder_ids=set(),
        reconcile_orphan_ids={"message-1"},
        folder_inventory_pending=2,
        folder_inventory_complete=False,
        folder_inventory_failed=True,
        reconcile_complete=False,
        run_failed=True,
        failure_reasons={"item_error"},
        delta_start_scheduled=True,
    )
    restored = MailDeltaExecutionState.restore(payload, default_run_id="fallback")

    if restored.run_id != "run-1":
        pytest.fail("Expected persisted Mail delta run identity")
    if restored.seen_folder_ids != frozenset({"folder-a", "folder-b"}):
        pytest.fail("Expected deterministic folder-state restoration")
    if restored.failure_reasons != frozenset({"item_error"}):
        pytest.fail("Expected failure reasons to survive JOBDIR serialization")
    if "delta_link" in payload or "delta_links" in payload:
        pytest.fail("Provider cursors must not be stored in Scrapy execution state")
