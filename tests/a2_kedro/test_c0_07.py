"""C0-07 prepared@2, filter_result@2, group_result@2 and the manifest."""

from __future__ import annotations

import json
from typing import Any

import pytest

from msgloom.a2_kedro.contracts.codec import (
    A2ContractError,
    canonical_json_bytes,
    sha256_hex,
)
from msgloom.a2_kedro.contracts.result_manifest import ResultManifest
from msgloom.a2_kedro.contracts.results import (
    FilterResult,
    GroupResult,
    Prepared,
    decode_result,
)
from msgloom.a2_kedro.contracts.schema_ids import STAGE_SCHEMAS, require_stage_schema
from tests.a2_kedro.helpers import check, hexd
from tests.a2_kedro.result_fixtures import (
    ALL,
    BAD,
    BUILDERS,
    edit,
    filter_data,
    group_data,
    head,
    limit,
    make,
    old_member,
    prepared_data,
    ref_dict,
    rule,
)
from tests.a2_kedro.result_fixtures import (
    reject_data as rejects,
)
from tests.a2_kedro.test_c0_04 import rich
from tests.a2_kedro.test_c0_05 import make_zones


@pytest.mark.parametrize("cls", ALL)
def test_round_trip_and_canonical_bytes_are_stable(cls: Any) -> None:
    value = make(cls, BUILDERS[cls]())
    data = value.encode()
    check(cls.decode(data) == value, "round trip")
    check(cls.decode(data).encode() == data, "bytes are stable")
    check(decode_result(data) == value, "header dispatch")
    check(sha256_hex(data) == sha256_hex(make(cls, BUILDERS[cls]()).encode()), "sha")
    key_order = canonical_json_bytes(json.loads(data))
    check(key_order == data, "keys sorted, no whitespace")


def test_wire_field_names_are_pinned() -> None:
    names = {cls: set(make(cls, BUILDERS[cls]()).model_dump()) for cls in ALL}
    check(
        names[Prepared]
        == {
            "header", "root", "status", "limitations", "parsed", "normalized",
            "zones", "relations", "lineage_sha256", "parts", "blocks", "sent_at",
            "participants", "rule_version",
        },
        "prepared fields",
    )  # fmt: skip
    check(
        names[FilterResult]
        == {
            "header", "prepared", "policy_id", "policy_version", "evaluations",
            "matched", "verdict", "reasons", "status", "limitations",
        },
        "filter fields",
    )  # fmt: skip
    check(
        names[GroupResult]
        == {
            "header", "scope_kind", "scope_id", "rule_version", "relations",
            "members", "evidence", "unknown", "status", "limitations",
        },
        "group fields",
    )  # fmt: skip
    check(
        names[ResultManifest]
        == {
            "header", "workset", "entries", "configuration_version",
            "code_version", "policy_version", "limitations",
        },
        "manifest fields",
    )  # fmt: skip


def test_schema_ids_come_from_the_allowlist() -> None:
    for cls in ALL:
        value = make(cls, BUILDERS[cls]())
        pair = (value.header.kind, value.header.version)
        check(pair == (cls.KIND, STAGE_SCHEMAS[cls.KIND]), "pair from allowlist")
    check(STAGE_SCHEMAS["prepared"] == "2", "prepared@2")
    check(STAGE_SCHEMAS["filter_result"] == "2", "filter_result@2")
    check(STAGE_SCHEMAS["group_result"] == "2", "group_result@2")


# --- version separation ---------------------------------------------------


@pytest.mark.parametrize("cls", [Prepared, FilterResult, GroupResult])
def test_v1_pair_is_refused_by_the_v2_codec(cls: Any) -> None:
    data = BUILDERS[cls]()
    old = {**data, "header": {**data["header"], "version": "1"}}
    rejects(cls, old, "")
    payload = canonical_json_bytes(old)
    with pytest.raises(A2ContractError, match="historical"):
        decode_result(payload)
    with pytest.raises(A2ContractError):
        cls.decode(payload)
    with pytest.raises(A2ContractError, match="read-only"):
        require_stage_schema(cls.KIND, "1")


def test_kinds_do_not_decode_as_each_other() -> None:
    prepared = make(Prepared, prepared_data()).encode()
    with pytest.raises(A2ContractError):
        FilterResult.decode(prepared)
    with pytest.raises(A2ContractError):
        GroupResult.decode(prepared)
    wrong_header = prepared_data(header=head("filter_result"))
    rejects(Prepared, wrong_header, "approved pair")
    for bad in (b"{}", b'{"header":1}', b'{"header":{"kind":1,"version":2}}'):
        with pytest.raises(A2ContractError):
            decode_result(bad)
    unknown = canonical_json_bytes({"header": {"kind": "x", "version": "2"}})
    with pytest.raises(A2ContractError, match="not a v2"):
        decode_result(unknown)


