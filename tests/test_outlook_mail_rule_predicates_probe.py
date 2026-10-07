"""Probe-backed Outlook Mail predicate evaluation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

import pytest

from message_ingest.acquisition.microsoft.outlook.email.rule_config import (
    MailRulePredicates,
)
from message_ingest.acquisition.microsoft.outlook.email.rule_evaluation import (
    MailRuleFact,
    MailRuleFacts,
    MailRuleRequiredData,
)
from message_ingest.acquisition.microsoft.outlook.email.rule_predicates import (
    MailTruth,
    evaluate_predicate_block,
)
from message_ingest.acquisition.microsoft.outlook.email.rule_regex import (
    MailRegexEngine,
)


def _facts(**overrides: object) -> MailRuleFacts:
    values: dict[str, object] = {
        "subject": "Urgent Approval",
        "body": "Invoice approval body",
        "headers": (
            "X-Workflow: Finance",
            "Message-ID: <example@example.test>",
        ),
        "sensitivity": "private",
        "message_size_bytes": 2048,
        "item_class": "IPM.Note",
        "importance": "high",
        "available_facts": frozenset(
            {
                MailRuleFact.SUBJECT,
                MailRuleFact.BODY,
                MailRuleFact.HEADERS,
                MailRuleFact.SENSITIVITY,
                MailRuleFact.MESSAGE_SIZE_BYTES,
                MailRuleFact.ITEM_CLASS,
                MailRuleFact.IMPORTANCE,
            }
        ),
    }
    values.update(overrides)
    return MailRuleFacts(**cast(Any, values))


def _evaluate(
    raw: Mapping[str, object],
    facts: MailRuleFacts | None = None,
):
    return evaluate_predicate_block(
        MailRulePredicates.model_validate(dict(raw)),
        facts or _facts(),
        regex_engine=MailRegexEngine(),
    )


def _without(
    fact: MailRuleFact,
    *,
    source_field: str,
    source_value: object = None,
) -> MailRuleFacts:
    base = _facts()
    return _facts(
        **{
            source_field: source_value,
            "available_facts": base.available_facts - {fact},
        }
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    (
        ({"body_contains": ["APPROVAL BODY"]}, MailTruth.TRUE),
        ({"body_contains": ["missing"]}, MailTruth.FALSE),
        ({"body_regex": [r"invoice\s+approval"]}, MailTruth.TRUE),
        ({"body_regex": [r"^approval"]}, MailTruth.FALSE),
        ({"header_contains": ["workflow: finance"]}, MailTruth.TRUE),
        ({"header_contains": ["missing"]}, MailTruth.FALSE),
        ({"header_regex": [r"message-id:.*example"]}, MailTruth.TRUE),
        ({"sensitivity": ["PRIVATE"]}, MailTruth.TRUE),
        ({"sensitivity": ["normal"]}, MailTruth.FALSE),
        ({"item_class_exact": ["ipm.note"]}, MailTruth.TRUE),
        ({"item_class_exact": ["IPM.Note.Custom"]}, MailTruth.FALSE),
        ({"item_class_contains": [".NOTE"]}, MailTruth.TRUE),
        ({"item_class_regex": [r"^ipm.note$"]}, MailTruth.TRUE),
    ),
)
def test_probe_backed_text_predicates(
    raw: dict[str, object], expected: MailTruth
) -> None:
    result = _evaluate(raw)

    if result.truth is not expected:
        pytest.fail(f"Probe-backed text predicate changed: {raw!r} -> {result!r}")
    if result.required_data or result.reason_codes:
        pytest.fail("Available probe facts retained unresolved state")


@pytest.mark.parametrize(
    ("raw", "expected"),
    (
        ({"message_size_min_kb": 2}, MailTruth.TRUE),
        ({"message_size_min_kb": 3}, MailTruth.FALSE),
        ({"message_size_max_kb": 2}, MailTruth.TRUE),
        ({"message_size_max_kb": 1}, MailTruth.FALSE),
        (
            {"message_size_min_kb": 2, "message_size_max_kb": 2},
            MailTruth.TRUE,
        ),
    ),
)
def test_message_size_kib_boundaries_are_exact(
    raw: dict[str, object], expected: MailTruth
) -> None:
    result = _evaluate(raw)

    if result.truth is not expected:
        pytest.fail(f"Message size KiB boundary changed: {raw!r} -> {result!r}")


@pytest.mark.parametrize(
    ("item_class", "field", "expected"),
    (
        ("IPM.Schedule.Meeting.Request", "is_meeting_request", True),
        ("IPM.Schedule.Meeting.Resp.Pos", "is_meeting_response", True),
        ("IPM.Schedule.Meeting.Resp.Tent", "is_meeting_response", True),
        ("IPM.Schedule.Meeting.Resp.Neg", "is_meeting_response", True),
        ("IPM.Schedule.Meeting.Canceled", "is_meeting_request", False),
        ("IPM.Schedule.Meeting.Canceled", "is_meeting_response", False),
        ("REPORT.IPM.Note.NDR", "is_non_delivery_report", True),
        ("report.custom.ndr", "is_non_delivery_report", True),
        ("REPORT.IPM.Note.IPNRN", "is_read_receipt", True),
        ("IPM.Note.Receipt.SMIME", "is_read_receipt", True),
        ("REPORT.IPM.Note.DR", "is_non_delivery_report", False),
        ("IPM.Note", "is_read_receipt", False),
    ),
)
def test_special_message_predicates_use_exact_message_class_contract(
    item_class: str,
    field: str,
    expected: bool,
) -> None:
    result = _evaluate({field: True}, _facts(item_class=item_class))

    wanted = MailTruth.TRUE if expected else MailTruth.FALSE
    if result.truth is not wanted:
        pytest.fail(f"Special-message class mapping changed: {item_class} / {field}")


@pytest.mark.parametrize(
    ("fact", "source_field", "raw", "required"),
    (
        (
            MailRuleFact.BODY,
            "body",
            {"body_contains": ["approval"]},
            MailRuleRequiredData.BODY,
        ),
        (
            MailRuleFact.HEADERS,
            "headers",
            {"header_contains": ["workflow"]},
            MailRuleRequiredData.HEADERS,
        ),
        (
            MailRuleFact.SENSITIVITY,
            "sensitivity",
            {"sensitivity": ["private"]},
            MailRuleRequiredData.EXTENDED_PROPERTIES,
        ),
        (
            MailRuleFact.MESSAGE_SIZE_BYTES,
            "message_size_bytes",
            {"message_size_min_kb": 1},
            MailRuleRequiredData.EXTENDED_PROPERTIES,
        ),
        (
            MailRuleFact.ITEM_CLASS,
            "item_class",
            {"item_class_exact": ["IPM.Note"]},
            MailRuleRequiredData.EXTENDED_PROPERTIES,
        ),
        (
            MailRuleFact.ITEM_CLASS,
            "item_class",
            {"is_meeting_request": True},
            MailRuleRequiredData.EXTENDED_PROPERTIES,
        ),
    ),
)
def test_missing_probe_fact_requests_exact_required_group(
    fact: MailRuleFact,
    source_field: str,
    raw: dict[str, object],
    required: MailRuleRequiredData,
) -> None:
    result = _evaluate(raw, _without(fact, source_field=source_field))

    if result.truth is not MailTruth.UNKNOWN:
        pytest.fail(f"Unavailable probe fact did not remain UNKNOWN: {raw!r}")
    if result.required_data != frozenset({required}):
        pytest.fail(f"Unavailable probe fact requested wrong group: {result!r}")


def test_body_or_subject_literal_short_circuits_body_when_subject_matches() -> None:
    facts = _without(MailRuleFact.BODY, source_field="body")

    result = _evaluate({"body_or_subject_contains": ["urgent"]}, facts)

    if result.truth is not MailTruth.TRUE:
        pytest.fail("Subject TRUE did not satisfy body-or-subject literal predicate")
    if result.required_data:
        pytest.fail("Subject TRUE unnecessarily requested BODY")


def test_body_or_subject_regex_short_circuits_body_when_subject_matches() -> None:
    facts = _without(MailRuleFact.BODY, source_field="body")

    result = _evaluate({"body_or_subject_regex": [r"^urgent"]}, facts)

    if result.truth is not MailTruth.TRUE:
        pytest.fail("Subject regex TRUE did not satisfy body-or-subject predicate")
    if result.required_data:
        pytest.fail("Subject regex TRUE unnecessarily requested BODY")


def test_body_or_subject_subject_false_and_body_missing_requests_body() -> None:
    facts = _without(MailRuleFact.BODY, source_field="body")

    result = _evaluate({"body_or_subject_contains": ["invoice"]}, facts)

    if result.truth is not MailTruth.UNKNOWN:
        pytest.fail("Missing BODY did not keep body-or-subject predicate UNKNOWN")
    if result.required_data != frozenset({MailRuleRequiredData.BODY}):
        pytest.fail("Body-or-subject miss requested wrong fact group")


def test_body_or_subject_body_true_dominates_unavailable_subject() -> None:
    base = _facts()
    facts = _facts(
        subject=None,
        available_facts=base.available_facts - {MailRuleFact.SUBJECT},
    )

    result = _evaluate({"body_or_subject_contains": ["invoice"]}, facts)

    if result.truth is not MailTruth.TRUE:
        pytest.fail("BODY TRUE did not dominate unavailable subject")
    if result.required_data or result.reason_codes:
        pytest.fail("BODY TRUE retained irrelevant subject UNKNOWN")


def test_body_or_subject_no_true_with_unavailable_subject_remains_unknown() -> None:
    base = _facts()
    facts = _facts(
        subject=None,
        body="ordinary body",
        available_facts=base.available_facts - {MailRuleFact.SUBJECT},
    )

    result = _evaluate({"body_or_subject_contains": ["missing"]}, facts)

    if result.truth is not MailTruth.UNKNOWN:
        pytest.fail("Unavailable subject was incorrectly treated as FALSE")
    if result.required_data != frozenset({MailRuleRequiredData.METADATA}):
        pytest.fail("Unavailable subject did not request METADATA")


def test_body_preview_never_proves_body_truth() -> None:
    base = _facts()
    facts = _facts(
        body=None,
        body_preview="PRIVATE APPROVAL preview",
        available_facts=(base.available_facts - {MailRuleFact.BODY})
        | {MailRuleFact.BODY_PREVIEW},
    )

    result = _evaluate({"body_contains": ["approval"]}, facts)

    if result.truth is not MailTruth.UNKNOWN:
        pytest.fail("bodyPreview incorrectly proved BODY truth")
    if result.required_data != frozenset({MailRuleRequiredData.BODY}):
        pytest.fail("bodyPreview incorrectly eliminated BODY acquisition")


def test_false_metadata_field_dominates_missing_body_without_probe_requirement() -> (
    None
):
    facts = _without(MailRuleFact.BODY, source_field="body")

    result = _evaluate(
        {
            "body_contains": ["approval"],
            "importance": ["low"],
        },
        facts,
    )

    if result.truth is not MailTruth.FALSE:
        pytest.fail("Cheap metadata FALSE did not dominate missing BODY")
    if result.required_data or result.reason_codes:
        pytest.fail("False block retained unnecessary BODY requirement")


@pytest.mark.parametrize(
    ("body", "raw", "expected"),
    (
        (None, {"body_contains": ["x"]}, MailTruth.FALSE),
        (None, {"body_regex": ["x"]}, MailTruth.FALSE),
    ),
)
def test_known_null_body_is_false_not_unknown(
    body: str | None,
    raw: dict[str, object],
    expected: MailTruth,
) -> None:
    facts = _facts(body=body)

    result = _evaluate(raw, facts)

    if result.truth is not expected:
        pytest.fail("Known-null BODY was not treated as a known non-match")


def test_known_empty_headers_are_false_not_unknown() -> None:
    facts = _facts(headers=())

    result = _evaluate({"header_contains": ["x"]}, facts)

    if result.truth is not MailTruth.FALSE:
        pytest.fail("Known-empty headers were not a known FALSE")


def test_known_null_extended_scalar_is_false_not_unknown() -> None:
    for field, raw in (
        ("sensitivity", {"sensitivity": ["private"]}),
        ("message_size_bytes", {"message_size_min_kb": 1}),
        ("item_class", {"item_class_exact": ["IPM.Note"]}),
    ):
        facts = _facts(**{field: None})
        result = _evaluate(raw, facts)
        if result.truth is not MailTruth.FALSE:
            pytest.fail(f"Known-null {field} did not become FALSE")
