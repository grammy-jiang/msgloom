"""Contracts for deterministic Outlook Mail acquisition-rule facts."""

from __future__ import annotations

from typing import Any, cast

import pytest

from message_ingest.acquisition.microsoft.outlook.email.rule_evaluation import (
    MailRecipientFact,
    MailRuleDecisionOutcome,
    MailRuleEvaluation,
    MailRuleEvaluationState,
    MailRuleFact,
    MailRuleProbeStatus,
    MailRuleRequiredData,
    mail_rule_observation_from_item,
)
from message_ingest.items.microsoft.outlook.email import OutlookMailItem


def _item(raw: dict[str, Any] | None = None) -> OutlookMailItem:
    resource: dict[str, Any] = {
        "id": "message-1",
        "changeKey": "change-1",
        "subject": "Approval requested",
        "sender": {
            "emailAddress": {
                "name": "Actual Sender",
                "address": "sender@example.test",
            }
        },
        "from": {
            "emailAddress": {
                "name": "From Display",
                "address": "from@example.test",
            }
        },
        "toRecipients": [
            {"emailAddress": {"name": "To One", "address": "to-1@example.test"}},
            {"emailAddress": {"name": "To Two", "address": "to-2@example.test"}},
        ],
        "ccRecipients": [
            {"emailAddress": {"name": "Cc One", "address": "cc@example.test"}}
        ],
        "bccRecipients": [
            {"emailAddress": {"name": "Bcc One", "address": "bcc@example.test"}}
        ],
        "replyTo": [
            {"emailAddress": {"name": "Reply One", "address": "reply@example.test"}}
        ],
        "receivedDateTime": "2026-09-30T01:00:00Z",
        "sentDateTime": "2026-09-30T00:59:00Z",
        "createdDateTime": "2026-09-30T00:58:00Z",
        "lastModifiedDateTime": "2026-09-30T01:02:03Z",
        "importance": "high",
        "categories": ["Finance", "Approvals"],
        "hasAttachments": True,
        "isRead": False,
        "isDraft": False,
        "inferenceClassification": "focused",
        "flag": {"flagStatus": "flagged"},
        "bodyPreview": "Preview text",
    }
    if raw is not None:
        resource = raw
    return OutlookMailItem.from_graph(
        resource,
        source_response_url="https://graph.example.test/messages",
        observed_at="2026-09-30T01:02:04Z",
        observation_kind="delta",
        evidence_id="evidence-1",
        run_id="run-1",
    )


def test_rule_observation_projects_bounded_facts_without_retaining_raw() -> None:
    observation = mail_rule_observation_from_item(_item())
    facts = observation.facts

    if (
        observation.message_id,
        observation.run_id,
        observation.evidence_id,
        observation.observation_kind,
    ) != ("message-1", "run-1", "evidence-1", "delta"):
        pytest.fail("Rule observation correlation fields changed")
    if facts.change_key != "change-1":
        pytest.fail("Rule observation lost changeKey")
    if facts.subject != "Approval requested":
        pytest.fail("Rule observation lost subject")
    if facts.sender_recipient != MailRecipientFact(
        name="Actual Sender", address="sender@example.test"
    ):
        pytest.fail("Rule observation lost Sender recipient")
    if facts.from_recipient != MailRecipientFact(
        name="From Display", address="from@example.test"
    ):
        pytest.fail("Rule observation lost From recipient")
    if facts.to_recipients[0].name != "To One":
        pytest.fail("Rule observation lost recipient display names")
    if facts.reply_to_recipients[0].address != "reply@example.test":
        pytest.fail("Rule observation lost Reply-To facts")
    if facts.followup_status != "flagged":
        pytest.fail("Rule observation lost follow-up status")
    if MailRuleFact.BODY in facts.available_facts:
        pytest.fail("Discovery observation must not claim complete BODY availability")
    if MailRuleFact.ITEM_CLASS in facts.available_facts:
        pytest.fail("Discovery observation must not claim probed extended properties")
    if hasattr(observation, "raw"):
        pytest.fail("Rule observation must not retain the provider raw payload")


def test_known_empty_categories_and_recipients_remain_available() -> None:
    item = _item(
        {
            "id": "message-1",
            "changeKey": "change-1",
            "categories": [],
            "toRecipients": [],
        }
    )

    facts = mail_rule_observation_from_item(item).facts

    if facts.categories != () or MailRuleFact.CATEGORIES not in facts.available_facts:
        pytest.fail("Present empty categories must be known-empty, not unavailable")
    if (
        facts.to_recipients != ()
        or MailRuleFact.TO_RECIPIENTS not in facts.available_facts
    ):
        pytest.fail("Present empty recipients must be known-empty, not unavailable")


def test_absent_categories_and_recipients_are_unavailable() -> None:
    facts = mail_rule_observation_from_item(
        _item({"id": "message-1", "changeKey": "change-1"})
    ).facts

    if MailRuleFact.CATEGORIES in facts.available_facts:
        pytest.fail("Absent categories must be unavailable")
    if MailRuleFact.TO_RECIPIENTS in facts.available_facts:
        pytest.fail("Absent recipients must be unavailable")


def test_malformed_recipient_list_is_unavailable() -> None:
    facts = mail_rule_observation_from_item(
        _item(
            {
                "id": "message-1",
                "changeKey": "change-1",
                "toRecipients": [{"emailAddress": "not-an-object"}],
            }
        )
    ).facts

    if MailRuleFact.TO_RECIPIENTS in facts.available_facts:
        pytest.fail("Malformed recipient representation must be unavailable")
    if facts.to_recipients:
        pytest.fail("Malformed recipient representation must not retain partial values")


