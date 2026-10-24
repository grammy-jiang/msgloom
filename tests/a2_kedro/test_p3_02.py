"""P3-02 relation safety review: each reason, combinations, order, bounds."""

from __future__ import annotations

import random
from typing import Any

import pytest
from pydantic import ValidationError

from msgloom.a2_kedro.contracts.relations import NativeRelations, NodeRef, Relation
from msgloom.a2_kedro.semantics.relation_safety import (
    MAX_REVIEW_NODES,
    CandidateRelation,
    RelationReview,
    RelationReviewInput,
    RelationSafetyReview,
    ReviewReason,
    SafetyStatus,
    review_relations,
)
from tests.a2_kedro.helpers import check

SECRET = "secret-id-x9@example.invalid"
CYCLE = ReviewReason.CYCLE
MISSING = ReviewReason.MISSING_PARENT
DUPLICATE = ReviewReason.DUPLICATE_MESSAGE_ID
CROSS = ReviewReason.CROSS_SCOPE


def node(node_id: str, scope: str = "s1") -> NodeRef:
    return NodeRef(scope_kind="thread", scope_id=scope, node_id=node_id)


def rel(
    child: str,
    parent: str,
    *,
    kind: str = "reply_to",
    child_scope: str = "s1",
    parent_scope: str = "s1",
) -> CandidateRelation:
    return CandidateRelation(
        kind=kind,  # type: ignore[arg-type]
        child=node(child, child_scope),
        parent=node(parent, parent_scope),
        basis="same_source:test",
    )


def review(
    nodes: list[NodeRef], relations: list[CandidateRelation]
) -> RelationSafetyReview:
    return review_relations(
        RelationReviewInput(nodes=tuple(nodes), relations=tuple(relations))
    )


def plain(nodes: list[str], relations: list[CandidateRelation]) -> RelationSafetyReview:
    return review([node(n) for n in nodes], relations)


def outcome(result: RelationSafetyReview) -> dict[tuple[str, str], list[str]]:
    """Map (child, parent) to the sorted reason values."""
    return {
        (r.relation.child.node_id, r.relation.parent.node_id): [
            reason.value for reason in r.reasons
        ]
        for r in result.reviews
    }


def test_empty_input_gives_empty_review() -> None:
    result = review([], [])
    check(result.reviews == (), "no reviews")
    check(result.with_status(SafetyStatus.CONFIRMED) == (), "nothing confirmed")


def test_clean_relation_is_confirmed() -> None:
    result = plain(["a", "b"], [rel("a", "b")])
    check(len(result.reviews) == 1, "one review")
    (item,) = result.reviews
    check(item.status is SafetyStatus.CONFIRMED, "same scope, present, unique")
    check(item.reasons == (), "no reason")


def test_chain_without_cycle_has_no_false_positive() -> None:
    names = [f"m{i}" for i in range(6)]
    relations = [rel(names[i], names[i + 1]) for i in range(5)]
    relations.append(rel("m0", "m3", kind="ancestor"))
    result = plain(names, relations)
    check(
        len(result.with_status(SafetyStatus.CONFIRMED)) == len(relations),
        "a DAG is fully confirmed",
    )


def test_long_chain_uses_no_recursion() -> None:
    size = 5000
    names = [f"m{i:05d}" for i in range(size)]
    relations = [rel(names[i], names[i + 1]) for i in range(size - 1)]
    result = plain(names, relations)
    check(len(result.reviews) == size - 1, "every edge reviewed")
    check(
        len(result.with_status(SafetyStatus.CONFIRMED)) == size - 1,
        "a long chain has no cycle",
    )
    closed = plain(names, [*relations, rel(names[-1], names[0])])
    check(
        len(closed.with_status(SafetyStatus.NEEDS_REVIEW)) == size,
        "closing the long chain flags every member",
    )


@pytest.mark.parametrize("length", [1, 2, 3, 7])
def test_cycle_of_any_length_flags_every_member(length: int) -> None:
    names = [f"c{i}" for i in range(length)]
    relations = [rel(names[i], names[(i + 1) % length]) for i in range(length)]
    result = plain(names, relations)
    check(len(result.reviews) == length, "one review per edge")
    for item in result.reviews:
        check(item.status is SafetyStatus.NEEDS_REVIEW, "cycle edge needs review")
        check(item.reasons == (CYCLE,), "only the cycle reason")


