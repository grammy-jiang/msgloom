"""Contracts for deterministic Outlook Mail acquisition-rule evaluation."""

from __future__ import annotations

from typing import Any, cast

import pytest

from message_ingest.acquisition.microsoft.outlook.email.rule_evaluation import (
    MailRuleDecisionOutcome,
    MailRuleEvaluation,
    MailRuleEvaluationState,
    MailRuleProbeStatus,
    MailRuleRequiredData,
    mail_rule_observation_from_item,
)
from message_ingest.items.microsoft.outlook.email import OutlookMailItem


def _item() -> OutlookMailItem:
    return OutlookMailItem.from_graph(
        {
            "id": "message-1",
            "subject": "Approval requested",
            "sender": {"emailAddress": {"address": "sender@example.test"}},
            "from": {"emailAddress": {"address": "from@example.test"}},
            "toRecipients": [
                {"emailAddress": {"address": "to-1@example.test"}},
                {"emailAddress": {"address": "to-2@example.test"}},
            ],
            "ccRecipients": [
                {"emailAddress": {"address": "cc@example.test"}},
            ],
            "bccRecipients": [
                {"emailAddress": {"address": "bcc@example.test"}},
            ],
            "importance": "high",
            "categories": ["Finance", "Approvals"],
            "hasAttachments": True,
            "bodyPreview": "Preview text",
            "lastModifiedDateTime": "2026-09-30T01:02:03Z",
        },
        source_response_url="https://graph.example.test/messages",
        observed_at="2026-09-30T01:02:04Z",
        observation_kind="delta",
        evidence_id="evidence-1",
        run_id="run-1",
    )


def test_rule_observation_projects_discovery_facts_without_retaining_raw() -> None:
    observation = mail_rule_observation_from_item(_item())

    expected = (
        "message-1",
        "run-1",
        "evidence-1",
        "delta",
        "2026-09-30T01:02:03Z",
        "Approval requested",
        "sender@example.test",
        "from@example.test",
        ("to-1@example.test", "to-2@example.test"),
        ("cc@example.test",),
        ("bcc@example.test",),
        "high",
        ("Finance", "Approvals"),
        True,
        "Preview text",
    )
    actual = (
        observation.message_id,
        observation.run_id,
        observation.evidence_id,
        observation.observation_kind,
        observation.last_modified_date_time,
        observation.subject,
        observation.sender_address,
        observation.from_address,
        observation.to_addresses,
        observation.cc_addresses,
        observation.bcc_addresses,
        observation.importance,
        observation.categories,
        observation.has_attachments,
        observation.body_preview,
    )
    if actual != expected:
        pytest.fail(f"Rule observation projection changed: {actual!r}")
    if hasattr(observation, "raw"):
        pytest.fail("Rule observation must not retain the provider raw payload")


def test_final_evaluation_requires_profile_and_terminal_outcome() -> None:
    with pytest.raises(ValueError):
        MailRuleEvaluation(
            state=MailRuleEvaluationState.FINAL,
            selected_profile=None,
            outcome=MailRuleDecisionOutcome.MATCHED,
        )
    with pytest.raises(ValueError):
        MailRuleEvaluation(
            state=MailRuleEvaluationState.FINAL,
            selected_profile="outlook-mail-full-v1",
            outcome=None,
        )
    with pytest.raises(ValueError):
        MailRuleEvaluation(
            state=MailRuleEvaluationState.FINAL,
            selected_profile="outlook-mail-full-v1",
            outcome=MailRuleDecisionOutcome.UNRESOLVED,
        )


def test_needs_data_requires_body_and_has_no_terminal_profile() -> None:
    evaluation = MailRuleEvaluation(
        state=MailRuleEvaluationState.NEEDS_DATA,
        required_data=MailRuleRequiredData.BODY,
    )
    if evaluation.required_data is not MailRuleRequiredData.BODY:
        pytest.fail("NEEDS_DATA must retain the required body-data token")

    with pytest.raises(ValueError):
        MailRuleEvaluation(state=MailRuleEvaluationState.NEEDS_DATA)
    with pytest.raises(ValueError):
        MailRuleEvaluation(
            state=MailRuleEvaluationState.NEEDS_DATA,
            required_data=MailRuleRequiredData.BODY,
            selected_profile="outlook-mail-full-v1",
        )


def test_unresolved_requires_profile_reason_and_fallback() -> None:
    evaluation = MailRuleEvaluation(
        state=MailRuleEvaluationState.UNRESOLVED,
        selected_profile="outlook-mail-full-v1",
        outcome=MailRuleDecisionOutcome.UNRESOLVED,
        fallback_used=True,
        reason_code="probe_request_failed",
    )
    if evaluation.fallback_used is not True:
        pytest.fail("UNRESOLVED must explicitly retain fail-safe fallback use")

    with pytest.raises(ValueError):
        MailRuleEvaluation(
            state=MailRuleEvaluationState.UNRESOLVED,
            selected_profile="outlook-mail-full-v1",
            outcome=MailRuleDecisionOutcome.UNRESOLVED,
            fallback_used=False,
            reason_code="probe_request_failed",
        )
    with pytest.raises(ValueError):
        MailRuleEvaluation(
            state=MailRuleEvaluationState.UNRESOLVED,
            selected_profile="outlook-mail-full-v1",
            outcome=MailRuleDecisionOutcome.UNRESOLVED,
            fallback_used=True,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("ruleset_id", "rule\nforged"),
        ("ruleset_id", "rule with spaces"),
        ("matched_rule_ids", ("rule\nforged",)),
        ("matched_rule_ids", ("rule with spaces",)),
    ],
)
def test_rule_correlation_tokens_reject_log_injection_characters(
    field: str,
    value: str | tuple[str, ...],
) -> None:
    kwargs: dict[str, object] = {
        "state": MailRuleEvaluationState.FINAL,
        "selected_profile": "outlook-mail-full-v1",
        "outcome": MailRuleDecisionOutcome.MATCHED,
        field: value,
    }
    with pytest.raises(ValueError):
        MailRuleEvaluation(**cast(Any, kwargs))


def test_stop_rule_must_be_one_of_the_matched_rules() -> None:
    with pytest.raises(ValueError):
        MailRuleEvaluation(
            state=MailRuleEvaluationState.FINAL,
            selected_profile="outlook-mail-full-v1",
            outcome=MailRuleDecisionOutcome.MATCHED,
            matched_rule_ids=("r1",),
            stop_rule_id="r2",
        )


def test_probe_status_values_are_stable() -> None:
    if MailRuleProbeStatus.COMPLETE.value != "complete":
        pytest.fail("Probe COMPLETE value changed")
    if MailRuleProbeStatus.FAILED.value != "failed":
        pytest.fail("Probe FAILED value changed")