def test_a_missing_header_is_refused() -> None:
    data = prepared_data()
    del data["header"]
    rejects(Prepared, data, "header")


def test_historical_refs_are_refused_inside_v2_records() -> None:
    rejects(FilterResult, filter_data(prepared=ref_dict("5", "prepared", "1")), "wrong")
    rejects(GroupResult, group_data(members=[old_member()]), "wrong")


# --- prepared@2 -----------------------------------------------------------


@pytest.mark.parametrize("field", ["parsed", "normalized", "zones", "relations"])
def test_forged_or_missing_lineage_refs_are_refused(field: str) -> None:
    good = prepared_data()[field]
    forged_id = {**good, "result_id": "plain-id"}
    wrong_kind = {**good, "kind": "prepared", "schema_version": "2"}
    wrong_ver = {**good, "schema_version": "2"}
    for forged in (forged_id, wrong_kind, wrong_ver):
        rejects(Prepared, prepared_data(**{field: forged}), "reference")
    data = prepared_data()
    del data[field]
    with pytest.raises(BAD):
        make(Prepared, data)


def test_lineage_must_be_distinct_and_digest_bound() -> None:
    data = prepared_data()
    same = {**data["parsed"], "kind": "zones"}
    rejects(Prepared, {**data, "zones": data["zones"], "parsed": same}, "reference")
    rejects(Prepared, prepared_data(lineage_sha256=hexd("0")), "lineage digest")
    swapped = prepared_data(parsed=data["zones"], zones=data["parsed"])
    with pytest.raises(BAD):
        make(Prepared, swapped)


def test_prepared_keeps_every_part_and_every_zone() -> None:
    value = make(Prepared, prepared_data())
    value.validate_against(rich(), make_zones())
    check(len(value.parts) == 3 and len(value.blocks) == 3, "all kept")
    parts = prepared_data()["parts"]
    dropped_attachment = make(Prepared, prepared_data(parts=parts[:2]))
    with pytest.raises(A2ContractError, match="parts differ"):
        dropped_attachment.validate_against(rich(), make_zones())
    blocks = prepared_data()["blocks"]
    dropped_zone = make(Prepared, prepared_data(blocks=blocks[:2]))
    with pytest.raises(A2ContractError, match="blocks differ"):
        dropped_zone.validate_against(rich(), make_zones())
    renamed = prepared_data(blocks=[{**blocks[0], "original": {"start": 0, "end": 3}}])
    with pytest.raises(A2ContractError, match="blocks differ"):
        make(Prepared, renamed).validate_against(rich(), make_zones())


def test_block_and_part_shape_rules() -> None:
    data = prepared_data()
    parts, blocks = data["parts"], data["blocks"]
    rejects(Prepared, prepared_data(parts=[]), "part count")
    rejects(Prepared, prepared_data(parts=[parts[0], parts[0]]), "duplicate")
    rejects(Prepared, prepared_data(parts=[parts[1], parts[0], parts[2]]), "sorted")
    rejects(Prepared, prepared_data(blocks=[{**blocks[0], "part_id": "p1"}]), "body")
    rejects(Prepared, prepared_data(blocks=[blocks[0], blocks[0]]), "duplicate")
    rejects(Prepared, prepared_data(blocks=[blocks[1], blocks[0]]), "not sorted")
    rejects(Prepared, prepared_data(parts=[{**parts[0], "sha256": None}]), "digest")
    rejects(Prepared, prepared_data(sent_at=-1), "")
    twice = [data["participants"][0]] * 2
    rejects(Prepared, prepared_data(participants=twice), "duplicate")


def test_blocks_reject_a_missing_body_part() -> None:
    data = prepared_data()
    parts, blocks = data["parts"], data["blocks"]
    check(parts[0]["role"] == "body", "fixture part 0 is the body")
    check(len(make(Prepared, data).blocks) == len(blocks), "present body passes")
    partial = {**parts[0], "status": "partial"}
    kept = prepared_data(
        parts=[partial, *parts[1:]],
        status="incomplete",
        limitations=[limit("body_partial")],
    )
    check(len(make(Prepared, kept).blocks) == len(blocks), "partial body keeps blocks")
    missing = {**parts[0], "status": "missing", "sha256": None}
    rejects(Prepared, prepared_data(parts=[missing, *parts[1:]]), "missing body")


