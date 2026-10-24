"""
C0-00: the decision record matches the code identifiers.

The test parses the tables of ``docs/decisions/a2-v2-schema-ids.md``. Each
table row names one check: ``Kind``, ``Version``, ``Fields``, ``Literal``,
``Enum``, ``Const`` or ``Dict``. A positive test compares every row with the
code. A negative test shows that a wrong row is detected.
"""

from __future__ import annotations

import importlib
import re
import typing
from enum import Enum
from pathlib import Path
from typing import Any

import pytest

from msgloom.a2_kedro.contracts.header import approved_pairs
from tests.a2_kedro.helpers import check

DECISION = (
    Path(__file__).resolve().parents[2] / "docs" / "decisions" / "a2-v2-schema-ids.md"
)
TICKS = re.compile(r"`([^`]*)`")
Tables = dict[str, dict[str, list[str]]]


def parse_tables(text: str) -> Tables:
    """Return ``{heading: {row label: [backticked values]}}``."""
    tables: Tables = {}
    heading = ""
    for line in text.splitlines():
        if line.startswith("### "):
            heading = line[4:].strip()
            continue
        if not heading or not line.startswith("| "):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 2 or cells[0] in ("Item", "---") or set(cells[0]) == {"-"}:
            continue
        tables.setdefault(heading, {})[cells[0]] = TICKS.findall(cells[1])
    return tables


def parse_kind_table(text: str) -> dict[str, str]:
    """Return ``{kind: version}`` from the "Kinds and versions" table."""
    section = text.split("## Kinds and versions", 1)[1].split("\n## ", 1)[0]
    pairs: dict[str, str] = {}
    for line in section.splitlines():
        found = re.match(r"\| `([a-z_0-9]+)` \| (\d+) \|", line)
        if found:
            pairs[found.group(1)] = found.group(2)
    return pairs


def _resolve(module: Any, name: str) -> Any:
    if "." not in name:
        return getattr(module, name)
    cls_name, field = name.split(".", 1)
    return getattr(module, cls_name).model_fields[field].annotation


def check_row(module: Any, label: str, values: list[str]) -> str | None:
    """Return a problem text for one row, or ``None`` when it matches."""
    verb, _, name = label.partition(" ")
    if verb == "Fields":
        actual = list(getattr(module, name).model_fields)
        return None if actual == values else f"{label}: {actual}"
    if verb == "Literal":
        actual = [str(item) for item in typing.get_args(_resolve(module, name))]
        return None if actual == values else f"{label}: {actual}"
    if verb == "Enum":
        enum: type[Enum] = getattr(module, name)
        actual = [str(member.value) for member in enum]
        return None if actual == values else f"{label}: {actual}"
    if verb == "Const":
        actual_text = str(getattr(module, name))
        return None if [actual_text] == values else f"{label}: {actual_text}"
    if verb == "Dict":
        actual_items = [f"{k}={v}" for k, v in getattr(module, name).items()]
        return None if actual_items == values else f"{label}: {actual_items}"
    return f"{label}: unknown check"


def problems(tables: Tables, pairs: dict[str, str]) -> list[str]:
    """Return every mismatch between the tables and the code."""
    found: list[str] = []
    for heading, rows in tables.items():
        module = importlib.import_module(rows["Module"][0])
        for label, values in rows.items():
            if label == "Module":
                continue
            if label in ("Kind", "Version"):
                continue
            if bad := check_row(module, label, values):
                found.append(f"{heading}: {bad}")
        if "Kind" in rows:
            kind, version = rows["Kind"][0], rows["Version"][0]
            if pairs.get(kind) != version:
                found.append(f"{heading}: {kind}@{version} not approved")
    return found


def decision_text() -> str:
    return DECISION.read_text(encoding="utf-8")


def test_decision_tables_match_code() -> None:
    tables = parse_tables(decision_text())
    check(len(tables) >= 8, "decision record has the contract tables")
    found = problems(tables, approved_pairs())
    check(not found, f"decision record disagrees with code: {found}")


def test_every_contract_kind_has_a_table() -> None:
    tables = parse_tables(decision_text())
    pairs = {
        row["Kind"][0]: row["Version"][0] for row in tables.values() if "Kind" in row
    }
    for kind in (
        "frozen_source_selection",
        "extracted_components",
        "native_relations",
        "prepared_transitions",
        "a2_input_disposition",
        "a2_completion_receipt",
        "triage_input",
    ):
        check(kind in pairs, f"missing table for {kind}")
    for kind, version in pairs.items():
        check(approved_pairs()[kind] == version, f"version of {kind}")


def test_kind_table_equals_approved_pairs() -> None:
    check(
        parse_kind_table(decision_text()) == approved_pairs(),
        "kinds table equals approved header pairs",
    )


def test_nine_provisional_decisions_are_marked() -> None:
    section = decision_text().split("## Provisional wire field decisions", 1)[1]
    section = section.split("\n## ", 1)[0]
    rows = re.findall(r"^\| (\d) \| PROVISIONAL \|", section, flags=re.MULTILINE)
    check(rows == [str(n) for n in range(1, 10)], "nine PROVISIONAL rows")
    check(
        "may not change an identifier" in decision_text(),
        "change prohibition is stated",
    )


@pytest.mark.parametrize(
    ("heading", "label", "wrong"),
    [
        ("extracted_components@1", "Fields ComponentEntry", ["component_id"]),
        ("extracted_components@1", "Literal ComponentRole", ["primary", "other"]),
        ("native_relations@1", "Const MAX_NODES", ["1025"]),
        ("prepared_transitions@2", "Const BATCH_DOMAIN", ["a2-transition-batch@2"]),
        ("a2_input_disposition@1", "Enum HeldReason", ["proof_missing"]),
        ("header", "Dict LIMITS", ["max_depth=33"]),
        ("frozen_source_selection@1", "Literal FrozenRoot.role", ["primary"]),
    ],
)
def test_mismatched_row_is_detected(heading: str, label: str, wrong: list[str]) -> None:
    tables = parse_tables(decision_text())
    check(label in tables[heading], "row exists before mutation")
    tables[heading][label] = wrong
    found = problems(tables, approved_pairs())
    check(
        any(item.startswith(f"{heading}: {label}") for item in found),
        f"mutated row {label} was not detected",
    )


def test_mismatched_kind_version_is_detected() -> None:
    tables = parse_tables(decision_text())
    tables["prepared_transitions@2"]["Version"] = ["1"]
    found = problems(tables, approved_pairs())
    check(
        any("prepared_transitions@1 not approved" in item for item in found),
        "wrong version was not detected",
    )
    tables = parse_tables(decision_text())
    tables["triage_input@2"]["Kind"] = ["triage_inputs"]
    check(bool(problems(tables, approved_pairs())), "wrong kind not detected")
