"""P3-01 native relation recovery: negative cases and bounds."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from msgloom.a2_kedro.contracts.relations import MAX_NODES, MAX_RELATIONS
from msgloom.a2_kedro.semantics.relations import (
    MAX_ANCESTOR_DEPTH,
    MAX_PARENT_REFS,
    MAX_QUOTE_MARKERS,
    MessageEvidence,
    QuoteMarker,
    SourceEvidence,
    recover_relations,
)
from tests.a2_kedro.helpers import check
from tests.a2_kedro.test_p3_01 import codes, edges, msg, run

SECRET = "secret-id-x9@example.invalid"


def test_self_reply_self_ancestor_and_self_quote_are_dropped() -> None:
    result = run(msg("a", reply_parent_ids=["a"], ancestor_ids=["a"], quotes=["a"]))
    check(edges(result) == [], "no self relation")
    check(codes(result) == ["self_reference"] * 3, "one limitation per kind")
    check(result.unresolved == (), "a self reference is not unresolved")


def test_reply_cycle_drops_every_edge_inside_it() -> None:
    result = run(
        msg("a", reply_parent_ids=["b"]),
        msg("b", reply_parent_ids=["a"]),
        msg("c", reply_parent_ids=["a"]),
    )
    check(
        [e[:3] for e in edges(result)] == [("reply_to", "c", "a")],
        "edge outside the cycle stays; both cycle edges go",
    )
    check(codes(result) == ["cycle", "cycle"], "cycle reported per edge")


def test_mixed_reply_and_ancestor_cycle_is_detected() -> None:
    result = run(
        msg("a", reply_parent_ids=["b"]),
        msg("b", ancestor_ids=["c"]),
        msg("c", reply_parent_ids=["a"]),
    )
    check(edges(result) == [], "three-node cycle across kinds is dropped")
    check(codes(result) == ["cycle"] * 3, "three limitations")
    kinds = sorted(item.kind or "" for item in result.limitations)
    check(kinds == ["ancestor", "reply_to", "reply_to"], "kinds are kept")


def test_ancestor_mutual_lists_are_a_cycle() -> None:
    result = run(msg("a", ancestor_ids=["b"]), msg("b", ancestor_ids=["a"]))
    check(edges(result) == [] and codes(result) == ["cycle"] * 2, "cycle")


def test_quote_cycle_with_reply_edge_is_not_a_cycle() -> None:
    result = run(msg("a", quotes=["b"]), msg("b", reply_parent_ids=["a"]))
    check(codes(result) == [], "reference joins no acyclic graph")
    check(len(edges(result)) == 2, "both kept")


def test_conflicting_parents_record_no_reply() -> None:
    result = run(msg("a"), msg("b"), msg("c", reply_parent_ids=["a", "b"]))
    check(edges(result) == [], "no guessed parent")
    check(codes(result) == ["conflicting_parents"], "reported")
    check(result.unresolved == (), "not unresolved")


def test_conflicting_parent_does_not_block_other_kinds() -> None:
    result = run(
        msg("a"), msg("b"), msg("c", reply_parent_ids=["a", "b"], ancestor_ids=["a"])
    )
    check([e[0] for e in edges(result)] == ["ancestor"], "ancestor still recorded")


def test_duplicate_id_with_different_evidence_is_ambiguous() -> None:
    result = run(
        msg("a"),
        msg("b", reply_parent_ids=["a"]),
        msg("b", reply_parent_ids=[]),
        msg("c", reply_parent_ids=["b"]),
    )
    check(edges(result) == [], "no relation from or to an ambiguous id")
    check(
        sorted(codes(result)) == ["ambiguous_target", "duplicate_message_id"],
        "both reported",
    )
    check(
        [(u.source_id, u.target_id, u.limitation.value) for u in result.unresolved]
        == [("c", "b", "ambiguous_target")],
        "incoming relation is unresolved",
    )
    check([n.node_id for n in result.relations.nodes] == ["a", "b", "c"], "node once")


def test_conversation_mismatch_drops_the_relation() -> None:
    result = run(
        msg("a", conversation_id="c1"),
        msg("b", conversation_id="c2", reply_parent_ids=["a"]),
        msg("c", conversation_id="c1", reply_parent_ids=["a"]),
        msg("d", reply_parent_ids=["a"]),
    )
    check(
        [e[1] for e in edges(result)] == ["c", "d"],
        "same or absent conversation ID is accepted",
    )
    check(codes(result) == ["conversation_mismatch"], "reported")


def test_quote_marker_without_target_is_a_limitation() -> None:
    result = run(
        MessageEvidence(message_id="a", quote_markers=(QuoteMarker(),)),
    )
    check(edges(result) == [], "no link")
    check(codes(result) == ["quote_without_target"], "reported")
    check(result.unresolved == (), "nothing to name, so nothing unresolved")


def test_ancestor_depth_is_bounded_and_keeps_nearest() -> None:
    ids = [f"n{i:03d}" for i in range(MAX_ANCESTOR_DEPTH + 3)]
    result = run(*(msg(i) for i in ids), msg("m", ancestor_ids=ids))
    targets = [e[2] for e in edges(result)]
    check(len(targets) == MAX_ANCESTOR_DEPTH, "depth bound")
    check(ids[-1] in targets and ids[0] not in targets, "nearest kept")
    check(codes(result) == ["depth_exceeded"], "reported")
    at_bound = run(
        *(msg(i) for i in ids[:MAX_ANCESTOR_DEPTH]),
        msg("m", ancestor_ids=ids[:MAX_ANCESTOR_DEPTH]),
    )
    check(codes(at_bound) == [], "exactly at the bound is complete")


def test_parent_and_quote_lists_are_bounded() -> None:
    many = [f"p{i}" for i in range(MAX_PARENT_REFS + 1)]
    result = run(*(msg(i) for i in many), msg("m", reply_parent_ids=many))
    check(edges(result) == [], "oversized parent list gives no reply")
    check(
        sorted(codes(result)) == ["conflicting_parents", "list_too_long"],
        "bounded and conflicting",
    )
    quotes = [f"q{i}" for i in range(MAX_QUOTE_MARKERS + 1)]
    result = run(*(msg(i) for i in quotes), msg("m", quotes=quotes))
    check(len(edges(result)) == MAX_QUOTE_MARKERS, "quote bound")
    check(codes(result) == ["list_too_long"], "reported")


def test_message_count_is_bounded_deterministically() -> None:
    ids = [f"m{i:05d}" for i in range(MAX_NODES + 2)]
    result = run(*(msg(i) for i in reversed(ids)))
    nodes = [n.node_id for n in result.relations.nodes]
    check(nodes == ids[:MAX_NODES], "smallest IDs kept")
    check(codes(result) == ["too_many_messages"], "reported")
    lost = run(msg(ids[0], reply_parent_ids=[ids[-1]]), *(msg(i) for i in ids[1:]))
    check(
        [u.target_id for u in lost.unresolved] == [ids[-1]],
        "target lost to the bound is unresolved",
    )


def test_relation_count_is_bounded() -> None:
    per = 64
    count = MAX_RELATIONS // per + 2
    ids = [f"n{i:04d}" for i in range(per)]
    items = [msg(i) for i in ids]
    items += [
        msg(f"s{k:03d}", ancestor_ids=ids, reply_parent_ids=[ids[0]], quotes=ids[:8])
        for k in range(count)
    ]
    result = run(*items)
    check(len(result.relations.relations) == MAX_RELATIONS, "relation bound")
    check(codes(result) == ["too_many_relations"], "reported")
    keys = [r.sort_key() for r in result.relations.relations]
    check(keys == sorted(keys), "kept relations are the sorted prefix")


def test_malformed_evidence_is_rejected_without_echo() -> None:
    bad: list[dict[str, object]] = [
        {"message_id": SECRET + "\n"},
        {"message_id": ""},
        {"message_id": SECRET, "reply_parent_ids": [SECRET]},
        {"message_id": SECRET, "subject": SECRET},
        {"message_id": SECRET, "ancestor_ids": (SECRET, "")},
    ]
    for payload in bad:
        with pytest.raises(ValidationError) as caught:
            MessageEvidence.model_validate(payload)
        check(SECRET not in str(caught.value), "input is hidden in the error")
    with pytest.raises(ValidationError):
        SourceEvidence(scope_kind="folder", scope_id="x")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        QuoteMarker(target_id="")


def test_models_are_frozen() -> None:
    item = msg("a")
    with pytest.raises(ValidationError):
        item.message_id = "b"  # type: ignore[misc]
    result = recover_relations(SourceEvidence(scope_kind="mailbox", scope_id="mb"))
    check(result.relations.nodes == (), "mailbox scope is accepted")
