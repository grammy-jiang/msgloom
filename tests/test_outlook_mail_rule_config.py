"""Closed Outlook Mail rule configuration and policy identity tests."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import cast

import pytest
from pydantic import ValidationError

from msgloom.configuration import ConfigurationError, ConfigurationErrorCode


def _module():
    from message_ingest.acquisition.microsoft.outlook.email import rule_config

    return rule_config


def _rule(
    *,
    rule_id: str = "finance-01",
    sequence: int = 10,
    enabled: bool = True,
    profile: str = "full",
    conditions: Mapping[str, object] | None = None,
    exceptions: Sequence[Mapping[str, object]] | None = None,
    stop_processing: bool = False,
) -> dict[str, object]:
    value: dict[str, object] = {
        "id": rule_id,
        "sequence": sequence,
        "enabled": enabled,
        "profile": profile,
        "stop_processing": stop_processing,
        "conditions": (
            {"subject_contains": ["approval"]}
            if conditions is None
            else dict(conditions)
        ),
    }
    if exceptions is not None:
        value["exceptions"] = [dict(block) for block in exceptions]
    return value


def _policy(
    *,
    enabled: bool = True,
    default_profile: str = "discovery",
    rules: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "enabled": enabled,
        "default_profile": default_profile,
        "rules": [_rule()] if rules is None else rules,
    }


def _parse(raw: dict[str, object] | None, *, source: str | None = "explicit"):
    return _module().parse_mail_rule_policy(raw, source_label=source)


def _diagnostic(error: ConfigurationError):
    if error.diagnostic is None:
        pytest.fail("Mail policy validation did not attach a safe diagnostic")
    return error.diagnostic


def test_absent_section_is_disabled_policy() -> None:
    policy = _parse(None, source=None)

    if policy.enabled:
        pytest.fail("Absent Mail section unexpectedly enabled policy")
    if policy.default_profile.value != "discovery" or policy.rules:
        pytest.fail("Absent Mail section did not produce empty discovery defaults")


def test_enabled_empty_policy_defaults_to_discovery() -> None:
    policy = _parse({"enabled": True})

    if not policy.enabled or policy.default_profile.value != "discovery":
        pytest.fail("Enabled empty policy did not default to discovery")
    if policy.rules:
        pytest.fail("Enabled empty policy fabricated rules")


def test_default_full_maps_to_internal_full_v1() -> None:
    module = _module()
    policy = _parse({"enabled": True, "default_profile": "FULL"})

    if policy.default_profile.value != "full":
        pytest.fail("Profile values are not accepted case-insensitively")
    if module.internal_mail_profile(policy.default_profile) != "outlook-mail-full-v1":
        pytest.fail("User full profile did not map to internal Full-v1")


def test_discovery_profile_maps_to_internal_discovery_v1() -> None:
    module = _module()
    profile = module.MailRuleProfile("discovery")

    if module.internal_mail_profile(profile) != "outlook-mail-discovery-v1":
        pytest.fail("User discovery profile did not map to the versioned contract")


def test_policy_models_are_frozen() -> None:
    policy = _parse(_policy())

    with pytest.raises(ValidationError):
        policy.enabled = False  # type: ignore[misc]


def test_predicate_public_vocabulary_is_exact() -> None:
    expected = {
        "subject_contains",
        "subject_exact",
        "subject_regex",
        "body_contains",
        "body_regex",
        "body_or_subject_contains",
        "body_or_subject_regex",
        "from_addresses",
        "from_contains",
        "from_address_contains",
        "from_address_regex",
        "sender_addresses",
        "sender_contains",
        "sender_address_contains",
        "sender_address_regex",
        "to_addresses",
        "to_address_contains",
        "to_address_regex",
        "cc_addresses",
        "cc_address_contains",
        "cc_address_regex",
        "bcc_addresses",
        "bcc_address_contains",
        "bcc_address_regex",
        "recipient_contains",
        "recipient_address_contains",
        "recipient_address_regex",
        "reply_to_addresses",
        "reply_to_address_contains",
        "reply_to_address_regex",
        "categories",
        "importance",
        "has_attachments",
        "header_contains",
        "header_regex",
        "sensitivity",
        "message_size_min_kb",
        "message_size_max_kb",
        "received_after",
        "received_before",
        "sent_after",
        "sent_before",
        "created_after",
        "created_before",
        "is_read",
        "is_draft",
        "inference_classification",
        "followup_status",
        "item_class_exact",
        "item_class_contains",
        "item_class_regex",
        "is_meeting_request",
        "is_meeting_response",
        "is_non_delivery_report",
        "is_read_receipt",
    }

    if set(_module().MailRulePredicates.model_fields) != expected:
        pytest.fail("Mail predicate public vocabulary drifted from V1 contract")


def test_rule_defaults_enabled_and_stop_processing_false() -> None:
    raw = _rule()
    del raw["enabled"]
    del raw["stop_processing"]

    rule = _parse(_policy(rules=[raw])).rules[0]

    if not rule.enabled or rule.stop_processing:
        pytest.fail("Rule default flags do not match V1 contract")


def test_rule_ids_and_sequences_must_be_unique() -> None:
    duplicate_id = [_rule(sequence=1), _rule(sequence=2)]
    duplicate_sequence = [
        _rule(rule_id="one", sequence=1),
        _rule(rule_id="two", sequence=1),
    ]

    for raw, reason in (
        (duplicate_id, "duplicate_rule_id"),
        (duplicate_sequence, "duplicate_sequence"),
    ):
        with pytest.raises(ConfigurationError) as caught:
            _parse(_policy(rules=raw))
        if _diagnostic(caught.value).reason_code != reason:
            pytest.fail(f"Duplicate rule validation used wrong reason for {reason}")


@pytest.mark.parametrize("rule_id", ("", "space id", "line\nbreak", "x" * 97))
def test_rule_id_is_bounded_safe_audit_token(rule_id: str) -> None:
    with pytest.raises(ConfigurationError):
        _parse(_policy(rules=[_rule(rule_id=rule_id)]))


@pytest.mark.parametrize("sequence", (-1, 2_147_483_648))
def test_sequence_bound_is_enforced(sequence: int) -> None:
    with pytest.raises(ConfigurationError) as caught:
        _parse(_policy(rules=[_rule(sequence=sequence)]))
    if _diagnostic(caught.value).reason_code != "bound_exceeded":
        pytest.fail("Sequence bound used the wrong safe diagnostic")


def test_rule_count_bound_is_enforced() -> None:
    rules = [_rule(rule_id=f"r{i}", sequence=i) for i in range(257)]

    with pytest.raises(ConfigurationError) as caught:
        _parse(_policy(rules=rules))

    if _diagnostic(caught.value).reason_code != "bound_exceeded":
        pytest.fail("Rule-count bound used the wrong diagnostic")


def test_exception_block_bound_is_enforced() -> None:
    exceptions = [{"subject_contains": [f"x{i}"]} for i in range(33)]

    with pytest.raises(ConfigurationError) as caught:
        _parse(_policy(rules=[_rule(exceptions=exceptions)]))

    if _diagnostic(caught.value).reason_code != "bound_exceeded":
        pytest.fail("Exception-block bound used the wrong diagnostic")


def test_predicate_value_count_bound_is_enforced() -> None:
    values = [f"value-{i}" for i in range(129)]

    with pytest.raises(ConfigurationError) as caught:
        _parse(_policy(rules=[_rule(conditions={"subject_contains": values})]))

    if _diagnostic(caught.value).reason_code != "bound_exceeded":
        pytest.fail("Predicate-value bound used the wrong diagnostic")


def test_empty_condition_exception_and_list_are_rejected() -> None:
    invalids = (
        _rule(conditions={}),
        _rule(conditions={"subject_contains": []}),
        _rule(exceptions=[{}]),
    )

    for raw in invalids:
        with pytest.raises(ConfigurationError):
            _parse(_policy(rules=[raw]))


def test_casefold_duplicate_literal_is_rejected() -> None:
    with pytest.raises(ConfigurationError):
        _parse(
            _policy(
                rules=[_rule(conditions={"subject_contains": ["Approval", "APPROVAL"]})]
            )
        )


def test_regex_duplicates_remain_literal_pattern_distinct() -> None:
    policy = _parse(
        _policy(
            rules=[
                _rule(
                    conditions={
                        "subject_regex": ["Invoice", "invoice"],
                    }
                )
            ]
        )
    )

    if policy.rules[0].conditions.subject_regex != ("Invoice", "invoice"):
        pytest.fail("Regex pattern strings were casefolded or rewritten")


def test_address_literals_strip_surrounding_whitespace() -> None:
    policy = _parse(
        _policy(
            rules=[
                _rule(
                    conditions={
                        "from_addresses": ["  Person@Example.COM  "],
                        "subject_contains": [" approval "],
                    }
                )
            ]
        )
    )
    conditions = policy.rules[0].conditions
    if conditions.from_addresses != ("Person@Example.COM",):
        pytest.fail("Address literals did not strip surrounding whitespace")
    if conditions.subject_contains != (" approval ",):
        pytest.fail("Free-text literal whitespace was rewritten")


def test_empty_literal_and_empty_regex_are_rejected() -> None:
    for field in ("subject_contains", "subject_regex"):
        with pytest.raises(ConfigurationError):
            _parse(_policy(rules=[_rule(conditions={field: [""]})]))


def test_disabled_rule_still_validates_invalid_regex() -> None:
    private_pattern = "PRIVATE_PATTERN_91(?="

    with pytest.raises(ConfigurationError) as caught:
        _parse(
            _policy(
                rules=[
                    _rule(
                        enabled=False,
                        conditions={"subject_regex": [private_pattern]},
                    )
                ]
            )
        )

    diagnostic = _diagnostic(caught.value)
    if diagnostic.reason_code != "invalid_regex":
        pytest.fail("Disabled invalid regex was not classified as invalid regex")
    exposed = f"{caught.value} {diagnostic!r}"
    if private_pattern in exposed:
        pytest.fail("Private invalid regex leaked from configuration validation")


def test_more_than_64_regex_entries_is_rejected_even_when_disabled() -> None:
    rules = [
        _rule(
            rule_id=f"r{i}",
            sequence=i,
            enabled=False,
            conditions={"subject_regex": [f"pattern-{i}"]},
        )
        for i in range(65)
    ]

    with pytest.raises(ConfigurationError) as caught:
        _parse(_policy(rules=rules))

    if _diagnostic(caught.value).reason_code != "bound_exceeded":
        pytest.fail("Regex-entry bound used the wrong diagnostic")


def test_deferred_message_action_flag_is_unknown_field() -> None:
    with pytest.raises(ConfigurationError) as caught:
        _parse(
            _policy(
                rules=[
                    _rule(
                        conditions=cast(
                            dict[str, object],
                            {"messageActionFlag": ["reply"]},
                        )
                    )
                ]
            )
        )

    diagnostic = _diagnostic(caught.value)
    if diagnostic.reason_code != "unknown_field":
        pytest.fail("Deferred predicate was not rejected as an unknown field")
    if "messageActionFlag" in f"{caught.value} {diagnostic!r}":
        pytest.fail("Unknown predicate name leaked through the safe diagnostic")


def test_unknown_private_key_is_rendered_as_unknown_placeholder() -> None:
    private_key = "PRIVATE_CLIENT_NAME"
    raw = _policy()
    conditions = cast(
        dict[str, object], cast(list[dict[str, object]], raw["rules"])[0]["conditions"]
    )
    conditions[private_key] = ["private-value"]

    with pytest.raises(ConfigurationError) as caught:
        _parse(raw)

    diagnostic = _diagnostic(caught.value)
    if diagnostic.field_path is None or "<unknown>" not in diagnostic.field_path:
        pytest.fail("Unknown key was not replaced with the safe placeholder")
    if private_key in f"{caught.value} {diagnostic!r}":
        pytest.fail("Unknown private key leaked through validation")


def test_unsupported_profile_has_safe_field_path_and_reason() -> None:
    private = "PRIVATE_FULL_PROFILE"
    raw = _policy(default_profile=private)

    with pytest.raises(ConfigurationError) as caught:
        _parse(raw)

    diagnostic = _diagnostic(caught.value)
    if diagnostic.field_path != "acquisition.microsoft.outlook.mail.default_profile":
        pytest.fail(f"Unsupported profile path was not safe/precise: {diagnostic!r}")
    if diagnostic.reason_code != "unsupported_profile":
        pytest.fail("Unsupported profile used the wrong safe reason")
    if private in f"{caught.value} {diagnostic!r}":
        pytest.fail("Unsupported private profile value leaked")


def test_lists_reject_wrong_scalar_types_instead_of_coercing() -> None:
    with pytest.raises(ConfigurationError):
        _parse(_policy(rules=[_rule(conditions={"subject_contains": "approval"})]))


def test_enum_values_are_case_insensitive_and_canonicalized() -> None:
    policy = _parse(
        _policy(
            rules=[
                _rule(
                    conditions={
                        "importance": ["HIGH"],
                        "sensitivity": ["Private"],
                        "inference_classification": ["FOCUSED"],
                        "followup_status": ["Not_Flagged"],
                    }
                )
            ]
        )
    )
    conditions = policy.rules[0].conditions

    if tuple(x.value for x in conditions.importance or ()) != ("high",):
        pytest.fail("Importance enum did not canonicalize case-insensitively")
    if tuple(x.value for x in conditions.sensitivity or ()) != ("private",):
        pytest.fail("Sensitivity enum did not canonicalize case-insensitively")
    if tuple(x.value for x in conditions.inference_classification or ()) != (
        "focused",
    ):
        pytest.fail("Inference classification did not canonicalize")
    if tuple(x.value for x in conditions.followup_status or ()) != ("not_flagged",):
        pytest.fail("Follow-up status did not canonicalize")


def test_size_range_bounds_and_order_are_validated() -> None:
    for conditions, reason in (
        ({"message_size_min_kb": -1}, "bound_exceeded"),
        ({"message_size_max_kb": 2_097_152}, "bound_exceeded"),
        (
            {"message_size_min_kb": 10, "message_size_max_kb": 9},
            "invalid_range",
        ),
    ):
        with pytest.raises(ConfigurationError) as caught:
            _parse(_policy(rules=[_rule(conditions=conditions)]))
        if _diagnostic(caught.value).reason_code != reason:
            pytest.fail(f"Size validation used wrong safe reason for {conditions}")


def test_datetimes_must_be_timezone_aware_and_normalize_for_digest() -> None:
    with pytest.raises(ConfigurationError) as caught:
        _parse(
            _policy(rules=[_rule(conditions={"received_after": "2026-01-01T00:00:00"})])
        )
    if _diagnostic(caught.value).reason_code != "invalid_range":
        pytest.fail("Naive datetime was not rejected through bounded range validation")

    left = _parse(
        _policy(
            rules=[_rule(conditions={"received_after": "2026-01-01T00:00:00+00:00"})]
        )
    )
    right = _parse(
        _policy(
            rules=[_rule(conditions={"received_after": "2026-01-01T11:00:00+11:00"})]
        )
    )

    if _module().effective_mail_policy_digest(
        left
    ) != _module().effective_mail_policy_digest(right):
        pytest.fail(
            "Equivalent timezone-aware instants produced different policy digests"
        )


def test_datetime_model_retains_aware_datetime() -> None:
    policy = _parse(
        _policy(rules=[_rule(conditions={"received_after": "2026-01-01T00:00:00Z"})])
    )
    value = policy.rules[0].conditions.received_after
    if not isinstance(value, datetime) or value.tzinfo is None:
        pytest.fail("Datetime predicate was not parsed as timezone-aware datetime")


def test_globally_disabled_digest_ignores_draft_rule_content() -> None:
    module = _module()
    left = _parse(
        _policy(enabled=False, rules=[_rule(conditions={"subject_contains": ["a"]})])
    )
    right = _parse(
        _policy(enabled=False, rules=[_rule(conditions={"subject_contains": ["b"]})])
    )

    if module.effective_mail_policy_digest(left) != module.effective_mail_policy_digest(
        right
    ):
        pytest.fail("Disabled policy digest depends on inactive draft rules")


def test_disabled_rule_edit_does_not_change_enabled_policy_digest() -> None:
    module = _module()
    enabled = _rule(rule_id="active", sequence=1)
    left = _parse(
        _policy(
            rules=[
                enabled,
                _rule(
                    rule_id="draft",
                    sequence=2,
                    enabled=False,
                    conditions={"subject_contains": ["one"]},
                ),
            ]
        )
    )
    right = _parse(
        _policy(
            rules=[
                enabled,
                _rule(
                    rule_id="draft",
                    sequence=2,
                    enabled=False,
                    conditions={"subject_contains": ["two"]},
                ),
            ]
        )
    )

    if module.effective_mail_policy_digest(left) != module.effective_mail_policy_digest(
        right
    ):
        pytest.fail("Disabled individual rule changed effective enabled-policy digest")


def test_enabled_rule_id_rename_changes_digest() -> None:
    module = _module()
    left = _parse(_policy(rules=[_rule(rule_id="one")]))
    right = _parse(_policy(rules=[_rule(rule_id="two")]))

    if module.effective_mail_policy_digest(left) == module.effective_mail_policy_digest(
        right
    ):
        pytest.fail("Enabled rule audit identity was omitted from policy digest")


def test_case_only_literal_change_keeps_digest() -> None:
    module = _module()
    left = _parse(_policy(rules=[_rule(conditions={"subject_contains": ["Urgent"]})]))
    right = _parse(_policy(rules=[_rule(conditions={"subject_contains": ["URGENT"]})]))

    if module.effective_mail_policy_digest(left) != module.effective_mail_policy_digest(
        right
    ):
        pytest.fail("Case-insensitive literal spelling changed semantic digest")


def test_regex_case_or_text_change_changes_digest() -> None:
    module = _module()
    left = _parse(_policy(rules=[_rule(conditions={"subject_regex": ["Urgent"]})]))
    right = _parse(_policy(rules=[_rule(conditions={"subject_regex": ["URGENT"]})]))

    if module.effective_mail_policy_digest(left) == module.effective_mail_policy_digest(
        right
    ):
        pytest.fail("Regex pattern text was incorrectly casefolded in digest")


def test_or_value_rule_and_exception_order_do_not_change_digest() -> None:
    module = _module()
    left = _parse(
        _policy(
            rules=[
                _rule(
                    rule_id="later",
                    sequence=20,
                    conditions={"subject_contains": ["one", "two"]},
                    exceptions=[
                        {"categories": ["Ignore"]},
                        {"from_addresses": ["bot@example.com"]},
                    ],
                ),
                _rule(rule_id="earlier", sequence=10),
            ]
        )
    )
    right = _parse(
        _policy(
            rules=[
                _rule(rule_id="earlier", sequence=10),
                _rule(
                    rule_id="later",
                    sequence=20,
                    conditions={"subject_contains": ["two", "one"]},
                    exceptions=[
                        {"from_addresses": ["BOT@EXAMPLE.COM"]},
                        {"categories": ["ignore"]},
                    ],
                ),
            ]
        )
    )

    if module.effective_mail_policy_digest(left) != module.effective_mail_policy_digest(
        right
    ):
        pytest.fail("Order-independent Mail policy material changed semantic digest")


def test_policy_digest_is_lowercase_sha256() -> None:
    digest = _module().effective_mail_policy_digest(_parse(_policy()))

    if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        pytest.fail(f"Policy digest is not lowercase SHA-256: {digest!r}")


def test_policy_inspection_is_safe_and_excludes_digest_and_values() -> None:
    module = _module()
    private = "PRIVATE_SUBJECT_511"
    policy = _parse(
        _policy(
            rules=[
                _rule(
                    conditions={"subject_contains": [private]},
                ),
                _rule(rule_id="disabled", sequence=20, enabled=False),
            ]
        )
    )

    inspected = module.mail_policy_inspection(policy)

    if inspected != {
        "enabled": True,
        "policy_family": "outlook-mail-acquisition-rules-v1",
        "rule_count": 2,
        "enabled_rule_count": 1,
    }:
        pytest.fail(f"Unexpected safe policy inspection: {inspected!r}")
    if private in repr(inspected) or "digest" in repr(inspected).casefold():
        pytest.fail("Inspection exposed policy values or private digest")


def test_source_label_is_bounded_safe_enum() -> None:
    with pytest.raises(ConfigurationError) as caught:
        _module().parse_mail_rule_policy(_policy(), source_label="PRIVATE_PATH")

    if caught.value.code is not ConfigurationErrorCode.INVALID_INPUT:
        pytest.fail("Unsafe source label did not become bounded invalid-input failure")


def test_policy_family_is_fixed() -> None:
    if _module().MAIL_RULE_POLICY_FAMILY != "outlook-mail-acquisition-rules-v1":
        pytest.fail("Mail policy family identifier drifted")