def test_explicit_null_from_and_subject_are_known_values() -> None:
    facts = mail_rule_observation_from_item(
        _item(
            {
                "id": "message-1",
                "changeKey": "change-1",
                "from": None,
                "subject": None,
            }
        )
    ).facts

    if (
        facts.from_recipient is not None
        or MailRuleFact.FROM_RECIPIENT not in facts.available_facts
    ):
        pytest.fail("Explicit null From must be known nullable")
    if facts.subject is not None or MailRuleFact.SUBJECT not in facts.available_facts:
        pytest.fail("Explicit null subject must be known nullable")


def test_absent_or_malformed_from_and_subject_are_unavailable() -> None:
    absent = mail_rule_observation_from_item(
        _item({"id": "message-1", "changeKey": "change-1"})
    ).facts
    malformed_item = _item(
        {
            "id": "message-1",
            "changeKey": "change-1",
            "from": {"emailAddress": {"address": "valid@example.test"}},
            "subject": "valid",
        }
    )
    malformed_item.raw["from"] = {"emailAddress": "invalid"}
    malformed_item.raw["subject"] = 123
    malformed = mail_rule_observation_from_item(malformed_item).facts

    for facts in (absent, malformed):
        if MailRuleFact.FROM_RECIPIENT in facts.available_facts:
            pytest.fail("Absent/malformed From must be unavailable")
        if MailRuleFact.SUBJECT in facts.available_facts:
            pytest.fail("Absent/malformed subject must be unavailable")


def test_recipient_aggregate_over_256_is_unavailable_without_retention() -> None:
    recipients = [
        {"emailAddress": {"name": f"n{i}", "address": f"a{i}@example.test"}}
        for i in range(257)
    ]
    facts = mail_rule_observation_from_item(
        _item(
            {
                "id": "message-1",
                "changeKey": "change-1",
                "toRecipients": recipients,
                "ccRecipients": [],
                "bccRecipients": [],
                "replyTo": [],
            }
        )
    ).facts

    for fact in (
        MailRuleFact.TO_RECIPIENTS,
        MailRuleFact.CC_RECIPIENTS,
        MailRuleFact.BCC_RECIPIENTS,
        MailRuleFact.REPLY_TO_RECIPIENTS,
    ):
        if fact in facts.available_facts:
            pytest.fail("Oversized recipient aggregate must be unavailable")
    if (
        facts.to_recipients
        or facts.cc_recipients
        or facts.bcc_recipients
        or facts.reply_to_recipients
    ):
        pytest.fail("Oversized recipient aggregate must not retain truncated data")


@pytest.mark.parametrize(
    ("field", "value", "fact"),
    (
        ("subject", "s" * 16_385, MailRuleFact.SUBJECT),
        ("bodyPreview", "p" * 1_025, MailRuleFact.BODY_PREVIEW),
        ("categories", ["c" * 1_025], MailRuleFact.CATEGORIES),
        ("changeKey", "k" * 2_049, MailRuleFact.CHANGE_KEY),
    ),
)
def test_oversized_discovery_fact_becomes_unavailable_without_truncation(
    field: str,
    value: object,
    fact: MailRuleFact,
) -> None:
    facts = mail_rule_observation_from_item(
        _item({"id": "message-1", field: value})
    ).facts

    if fact in facts.available_facts:
        pytest.fail(f"Oversized {field} must be unavailable")
    retained = {
        MailRuleFact.SUBJECT: facts.subject,
        MailRuleFact.BODY_PREVIEW: facts.body_preview,
        MailRuleFact.CATEGORIES: facts.categories,
        MailRuleFact.CHANGE_KEY: facts.change_key,
    }[fact]
    if retained not in (None, ()):
        pytest.fail(f"Oversized {field} retained truncated source data")


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


def test_needs_data_requires_nonempty_immutable_set_and_no_terminal_profile() -> None:
    required = frozenset({MailRuleRequiredData.BODY})
    evaluation = MailRuleEvaluation(
        state=MailRuleEvaluationState.NEEDS_DATA,
        required_data=required,
    )
    if evaluation.required_data != required:
        pytest.fail("NEEDS_DATA did not retain its immutable required-data set")

    with pytest.raises(ValueError):
        MailRuleEvaluation(
            state=MailRuleEvaluationState.NEEDS_DATA,
            required_data=frozenset(),
        )
    with pytest.raises(ValueError):
        MailRuleEvaluation(
            state=MailRuleEvaluationState.NEEDS_DATA,
            required_data=required,
            selected_profile="outlook-mail-full-v1",
        )


def test_terminal_evaluations_carry_no_pending_required_data() -> None:
    with pytest.raises(ValueError):
        MailRuleEvaluation(
            state=MailRuleEvaluationState.FINAL,
            selected_profile="outlook-mail-full-v1",
            outcome=MailRuleDecisionOutcome.MATCHED,
            required_data=frozenset({MailRuleRequiredData.BODY}),
        )
    with pytest.raises(ValueError):
        MailRuleEvaluation(
            state=MailRuleEvaluationState.UNRESOLVED,
            selected_profile="outlook-mail-full-v1",
            outcome=MailRuleDecisionOutcome.UNRESOLVED,
            fallback_used=True,
            reason_code="probe_request_failed",
            required_data=frozenset({MailRuleRequiredData.BODY}),
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
    if MailRuleProbeStatus.PARTIAL.value != "partial":
        pytest.fail("Probe PARTIAL value changed")
    if MailRuleProbeStatus.FAILED.value != "failed":
        pytest.fail("Probe FAILED value changed")


def test_required_data_values_are_stable() -> None:
    if {value.value for value in MailRuleRequiredData} != {
        "metadata",
        "body",
        "headers",
        "extended_properties",
    }:
        pytest.fail("Mail required-data vocabulary drifted")
