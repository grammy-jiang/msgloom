"""Mutation tests for the hand-written T0-08 historical reader oracle.

Each answer, edit and key of every case is changed one at a time,
and every rule of the reference reader is switched off one at a time. Each
change must be detected. The reference reader lives in
``test_gold_t0_08.py``. This module never imports ``msgloom``.
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Iterator
from typing import Any

import pytest
from test_gold_t0_08 import (
    CODES,
    OPERATIONS,
    PINNED,
    RULE_CASES,
    _canonical,
    _case,
    _cases,
    _doc,
    _ids,
    check_case,
)
from test_gold_t0_08_reader import RULES, Case, evaluate, materialize


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


def _perturb(value: Any) -> Any:
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    if isinstance(value, str):
        return value + "x"
    if isinstance(value, list):
        return [*value, "extra"] if value else ["extra"]
    if value is None:
        return "extra"
    return None


def _answer_mutants(case: Case) -> Iterator[tuple[str, Case]]:
    exp = case["expected"]
    for path in _paths(exp):
        node = exp
        for step in path[:-1]:
            node = node[step]
        if isinstance(node[path[-1]], dict):
            continue
        m = copy.deepcopy(case)
        target = m["expected"]
        for step in path[:-1]:
            target = target[step]
        target[path[-1]] = _perturb(node[path[-1]])
        yield "perturb " + "/".join(map(str, path)), m
    if exp["decision"] == "reject":
        for code in CODES:
            if code != exp["code"]:
                m = copy.deepcopy(case)
                m["expected"]["code"] = code
                yield f"code {code}", m
    m = copy.deepcopy(case)
    m["expected"]["surprise"] = 1
    yield "extra expected key", m


def _edit_mutants(case: Case) -> Iterator[tuple[str, Case]]:
    """Delete one edit. Every edit of every case must matter."""
    for i in range(len(case["input"]["stored"]["edits"])):
        m = copy.deepcopy(case)
        del m["input"]["stored"]["edits"][i]
        yield f"delete edit {i}", m


def _routing_mutants(case: Case) -> Iterator[tuple[str, Case]]:
    """Change the label, the target or the operation.

    Some of these keep the outcome (for example another bad label on a payload
    that fails first). A case needs only one routing change that the checker
    detects, so that the label and the operation are not dead data.
    """
    stored = case["input"]["stored"]
    for label in ("1", "2", "3"):
        if label != stored["schema_version"]:
            m = copy.deepcopy(case)
            m["input"]["stored"]["schema_version"] = label
            yield f"label {label}", m
    if stored["kind"] != "prepared":
        m = copy.deepcopy(case)
        m["input"]["stored"]["kind"] = "prepared"
        yield "kind prepared", m
    if "target" in case["input"]:
        m = copy.deepcopy(case)
        flip = "1" if case["input"]["target"].endswith("2") else "2"
        m["input"]["target"] = f"triage_input@{flip}"
        yield f"target {flip}", m
    for op in OPERATIONS:
        if op == case["input"]["operation"]:
            continue
        if op == "project_to_v1" and stored["schema_version"] != "2":
            continue
        m = copy.deepcopy(case)
        m["input"]["operation"] = op
        if op == "bind_triage_input":
            m["input"]["target"] = "triage_input@1"
        elif "target" in m["input"]:
            del m["input"]["target"]
        yield f"operation {op}", m


def _key_mutants(case: Case) -> Iterator[tuple[str, Case]]:
    for path in _paths(case):
        m = copy.deepcopy(case)
        del _parent(m, path)[path[-1]]
        yield "delete key " + "/".join(map(str, path)), m


@pytest.mark.parametrize("case_id", _ids())
def test_every_mutation_is_detected(case_id: str) -> None:
    doc, cases = _doc(), _cases()
    case = _case(case_id)
    count = 0
    makers = (_answer_mutants, _edit_mutants, _key_mutants)
    for make in makers:
        for label, mutant in make(case):
            count += 1
            if not check_case(mutant, doc, cases):
                pytest.fail(f"{case_id}: mutation {label!r} went unnoticed")
    if count < 15:
        pytest.fail(f"{case_id}: only {count} mutations were tried")


@pytest.mark.parametrize("case_id", _ids())
def test_label_and_operation_are_not_dead_data(case_id: str) -> None:
    doc, cases = _doc(), _cases()
    case = _case(case_id)
    hits = [
        label
        for label, mutant in _routing_mutants(case)
        if check_case(mutant, doc, cases)
    ]
    if not hits:
        pytest.fail(f"{case_id}: no routing change was detected")


@pytest.mark.parametrize("rule", RULES)
def test_each_rule_has_a_mutant_that_dies(rule: str) -> None:
    doc = _doc()
    named = RULE_CASES.get(rule, ())
    if not named:
        pytest.fail(f"rule {rule} has no designated case")
    for suffix in named:
        case = _case(f"T0-08-{suffix}")
        if evaluate(case, doc["bases"]) != case["expected"]:
            pytest.fail(f"{suffix}: the full reader disagrees with the fixture")
        if evaluate(case, doc["bases"], frozenset({rule})) == case["expected"]:
            pytest.fail(f"{suffix}: switching off {rule} changed nothing")


def test_rule_table_is_complete_and_has_no_dead_rule() -> None:
    if set(RULE_CASES) != set(RULES):
        pytest.fail("RULE_CASES keys differ from RULES")
    doc = _doc()
    for rule in RULES:
        killed = {
            c["case_id"][-3:]
            for c in _cases()
            if evaluate(c, doc["bases"], frozenset({rule})) != c["expected"]
        }
        if not killed:
            pytest.fail(f"rule {rule} kills no case")
        if not set(RULE_CASES[rule]) <= killed:
            pytest.fail(f"rule {rule}: designated cases {set(RULE_CASES[rule]) - killed} survive")  # fmt: skip


def test_unknown_rule_name_changes_nothing() -> None:
    doc = _doc()
    case = _case("T0-08-P01")
    if evaluate(case, doc["bases"], frozenset({"no-such-rule"})) != case["expected"]:
        pytest.fail("an unknown rule name changed the result")


def test_pinned_digest_detects_base_and_pin_changes() -> None:
    doc, cases = _doc(), _cases()
    for case_id in PINNED:
        case = _case(case_id)
        pin = case["pinned"]
        data = _canonical(materialize(case["input"]["stored"], doc["bases"]))
        if pin["canonical_sha256"] != hashlib.sha256(data).hexdigest():
            pytest.fail(f"{case_id}: stored digest is stale")
        bumped = copy.deepcopy(case)
        bumped["pinned"]["canonical_byte_count"] += 1
        wrong = copy.deepcopy(case)
        wrong["pinned"]["canonical_sha256"] = "0" * 64
        bare = {k: v for k, v in case.items() if k != "pinned"}
        for label, mutant in (("count", bumped), ("sha", wrong), ("missing", bare)):
            if not check_case(mutant, doc, cases):
                pytest.fail(f"{case_id}: pin mutation {label} went unnoticed")
        edited = copy.deepcopy(doc)
        edited["bases"][case["input"]["stored"]["base"]]["body"] += " "
        if not check_case(case, edited, cases):
            pytest.fail(f"{case_id}: a change of the base went unnoticed")
    unpinned = copy.deepcopy(_case("T0-08-P03"))
    unpinned["pinned"] = {"canonical_sha256": "0" * 64, "canonical_byte_count": 1}
    if not check_case(unpinned, doc, cases):
        pytest.fail("a pin on an unpinned case went unnoticed")


def test_historical_link_detects_a_changed_view() -> None:
    doc, cases = _doc(), _cases()
    mutant = copy.deepcopy(_case("T0-08-P06"))
    mutant["expected"]["view"]["body"] = "changed"
    if not check_case(mutant, doc, cases):
        pytest.fail("a changed historical view went unnoticed")
    broken = copy.deepcopy(_case("T0-08-P06"))
    broken["links"]["same_view_as"] = "T0-08-P99"
    if not check_case(broken, doc, cases):
        pytest.fail("a dangling link went unnoticed")
