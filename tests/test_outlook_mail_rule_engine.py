"""Ordered deterministic Outlook Mail RuleEngine behavior."""

from __future__ import annotations

from typing import Any, cast

import pytest

from message_ingest.acquisition.microsoft.outlook.email.profile import (
    DISCOVERY_V1,
    FULL_V1,
)
from message_ingest.acquisition.microsoft.outlook.email.rule_config import (
    MAIL_RULE_POLICY_FAMILY,
    effective_mail_policy_digest,
    parse_mail_rule_policy,
)
from message_ingest.acquisition.microsoft.outlook.email.rule_evaluation import (
    MailRuleDecisionOutcome,
    MailRuleEvaluationState,
    MailRuleFact,
    MailRuleFacts,
    MailRuleObservation,
    MailRuleProbeData,
    MailRuleProbeFailure,
    MailRuleProbeStatus,
    MailRuleRequiredData,
)
from message_ingest.acquisition.microsoft.outlook.email.rule_regex import (
    MailRegexEngine,
    MailRegexEvaluationError,
)


def _rule(
    *,
    rule_id: str,
    sequence: int,
    profile: str = "full",
    conditions: dict[str, object] | None = None,
    exceptions: list[dict[str, object]] | None = None,
    stop: bool = False,
    enabled: bool = True,
) -> dict[str, object]:
    value: dict[str, object] = {
        "id": rule_id,
        "sequence": sequence,
        "enabled": enabled,
        "profile": profile,
        "stop_processing": stop,
        "conditions": conditions or {"subject_contains": [rule_id]},
    }
    if exceptions is not None:
        value["exceptions"] = exceptions
    return value


def _policy(
    *,
    default: str = "discovery",
    rules: list[dict[str, object]] | None = None,
    enabled: bool = True,
):
    return parse_mail_rule_policy(
        {
            "enabled": enabled,
            "default_profile": default,
            "rules": rules or [],
        }
    )


def _facts(**overrides: object) -> MailRuleFacts:
    values: dict[str, object] = {
        "change_key": "change-1",
        "subject": "urgent approval",
        "categories": ("Finance",),
        "importance": "high",
        "available_facts": frozenset(
            {
                MailRuleFact.CHANGE_KEY,
                MailRuleFact.SUBJECT,
                MailRuleFact.CATEGORIES,
                MailRuleFact.IMPORTANCE,
            }
        ),
    }
    values.update(overrides)
    return MailRuleFacts(**cast(Any, values))


def _observation(facts: MailRuleFacts | None = None) -> MailRuleObservation:
    return MailRuleObservation(
        message_id="message-1",
        run_id="run-1",
        evidence_id="evidence-1",
        observation_kind="delta",
        facts=facts or _facts(),
    )


def _evaluator(policy=None, *, regex_engine: MailRegexEngine | None = None):
    from message_ingest.acquisition.microsoft.outlook.email.rule_engine import (
        DeterministicMailRuleEvaluator,
    )

    return DeterministicMailRuleEvaluator(
        policy or _policy(),
        regex_engine=regex_engine,
    )


def _probe(
    facts: MailRuleFacts,
    *,
    status: MailRuleProbeStatus = MailRuleProbeStatus.COMPLETE,
    failures: tuple[MailRuleProbeFailure, ...] = (),
) -> MailRuleProbeData:
    return MailRuleProbeData(
        status=status,
        facts=facts,
        evidence_id="probe-evidence",
        failures=failures,
    )


def test_disabled_policy_cannot_construct_rule_engine() -> None:
    with pytest.raises(ValueError):
        _evaluator(_policy(enabled=False))


def test_default_discovery_no_match_is_final_default() -> None:
    policy = _policy(
        rules=[
            _rule(
                rule_id="r1",
                sequence=10,
                conditions={"subject_contains": ["missing"]},
            )
        ]
    )
    result = _evaluator(policy).evaluate(_observation())

    if result.state is not MailRuleEvaluationState.FINAL:
        pytest.fail("No-match discovery policy was not terminal")
    if result.selected_profile != DISCOVERY_V1:
        pytest.fail("No-match policy lost discovery default")
    if result.outcome is not MailRuleDecisionOutcome.DEFAULT:
        pytest.fail("No-match policy did not report DEFAULT")
    if result.matched_rule_ids:
        pytest.fail("No-match policy fabricated matched rules")
    if result.ruleset_id != MAIL_RULE_POLICY_FAMILY:
        pytest.fail("Evaluation lost fixed policy-family identity")
    if result.ruleset_digest != effective_mail_policy_digest(policy):
        pytest.fail("Evaluation lost private effective policy digest")


