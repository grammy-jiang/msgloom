"""
Portable builders for the C0-07 result tests.

All data is synthetic. A builder returns plain JSON-like data, and
:func:`make` validates it through ``model_validate_json``, so each test
variant passes the same strict path as a decoded payload.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import asdict
from typing import Any

import pytest

from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.a2_kedro.contracts.identity import lineage_digest
from msgloom.a2_kedro.contracts.result_manifest import ResultManifest
from msgloom.a2_kedro.contracts.results import (
    FilterResult,
    GroupResult,
    Prepared,
    header_for,
)
from msgloom.contracts import ResultRef
from tests.a2_kedro.helpers import WORKSET_REF, accepted_ref, hexd, root_for, workset
from tests.a2_kedro.test_c0_04 import rich
from tests.a2_kedro.test_c0_05 import make_zones

SENTINEL = "alice.private@example.invalid"


def ref(char: str, kind: str, version: str = "1") -> ResultRef:
    """Return an accepted-key ref for ``kind``."""
    return accepted_ref(char, kind, version)


def head(kind: str) -> dict[str, Any]:
    """Return the header data of the approved pair of ``kind``."""
    return header_for(kind).model_dump(mode="json")


def make(cls: Any, data: dict[str, Any]) -> Any:
    """Validate ``data`` through the strict JSON path."""
    return cls.model_validate_json(json.dumps(data))


def prepared_data(**changes: Any) -> dict[str, Any]:
    """Return valid ``prepared@2`` data. The record is COMPLETE."""
    lineage = (
        ref("1", "parsed_parts"),
        ref("2", "normalized_content"),
        ref("3", "zones"),
        ref("4", "native_relations"),
    )
    data: dict[str, Any] = {
        "header": head("prepared"),
        "root": root_for(workset(1)).model_dump(mode="json"),
        "status": "complete",
        "limitations": [],
        "parsed": asdict(lineage[0]),
        "normalized": asdict(lineage[1]),
        "zones": asdict(lineage[2]),
        "relations": asdict(lineage[3]),
        "lineage_sha256": lineage_digest(lineage),
        "parts": [
            {
                "part_id": part.part_id,
                "role": part.role,
                "status": "present",
                "sha256": hexd("a"),
            }
            for part in rich().parts
        ],
        "blocks": [
            {
                "part_id": "p0",
                "zone_id": zone.zone_id,
                "kind": zone.kind,
                "original": {"start": zone.original.start, "end": zone.original.end},
                "text_sha256": hexd("d"),
            }
            for zone in make_zones().zones
        ],
        "sent_at": 1_700_000_000,
        "participants": [{"role": "from", "identity_sha256": hexd("e")}],
        "rule_version": "rule-1",
    }
    return {**data, **changes}


def rule(rule_id: str, outcome: str, effect: str | None = None) -> dict[str, Any]:
    """Return one rule evaluation."""
    item: dict[str, Any] = {
        "rule_id": rule_id,
        "rule_version": "1",
        "outcome": outcome,
        "effect": effect,
    }
    return item


def filter_data(**changes: Any) -> dict[str, Any]:
    """Return valid ``filter_result@2`` data with two matched rules."""
    data: dict[str, Any] = {
        "header": head("filter_result"),
        "prepared": asdict(ref("5", "prepared", "2")),
        "policy_id": "policy-1",
        "policy_version": "7",
        "evaluations": [
            rule("r1", "matched", "include"),
            rule("r2", "matched", "include"),
            rule("r3", "not_matched"),
        ],
        "matched": ["r1", "r2"],
        "verdict": "include",
        "reasons": [],
        "status": "complete",
        "limitations": [],
    }
    return {**data, **changes}


def node(node_id: str, scope: str = "T1") -> dict[str, str]:
    """Return a node in a thread scope."""
    return {"scope_kind": "thread", "scope_id": scope, "node_id": node_id}


def member(node_id: str, char: str, scope: str = "T1") -> dict[str, Any]:
    """Return a member at ``node_id`` with a prepared ref."""
    return {
        "node": node(node_id, scope),
        "prepared": asdict(ref(char, "prepared", "2")),
    }


def reply(source: str, target: str, kind: str = "reply_to") -> dict[str, Any]:
    """Return native evidence that ``source`` replies to ``target``."""
    return {"kind": kind, "source": node(source), "target": node(target), "basis": "h"}


def group_data(**changes: Any) -> dict[str, Any]:
    """Return valid ``group_result@2`` data: three members, two replies."""
    data: dict[str, Any] = {
        "header": head("group_result"),
        "scope_kind": "thread",
        "scope_id": "T1",
        "rule_version": "grp-1",
        "relations": asdict(ref("4", "native_relations")),
        "members": [member("a", "5"), member("b", "6"), member("c", "7")],
        "evidence": [reply("b", "a"), reply("c", "b")],
        "unknown": [],
        "status": "complete",
        "limitations": [],
    }
    return {**data, **changes}


def entry(index: int | None, kind: str, char: str, **changes: Any) -> dict[str, Any]:
    """Return one manifest entry."""
    version = {"prepared": "2", "filter_result": "2", "group_result": "2"}.get(
        kind, "1"
    )
    version = "2" if kind == "prepared_transitions" else version
    item: dict[str, Any] = {
        "workset_index": index,
        "ref": asdict(ref(char, kind, version)),
        "metadata_sha256": hexd(char),
        "status": "complete",
        "limitations": [],
    }
    return {**item, **changes}


HELD_LIMIT = [{"code": "held", "detail": "operator_repair"}]


def ordered(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return manifest entries in canonical order."""

    def key(item: dict[str, Any]) -> tuple[int, str, str]:
        index = -1 if item["workset_index"] is None else item["workset_index"]
        return (index, item["ref"]["kind"], item["ref"]["result_id"])

    return sorted(entries, key=key)


