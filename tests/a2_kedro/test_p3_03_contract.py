"""P3-03 output against the ``filter_result@2`` contract (review F7)."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from msgloom.a2_kedro.contracts.results import FilterResult, Reason, RuleEvaluation
from msgloom.a2_kedro.semantics.filters import (
    FilterEvaluation,
    FilterField,
    FilterInput,
    FilterPredicate,
    FilterRule,
    FilterVerdict,
    RuleSet,
    evaluate_filters,
)
from msgloom.contracts import Limitation, TerminalStatus
from tests.a2_kedro.helpers import check
from tests.a2_kedro.result_fixtures import filter_data


def rule(rule_id: str, effect: str, field: str, value: str) -> FilterRule:
    return FilterRule(
        rule_id=rule_id,
        rule_version="1",
        effect=effect,  # type: ignore[arg-type]
        predicate=FilterPredicate(field=FilterField(field), value=value),
    )


def record(**kw: Any) -> FilterInput:
    data: dict[str, Any] = {
        "sender_domain": "example.com",
        "folder_id": "inbox",
        "labels": ("work",),
        "subject": "plan",
    }
    return FilterInput(**{**data, **kw})


def contract_data(result: FilterEvaluation) -> dict[str, Any]:
    dumped = result.model_dump(mode="json")
    return filter_data(
        evaluations=dumped["evaluations"],
        matched=list(result.matched),
        verdict=result.verdict.value,
        reasons=dumped["reasons"],
        status=result.status.value,
        limitations=dumped["limitations"],
    )


#: One case for every verdict. Each item is (verdict, rules, record).
CASES = [
    (
        FilterVerdict.INCLUDE,
        (rule("a", "include", "folder_id", "inbox"),),
        record(),
    ),
    (
        FilterVerdict.EXCLUDE,
        (rule("a", "exclude", "folder_id", "inbox"),),
        record(),
    ),
    (
        FilterVerdict.CONFLICT,
        (
            rule("a", "include", "folder_id", "inbox"),
            rule("b", "exclude", "label", "work"),
        ),
        record(),
    ),
    (
        FilterVerdict.UNKNOWN,
        (rule("a", "include", "sender_domain", "example.com"),),
        record(sender_domain=None),
    ),
    (
        FilterVerdict.NO_MATCH,
        (rule("a", "include", "folder_id", "archive"),),
        record(),
    ),
]


def evaluated(case: int) -> FilterEvaluation:
    verdict, items, data = CASES[case]
    result = evaluate_filters(RuleSet(rule_set_version="rs", rules=items), data)
    check(result.verdict is verdict, "case produces its verdict")
    return result


def test_filter_result_accepts_every_p3_03_verdict() -> None:
    seen = set()
    for case in range(len(CASES)):
        result = evaluated(case)
        built = FilterResult.model_validate(contract_data(result), strict=False)
        check(built.verdict == result.verdict.value, "verdict carried")
        check(built.status == result.status, "status carried")
        check(built.matched == result.matched, "matched carried")
        check(list(built.limitations) == list(result.limitations), "limits carried")
        seen.add(built.verdict)
    check(
        seen == {"include", "exclude", "conflict", "unknown", "no_match"},
        "every contract verdict is covered",
    )


def test_verdict_domain_equals_the_contract_domain() -> None:
    contract = {"include", "exclude", "conflict", "unknown", "no_match"}
    check({v.value for v in FilterVerdict} == contract, "same verdict domain")


def test_forged_verdict_is_rejected_for_every_case() -> None:
    for case in range(len(CASES)):
        good = evaluated(case)
        for wrong in FilterVerdict:
            if wrong is good.verdict:
                continue
            with pytest.raises(ValidationError, match="verdict or reasons differ"):
                FilterEvaluation(**{**dict(good), "verdict": wrong})


def test_forged_reasons_or_matched_are_rejected() -> None:
    good = evaluated(2)
    with pytest.raises(ValidationError, match="verdict or reasons differ"):
        FilterEvaluation(**{**dict(good), "reasons": ()})
    forged = Reason(code="excluded", rule_ids=("a",))
    with pytest.raises(ValidationError, match="verdict or reasons differ"):
        FilterEvaluation(**{**dict(good), "reasons": (forged,)})
    with pytest.raises(ValidationError, match="matched list"):
        FilterEvaluation(**{**dict(good), "matched": ("a",)})


def test_forged_no_match_over_a_matched_rule_is_rejected() -> None:
    match = RuleEvaluation(
        rule_id="a", rule_version="1", outcome="matched", effect="include"
    )
    with pytest.raises(ValidationError, match="verdict or reasons differ"):
        FilterEvaluation(
            rule_set_version="rs",
            evaluations=(match,),
            matched=("a",),
            verdict=FilterVerdict.NO_MATCH,
            status=TerminalStatus.INCOMPLETE,
            limitations=(Limitation("no_rule_matched", "no rule matched"),),
        )


def test_empty_evaluations_are_rejected() -> None:
    with pytest.raises(ValidationError, match="rule count"):
        FilterEvaluation(
            rule_set_version="rs",
            evaluations=(),
            matched=(),
            verdict=FilterVerdict.NO_MATCH,
            status=TerminalStatus.INCOMPLETE,
            limitations=(Limitation("no_rule_matched", "no rule matched"),),
        )


def test_no_match_limitation_is_exactly_the_documented_one() -> None:
    result = evaluated(4)
    check(
        [(i.code, i.detail) for i in result.limitations]
        == [("no_rule_matched", "no rule matched")],
        "documented limitation",
    )
    check(result.status is TerminalStatus.INCOMPLETE, "status follows limitation")
