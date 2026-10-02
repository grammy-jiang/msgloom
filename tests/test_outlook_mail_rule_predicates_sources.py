"""Probe-backed Outlook Mail predicate source classification tests."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from message_ingest.acquisition.microsoft.outlook.email.rule_config import (
    MailRulePredicates,
)
from message_ingest.acquisition.microsoft.outlook.email.rule_evaluation import (
    MailRuleFact,
    MailRuleFacts,
    MailRuleRequiredData,
)
from message_ingest.acquisition.microsoft.outlook.email.rule_regex import (
    MailRegexEngine,
)


def _module():
    from message_ingest.acquisition.microsoft.outlook.email import rule_predicates

    return rule_predicates


def _evaluate(raw: Mapping[str, object]):
    predicates = MailRulePredicates.model_validate(dict(raw))
    return _module().evaluate_predicate_block(
        predicates,
        MailRuleFacts(
            subject="Urgent Approval",
            available_facts=frozenset({MailRuleFact.SUBJECT}),
        ),
        regex_engine=MailRegexEngine(),
    )


@pytest.mark.parametrize(
    ("field", "required"),
    (
        ("body_contains", MailRuleRequiredData.BODY),
        ("body_regex", MailRuleRequiredData.BODY),
        ("body_or_subject_contains", MailRuleRequiredData.BODY),
        ("body_or_subject_regex", MailRuleRequiredData.BODY),
        ("header_contains", MailRuleRequiredData.HEADERS),
        ("header_regex", MailRuleRequiredData.HEADERS),
        ("sensitivity", MailRuleRequiredData.EXTENDED_PROPERTIES),
        ("message_size_min_kb", MailRuleRequiredData.EXTENDED_PROPERTIES),
        ("message_size_max_kb", MailRuleRequiredData.EXTENDED_PROPERTIES),
        ("item_class_exact", MailRuleRequiredData.EXTENDED_PROPERTIES),
        ("item_class_contains", MailRuleRequiredData.EXTENDED_PROPERTIES),
        ("item_class_regex", MailRuleRequiredData.EXTENDED_PROPERTIES),
        ("is_meeting_request", MailRuleRequiredData.EXTENDED_PROPERTIES),
        ("is_meeting_response", MailRuleRequiredData.EXTENDED_PROPERTIES),
        ("is_non_delivery_report", MailRuleRequiredData.EXTENDED_PROPERTIES),
        ("is_read_receipt", MailRuleRequiredData.EXTENDED_PROPERTIES),
    ),
)
def test_probe_backed_fields_are_unknown_with_required_group_in_task7(
    field: str,
    required: MailRuleRequiredData,
) -> None:
    value: object
    if field in {
        "message_size_min_kb",
        "message_size_max_kb",
    }:
        value = 1
    elif field.startswith("is_"):
        value = True
    elif field == "sensitivity":
        value = ["private"]
    else:
        value = ["value"]

    result = _evaluate({field: value})

    if result.truth is not _module().MailTruth.UNKNOWN:
        pytest.fail(f"Probe-backed field was prematurely evaluated: {field}")
    if result.required_data != frozenset({required}):
        pytest.fail(f"Probe-backed field used wrong required-data group: {field}")