def manifest_data(**changes: Any) -> dict[str, Any]:
    """Return a valid manifest: one prepared, one held, one batch."""
    entries = [
        entry(0, "prepared", "1"),
        entry(0, "filter_result", "2"),
        entry(
            1, "a2_input_disposition", "3", status="incomplete", limitations=HELD_LIMIT
        ),
        entry(None, "prepared_transitions", "4"),
    ]
    entries = ordered(entries)
    data: dict[str, Any] = {
        "header": head("a2_result_manifest"),
        "workset": asdict(WORKSET_REF),
        "entries": entries,
        "configuration_version": "config-1",
        "code_version": "code-1",
        "policy_version": "policy-1",
        "limitations": HELD_LIMIT,
    }
    return {**data, **changes}


def edit(data: dict[str, Any], path: str, value: Any) -> dict[str, Any]:
    """Return a deep copy of ``data`` with the dotted ``path`` replaced."""
    out = deepcopy(data)
    target: Any = out
    *parents, last = path.split(".")
    for key in parents:
        target = target[int(key)] if isinstance(target, list) else target[key]
    if isinstance(target, list):
        target[int(last)] = value
    else:
        target[last] = value
    return out


BUILDERS = {
    Prepared: prepared_data,
    FilterResult: filter_data,
    GroupResult: group_data,
    ResultManifest: manifest_data,
}


ALL = list(BUILDERS)
BAD = (A2ContractError, ValueError)


def reject_data(cls: Any, data: dict[str, Any], match: str) -> None:
    with pytest.raises(BAD, match=match or None):
        make(cls, data)


def limit(code: str) -> dict[str, str]:
    return {"code": code, "detail": "d"}


def ref_dict(char: str, kind: str, version: str) -> dict[str, str]:
    return {
        "result_id": "a2-accepted:" + hexd(char),
        "kind": kind,
        "schema_version": version,
    }


def old_member() -> dict[str, Any]:
    return {**member("a", "5"), "prepared": ref_dict("5", "prepared", "1")}