def test_matching_full_rule_upgrades_profile_and_reports_match() -> None:
    policy = _policy(
        rules=[
            _rule(
                rule_id="full-rule",
                sequence=10,
                conditions={"subject_contains": ["approval"]},
            )
        ]
    )

    result = _evaluator(policy).evaluate(_observation())

    if result.selected_profile != FULL_V1:
        pytest.fail("Matching Full rule did not upgrade profile")
    if result.outcome is not MailRuleDecisionOutcome.MATCHED:
        pytest.fail("Matching rule did not report MATCHED")
    if result.matched_rule_ids != ("full-rule",):
        pytest.fail("Matched rule IDs changed")


def test_later_discovery_rule_cannot_downgrade_full_and_is_not_audit_probed() -> None:
    policy = _policy(
        rules=[
            _rule(
                rule_id="full-first",
                sequence=10,
                conditions={"subject_contains": ["approval"]},
            ),
            _rule(
                rule_id="later-discovery",
                sequence=20,
                profile="discovery",
                conditions={"body_contains": ["unknown-body"]},
            ),
        ]
    )

    result = _evaluator(policy).evaluate(_observation())

    if result.state is not MailRuleEvaluationState.FINAL:
        pytest.fail("Known Full result unnecessarily requested later audit data")
    if result.selected_profile != FULL_V1:
        pytest.fail("Later discovery rule downgraded Full")
    if result.matched_rule_ids != ("full-first",):
        pytest.fail("Rules after maximal Full were evaluated for audit only")


def test_matching_stop_processing_rule_prevents_later_full_rule() -> None:
    policy = _policy(
        rules=[
            _rule(
                rule_id="stop",
                sequence=10,
                profile="discovery",
                stop=True,
                conditions={"subject_contains": ["approval"]},
            ),
            _rule(
                rule_id="later-full",
                sequence=20,
                conditions={"subject_contains": ["urgent"]},
            ),
        ]
    )

    result = _evaluator(policy).evaluate(_observation())

    if result.selected_profile != DISCOVERY_V1:
        pytest.fail("stop_processing did not prevent later Full upgrade")
    if result.matched_rule_ids != ("stop",) or result.stop_rule_id != "stop":
        pytest.fail("stop_processing audit path changed")


def test_matching_rule_that_keeps_default_profile_still_reports_matched() -> None:
    policy = _policy(
        rules=[
            _rule(
                rule_id="discovery-match",
                sequence=10,
                profile="discovery",
                conditions={"subject_contains": ["approval"]},
            )
        ]
    )

    result = _evaluator(policy).evaluate(_observation())

    if result.selected_profile != DISCOVERY_V1:
        pytest.fail("Discovery match changed acquisition depth")
    if result.outcome is not MailRuleDecisionOutcome.MATCHED:
        pytest.fail("Matching no-op profile rule lost MATCHED audit outcome")
    if result.matched_rule_ids != ("discovery-match",):
        pytest.fail("Matching discovery rule was omitted from audit path")


class _ExplodingRegexEngine(MailRegexEngine):
    @staticmethod
    def compile(pattern: str):  # type: ignore[override]
        return cast(Any, pattern)

    @staticmethod
    def search(compiled, text: str) -> bool:  # type: ignore[override]
        del text
        raise MailRegexEvaluationError


def test_default_full_is_immediate_default_without_rule_evaluation() -> None:
    policy = _policy(
        default="full",
        rules=[
            _rule(
                rule_id="audit-only",
                sequence=10,
                conditions={"subject_regex": ["valid-pattern"]},
            )
        ],
    )

    result = _evaluator(policy, regex_engine=_ExplodingRegexEngine()).evaluate(
        _observation()
    )

    if result.state is not MailRuleEvaluationState.FINAL:
        pytest.fail("Default Full unexpectedly tried to evaluate rules")
    if result.selected_profile != FULL_V1:
        pytest.fail("Default Full lost internal profile")
    if result.outcome is not MailRuleDecisionOutcome.DEFAULT:
        pytest.fail("Default Full should be DEFAULT without audit-only rule evaluation")
    if result.matched_rule_ids or result.reason_code:
        pytest.fail("Default Full retained audit-only rule state")


