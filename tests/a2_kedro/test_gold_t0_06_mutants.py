"""Mutation tests for the hand-written T0-06 coverage oracle.

Every answer, input element and key of every case is changed or deleted one
at a time, and every checker rule is switched off one at a time. Each change
must be detected. The checker lives in ``test_gold_t0_06.py``. This module
never imports ``msgloom`` code.
"""

from __future__ import annotations

import copy
from collections.abc import Iterator
from typing import Any

import pytest
from test_gold_t0_06 import (
    CEILINGS,
    CODES,
    COVERAGE_VALUES,
    RULE_CASES,
    RULES,
    SCOPE_KEYS,
    Case,
    _case,
    _cases,
    _ids,
    check_case,
    evaluate,
)


def _paths(node: Any, path: tuple[Any, ...] = ()) -> Iterator[tuple[Any, ...]]:
    """Yield the path of every dict key in the tree."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield (*path, key)
            yield from _paths(value, (*path, key))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _paths(value, (*path, i))


def _parent(case: Case, path: tuple[Any, ...]) -> Any:
    node: Any = case
    for step in path[:-1]:
        node = node[step]
    return node


def _answer_mutants(case: Case) -> Iterator[tuple[str, Case]]:
    exp = case["expected"]
    for item, label in exp["coverage"].items():
        for other in COVERAGE_VALUES:
            if other != label:
                m = copy.deepcopy(case)
                m["expected"]["coverage"][item] = other
                yield f"{item} -> {other}", m
    for i in range(len(exp["problems"])):
        m = copy.deepcopy(case)
        del m["expected"]["problems"][i]
        yield f"drop problem {i}", m
    for code in CODES:
        m = copy.deepcopy(case)
        m["expected"]["problems"] = sorted(
            [*exp["problems"], {"subject": "zz-extra", "code": code}],
            key=lambda p: (p["subject"], p["code"]),
        )
        yield f"extra {code}", m
    for other in CEILINGS:
        if other != exp["ceiling"]:
            m = copy.deepcopy(case)
            m["expected"]["ceiling"] = other
            yield f"ceiling {other}", m


def _input_mutants(case: Case) -> Iterator[tuple[str, Case]]:
    """Delete one input element. No element may be dead data."""
    inp = case["input"]
    spots = [("store", None), ("receipt", None)]
    spots += [("workset", key) for key, _ in SCOPE_KEYS]
    for top, key in spots:
        rows = inp[top] if key is None else inp[top][key]
        for i in range(len(rows)):
            m = copy.deepcopy(case)
            target = m["input"][top] if key is None else m["input"][top][key]
            del target[i]
            yield f"delete {top}.{key}[{i}]", m


def _key_mutants(case: Case) -> Iterator[tuple[str, Case]]:
    for path in _paths(case):
        m = copy.deepcopy(case)
        del _parent(m, path)[path[-1]]
        yield "delete key " + "/".join(map(str, path)), m


@pytest.mark.parametrize("case_id", _ids())
def test_every_mutation_is_detected(case_id: str) -> None:
    case = _case(case_id)
    count = 0
    for make in (_answer_mutants, _input_mutants, _key_mutants):
        for label, mutant in make(case):
            count += 1
            if not check_case(mutant):
                pytest.fail(f"{case_id}: mutation {label!r} went unnoticed")
    if count < 20:
        pytest.fail(f"{case_id}: only {count} mutations were tried")


@pytest.mark.parametrize("rule", RULES)
def test_each_rule_has_a_mutant_that_dies(rule: str) -> None:
    named = RULE_CASES.get(rule, ())
    if not named:
        pytest.fail(f"rule {rule} has no designated case")
    for suffix in named:
        case = _case(f"T0-06-{suffix}")
        if evaluate(case, frozenset({rule})) == case["expected"]:
            pytest.fail(f"{suffix}: switching off {rule} changed nothing")
        if evaluate(case) != case["expected"]:
            pytest.fail(f"{suffix}: the full checker disagrees with the fixture")


def test_rule_table_and_fixture_cover_every_rule() -> None:
    if set(RULE_CASES) != set(RULES):
        pytest.fail("RULE_CASES keys differ from RULES")
    seen = {p["code"] for c in _cases() for p in c["expected"]["problems"]}
    if seen != set(CODES):
        pytest.fail(f"fixture problem codes differ: {sorted(seen ^ set(CODES))}")
    if {c["expected"]["ceiling"] for c in _cases()} != set(CEILINGS):
        pytest.fail("fixture does not show every ceiling value")
    if {v for c in _cases() for v in c["expected"]["coverage"].values()} != set(COVERAGE_VALUES):  # fmt: skip
        pytest.fail("fixture does not show every coverage label")


def test_empty_scope_and_unknown_rule_are_stable() -> None:
    empty = evaluate(_case("T0-06-P11"))
    if empty != {"coverage": {}, "problems": [], "ceiling": "COMPLETE_ALLOWED"}:
        pytest.fail(f"empty scope gives {empty}")
    if evaluate(_case("T0-06-P01"), frozenset({"no-such-rule"})) != _case("T0-06-P01")["expected"]:  # fmt: skip
        pytest.fail("an unknown rule name changed the result")
