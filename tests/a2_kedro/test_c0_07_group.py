"""C0-07 group_result@2, the manifest and shared negative rules."""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import ValidationError

from msgloom.a2_kedro.contracts import results
from msgloom.a2_kedro.contracts.codec import (
    A2ContractError,
    canonical_json_bytes,
    decode_model_bytes,
)
from msgloom.a2_kedro.contracts.result_manifest import ResultManifest
from msgloom.a2_kedro.contracts.results import (
    FilterResult,
    GroupResult,
    Prepared,
    decode_result,
)
from tests.a2_kedro.helpers import check
from tests.a2_kedro.result_fixtures import (
    ALL,
    BAD,
    BUILDERS,
    SENTINEL,
    edit,
    entry,
    filter_data,
    group_data,
    limit,
    make,
    manifest_data,
    member,
    ordered,
    prepared_data,
    ref_dict,
    reply,
    rule,
)
from tests.a2_kedro.result_fixtures import (
    reject_data as rejects,
)

# --- group_result@2 -------------------------------------------------------


def test_group_binds_exact_scope_members_evidence_and_unknowns() -> None:
    value = make(GroupResult, group_data())
    check((value.scope_kind, value.scope_id) == ("thread", "T1"), "scope")
    check(len(value.members) == 3 and len(value.evidence) == 2, "members")
    unknown = group_data(
        unknown=[{"kind": "missing_parent", "node": node_c()}],
        status="incomplete",
        limitations=[limit("unknown_relations")],
    )
    check(len(make(GroupResult, unknown).unknown) == 1, "unknown kept")
    dropped = {**unknown, "limitations": [limit("other")], "status": "incomplete"}
    rejects(GroupResult, dropped, "required limitation")
    rejects(
        GroupResult, {**unknown, "status": "complete", "limitations": []}, "required"
    )
    single = group_data(members=[member("a", "5")], evidence=[])
    check(len(make(GroupResult, single).members) == 1, "singleton group")


def node_c() -> dict[str, str]:
    return {"scope_kind": "thread", "scope_id": "T1", "node_id": "c"}


def test_cross_scope_members_are_never_merged() -> None:
    other_id = group_data(members=[member("a", "5"), member("b", "6", "T2")])
    rejects(GroupResult, other_id, "outside the group scope")
    kind = member("b", "6")
    kind["node"]["scope_kind"] = "mailbox"
    rejects(GroupResult, group_data(members=[member("a", "5"), kind]), "outside")
    cross = group_data(
        evidence=[
            reply("c", "b"),
            {
                **reply("b", "a"),
                "source": {**reply("b", "a")["source"], "scope_id": "T2"},
            },
        ]
    )
    rejects(GroupResult, cross, "non-member")
    unknown = group_data(
        unknown=[{"kind": "cross_scope", "node": {**node_c(), "scope_id": "T2"}}],
        status="incomplete",
        limitations=[limit("unknown_relations")],
    )
    rejects(GroupResult, unknown, "non-member")
    same_node_other_scope = group_data(
        members=[member("a", "5"), member("a", "6", "T2")]
    )
    rejects(GroupResult, same_node_other_scope, "outside the group scope")


def test_duplicate_and_unsorted_members_are_refused() -> None:
    dup_node = group_data(members=[member("a", "5"), member("a", "6")])
    rejects(GroupResult, dup_node, "duplicate member")
    dup_result = group_data(
        members=[member("a", "5"), member("b", "5")], evidence=[reply("b", "a")]
    )
    rejects(GroupResult, dup_result, "duplicate member result")
    unsorted = group_data(
        members=[member("b", "6"), member("a", "5")], evidence=[reply("b", "a")]
    )
    rejects(GroupResult, unsorted, "not sorted")
    rejects(GroupResult, group_data(members=[]), "member count")


def test_subject_alone_never_groups_members() -> None:
    none = group_data(evidence=[])
    rejects(GroupResult, none, "lack native evidence")
    partial = group_data(evidence=[reply("b", "a")])
    rejects(GroupResult, partial, "lack native evidence")
    subject = {**reply("b", "a"), "kind": "subject"}
    rejects(GroupResult, group_data(evidence=[subject, reply("c", "b")]), "")
    rejects(GroupResult, {**group_data(), "subject": "same subject"}, "")
    rejects(
        GroupResult,
        group_data(evidence=[{**reply("b", "a"), "subject": "s"}, reply("c", "b")]),
        "",
    )
    self_edge = group_data(evidence=[reply("a", "a"), reply("b", "a"), reply("c", "b")])
    rejects(GroupResult, self_edge, "itself")
    nonmember = group_data(evidence=[reply("b", "a"), reply("c", "b"), reply("z", "a")])
    rejects(GroupResult, nonmember, "non-member")


# --- manifest -------------------------------------------------------------


def test_manifest_has_one_terminal_per_occurrence() -> None:
    value = make(ResultManifest, manifest_data())
    check(len(value.entries) == 4, "entries")
    data = manifest_data()
    second = entry(1, "prepared", "6")
    two_terminals = ordered([*data["entries"], second])
    rejects(ResultManifest, manifest_data(entries=two_terminals), "exactly one")
    no_terminal = [e for e in data["entries"] if e["ref"]["kind"] != "prepared"]
    rejects(ResultManifest, manifest_data(entries=no_terminal), "exactly one terminal")
    held_filter = ordered([*data["entries"], entry(1, "filter_result", "8")])
    rejects(ResultManifest, manifest_data(entries=held_filter), "held occurrence")
    rejects(ResultManifest, manifest_data(limitations=[]), "differ from entries")
    rejects(
        ResultManifest, manifest_data(workset=ref_dict("9", "prepared", "2")), "workset"
    )
    rejects(ResultManifest, manifest_data(entries=[]), "entry count")
    rejects(ResultManifest, manifest_data(entries=data["entries"][::-1]), "not sorted")
    rejects(
        ResultManifest, manifest_data(entries=[data["entries"][0]] * 2), "duplicate"
    )


