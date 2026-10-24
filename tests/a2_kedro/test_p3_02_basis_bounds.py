"""P3-02 relation safety review: basis allowlist and count bounds."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from msgloom.a2_kedro.contracts.relations import NodeRef
from msgloom.a2_kedro.semantics.relation_safety import (
    CONFIRMABLE_BASES,
    MAX_REVIEW_NODES,
    MAX_REVIEW_RELATIONS,
    CandidateRelation,
    RelationReview,
    RelationReviewInput,
    ReviewReason,
    SafetyStatus,
    review_relations,
)
from tests.a2_kedro.helpers import check

SECRET = "secret-id-x9@example.invalid"
SAME_SOURCE = (
    "same_source:reply_parent",
    "same_source:ancestor_list",
    "same_source:quote_marker",
)


def node(node_id: str) -> NodeRef:
    return NodeRef(scope_kind="thread", scope_id="s1", node_id=node_id)


def candidate(basis: str, kind: str = "reply_to") -> CandidateRelation:
    return CandidateRelation(
        kind=kind,  # type: ignore[arg-type]
        child=node("a"),
        parent=node("b"),
        basis=basis,
    )


def review_one(basis: str, kind: str = "reply_to") -> RelationReview:
    result = review_relations(
        RelationReviewInput(
            nodes=(node("a"), node("b")), relations=(candidate(basis, kind),)
        )
    )
    (item,) = result.reviews
    return item


def test_confirmable_bases_are_the_closed_same_source_set() -> None:
    check(CONFIRMABLE_BASES == frozenset(SAME_SOURCE), "exact allowlist")
    check(isinstance(CONFIRMABLE_BASES, frozenset), "allowlist is immutable")


@pytest.mark.parametrize(
    ("basis", "kind"),
    [
        ("same_source:reply_parent", "reply_to"),
        ("same_source:ancestor_list", "ancestor"),
        ("same_source:quote_marker", "reference"),
    ],
)
def test_same_source_basis_is_confirmed(basis: str, kind: str) -> None:
    item = review_one(basis, kind)
    check(item.status is SafetyStatus.CONFIRMED, "same-source basis confirms")
    check(item.reasons == (), "no reason")


@pytest.mark.parametrize(
    "basis",
    [
        "conversation_id",
        "conversation_id:abc",
        "same_source:conversation_id",
        "x",
        "same_source:test",
        "Same_Source:reply_parent",
        "same_source:reply_parent ",
        " same_source:reply_parent",
        "same_source:",
        "same_source",
    ],
)
def test_other_basis_is_never_confirmed(basis: str) -> None:
    item = review_one(basis)
    check(item.status is SafetyStatus.NEEDS_REVIEW, "candidate-only evidence")
    check(item.reasons == (ReviewReason.UNCONFIRMABLE_BASIS,), "basis reason only")


def test_empty_basis_is_rejected_by_the_model() -> None:
    with pytest.raises(ValidationError):
        candidate("")


def test_basis_reason_combines_with_other_reasons_in_sorted_order() -> None:
    child, parent = node("a"), node("ghost")
    result = review_relations(
        RelationReviewInput(
            nodes=(child,),
            relations=(
                CandidateRelation(
                    kind="reply_to", child=child, parent=parent, basis="conversation_id"
                ),
            ),
        )
    )
    (item,) = result.reviews
    check(
        item.reasons == (ReviewReason.MISSING_PARENT, ReviewReason.UNCONFIRMABLE_BASIS),
        "two reasons, sorted",
    )


def test_basis_check_is_what_blocks_confirmation() -> None:
    # Mutation guard: the only difference between the two relations is the
    # basis text. Removing the basis check makes both CONFIRMED.
    good = review_one("same_source:reply_parent")
    bad = review_one("conversation_id")
    check(good.status is SafetyStatus.CONFIRMED, "same-source confirmed")
    check(bad.status is not SafetyStatus.CONFIRMED, "conversation_id not confirmed")
    check(good.status != bad.status, "basis alone decides the status")


def test_review_ignores_basis_of_unrelated_kinds_consistently() -> None:
    for kind in ("reply_to", "ancestor", "reference"):
        check(
            review_one("conversation_id", kind).status is SafetyStatus.NEEDS_REVIEW,
            f"{kind} with conversation_id needs review",
        )


def test_node_bound_accepts_maximum_and_rejects_one_more() -> None:
    one = node("a")
    accepted = RelationReviewInput(nodes=(one,) * MAX_REVIEW_NODES)
    check(len(accepted.nodes) == MAX_REVIEW_NODES, "maximum accepted")
    with pytest.raises(ValidationError):
        RelationReviewInput(nodes=(one,) * (MAX_REVIEW_NODES + 1))


def test_relation_bound_accepts_maximum_and_rejects_one_more() -> None:
    relation = candidate("same_source:reply_parent")
    nodes = (node("a"), node("b"))
    accepted = RelationReviewInput(
        nodes=nodes, relations=(relation,) * MAX_REVIEW_RELATIONS
    )
    check(len(accepted.relations) == MAX_REVIEW_RELATIONS, "maximum accepted")
    with pytest.raises(ValidationError):
        RelationReviewInput(
            nodes=nodes, relations=(relation,) * (MAX_REVIEW_RELATIONS + 1)
        )


def test_oversize_input_stops_before_validating_later_elements() -> None:
    # Pydantic stops at the first element past the limit. A raw string
    # after that element would add an element error if every element were
    # validated first. Only the length error may appear, and no raw text.
    one, other = node("a"), node("b")
    relation = candidate("same_source:reply_parent")
    too_many_nodes: list[Any] = [one] * (MAX_REVIEW_NODES + 1) + [SECRET]
    too_many_relations: list[Any] = [relation] * (MAX_REVIEW_RELATIONS + 1) + [SECRET]
    cases: list[dict[str, Any]] = [
        {"nodes": tuple(too_many_nodes)},
        {"nodes": (one, other), "relations": tuple(too_many_relations)},
    ]
    for kwargs in cases:
        with pytest.raises(ValidationError) as caught:
            RelationReviewInput(**kwargs)
        types = [err["type"] for err in caught.value.errors()]
        check(types == ["too_long"], "only the length error")
        check(SECRET not in str(caught.value), "no raw text in error")