def test_every_limitation_is_required_and_status_agrees() -> None:
    parts = prepared_data()["parts"]
    cases = [
        ({"parts": [{**parts[0], "status": "partial"}, *parts[1:]]}, "body_partial"),
        ({"parts": [*parts[:2], {**parts[2], "status": "missing", "sha256": None}]},
         "attachment_missing"),
        ({"blocks": []}, "body_absent"),
        ({"sent_at": None}, "time_unknown"),
        ({"participants": []}, "participants_unknown"),
    ]  # fmt: skip
    for changes, code in cases:
        rejects(Prepared, prepared_data(**changes), "required limitation|status")
        kept = prepared_data(**changes, status="incomplete", limitations=[limit(code)])
        value = make(Prepared, kept)
        check(value.limitations[0].code == code, "limitation kept")
        dropped = prepared_data(
            **changes, status="incomplete", limitations=[limit("x")]
        )
        rejects(Prepared, dropped, "required limitation")
    rejects(Prepared, prepared_data(status="incomplete"), "conflicts")
    rejects(Prepared, prepared_data(limitations=[limit("x")]), "conflicts")
    rejects(Prepared, prepared_data(status="failed"), "complete or incomplete")


def test_limitations_are_a_sorted_set() -> None:
    two = [limit("b"), limit("a")]
    rejects(Prepared, prepared_data(status="incomplete", limitations=two), "sorted")
    dup = [limit("a"), limit("a")]
    rejects(Prepared, prepared_data(status="incomplete", limitations=dup), "duplicate")


# --- filter_result@2 ------------------------------------------------------


def test_filter_records_every_matched_rule_with_policy_and_version() -> None:
    value = make(FilterResult, filter_data())
    check(value.matched == ("r1", "r2"), "all matched rules")
    check((value.policy_id, value.policy_version) == ("policy-1", "7"), "policy")
    check(all(e.rule_version for e in value.evaluations), "rule versions")


def test_best_match_only_payloads_are_refused() -> None:
    rejects(FilterResult, filter_data(matched=["r1"]), "every matched rule")
    rejects(FilterResult, filter_data(matched=[]), "every matched rule")
    rejects(FilterResult, filter_data(matched=["r2", "r1"]), "every matched rule")
    rejects(FilterResult, filter_data(matched=["r1", "r2", "r3"]), "every matched")
    only_best = filter_data(evaluations=[rule("r1", "matched", "include")])
    rejects(FilterResult, only_best, "every matched rule")


def test_conflict_exclusion_and_unknown_reasons_are_complete() -> None:
    conflict = filter_data(
        evaluations=[
            rule("r1", "matched", "include"),
            rule("r2", "matched", "exclude"),
            rule("r3", "matched", "exclude"),
            rule("r4", "unknown"),
        ],
        matched=["r1", "r2", "r3"],
        verdict="conflict",
        reasons=[
            {"code": "conflict", "rule_ids": ["r1", "r2", "r3"]},
            {"code": "excluded", "rule_ids": ["r2", "r3"]},
            {"code": "unknown_rule", "rule_ids": ["r4"]},
        ],
    )
    value = make(FilterResult, conflict)
    check(value.verdict == "conflict" and len(value.reasons) == 3, "all reasons")
    best_only = edit(conflict, "reasons.1.rule_ids", ["r2"])
    rejects(FilterResult, best_only, "differ from evaluations")
    rejects(FilterResult, edit(conflict, "verdict", "include"), "differ")
    rejects(FilterResult, edit(conflict, "reasons", []), "differ")
    exclude_only = filter_data(
        evaluations=[rule("r1", "matched", "exclude")],
        matched=["r1"],
        verdict="exclude",
        reasons=[{"code": "excluded", "rule_ids": ["r1"]}],
    )
    check(make(FilterResult, exclude_only).verdict == "exclude", "exclusion")
    rejects(FilterResult, {**exclude_only, "reasons": []}, "differ")
    unknown = filter_data(
        evaluations=[rule("r1", "unknown")],
        matched=[],
        verdict="unknown",
        reasons=[{"code": "unknown_rule", "rule_ids": ["r1"]}],
    )
    check(make(FilterResult, unknown).verdict == "unknown", "unknown")
    rejects(FilterResult, {**unknown, "verdict": "no_match"}, "differ")


def test_filter_shape_rules() -> None:
    rejects(FilterResult, filter_data(evaluations=[]), "rule count")
    twice = [rule("r1", "matched", "include")] * 2
    rejects(FilterResult, filter_data(evaluations=twice), "duplicate")
    unsorted = [rule("r2", "not_matched"), rule("r1", "not_matched")]
    rejects(FilterResult, filter_data(evaluations=unsorted), "not sorted")
    rejects(FilterResult, filter_data(evaluations=[rule("r1", "matched")]), "effect")
    rejects(
        FilterResult,
        filter_data(evaluations=[rule("r1", "unknown", "include")]),
        "effect",
    )
    none = filter_data(
        evaluations=[rule("r1", "not_matched")], matched=[], verdict="no_match"
    )
    check(make(FilterResult, none).verdict == "no_match", "no match is legal")
    rejects(FilterResult, filter_data(status="incomplete"), "conflicts")
    rejects(
        FilterResult, filter_data(prepared=ref_dict("5", "group_result", "2")), "wrong"
    )
