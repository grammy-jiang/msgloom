"""Pure tri-state metadata predicate evaluation for Outlook Mail rules."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

import pytest

from message_ingest.acquisition.microsoft.outlook.email.rule_config import (
    MailRulePredicates,
)
from message_ingest.acquisition.microsoft.outlook.email.rule_evaluation import (
    MailRecipientFact,
    MailRuleFact,
    MailRuleFacts,
    MailRuleRequiredData,
)
from message_ingest.acquisition.microsoft.outlook.email.rule_regex import (
    MailRegexEngine,
    MailRegexEvaluationError,
)


def _module():
    from message_ingest.acquisition.microsoft.outlook.email import rule_predicates

    return rule_predicates


def _facts(**overrides: object) -> MailRuleFacts:
    values: dict[str, object] = {
        "subject": "Urgent Approval",
        "from_recipient": MailRecipientFact(
            name="Manager One",
            address="Manager@Example.COM",
        ),
        "sender_recipient": MailRecipientFact(
            name="Delegate Sender",
            address="delegate@example.com",
        ),
        "to_recipients": (
            MailRecipientFact(name="Primary User", address="user@example.com"),
        ),
        "cc_recipients": (
            MailRecipientFact(name="Finance Team", address="finance@example.com"),
        ),
        "bcc_recipients": (
            MailRecipientFact(name="Hidden Person", address="hidden@example.com"),
        ),
        "reply_to_recipients": (
            MailRecipientFact(name="Replies", address="reply@example.com"),
        ),
        "received_date_time": "2026-01-01T00:00:00Z",
        "sent_date_time": "2025-12-31T23:59:00Z",
        "created_date_time": "2025-12-31T23:58:00Z",
        "importance": "high",
        "categories": ("Finance", "Approval"),
        "has_attachments": True,
        "is_read": False,
        "is_draft": False,
        "inference_classification": "focused",
        "followup_status": "flagged",
        "available_facts": frozenset(
            {
                MailRuleFact.SUBJECT,
                MailRuleFact.FROM_RECIPIENT,
                MailRuleFact.SENDER_RECIPIENT,
                MailRuleFact.TO_RECIPIENTS,
                MailRuleFact.CC_RECIPIENTS,
                MailRuleFact.BCC_RECIPIENTS,
                MailRuleFact.REPLY_TO_RECIPIENTS,
                MailRuleFact.RECEIVED_DATE_TIME,
                MailRuleFact.SENT_DATE_TIME,
                MailRuleFact.CREATED_DATE_TIME,
                MailRuleFact.IMPORTANCE,
                MailRuleFact.CATEGORIES,
                MailRuleFact.HAS_ATTACHMENTS,
                MailRuleFact.IS_READ,
                MailRuleFact.IS_DRAFT,
                MailRuleFact.INFERENCE_CLASSIFICATION,
                MailRuleFact.FOLLOWUP_STATUS,
            }
        ),
    }
    values.update(overrides)
    return MailRuleFacts(**cast(Any, values))


def _evaluate(
    raw: Mapping[str, object],
    facts: MailRuleFacts | None = None,
    *,
    engine: MailRegexEngine | None = None,
):
    predicates = MailRulePredicates.model_validate(dict(raw))
    return _module().evaluate_predicate_block(
        predicates,
        facts or _facts(),
        regex_engine=engine or MailRegexEngine(),
    )


def test_different_fields_are_and_and_values_within_field_are_or() -> None:
    result = _evaluate(
        {
            "subject_contains": ["missing", "approval"],
            "importance": ["normal", "HIGH"],
            "categories": ["not-this", "finance"],
        }
    )

    if result.truth is not _module().MailTruth.TRUE:
        pytest.fail(f"AND/OR predicate composition changed: {result!r}")


def test_false_field_dominates_other_true_fields() -> None:
    result = _evaluate(
        {
            "subject_contains": ["approval"],
            "importance": ["low"],
            "categories": ["finance"],
        }
    )

    if result.truth is not _module().MailTruth.FALSE:
        pytest.fail("One false field must make an AND block false")
    if result.required_data or result.reason_codes:
        pytest.fail("Terminal false block retained irrelevant unknown state")


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("subject_exact", ["URGENT APPROVAL"]),
        ("subject_contains", ["APPROVAL"]),
        ("categories", ["FINANCE"]),
        ("importance", ["HIGH"]),
        ("inference_classification", ["FOCUSED"]),
        ("followup_status", ["FLAGGED"]),
    ),
)
def test_literal_metadata_matching_is_case_insensitive(
    field: str, value: object
) -> None:
    result = _evaluate({field: value})

    if result.truth is not _module().MailTruth.TRUE:
        pytest.fail(f"Case-insensitive metadata predicate failed: {field}")


def test_subject_exact_differs_from_contains() -> None:
    exact = _evaluate({"subject_exact": ["approval"]})
    contains = _evaluate({"subject_contains": ["approval"]})

    if exact.truth is not _module().MailTruth.FALSE:
        pytest.fail("subject_exact unexpectedly used substring semantics")
    if contains.truth is not _module().MailTruth.TRUE:
        pytest.fail("subject_contains lost substring semantics")


def test_from_outlook_contains_searches_name_or_address() -> None:
    name = _evaluate({"from_contains": ["manager one"]})
    address = _evaluate({"from_contains": ["@example.com"]})

    if name.truth is not _module().MailTruth.TRUE:
        pytest.fail("Outlook from_contains did not search display name")
    if address.truth is not _module().MailTruth.TRUE:
        pytest.fail("Outlook from_contains did not search address")


def test_from_exact_address_and_address_only_contains_are_distinct() -> None:
    exact = _evaluate({"from_addresses": ["manager@example.com"]})
    contains = _evaluate({"from_address_contains": ["MANAGER@"]})
    display_only = _evaluate({"from_address_contains": ["manager one"]})

    if exact.truth is not _module().MailTruth.TRUE:
        pytest.fail("From exact address lost case-insensitive equality")
    if contains.truth is not _module().MailTruth.TRUE:
        pytest.fail("From address-only contains failed")
    if display_only.truth is not _module().MailTruth.FALSE:
        pytest.fail("Address-only predicate unexpectedly searched display name")


def test_sender_predicates_use_actual_sender_not_from() -> None:
    sender = _evaluate({"sender_addresses": ["delegate@example.com"]})
    wrong_from = _evaluate({"sender_addresses": ["manager@example.com"]})
    name = _evaluate({"sender_contains": ["delegate sender"]})

    if sender.truth is not _module().MailTruth.TRUE:
        pytest.fail("Actual Sender exact predicate failed")
    if wrong_from.truth is not _module().MailTruth.FALSE:
        pytest.fail("Sender predicate incorrectly used From")
    if name.truth is not _module().MailTruth.TRUE:
        pytest.fail("Sender name-or-address contains failed")


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("to_addresses", ["USER@EXAMPLE.COM"]),
        ("to_address_contains", ["user@"]),
        ("cc_addresses", ["finance@example.com"]),
        ("cc_address_contains", ["FINANCE@"]),
        ("bcc_addresses", ["hidden@example.com"]),
        ("bcc_address_contains", ["HIDDEN@"]),
        ("reply_to_addresses", ["reply@example.com"]),
        ("reply_to_address_contains", ["REPLY@"]),
    ),
)
def test_recipient_address_predicates_match_expected_list(
    field: str, value: object
) -> None:
    if _evaluate({field: value}).truth is not _module().MailTruth.TRUE:
        pytest.fail(f"Recipient address predicate failed: {field}")


def test_recipient_contains_uses_to_and_cc_name_or_address_but_excludes_bcc() -> None:
    to_name = _evaluate({"recipient_contains": ["primary user"]})
    cc_address = _evaluate({"recipient_contains": ["finance@"]})
    hidden_name = _evaluate({"recipient_contains": ["hidden person"]})
    hidden_address = _evaluate({"recipient_address_contains": ["hidden@"]})

    if to_name.truth is not _module().MailTruth.TRUE:
        pytest.fail("recipient_contains lost To display-name semantics")
    if cc_address.truth is not _module().MailTruth.TRUE:
        pytest.fail("recipient_contains lost Cc address semantics")
    if hidden_name.truth is not _module().MailTruth.FALSE:
        pytest.fail("recipient_contains incorrectly included Bcc display name")
    if hidden_address.truth is not _module().MailTruth.FALSE:
        pytest.fail("recipient_address_contains incorrectly included Bcc")


def test_known_empty_collections_are_false_not_unknown() -> None:
    facts = _facts(
        to_recipients=(),
        categories=(),
        available_facts=(
            _facts().available_facts
            | {MailRuleFact.TO_RECIPIENTS, MailRuleFact.CATEGORIES}
        ),
    )

    for raw in (
        {"to_addresses": ["user@example.com"]},
        {"to_address_contains": ["user"]},
        {"to_address_regex": ["user"]},
        {"categories": ["finance"]},
    ):
        result = _evaluate(raw, facts)
        if result.truth is not _module().MailTruth.FALSE:
            pytest.fail(f"Known-empty collection became non-false: {raw!r}")


def test_known_null_scalar_text_is_false_not_unknown() -> None:
    facts = _facts(
        subject=None,
        available_facts=_facts().available_facts | {MailRuleFact.SUBJECT},
    )

    result = _evaluate({"subject_contains": ["approval"]}, facts)

    if result.truth is not _module().MailTruth.FALSE:
        pytest.fail("Known-null subject must make a text predicate false")


def test_unavailable_relevant_metadata_is_unknown_and_requests_metadata() -> None:
    facts = _facts(
        subject=None,
        available_facts=_facts().available_facts - {MailRuleFact.SUBJECT},
    )

    result = _evaluate({"subject_contains": ["approval"]}, facts)

    if result.truth is not _module().MailTruth.UNKNOWN:
        pytest.fail("Unavailable relevant metadata must remain UNKNOWN")
    if result.required_data != frozenset({MailRuleRequiredData.METADATA}):
        pytest.fail("Unavailable metadata did not request the METADATA probe group")


def test_unavailable_metadata_is_irrelevant_when_another_and_field_is_false() -> None:
    facts = _facts(
        subject=None,
        available_facts=_facts().available_facts - {MailRuleFact.SUBJECT},
    )

    result = _evaluate(
        {
            "subject_contains": ["approval"],
            "importance": ["low"],
        },
        facts,
    )

    if result.truth is not _module().MailTruth.FALSE:
        pytest.fail("FALSE field did not dominate unrelated UNKNOWN metadata")
    if result.required_data or result.reason_codes:
        pytest.fail("FALSE block retained an unnecessary provider requirement")


def test_metadata_regex_uses_search_semantics() -> None:
    result = _evaluate({"subject_regex": [r"approval$"]})

    if result.truth is not _module().MailTruth.TRUE:
        pytest.fail("Metadata regex did not use search semantics")


class _ExplodingAlternativeEngine(MailRegexEngine):
    @staticmethod
    def compile(pattern: str):  # type: ignore[override]
        return cast(Any, pattern)

    @staticmethod
    def search(compiled, text: str) -> bool:  # type: ignore[override]
        del text
        if compiled == "explode":
            raise MailRegexEvaluationError
        return compiled == "match"


@pytest.mark.parametrize(
    "patterns",
    (
        ["explode", "match"],
        ["match", "explode"],
    ),
)
def test_regex_runtime_unknown_does_not_mask_true_or_alternative(
    patterns: list[str],
) -> None:
    result = _evaluate(
        {"subject_regex": patterns},
        engine=_ExplodingAlternativeEngine(),
    )

    if result.truth is not _module().MailTruth.TRUE:
        pytest.fail("TRUE regex alternative must dominate runtime UNKNOWN")
    if result.required_data or result.reason_codes:
        pytest.fail("Successful regex OR retained irrelevant runtime failure")


def test_regex_runtime_failure_without_match_is_unknown_not_false() -> None:
    result = _evaluate(
        {"subject_regex": ["explode", "no-match"]},
        engine=_ExplodingAlternativeEngine(),
    )

    if result.truth is not _module().MailTruth.UNKNOWN:
        pytest.fail("Relevant regex runtime failure must remain UNKNOWN")
    if result.required_data:
        pytest.fail("Regex engine failure cannot be repaired by provider metadata")
    if result.reason_codes != ("regex_evaluation_failed",):
        pytest.fail("Regex runtime failure reason changed")


@pytest.mark.parametrize(
    ("field", "source_field", "at_lower", "at_upper"),
    (
        (
            "received",
            "received_date_time",
            "2026-01-01T11:00:00+11:00",
            "2026-01-01T12:00:00+11:00",
        ),
        (
            "sent",
            "sent_date_time",
            "2026-01-01T10:59:00+11:00",
            "2026-01-01T11:00:00+11:00",
        ),
        (
            "created",
            "created_date_time",
            "2026-01-01T10:58:00+11:00",
            "2026-01-01T10:59:00+11:00",
        ),
    ),
)
def test_datetime_ranges_compare_instants_with_inclusive_lower_exclusive_upper(
    field: str,
    source_field: str,
    at_lower: str,
    at_upper: str,
) -> None:
    source = getattr(_facts(), source_field)
    assert source is not None

    lower = _evaluate({f"{field}_after": at_lower})
    upper = _evaluate({f"{field}_before": at_upper})
    exclusive_equal = _evaluate({f"{field}_before": source})

    if lower.truth is not _module().MailTruth.TRUE:
        pytest.fail(f"{field}_after lost inclusive instant comparison")
    if upper.truth is not _module().MailTruth.TRUE:
        pytest.fail(f"{field}_before failed before its upper bound")
    if exclusive_equal.truth is not _module().MailTruth.FALSE:
        pytest.fail(f"{field}_before upper bound must be exclusive")


def test_boolean_metadata_predicates_require_exact_state() -> None:
    result = _evaluate(
        {
            "has_attachments": True,
            "is_read": False,
            "is_draft": False,
        }
    )
    mismatch = _evaluate({"is_read": True})

    if result.truth is not _module().MailTruth.TRUE:
        pytest.fail("Boolean metadata predicates lost exact matching")
    if mismatch.truth is not _module().MailTruth.FALSE:
        pytest.fail("Boolean metadata mismatch did not become FALSE")


def test_followup_provider_not_flagged_maps_to_user_not_flagged_enum() -> None:
    facts = _facts(followup_status="notFlagged")

    result = _evaluate({"followup_status": ["not_flagged"]}, facts)

    if result.truth is not _module().MailTruth.TRUE:
        pytest.fail("Graph notFlagged did not map to user not_flagged semantics")


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
