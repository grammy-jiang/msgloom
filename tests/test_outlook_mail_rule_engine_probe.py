"""Ordered deterministic Outlook Mail RuleEngine behavior."""

from __future__ import annotations

from typing import Any, cast

import pytest

from message_ingest.acquisition.microsoft.outlook.email.profile import (
    FULL_V1,
)
from message_ingest.acquisition.microsoft.outlook.email.rule_config import (
    parse_mail_rule_policy,
)
from message_ingest.acquisition.microsoft.outlook.email.rule_evaluation import (
    MailRuleEvaluationState,
    MailRuleFact,
    MailRuleFacts,
    MailRuleObservation,
    MailRuleProbeData,
    MailRuleProbeFailure,
    MailRuleProbeStatus,
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


def test_same_change_key_probe_resolves_body_rule() -> None:
    policy = _policy(
        rules=[
            _rule(
                rule_id="body-full",
                sequence=10,
                conditions={"body_contains": ["approval"]},
            )
        ]
    )
    evaluator = _evaluator(policy)
    observation = _observation()

    initial = evaluator.evaluate(observation)
    if initial.state is not MailRuleEvaluationState.NEEDS_DATA:
        pytest.fail("Missing BODY did not request probe")

    probe = _probe(
        MailRuleFacts(
            change_key="change-1",
            body="approval in body",
            available_facts=frozenset({MailRuleFact.CHANGE_KEY, MailRuleFact.BODY}),
        )
    )
    result = evaluator.evaluate(observation, probe=probe)

    if result.state is not MailRuleEvaluationState.FINAL:
        pytest.fail("Same-version BODY probe did not resolve rule")
    if result.selected_profile != FULL_V1 or not result.probe_used:
        pytest.fail("Resolved probe did not record Full/probe use")
    if result.matched_rule_ids != ("body-full",):
        pytest.fail("Resolved body rule lost matched identity")


def test_missing_initial_change_key_fails_safe_before_scheduling_probe() -> None:
    policy = _policy(
        rules=[
            _rule(rule_id="body-full", sequence=10, conditions={"body_contains": ["x"]})
        ]
    )
    facts = _facts(
        change_key=None,
        available_facts=_facts().available_facts - {MailRuleFact.CHANGE_KEY},
    )

    result = _evaluator(policy).evaluate(_observation(facts))

    if result.state is not MailRuleEvaluationState.UNRESOLVED:
        pytest.fail("Probe-needed observation without changeKey did not fail safe")
    if result.selected_profile != FULL_V1 or not result.fallback_used:
        pytest.fail("Missing initial version did not select fail-safe Full")
    if result.reason_code != "initial_version_unavailable":
        pytest.fail("Missing initial version reason changed")


def test_missing_probe_change_key_fails_safe() -> None:
    policy = _policy(
        rules=[
            _rule(rule_id="body-full", sequence=10, conditions={"body_contains": ["x"]})
        ]
    )
    observation = _observation()
    probe = _probe(
        MailRuleFacts(
            body="x",
            available_facts=frozenset({MailRuleFact.BODY}),
        )
    )

    result = _evaluator(policy).evaluate(observation, probe=probe)

    if result.state is not MailRuleEvaluationState.UNRESOLVED:
        pytest.fail("Probe without changeKey did not fail safe")
    if result.reason_code != "probe_version_unavailable":
        pytest.fail("Missing probe version reason changed")


def test_changed_probe_change_key_fails_safe() -> None:
    policy = _policy(
        rules=[
            _rule(rule_id="body-full", sequence=10, conditions={"body_contains": ["x"]})
        ]
    )
    observation = _observation()
    probe = _probe(
        MailRuleFacts(
            change_key="change-2",
            body="x",
            available_facts=frozenset({MailRuleFact.CHANGE_KEY, MailRuleFact.BODY}),
        )
    )

    result = _evaluator(policy).evaluate(observation, probe=probe)

    if result.state is not MailRuleEvaluationState.UNRESOLVED:
        pytest.fail("Changed provider version did not fail safe")
    if result.reason_code != "source_changed_during_evaluation":
        pytest.fail("Source mutation reason changed")


def test_partial_probe_missing_irrelevant_fact_can_still_finalize() -> None:
    policy = _policy(
        rules=[
            _rule(
                rule_id="body-full",
                sequence=10,
                conditions={"body_contains": ["approval"]},
            )
        ]
    )
    observation = _observation()
    probe = _probe(
        MailRuleFacts(
            change_key="change-1",
            body="approval body",
            available_facts=frozenset({MailRuleFact.CHANGE_KEY, MailRuleFact.BODY}),
        ),
        status=MailRuleProbeStatus.PARTIAL,
        failures=(
            MailRuleProbeFailure(
                fact=MailRuleFact.HEADERS,
                reason_code="header_unavailable",
            ),
        ),
    )

    result = _evaluator(policy).evaluate(observation, probe=probe)

    if result.state is not MailRuleEvaluationState.FINAL:
        pytest.fail("Irrelevant missing probe fact forced fail-safe fallback")
    if result.selected_profile != FULL_V1:
        pytest.fail("Available relevant BODY did not finalize Full")


def test_partial_probe_missing_relevant_fact_becomes_unresolved_full() -> None:
    policy = _policy(
        rules=[
            _rule(
                rule_id="header-full",
                sequence=10,
                conditions={"header_contains": ["workflow"]},
            )
        ]
    )
    observation = _observation()
    probe = _probe(
        MailRuleFacts(
            change_key="change-1",
            available_facts=frozenset({MailRuleFact.CHANGE_KEY}),
        ),
        status=MailRuleProbeStatus.PARTIAL,
        failures=(
            MailRuleProbeFailure(
                fact=MailRuleFact.HEADERS,
                reason_code="header_unavailable",
            ),
        ),
    )

    result = _evaluator(policy).evaluate(observation, probe=probe)

    if result.state is not MailRuleEvaluationState.UNRESOLVED:
        pytest.fail("Relevant missing probe fact did not become UNRESOLVED")
    if result.selected_profile != FULL_V1 or not result.fallback_used:
        pytest.fail("Relevant missing probe fact did not fail safe to Full")
    if result.reason_code != "probe_fact_unavailable":
        pytest.fail("Relevant missing probe fact reason changed")


class _SelectiveRegexEngine(MailRegexEngine):
    @staticmethod
    def compile(pattern: str):  # type: ignore[override]
        return cast(Any, pattern)

    @staticmethod
    def search(compiled, text: str) -> bool:  # type: ignore[override]
        del text
        if compiled == "explode":
            raise MailRegexEvaluationError
        return compiled == "match"


def test_irrelevant_regex_runtime_failure_is_masked_by_true_or_alternative() -> None:
    policy = _policy(
        rules=[
            _rule(
                rule_id="regex-full",
                sequence=10,
                conditions={"subject_regex": ["explode", "match"]},
            )
        ]
    )

    result = _evaluator(policy, regex_engine=_SelectiveRegexEngine()).evaluate(
        _observation()
    )

    if result.state is not MailRuleEvaluationState.FINAL:
        pytest.fail("TRUE regex alternative did not mask irrelevant runtime failure")
    if result.selected_profile != FULL_V1:
        pytest.fail("TRUE regex alternative did not match Full rule")


def test_relevant_regex_runtime_failure_becomes_unresolved_full_without_probe() -> None:
    policy = _policy(
        rules=[
            _rule(
                rule_id="regex-full",
                sequence=10,
                conditions={"subject_regex": ["explode", "no-match"]},
            )
        ]
    )

    result = _evaluator(policy, regex_engine=_SelectiveRegexEngine()).evaluate(
        _observation()
    )

    if result.state is not MailRuleEvaluationState.UNRESOLVED:
        pytest.fail("Relevant regex engine failure did not fail safe")
    if result.required_data:
        pytest.fail("Regex runtime failure incorrectly requested provider data")
    if result.reason_code != "regex_evaluation_failed":
        pytest.fail("Regex runtime fallback reason changed")
    if result.selected_profile != FULL_V1 or not result.fallback_used:
        pytest.fail("Regex runtime failure did not select fail-safe Full")
