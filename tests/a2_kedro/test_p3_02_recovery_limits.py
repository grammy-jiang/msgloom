"""P3-02 relation safety review: P3-01 recovery limits cap confirmation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from msgloom.a2_kedro.contracts.relations import NativeRelations, NodeRef, Relation
from msgloom.a2_kedro.semantics.relation_safety import (
    RecoveryLimits,
    RelationReviewInput,
    ReviewReason,
    SafetyStatus,
    review_relations,
)
from tests.a2_kedro.helpers import check

LIMIT_CODES = (
    "list_too_long",
    "depth_exceeded",
    "too_many_relations",
    "conflicting_parents",
    "ambiguous_target",
)


def record() -> NativeRelations:
    a = NodeRef(scope_kind="thread", scope_id="s1", node_id="a")
    b = NodeRef(scope_kind="thread", scope_id="s1", node_id="b")
    relation = Relation(
        kind="reply_to", source=a, target=b, basis="same_source:reply_parent"
    )
    return NativeRelations(nodes=(a, b), relations=(relation,))


def test_complete_recovery_still_confirms() -> None:
    result = review_relations(
        RelationReviewInput.from_native(record(), recovery=RecoveryLimits())
    )
    check(result.reviews[0].status is SafetyStatus.CONFIRMED, "complete is confirmed")
    check(result.limitation_codes == (), "no codes recorded")
    check(result.unresolved_count == 0, "no unresolved recorded")


@pytest.mark.parametrize("code", LIMIT_CODES)
def test_each_limitation_code_blocks_confirmation(code: str) -> None:
    limits = RecoveryLimits(limitation_codes=(code,))
    result = review_relations(
        RelationReviewInput.from_native(record(), recovery=limits)
    )
    check(len(result.reviews) == 1, "one review")
    check(result.reviews[0].status is SafetyStatus.NEEDS_REVIEW, "not confirmed")
    check(
        result.reviews[0].reasons == (ReviewReason.RECOVERY_INCOMPLETE,),
        "reason is recorded",
    )
    check(result.limitation_codes == (code,), "code is kept in the review")
    check(result.with_status(SafetyStatus.CONFIRMED) == (), "nothing confirmed")


def test_unresolved_relations_alone_block_confirmation() -> None:
    limits = RecoveryLimits(unresolved_count=1)
    result = review_relations(
        RelationReviewInput.from_native(record(), recovery=limits)
    )
    check(result.reviews[0].status is SafetyStatus.NEEDS_REVIEW, "not confirmed")
    check(result.unresolved_count == 1, "unresolved count is kept")
    check(result.limitation_codes == (), "no code invented")


def test_any_unknown_code_blocks_confirmation() -> None:
    limits = RecoveryLimits(limitation_codes=("some_future_code",))
    result = review_relations(
        RelationReviewInput.from_native(record(), recovery=limits)
    )
    check(result.reviews[0].status is SafetyStatus.NEEDS_REVIEW, "not confirmed")


def test_codes_are_sorted_and_distinct() -> None:
    limits = RecoveryLimits(limitation_codes=("b", "a", "b"))
    check(limits.limitation_codes == ("a", "b"), "sorted and distinct")


def test_from_native_requires_recovery_limits() -> None:
    with pytest.raises(TypeError):
        RelationReviewInput.from_native(record())  # type: ignore[call-arg]


def test_reason_combines_in_sorted_order_with_other_reasons() -> None:
    a = NodeRef(scope_kind="thread", scope_id="s1", node_id="a")
    b = NodeRef(scope_kind="thread", scope_id="s1", node_id="b")
    rec = NativeRelations(
        nodes=(a, b),
        relations=(
            Relation(kind="reply_to", source=a, target=b, basis="conversation_id"),
        ),
    )
    limits = RecoveryLimits(limitation_codes=("depth_exceeded",))
    result = review_relations(RelationReviewInput.from_native(rec, recovery=limits))
    check(
        result.reviews[0].reasons
        == (ReviewReason.RECOVERY_INCOMPLETE, ReviewReason.UNCONFIRMABLE_BASIS),
        "reasons sorted",
    )


def test_invalid_limits_are_rejected_without_echo() -> None:
    secret = "secret-id-x9@example.invalid"
    with pytest.raises(ValidationError) as excinfo:
        RecoveryLimits(unresolved_count=-1, limitation_codes=(secret, ""))
    check(secret not in str(excinfo.value), "no input echoed")
