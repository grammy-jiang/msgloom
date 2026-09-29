"""Deterministic triage-rule contract regressions."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from msgloom.triage import (
    PredicateKind,
    Priority,
    RuleEffect,
    RuleEffectKind,
    RulePredicate,
    TriageRule,
    TriageRuleConfig,
    evaluate_rules,
)

from .helpers import prepared, ref


def _rule(
    identity: str,
    predicate: RulePredicate,
    *effects: RuleEffect,
) -> TriageRule:
    return TriageRule(
        rule_ref=ref("triage-rule", identity),
        predicates=(predicate,),
        effects=effects,
    )


def _subject(value: str = "Synthetic") -> RulePredicate:
    return RulePredicate(kind=PredicateKind.SUBJECT_CONTAINS, text_value=value)


def _effect(kind: RuleEffectKind, priority: Priority | None = None) -> RuleEffect:
    return RuleEffect(kind=kind, priority=priority)


def test_rule_evaluation_is_permutation_stable_and_retains_all_matches() -> None:
    first = prepared("source-a", subject="Synthetic urgent work")
    second = prepared("source-b", subject="Synthetic ordinary work")
    rules = (
        _rule(
            "minimum",
            _subject(),
            _effect(RuleEffectKind.MINIMUM_PRIORITY, Priority.IMPORTANT),
        ),
        _rule(
            "guidance",
            _subject(),
            RuleEffect(kind=RuleEffectKind.GUIDANCE, guidance="Review carefully"),
        ),
    )
    config_a = TriageRuleConfig(version=ref("rule-set", "v1"), rules=rules)
    config_b = TriageRuleConfig(version=ref("rule-set", "v1"), rules=rules[::-1])
    left = evaluate_rules((first, second), config_a)
    right = evaluate_rules((second, first), config_b)
    if left != right:
        pytest.fail("rule outcomes changed under input permutation")
    if any(item.excluded for item in left):
        pytest.fail("guidance or minimum priority unexpectedly excluded a source")
    if any(len(item.matches) != 2 for item in left):
        pytest.fail("not all matched deterministic effects were retained")


@pytest.mark.parametrize(
    ("effects", "code"),
    [
        (
            (
                _effect(RuleEffectKind.REQUIRED_PRIORITY, Priority.CRITICAL),
                _effect(RuleEffectKind.REQUIRED_PRIORITY, Priority.NORMAL),
            ),
            "conflicting-required-priorities",
        ),
        (
            (
                _effect(RuleEffectKind.EXCLUSION),
                _effect(RuleEffectKind.REQUIRED_PRIORITY, Priority.IMPORTANT),
            ),
            "exclusion-required-work-conflict",
        ),
        (
            (
                _effect(RuleEffectKind.REQUIRED_PRIORITY, Priority.NORMAL),
                _effect(RuleEffectKind.MINIMUM_PRIORITY, Priority.IMPORTANT),
            ),
            "required-below-minimum",
        ),
    ],
)
def test_conflicting_effects_create_review_and_no_required_priority(
    effects: tuple[RuleEffect, ...],
    code: str,
) -> None:
    record = prepared("source-a")
    rule = _rule("conflict", _subject(), *effects)
    outcome = evaluate_rules(
        (record,),
        TriageRuleConfig(version=ref("rule-set", "v1"), rules=(rule,)),
    )[0]
    if not outcome.review_items:
        pytest.fail("deterministic conflict did not create a review item")
    if code not in {item.code for item in outcome.review_items}:
        pytest.fail("expected deterministic conflict code was not retained")
    if outcome.required_priority is not None:
        pytest.fail("conflicted deterministic work exposed an accepted priority")


def test_bounded_predicates_cover_source_facts_without_regex_or_eval() -> None:
    record = prepared("source-a", sender="exact@example.invalid")
    predicates = (
        RulePredicate(
            kind=PredicateKind.SENDER_IDENTITY,
            text_value="exact@example.invalid",
        ),
        RulePredicate(
            kind=PredicateKind.SOURCE_TIME_AT_OR_AFTER,
            time_value=datetime(2026, 9, 1, tzinfo=UTC),
        ),
    )
    rule = TriageRule(
        rule_ref=ref("triage-rule", "facts"),
        predicates=predicates,
        effects=(_effect(RuleEffectKind.REQUIRED_PRIORITY, Priority.IMPORTANT),),
    )
    outcome = evaluate_rules(
        (record,),
        TriageRuleConfig(version=ref("rule-set", "v1"), rules=(rule,)),
    )[0]
    if outcome.required_priority is not Priority.IMPORTANT:
        pytest.fail("bounded source predicates did not apply the required priority")


def test_rule_models_reject_extra_fields_coercion_and_naive_time() -> None:
    with pytest.raises(ValidationError):
        RulePredicate.model_validate(
            {"kind": "subject-exact", "text_value": 7},
            strict=True,
        )
    with pytest.raises(ValidationError):
        RulePredicate(
            kind=PredicateKind.SOURCE_TIME_BEFORE,
            time_value=datetime.fromisoformat("2026-09-29T00:00:00"),
        )
    with pytest.raises(ValidationError):
        RuleEffect.model_validate(
            {"kind": "guidance", "guidance": "x", "unexpected": "value"},
            strict=True,
        )


def test_rule_outcome_summary_cannot_contradict_saved_matches() -> None:
    from msgloom.triage import RuleMatch, RuleOutcome

    source = ref("source", "source-a")
    rule_ref = ref("triage-rule", "critical")
    match = RuleMatch(
        rule_ref=rule_ref,
        source_ref=source,
        effect=RuleEffect(
            kind=RuleEffectKind.REQUIRED_PRIORITY,
            priority=Priority.CRITICAL,
        ),
    )
    with pytest.raises(ValidationError):
        RuleOutcome(
            source_ref=source,
            matches=(match,),
            excluded=False,
            required_priority=None,
            minimum_priority=None,
            guidance=(),
            review_items=(),
        )


def test_conflicting_required_priority_summary_is_permutation_stable() -> None:
    record = prepared("source-a")
    effects = (
        _effect(RuleEffectKind.REQUIRED_PRIORITY, Priority.CRITICAL),
        _effect(RuleEffectKind.REQUIRED_PRIORITY, Priority.NORMAL),
        _effect(RuleEffectKind.MINIMUM_PRIORITY, Priority.IMPORTANT),
    )
    left_rule = _rule("conflict", _subject(), *effects)
    right_rule = _rule("conflict", _subject(), *effects[::-1])
    left = evaluate_rules(
        (record,),
        TriageRuleConfig(version=ref("rule-set", "v1"), rules=(left_rule,)),
    )
    right = evaluate_rules(
        (record,),
        TriageRuleConfig(version=ref("rule-set", "v1"), rules=(right_rule,)),
    )
    if left != right:
        pytest.fail("conflicting rule summary changed with effect permutation")
    codes = tuple(item.code for item in left[0].review_items)
    if codes != ("conflicting-required-priorities",):
        pytest.fail("conflicting requirements produced unstable secondary review")
