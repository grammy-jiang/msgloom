"""P3-01 native relation recovery: positive rules, separation, order."""

from __future__ import annotations

import random
from typing import Any

from msgloom.a2_kedro.contracts.relations import NativeRelations
from msgloom.a2_kedro.semantics.relations import (
    BASIS_ANCESTOR,
    BASIS_QUOTE,
    BASIS_REPLY,
    LimitationCode,
    MessageEvidence,
    QuoteMarker,
    RelationRecovery,
    SourceEvidence,
    recover_relations,
)
from tests.a2_kedro.helpers import check


def msg(mid: str, **kw: Any) -> MessageEvidence:
    for key in ("reply_parent_ids", "ancestor_ids"):
        if key in kw:
            kw[key] = tuple(kw[key])
    if "quotes" in kw:
        kw["quote_markers"] = tuple(QuoteMarker(target_id=q) for q in kw.pop("quotes"))
    return MessageEvidence(message_id=mid, **kw)


def src(*messages: MessageEvidence, scope_id: str = "conv-1") -> SourceEvidence:
    return SourceEvidence(
        scope_kind="thread", scope_id=scope_id, messages=tuple(messages)
    )


def run(*messages: MessageEvidence) -> RelationRecovery:
    return recover_relations(src(*messages))


def edges(result: RelationRecovery) -> list[tuple[str, str, str, str]]:
    return [
        (r.kind, r.source.node_id, r.target.node_id, r.basis)
        for r in result.relations.relations
    ]


def codes(result: RelationRecovery) -> list[str]:
    return [item.code.value for item in result.limitations]


def test_reply_parent_from_explicit_parent_in_same_source() -> None:
    result = run(msg("a"), msg("b", reply_parent_ids=["a"]))
    check(edges(result) == [("reply_to", "b", "a", BASIS_REPLY)], "reply_to only")
    check(codes(result) == [], "no limitation")
    check(result.unresolved == (), "nothing unresolved")
    check([n.node_id for n in result.relations.nodes] == ["a", "b"], "nodes declared")


def test_ancestor_chain_keeps_list_order_and_basis() -> None:
    result = run(
        msg("r"),
        msg("a"),
        msg("b"),
        msg("m", ancestor_ids=["r", "a", "b"]),
    )
    got = [(e[0], e[1], e[2]) for e in edges(result)]
    check(
        got == [("ancestor", "m", "a"), ("ancestor", "m", "b"), ("ancestor", "m", "r")],
        "ancestor edges: one per listed id, sorted by contract key",
    )
    check(all(e[3] == BASIS_ANCESTOR for e in edges(result)), "ancestor basis")
    # An id the list does not name is never an ancestor: no transitive guess.
    result2 = run(msg("r"), msg("a", ancestor_ids=["r"]), msg("m", ancestor_ids=["a"]))
    check(
        ("ancestor", "m", "r") not in [e[:3] for e in edges(result2)],
        "no transitive ancestor",
    )


def test_quote_source_needs_marker_and_resolvable_target() -> None:
    result = run(msg("a"), msg("b", quotes=["a"]))
    check(edges(result) == [("reference", "b", "a", BASIS_QUOTE)], "quote reference")
    # A message that quotes nothing gets no reference, even with a parent.
    plain = run(msg("a"), msg("b", reply_parent_ids=["a"]))
    check([e[0] for e in edges(plain)] == ["reply_to"], "reply alone is not a quote")


def test_three_kinds_stay_separate_for_one_pair() -> None:
    result = run(
        msg("a"),
        msg("b", reply_parent_ids=["a"], ancestor_ids=["a"], quotes=["a"]),
    )
    got = edges(result)
    check(
        got
        == [
            ("ancestor", "b", "a", BASIS_ANCESTOR),
            ("reference", "b", "a", BASIS_QUOTE),
            ("reply_to", "b", "a", BASIS_REPLY),
        ],
        "one relation per kind, each with its own basis",
    )
    check(len({e[0] for e in got}) == 3, "three kinds")