def test_tail_into_cycle_and_out_of_cycle_are_not_flagged() -> None:
    result = plain(
        ["a", "b", "t", "u"],
        [rel("a", "b"), rel("b", "a"), rel("t", "a"), rel("b", "u")],
    )
    got = outcome(result)
    check(got[("a", "b")] == ["cycle"], "cycle edge a->b")
    check(got[("b", "a")] == ["cycle"], "cycle edge b->a")
    check(got[("t", "a")] == [], "edge into the cycle is not on it")
    check(got[("b", "u")] == [], "edge out of the cycle is not on it")


def test_cycle_joins_reply_and_ancestor_but_not_reference() -> None:
    mixed = plain(
        ["a", "b"], [rel("a", "b", kind="reply_to"), rel("b", "a", kind="ancestor")]
    )
    check(
        all(r.reasons == (CYCLE,) for r in mixed.reviews),
        "reply_to and ancestor share one graph",
    )
    legal = plain(
        ["a", "b"],
        [rel("a", "b", kind="reference"), rel("b", "a", kind="reference")],
    )
    check(
        len(legal.with_status(SafetyStatus.CONFIRMED)) == 2,
        "a reference cycle is legal",
    )
    half = plain(
        ["a", "b"], [rel("a", "b", kind="reply_to"), rel("b", "a", kind="reference")]
    )
    check(
        len(half.with_status(SafetyStatus.CONFIRMED)) == 2,
        "a reference edge does not close a reply cycle",
    )


def test_missing_parent_needs_review() -> None:
    result = plain(["a"], [rel("a", "ghost")])
    check(outcome(result) == {("a", "ghost"): ["missing_parent"]}, "missing parent")
    check(result.reviews[0].status is SafetyStatus.NEEDS_REVIEW, "not confirmed")


def test_duplicate_message_id_flags_every_touching_relation() -> None:
    result = plain(
        ["a", "b", "b", "c", "d"],
        [rel("a", "b"), rel("b", "c"), rel("c", "d")],
    )
    got = outcome(result)
    check(got[("a", "b")] == ["duplicate_message_id"], "parent is duplicated")
    check(got[("b", "c")] == ["duplicate_message_id"], "child is duplicated")
    check(got[("c", "d")] == [], "unrelated relation stays confirmed")


def test_duplicate_flags_all_colliding_nodes_with_no_winner() -> None:
    result = plain(
        ["a", "a", "b", "b"], [rel("a", "b"), rel("b", "a", kind="reference")]
    )
    check(
        all(r.reasons == (DUPLICATE,) for r in result.reviews),
        "both colliding ids are flagged and none wins",
    )


def test_same_id_in_two_scopes_is_not_a_duplicate() -> None:
    result = review(
        [node("a", "s1"), node("a", "s2"), node("b", "s1")],
        [rel("a", "b")],
    )
    check(result.reviews[0].reasons == (), "scoped IDs are different nodes")


def test_cross_scope_is_never_confirmed() -> None:
    result = review(
        [node("a", "s1"), node("b", "s2")],
        [rel("a", "b", parent_scope="s2")],
    )
    (item,) = result.reviews
    check(item.status is SafetyStatus.NEEDS_REVIEW, "cross scope needs review")
    check(item.reasons == (CROSS,), "otherwise perfect, still flagged")


def test_cross_scope_kind_difference_counts() -> None:
    parent = NodeRef(scope_kind="mailbox", scope_id="s1", node_id="b")
    child = node("a", "s1")
    result = review_relations(
        RelationReviewInput(
            nodes=(child, parent),
            relations=(
                CandidateRelation(
                    kind="reply_to", child=child, parent=parent, basis="x"
                ),
            ),
        )
    )
    check(result.reviews[0].reasons == (CROSS,), "same ID, different scope kind")


def test_reasons_combine_in_sorted_order() -> None:
    result = review(
        [node("a", "s1"), node("a", "s1")],
        [rel("a", "a"), rel("a", "ghost", parent_scope="s2")],
    )
    got = outcome(result)
    check(got[("a", "a")] == ["cycle", "duplicate_message_id"], "self parent + dup")
    check(
        got[("a", "ghost")]
        == ["cross_scope", "duplicate_message_id", "missing_parent"],
        "three reasons, sorted",
    )
    for item in result.reviews:
        check(item.status is SafetyStatus.NEEDS_REVIEW, "never auto-confirmed")


def test_cycle_across_scopes_also_flags_cross_scope() -> None:
    result = review(
        [node("a", "s1"), node("b", "s2")],
        [
            rel("a", "b", parent_scope="s2"),
            rel("b", "a", child_scope="s2", parent_scope="s1"),
        ],
    )
    check(
        all(r.reasons == (CROSS, CYCLE) for r in result.reviews),
        "cross scope and cycle combine",
    )