def test_disabled_rules_are_ignored_during_evaluation() -> None:
    policy = _policy(
        rules=[
            _rule(
                rule_id="disabled-full",
                sequence=10,
                enabled=False,
                conditions={"subject_contains": ["approval"]},
            )
        ]
    )

    result = _evaluator(policy).evaluate(_observation())

    if result.selected_profile != DISCOVERY_V1:
        pytest.fail("Disabled rule changed acquisition depth")
    if result.outcome is not MailRuleDecisionOutcome.DEFAULT:
        pytest.fail("Disabled rule changed DEFAULT outcome")


def test_true_exception_excludes_otherwise_matching_rule() -> None:
    policy = _policy(
        rules=[
            _rule(
                rule_id="excepted",
                sequence=10,
                conditions={"subject_contains": ["approval"]},
                exceptions=[{"categories": ["finance"]}],
            )
        ]
    )

    result = _evaluator(policy).evaluate(_observation())

    if result.outcome is not MailRuleDecisionOutcome.DEFAULT:
        pytest.fail("True exception did not exclude matching rule")
    if result.matched_rule_ids:
        pytest.fail("Excluded rule was included in matched_rule_ids")


def test_cheap_true_exception_suppresses_unknown_body_condition() -> None:
    policy = _policy(
        rules=[
            _rule(
                rule_id="excepted",
                sequence=10,
                conditions={"body_contains": ["approval"]},
                exceptions=[{"categories": ["finance"]}],
            )
        ]
    )

    result = _evaluator(policy).evaluate(_observation())

    if result.state is not MailRuleEvaluationState.FINAL:
        pytest.fail("Cheap true exception unnecessarily requested BODY")
    if result.outcome is not MailRuleDecisionOutcome.DEFAULT:
        pytest.fail("Cheap true exception did not exclude rule")
    if result.required_data:
        pytest.fail("Excluded rule retained BODY requirement")


def test_unknown_stop_rule_unions_later_reachable_branch_requirements() -> None:
    policy = _policy(
        rules=[
            _rule(
                rule_id="body-stop",
                sequence=10,
                profile="discovery",
                stop=True,
                conditions={"body_contains": ["approval"]},
            ),
            _rule(
                rule_id="header-full",
                sequence=20,
                conditions={"header_contains": ["x-workflow"]},
            ),
        ]
    )

    result = _evaluator(policy).evaluate(_observation())

    if result.state is not MailRuleEvaluationState.NEEDS_DATA:
        pytest.fail("Unknown stop branch did not remain NEEDS_DATA")
    if result.required_data != frozenset(
        {MailRuleRequiredData.BODY, MailRuleRequiredData.HEADERS}
    ):
        pytest.fail(f"Reachable branch data union changed: {result.required_data!r}")


def test_proven_stop_rule_excludes_later_required_data() -> None:
    policy = _policy(
        rules=[
            _rule(
                rule_id="known-stop",
                sequence=10,
                profile="discovery",
                stop=True,
                conditions={"subject_contains": ["approval"]},
            ),
            _rule(
                rule_id="header-full",
                sequence=20,
                conditions={"header_contains": ["x-workflow"]},
            ),
        ]
    )

    result = _evaluator(policy).evaluate(_observation())

    if result.state is not MailRuleEvaluationState.FINAL:
        pytest.fail("Proven stop rule incorrectly requested later branch data")
    if result.required_data:
        pytest.fail("Proven stop rule retained unreachable data requirement")


def test_known_later_full_makes_prior_non_stop_unknown_audit_only() -> None:
    policy = _policy(
        rules=[
            _rule(
                rule_id="body-full",
                sequence=10,
                conditions={"body_contains": ["approval"]},
            ),
            _rule(
                rule_id="known-full",
                sequence=20,
                conditions={"subject_contains": ["approval"]},
            ),
        ]
    )

    result = _evaluator(policy).evaluate(_observation())

    if result.state is not MailRuleEvaluationState.FINAL:
        pytest.fail("Known later Full did not eliminate prior audit-only probe")
    if result.selected_profile != FULL_V1:
        pytest.fail("Known later Full did not determine acquisition depth")
    if result.matched_rule_ids != ("known-full",):
        pytest.fail("Unknown earlier rule was fabricated as matched")
