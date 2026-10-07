"""Outlook Mail rule semantic policy digest tests."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

import pytest

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
