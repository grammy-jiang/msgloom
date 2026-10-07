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


def _snapshot(**overrides):
    value = {
        "run_id": "run-1",
        "started_folder_ids": {"folder-a", "folder-b"},
        "completed_folder_ids": {"folder-a", "folder-b"},
        "folder_inventory_complete": True,
        "folder_inventory_failed": False,
        "reconcile_complete": True,
        "reconcile_messages": True,
        "run_failed": False,
        "failure_reasons": set(),
    }
    value.update(overrides)
    return value


def test_validate_mail_delta_run_returns_bounded_handoff() -> None:
    from message_ingest.sync.microsoft.outlook.email.promotion import (
        ValidatedMailDeltaRun,
        validate_mail_delta_run,
    )

    validated = validate_mail_delta_run(
        _snapshot(),
        {"folder-a": object(), "folder-b": object()},
    )

    if validated != ValidatedMailDeltaRun(
        run_id="run-1",
        expected_folder_ids=frozenset({"folder-a", "folder-b"}),
        reconcile_messages=True,
        candidate_folder_ids=frozenset({"folder-a", "folder-b"}),
    ):
        pytest.fail(f"Validated delta handoff changed: {validated!r}")


@pytest.mark.parametrize(
    "snapshot,candidates",
    (
        (_snapshot(run_failed=True), {"folder-a": object(), "folder-b": object()}),
        (
            _snapshot(folder_inventory_failed=True),
            {"folder-a": object(), "folder-b": object()},
        ),
        (
            _snapshot(folder_inventory_complete=False),
            {"folder-a": object(), "folder-b": object()},
        ),
        (
            _snapshot(reconcile_complete=False),
            {"folder-a": object(), "folder-b": object()},
        ),
        (
            _snapshot(completed_folder_ids={"folder-a"}),
            {"folder-a": object(), "folder-b": object()},
        ),
        (_snapshot(), {"folder-a": object()}),
    ),
)
def test_validate_mail_delta_run_rejects_incomplete_integrity(
    snapshot,
    candidates,
) -> None:
    from message_ingest.sync.microsoft.outlook.email.promotion import (
        validate_mail_delta_run,
    )

    with pytest.raises(ValueError, match="delta run is incomplete"):
        validate_mail_delta_run(snapshot, candidates)


def test_mail_delta_commit_mode_derives_from_policy_and_private_owner() -> None:
    from scrapy.utils.test import get_crawler

    from message_ingest.acquisition.microsoft.outlook.email.rule_config import (
        parse_mail_rule_policy,
    )
    from message_ingest.spiders.microsoft.outlook.email._delta_state import (
        MailDeltaCommitMode,
    )
    from message_ingest.spiders.microsoft.outlook.email.delta import OutlookDeltaSpider

    crawler = get_crawler(
        OutlookDeltaSpider,
        settings_dict={"MSGLOOM_SOURCE_IDENTITY_REQUIRED": False},
    )
    disabled = parse_mail_rule_policy(None)
    enabled = parse_mail_rule_policy({"enabled": True})

    immediate = OutlookDeltaSpider.from_crawler(crawler, _mail_rule_policy=disabled)
    if immediate.mail_delta_commit_mode is not MailDeltaCommitMode.IMMEDIATE:
        pytest.fail("Disabled policy must preserve immediate delta commit")

    blocked = OutlookDeltaSpider.from_crawler(crawler, _mail_rule_policy=enabled)
    if blocked.mail_delta_commit_mode is not MailDeltaCommitMode.BLOCKED:
        pytest.fail("Enabled direct delta must fail closed as BLOCKED")

    deferred = OutlookDeltaSpider.from_crawler(
        crawler,
        _mail_rule_policy=enabled,
        _mail_delta_commit_mode=MailDeltaCommitMode.DEFERRED,
    )
    if deferred.mail_delta_commit_mode is not MailDeltaCommitMode.DEFERRED:
        pytest.fail("Enabled workflow-owned delta did not select DEFERRED")


def test_mail_delta_commit_mode_rejects_impossible_combinations() -> None:
    from scrapy.utils.test import get_crawler

    from message_ingest.acquisition.microsoft.outlook.email.rule_config import (
        parse_mail_rule_policy,
    )
    from message_ingest.spiders.microsoft.outlook.email._delta_state import (
        MailDeltaCommitMode,
    )
    from message_ingest.spiders.microsoft.outlook.email.delta import OutlookDeltaSpider

    crawler = get_crawler(
        OutlookDeltaSpider,
        settings_dict={"MSGLOOM_SOURCE_IDENTITY_REQUIRED": False},
    )
    enabled = parse_mail_rule_policy({"enabled": True})
    disabled = parse_mail_rule_policy(None)

    with pytest.raises(ValueError):
        OutlookDeltaSpider.from_crawler(
            crawler,
            _mail_rule_policy=enabled,
            _mail_delta_commit_mode=MailDeltaCommitMode.IMMEDIATE,
        )
    with pytest.raises(ValueError):
        OutlookDeltaSpider.from_crawler(
            crawler,
            _mail_rule_policy=disabled,
            _mail_delta_commit_mode=MailDeltaCommitMode.DEFERRED,
        )
    with pytest.raises(TypeError):
        OutlookDeltaSpider.from_crawler(
            crawler,
            _mail_rule_policy=enabled,
            _mail_delta_commit_mode="deferred",
        )