def test_quote_reference_cycle_is_legal_but_not_reply_cycle() -> None:
    result = run(msg("a", quotes=["b"]), msg("b", quotes=["a"]))
    check(len(edges(result)) == 2, "reference cycles are legal")
    check(codes(result) == [], "no limitation for a reference cycle")


def test_dangling_targets_become_unresolved_for_every_kind() -> None:
    result = run(
        msg(
            "b",
            reply_parent_ids=["gone-1"],
            ancestor_ids=["gone-2"],
            quotes=["gone-3"],
        )
    )
    check(edges(result) == [], "no guessed link")
    got = [(u.kind, u.target_id, u.limitation.value) for u in result.unresolved]
    check(
        got
        == [
            ("ancestor", "gone-2", "unresolved_target"),
            ("reference", "gone-3", "unresolved_target"),
            ("reply_to", "gone-1", "unresolved_target"),
        ],
        "unresolved by kind",
    )
    check(codes(result) == ["unresolved_target"] * 3, "one limitation each")
    check(len(result.relations.nodes) == 1, "dangling id is not a node")


def test_no_cross_source_linking() -> None:
    one = recover_relations(src(msg("a"), scope_id="conv-1"))
    two = recover_relations(src(msg("b", reply_parent_ids=["a"]), scope_id="conv-2"))
    check(edges(one) == [] and edges(two) == [], "sources never link")
    check(two.unresolved[0].target_id == "a", "target stays unresolved")
    check(
        {n.scope_id for n in two.relations.nodes} == {"conv-2"}, "scope is the source"
    )


def test_no_heuristics_subject_time_author_are_not_inputs() -> None:
    fields = set(MessageEvidence.model_fields)
    check(
        fields
        == {
            "message_id",
            "conversation_id",
            "reply_parent_ids",
            "ancestor_ids",
            "quote_markers",
        },
        "evidence has no subject, time or author field",
    )
    # Same conversation but no explicit parent: no relation at all.
    result = run(msg("a", conversation_id="c"), msg("b", conversation_id="c"))
    check(edges(result) == [] and codes(result) == [], "no guessed parent")


def test_duplicate_reference_is_deduped_with_limitation() -> None:
    result = run(
        msg("a"), msg("b", ancestor_ids=["a", "a"], reply_parent_ids=["a", "a"])
    )
    check(
        [e[:3] for e in edges(result)]
        == [("ancestor", "b", "a"), ("reply_to", "b", "a")],
        "deduped to one edge per kind",
    )
    check(codes(result) == ["duplicate_reference"] * 2, "reported per kind")


def test_equal_duplicate_message_merges_with_limitation() -> None:
    item = msg("b", reply_parent_ids=["a"])
    result = run(msg("a"), item, item)
    check(edges(result) == [("reply_to", "b", "a", BASIS_REPLY)], "merged")
    check(codes(result) == ["duplicate_message_id"], "reported")
    check(len(result.relations.nodes) == 2, "node declared once")


def test_output_is_deterministic_and_independent_of_input_order() -> None:
    items = [
        msg("a"),
        msg("b", reply_parent_ids=["a"], ancestor_ids=["a"]),
        msg("c", reply_parent_ids=["b"], ancestor_ids=["a", "b"], quotes=["a", "zz"]),
        msg("d", reply_parent_ids=["x", "y"]),
        msg("e", reply_parent_ids=["e"]),
    ]
    want = run(*items).relations.encode()
    want_all = run(*items).model_dump_json()
    rng = random.Random(7)
    for _ in range(10):
        rng.shuffle(items)
        got = run(*items)
        check(got.relations.encode() == want, "canonical bytes are stable")
        check(got.model_dump_json() == want_all, "limitations order is stable")
    check(NativeRelations.decode(want).encode() == want, "record round trips")


def test_empty_source_gives_empty_valid_record() -> None:
    result = recover_relations(src())
    check(result.relations.nodes == () and result.relations.relations == (), "empty")
    check(result.limitations == () and result.unresolved == (), "no limitation")
    check(LimitationCode("cycle") is LimitationCode.CYCLE, "closed code set")
