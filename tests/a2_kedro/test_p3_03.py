"""P3-03 versioned rule filters: verdicts, order, errors, immutability."""

from __future__ import annotations

import random
from typing import Any

import pytest
from pydantic import ValidationError

from msgloom.a2_kedro.contracts.results import Reason, RuleEvaluation
from msgloom.a2_kedro.semantics.filters import (
    DuplicateRuleIdError,
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

FAKE_EMAIL = "jane.doe.fake@example.invalid"
FAKE_SUBJECT = "Re: private fake subject"


def rule(
    rule_id: str,
    effect: str,
    field: str,
    value: str,
    version: str = "1",
) -> FilterRule:
    return FilterRule(
        rule_id=rule_id,
        rule_version=version,
        effect=effect,  # type: ignore[arg-type]
        predicate=FilterPredicate(field=FilterField(field), value=value),
    )


def rules(*items: FilterRule, version: str = "rs-1") -> RuleSet:
    return RuleSet(rule_set_version=version, rules=tuple(items))


def full(**kw: Any) -> FilterInput:
    data: dict[str, Any] = {
        "sender_domain": "Example.COM",
        "folder_id": "inbox",
        "labels": ("Work", "Urgent"),
        "subject": "Re: plan",
    }
    return FilterInput(**{**data, **kw})


def limits(result: FilterEvaluation) -> list[tuple[str, str]]:
    return [(item.code, item.detail) for item in result.limitations]


def test_include_when_only_include_rules_match() -> None:
    rs = rules(
        rule("a", "include", "sender_domain", "example.com"),
        rule("b", "include", "folder_id", "inbox"),
        rule("c", "include", "folder_id", "archive"),
    )
    result = evaluate_filters(rs, full())
    check(result.verdict is FilterVerdict.INCLUDE, "include")
    check(result.matched == ("a", "b"), "all matching ids, not one")
    check(result.reasons == (), "no reason for a plain include")
    check(result.status is TerminalStatus.COMPLETE, "complete")
    check(result.limitations == (), "no limitation")


def test_exclude_when_only_exclude_rules_match() -> None:
    rs = rules(
        rule("a", "include", "folder_id", "archive"),
        rule("x2", "exclude", "label", "urgent"),
        rule("x1", "exclude", "subject_prefix", "re:"),
    )
    result = evaluate_filters(rs, full())
    check(result.verdict is FilterVerdict.EXCLUDE, "exclude")
    check(result.matched == ("x1", "x2"), "sorted exclude ids")
    check([r.code for r in result.reasons] == ["excluded"], "excluded reason")
    check(result.status is TerminalStatus.COMPLETE, "complete")


def test_conflict_when_both_kinds_match_and_no_kind_is_picked() -> None:
    rs = rules(
        rule("i1", "include", "folder_id", "inbox"),
        rule("e1", "exclude", "label", "work"),
    )
    result = evaluate_filters(rs, full())
    check(result.verdict is FilterVerdict.CONFLICT, "conflict")
    check(result.matched == ("e1", "i1"), "both listed")
    codes = [r.code for r in result.reasons]
    check(codes == ["conflict", "excluded"], "conflict and excluded reasons")
    check(result.reasons[0].rule_ids == ("i1", "e1"), "include then exclude ids")


def test_no_match_when_no_rule_matches_with_limitation() -> None:
    rs = rules(rule("a", "include", "folder_id", "archive"))
    result = evaluate_filters(rs, full())
    check(result.verdict is FilterVerdict.NO_MATCH, "no_match, not include")
    check(result.reasons == (), "no reason for no_match")
    check(result.matched == (), "nothing matched")
    check(limits(result) == [("no_rule_matched", "no rule matched")], "limited")
    check(result.status is TerminalStatus.INCOMPLETE, "incomplete")


def test_no_match_does_not_default_to_exclude_either() -> None:
    rs = rules(rule("a", "exclude", "folder_id", "archive"))
    result = evaluate_filters(rs, full())
    check(result.verdict is FilterVerdict.NO_MATCH, "no_match, not exclude")


def test_missing_field_gives_unknown_with_limitation() -> None:
    rs = rules(rule("a", "include", "sender_domain", "example.com"))
    result = evaluate_filters(rs, full(sender_domain=None))
    check(result.verdict is FilterVerdict.UNKNOWN, "unknown")
    check(result.evaluations[0].outcome == "unknown", "rule is unknown")
    check(result.matched == (), "unknown is not a match")
    check([r.code for r in result.reasons] == ["unknown_rule"], "reason")
    check(limits(result) == [("missing_field", "sender_domain")], "limitation")
    check(result.status is TerminalStatus.INCOMPLETE, "incomplete")


def test_each_field_reports_missing_by_name() -> None:
    cases = {
        "sender_domain": {"sender_domain": None},
        "folder_id": {"folder_id": None},
        "label": {"labels": None},
        "subject_prefix": {"subject": None},
    }
    for field, change in cases.items():
        result = evaluate_filters(
            rules(rule("a", "include", field, "x")), full(**change)
        )
        check(limits(result) == [("missing_field", field)], f"missing {field}")


def test_empty_label_list_is_known_not_missing() -> None:
    result = evaluate_filters(
        rules(rule("a", "include", "label", "x")), full(labels=())
    )
    check(result.evaluations[0].outcome == "not_matched", "known, no match")
    check(limits(result) == [("no_rule_matched", "no rule matched")], "no match only")


def test_unknown_rule_blocks_include() -> None:
    rs = rules(
        rule("a", "include", "folder_id", "inbox"),
        rule("b", "exclude", "sender_domain", "example.com"),
    )
    result = evaluate_filters(rs, full(sender_domain=None))
    check(result.matched == ("a",), "include matched")
    check(result.verdict is FilterVerdict.UNKNOWN, "unknown rule blocks include")
    check(limits(result) == [("missing_field", "sender_domain")], "limitation")


def test_exclude_survives_an_unknown_rule_but_is_incomplete() -> None:
    rs = rules(
        rule("a", "exclude", "folder_id", "inbox"),
        rule("b", "include", "sender_domain", "example.com"),
    )
    result = evaluate_filters(rs, full(sender_domain=None))
    check(result.verdict is FilterVerdict.EXCLUDE, "exclude")
    check(result.status is TerminalStatus.INCOMPLETE, "incomplete")
    check(len(result.limitations) == 1, "limitation kept")


def test_unknown_verdict_never_complete_or_unlimited() -> None:
    cases = [
        (rules(rule("a", "include", "label", "work")), full(labels=None)),
        (
            rules(
                rule("a", "include", "folder_id", "inbox"),
                rule("b", "include", "label", "w"),
            ),
            full(labels=None),
        ),
        (rules(rule("a", "include", "folder_id", "inbox")), full(folder_id=None)),
    ]
    for rs, record in cases:
        result = evaluate_filters(rs, record)
        check(result.verdict is FilterVerdict.UNKNOWN, "unknown case")
        check(bool(result.limitations), "unknown carries a limitation")
        check(result.status is not TerminalStatus.COMPLETE, "not complete")


def test_no_match_carries_a_limitation_and_is_incomplete() -> None:
    cases = [
        (rules(rule("a", "include", "folder_id", "zzz")), full()),
        (rules(rule("a", "exclude", "label", "zzz")), full()),
    ]
    for rs, record in cases:
        result = evaluate_filters(rs, record)
        check(result.verdict is FilterVerdict.NO_MATCH, "no_match case")
        check(bool(result.limitations), "no_match carries a limitation")
        check(result.status is not TerminalStatus.COMPLETE, "not complete")


def unknown_model(
    status: TerminalStatus, limitations: tuple[Limitation, ...] = ()
) -> FilterEvaluation:
    return FilterEvaluation(
        rule_set_version="v",
        evaluations=(RuleEvaluation(rule_id="a", rule_version="1", outcome="unknown"),),
        matched=(),
        verdict=FilterVerdict.UNKNOWN,
        reasons=(Reason(code="unknown_rule", rule_ids=("a",)),),
        status=status,
        limitations=limitations,
    )


def test_model_refuses_unknown_complete_without_limitation() -> None:
    limit = (Limitation("missing_field", "folder_id"),)
    for status, limitations in [
        (TerminalStatus.COMPLETE, ()),
        (TerminalStatus.INCOMPLETE, ()),
        (TerminalStatus.COMPLETE, limit),
    ]:
        with pytest.raises(ValueError):
            unknown_model(status, limitations)
    ok = unknown_model(TerminalStatus.INCOMPLETE, limit)
    check(ok.verdict is FilterVerdict.UNKNOWN, "limited unknown is valid")


def test_case_folding_rules() -> None:
    record = full(sender_domain="EXAMPLE.com", folder_id="Inbox", subject="RE: Plan")
    rs = rules(
        rule("a", "include", "sender_domain", "Example.Com"),
        rule("b", "include", "folder_id", "inbox"),
        rule("c", "include", "subject_prefix", "re:"),
        rule("d", "include", "label", "WORK"),
        rule("e", "include", "subject_prefix", "plan"),
    )
    result = evaluate_filters(rs, record)
    check(result.matched == ("a", "c", "d"), "folder is exact, prefix is a prefix")


def test_order_independent() -> None:
    items = [
        rule("r1", "include", "folder_id", "inbox"),
        rule("r2", "exclude", "label", "work"),
        rule("r3", "include", "sender_domain", "example.com"),
        rule("r4", "exclude", "subject_prefix", "zzz"),
        rule("r5", "include", "label", "none"),
    ]
    want = evaluate_filters(rules(*items), full(labels=("Work",)))
    gen = random.Random(3)
    for _ in range(10):
        gen.shuffle(items)
        got = evaluate_filters(rules(*items), full(labels=("Work",)))
        check(got == want, "same result for any rule order")
        check(got.model_dump() == want.model_dump(), "same dump")
    check(
        [e.rule_id for e in want.evaluations] == ["r1", "r2", "r3", "r4", "r5"],
        "sorted",
    )


def test_rule_versions_and_set_version_are_carried() -> None:
    rs = rules(
        rule("a", "include", "folder_id", "inbox", version="7"),
        rule("b", "include", "folder_id", "x", version="9"),
        version="set-42",
    )
    result = evaluate_filters(rs, full())
    check(result.rule_set_version == "set-42", "rule set version")
    check(
        [(e.rule_id, e.rule_version) for e in result.evaluations]
        == [("a", "7"), ("b", "9")],
        "rule versions",
    )


def test_duplicate_rule_id_is_rejected_with_fixed_text() -> None:
    rs = rules(
        rule("r-secret-7", "include", "folder_id", "inbox"),
        rule("r-secret-7", "exclude", "folder_id", "inbox"),
    )
    with pytest.raises(DuplicateRuleIdError) as info:
        evaluate_filters(rs, full())
    check(str(info.value) == "duplicate rule id in rule set", "fixed text")
    check("r-secret-7" not in str(info.value), "no rule id echoed")


def test_empty_rule_set_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RuleSet(rule_set_version="v", rules=())


def test_errors_do_not_echo_input_values() -> None:
    texts: list[str] = []
    with pytest.raises(ValidationError) as info:
        FilterInput(sender_domain=FAKE_EMAIL, labels=[FAKE_EMAIL])  # type: ignore[arg-type]
    texts.append(str(info.value))
    with pytest.raises(ValidationError) as info:
        FilterInput(subject=FAKE_SUBJECT + "\n", folder_id=FAKE_EMAIL, extra=FAKE_EMAIL)  # type: ignore[call-arg]
    texts.append(str(info.value))
    with pytest.raises(DuplicateRuleIdError) as dup:
        evaluate_filters(
            rules(
                rule("a", "include", "sender_domain", FAKE_EMAIL),
                rule("a", "exclude", "sender_domain", FAKE_EMAIL),
            ),
            full(sender_domain=FAKE_EMAIL, subject=FAKE_SUBJECT),
        )
    texts.append(str(dup.value))
    for text in texts:
        check(FAKE_EMAIL not in text, "email absent from error text")
        check(FAKE_SUBJECT not in text, "subject absent from error text")


def test_result_does_not_hold_input_values() -> None:
    rs = rules(rule("a", "include", "sender_domain", FAKE_EMAIL))
    result = evaluate_filters(rs, full(sender_domain=FAKE_EMAIL, subject=FAKE_SUBJECT))
    check(FAKE_EMAIL not in result.model_dump_json(), "email absent from result")
    check(FAKE_SUBJECT not in result.model_dump_json(), "subject absent")


def test_result_is_frozen() -> None:
    result = evaluate_filters(rules(rule("a", "include", "folder_id", "inbox")), full())
    with pytest.raises(ValidationError):
        result.verdict = FilterVerdict.EXCLUDE  # type: ignore[misc]
    with pytest.raises(ValidationError):
        result.matched = ()  # type: ignore[misc]
    check(isinstance(result.matched, tuple), "tuple, not a mutable list")
    with pytest.raises(ValidationError):
        full().sender_domain = "x"  # type: ignore[misc]


class _CountingStr(str):
    """A ``str`` that counts its ``casefold`` calls in a shared list."""

    calls: list[int]

    def casefold(self) -> str:
        self.calls.append(1)
        return super().casefold()


def _counting(text: str, calls: list[int]) -> _CountingStr:
    item = _CountingStr(text)
    item.calls = calls
    return item


def test_labels_are_casefolded_once_per_evaluation() -> None:
    n_labels, n_rules = 256, 1024
    calls: list[int] = []
    labels = tuple(
        _counting(f"Label{i:04d}" + "X" * 990, calls) for i in range(n_labels)
    )
    # Validation requires an exact str, so build the record without it.
    record = FilterInput.model_construct(labels=labels)
    items = tuple(
        rule(f"r{i:04d}", "include", "label", f"label{i:04d}" + "x" * 990)
        for i in range(n_rules)
    )
    result = evaluate_filters(rules(*items), record)
    check(
        len(calls) <= n_labels + 4,
        "casefold work does not grow with rules x labels",
    )
    check(len(result.matched) == n_labels, "each rule with a label match matches")
    check(result.matched[0] == "r0000", "matched IDs are sorted")
    check(result.verdict is FilterVerdict.INCLUDE, "verdict is include")
    again = evaluate_filters(rules(*reversed(items)), record)
    check(again == result, "result is deterministic")


def test_repr_hides_input_values() -> None:
    text = repr(
        FilterInput(
            sender_domain=FAKE_EMAIL,
            folder_id="fake-folder-id",
            labels=("fake-label",),
            subject=FAKE_SUBJECT,
        )
    )
    for secret in (FAKE_EMAIL, "fake-folder-id", "fake-label", FAKE_SUBJECT):
        check(secret not in text, "repr hides input value")