def test_manifest_entry_rules() -> None:
    # Sorted order: batch, filter at 0, prepared at 0, held at 1.
    forged = edit(manifest_data(), "entries.2.ref.result_id", "plain")
    rejects(ResultManifest, forged, "")
    wrong_kind = edit(manifest_data(), "entries.2.ref.kind", "zones")
    rejects(ResultManifest, wrong_kind, "kind is not allowed")
    wrong_ver = edit(manifest_data(), "entries.2.ref.schema_version", "1")
    rejects(ResultManifest, wrong_ver, "wrong kind or version")
    batch_idx = edit(manifest_data(), "entries.0.workset_index", 5)
    rejects(ResultManifest, batch_idx, "no occurrence")
    no_idx = edit(manifest_data(), "entries.2.workset_index", None)
    rejects(ResultManifest, no_idx, "no occurrence")
    bare = edit(manifest_data(), "entries.3.limitations", [])
    rejects(ResultManifest, bare, "conflicts")


# --- shared negative rules ------------------------------------------------


@pytest.mark.parametrize("cls", ALL)
def test_unknown_extra_fields_are_refused(cls: Any) -> None:
    data = {**BUILDERS[cls](), "extra_field": 1}
    rejects(cls, data, "")
    with pytest.raises(A2ContractError):
        cls.decode(canonical_json_bytes(data))


def test_nested_unknown_fields_are_refused() -> None:
    rejects(Prepared, edit(prepared_data(), "parts.0.extra", 1), "")
    rejects(FilterResult, edit(filter_data(), "evaluations.0.extra", 1), "")
    rejects(GroupResult, edit(group_data(), "members.0.extra", 1), "")
    rejects(ResultManifest, edit(manifest_data(), "entries.0.extra", 1), "")


def test_non_canonical_bytes_are_refused() -> None:
    data = make(FilterResult, filter_data()).encode()
    spaced = json.dumps(json.loads(data), indent=1).encode()
    with pytest.raises(A2ContractError, match="canonical"):
        decode_result(spaced)
    with pytest.raises(A2ContractError, match="byte bound"):
        decode_model_bytes(FilterResult, data, max_bytes=10)


def test_lists_are_bounded() -> None:
    nums = [f"{i:064x}" for i in range(2000)]
    parts = [
        {
            "part_id": f"p{i}",
            "role": "attachment",
            "status": "present",
            "sha256": nums[i],
        }
        for i in range(results.MAX_PARTS + 1)
    ]
    rejects(Prepared, prepared_data(parts=parts), "part count")
    people = [
        {"role": "to", "identity_sha256": n}
        for n in nums[: results.MAX_PARTICIPANTS + 1]
    ]
    rejects(Prepared, prepared_data(participants=people), "count bound")
    rules = [rule(f"r{i:05d}", "not_matched") for i in range(results.MAX_RULES + 1)]
    rejects(FilterResult, filter_data(evaluations=rules, matched=[]), "rule count")
    many = [member(f"n{i:05d}", "5") for i in range(results.MAX_MEMBERS + 1)]
    rejects(GroupResult, group_data(members=many, evidence=[]), "member count")
    rejects(
        GroupResult,
        group_data(evidence=[reply("b", "a")] * (results.MAX_EVIDENCE + 1)),
        "count bound",
    )
    many = [limit(f"c{i:03d}") for i in range(65)]
    rejects(ResultManifest, manifest_data(limitations=many), "limitation count")


def test_error_text_never_carries_input_values() -> None:
    bad_cases: list[tuple[Any, dict[str, Any]]] = [
        (
            Prepared,
            prepared_data(
                zones={"result_id": SENTINEL, "kind": "zones", "schema_version": "1"}
            ),
        ),
        (
            Prepared,
            prepared_data(participants=[{"role": "to", "identity_sha256": SENTINEL}]),
        ),
        (
            Prepared,
            prepared_data(
                rule_version=SENTINEL,
                status="incomplete",
                limitations=[{"code": SENTINEL, "detail": SENTINEL}] * 2,
            ),
        ),
        (FilterResult, filter_data(matched=[SENTINEL])),
        (
            FilterResult,
            filter_data(evaluations=[rule(SENTINEL, "matched", "include")], matched=[]),
        ),
        (
            GroupResult,
            group_data(members=[member("a", "5"), member(SENTINEL, "6", SENTINEL)]),
        ),
        (GroupResult, group_data(scope_id=SENTINEL)),
        (
            ResultManifest,
            manifest_data(limitations=[{"code": SENTINEL, "detail": SENTINEL}]),
        ),
    ]
    for cls, data in bad_cases:
        with pytest.raises(BAD) as caught:
            make(cls, data)
        check(SENTINEL not in str(caught.value), "error text leaks input")
        check("alice" not in repr(caught.value.args), "error args leak input")
    with pytest.raises(ValidationError) as typed:
        make(Prepared, prepared_data(sent_at=SENTINEL))
    check(SENTINEL not in str(typed.value), "type error text leaks input")