def test_output_is_sorted_and_independent_of_input_order() -> None:
    nodes = [node(n) for n in ("a", "b", "b", "c", "d", "e")]
    relations = [
        rel("a", "b"),
        rel("c", "d"),
        rel("d", "c"),
        rel("e", "ghost"),
        rel("c", "e", kind="reference"),
        rel("a", "c", kind="ancestor"),
        rel("a", "b"),
    ]
    expected = review(nodes, relations)
    keys = [r.relation.sort_key() for r in expected.reviews]
    check(keys == sorted(keys), "reviews are sorted")
    check(len(expected.reviews) == len(relations) - 1, "equal candidates collapse")
    rng = random.Random(7)
    for _ in range(25):
        shuffled_nodes = nodes[:]
        shuffled_relations = relations[:]
        rng.shuffle(shuffled_nodes)
        rng.shuffle(shuffled_relations)
        check(
            review(shuffled_nodes, shuffled_relations) == expected,
            "shuffled input gives an equal result",
        )
        check(
            review(shuffled_nodes, shuffled_relations).model_dump_json()
            == expected.model_dump_json(),
            "shuffled input gives equal bytes",
        )


def test_from_native_record_is_confirmed_and_hypothesis_only() -> None:
    a, b = node("a"), node("b")
    record = NativeRelations(
        nodes=(a, b),
        relations=(
            Relation(kind="reply_to", source=a, target=b, basis="same_source:x"),
        ),
    )
    result = review_relations(RelationReviewInput.from_native(record))
    check(len(result.reviews) == 1, "one review")
    check(result.reviews[0].status is SafetyStatus.CONFIRMED, "clean P3-01 record")
    check(result.reviews[0].relation.basis == "same_source:x", "evidence kept")
    check(result.reviews[0].relation.child == a, "child is the source")


def test_results_are_immutable() -> None:
    result = plain(["a", "b"], [rel("a", "b")])
    first = result.reviews[0]
    with pytest.raises(ValidationError):
        result.reviews = ()  # type: ignore[misc]
    with pytest.raises(ValidationError):
        first.status = SafetyStatus.NEEDS_REVIEW  # type: ignore[misc]
    check(isinstance(result.reviews, tuple), "reviews are a tuple")
    check(isinstance(first.reasons, tuple), "reasons are a tuple")


def test_inconsistent_review_record_is_rejected() -> None:
    relation = rel("a", "b")
    bad: list[dict[str, Any]] = [
        {"status": SafetyStatus.CONFIRMED, "reasons": (CYCLE,)},
        {"status": SafetyStatus.NEEDS_REVIEW, "reasons": ()},
        {"status": SafetyStatus.NEEDS_REVIEW, "reasons": (MISSING, CYCLE)},
        {"status": SafetyStatus.NEEDS_REVIEW, "reasons": (CYCLE, CYCLE)},
    ]
    for fields in bad:
        with pytest.raises(ValidationError):
            RelationReview(relation=relation, **fields)


def test_undeclared_child_and_bounds_raise_fixed_text() -> None:
    with pytest.raises(ValidationError) as undeclared:
        plain(["b"], [rel(SECRET, "b")])
    check(SECRET not in str(undeclared.value), "no ID in undeclared child error")
    with pytest.raises(ValidationError) as bound:
        RelationReviewInput(
            nodes=tuple(node(f"{SECRET}{i}") for i in range(MAX_REVIEW_NODES + 1))
        )
    check(SECRET not in str(bound.value), "no ID in bound error")


def test_no_identifier_in_validation_errors() -> None:
    with pytest.raises(ValidationError) as bad_kind:
        CandidateRelation(
            kind="nope",  # type: ignore[arg-type]
            child=node(SECRET),
            parent=node("b"),
            basis=SECRET,
        )
    check(SECRET not in str(bad_kind.value), "no ID in kind error")
    with pytest.raises(ValidationError) as bad_node:
        RelationReviewInput(nodes=(SECRET,))  # type: ignore[arg-type]
    check(SECRET not in str(bad_node.value), "no ID in node error")
    with pytest.raises(ValidationError) as bad_extra:
        CandidateRelation(
            kind="reply_to",
            child=node("a"),
            parent=node("b"),
            basis=SECRET,
            extra=SECRET,  # type: ignore[call-arg]
        )
    check(SECRET not in str(bad_extra.value), "no ID in extra-field error")
