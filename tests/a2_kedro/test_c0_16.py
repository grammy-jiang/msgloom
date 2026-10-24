"""C0-16 partition policy: finite limits, no cross-workset merge, determinism."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.a2_kedro.partition_policy import (
    HARD_MAX_ITEMS,
    HARD_MAX_PARTITION_BYTES,
    HARD_MAX_WORKSETS,
    PROVISIONAL_POLICY,
    Partition,
    PartitionItem,
    PartitionPlan,
    PartitionPolicy,
    partition,
    plan_digest,
)
from msgloom.contracts import ResultRef
from tests.a2_kedro.helpers import check

WS_A = ResultRef("ws-a", "preparation_intake_workset", "1")
WS_B = ResultRef("ws-b", "preparation_intake_workset", "1")


def policy(**changes: Any) -> PartitionPolicy:
    data: dict[str, Any] = {
        "policy_version": "partition-test-1",
        "max_worksets_per_call": 4,
        "max_items_per_workset": 10,
        "max_items_per_partition": 3,
        "max_partitions_per_workset": 5,
        "max_bytes_per_partition": 100,
    }
    data.update(changes)
    return PartitionPolicy(**data)


def item(ws: ResultRef, index: int, size: int = 10) -> PartitionItem:
    return PartitionItem(workset=ws, index=index, size_bytes=size)


def run(ws: ResultRef, count: int, size: int = 10) -> list[PartitionItem]:
    return [item(ws, i, size) for i in range(count)]


def test_positive_split_by_item_limit() -> None:
    plan = partition(policy(), run(WS_A, 7))
    got = [(p.ordinal, p.indexes, p.total_bytes) for p in plan.partitions]
    check(
        got == [(0, (0, 1, 2), 30), (1, (3, 4, 5), 30), (2, (6,), 10)],
        "unexpected split",
    )
    check(plan.policy_sha256 == policy().digest(), "policy digest bound")
    plan.check_within(policy())


def test_split_by_byte_limit() -> None:
    plan = partition(policy(max_bytes_per_partition=25), run(WS_A, 5, size=10))
    check([p.indexes for p in plan.partitions] == [(0, 1), (2, 3), (4,)], "bytes")


def test_sparse_indexes_are_kept() -> None:
    items = [item(WS_A, 2), item(WS_A, 5), item(WS_A, 9)]
    plan = partition(policy(), items)
    check(plan.partitions[0].indexes == (2, 5, 9), "sparse indexes")


def test_never_merges_across_worksets() -> None:
    plan = partition(policy(), run(WS_A, 1) + run(WS_B, 1))
    check(len(plan.partitions) == 2, "one partition per workset")
    check(plan.partitions[0].workset == WS_A, "first workset")
    check(plan.partitions[1].workset == WS_B, "second workset")
    check([p.ordinal for p in plan.partitions] == [0, 0], "ordinal per workset")


def test_plan_rejects_split_workset_run() -> None:
    plan = partition(policy(), run(WS_A, 1) + run(WS_B, 1))
    first, second = plan.partitions
    again = first.model_copy(update={"ordinal": 0})
    with pytest.raises(ValidationError):
        rebuilt(plan, (first, second, again))


def rebuilt(plan: PartitionPlan, parts: tuple[Partition, ...]) -> PartitionPlan:
    return PartitionPlan(
        policy_version=plan.policy_version,
        policy_sha256=plan.policy_sha256,
        partitions=parts,
        plan_sha256=plan_digest(plan.policy_sha256, parts),
    )


def test_plan_rejects_forged_digest_and_order() -> None:
    plan = partition(policy(), run(WS_A, 4) + run(WS_B, 1))
    with pytest.raises(ValidationError):
        PartitionPlan(
            policy_version=plan.policy_version,
            policy_sha256=plan.policy_sha256,
            partitions=plan.partitions,
            plan_sha256="0" * 64,
        )
    swapped = tuple(reversed(plan.partitions))
    with pytest.raises(ValidationError):
        rebuilt(plan, swapped)
    skipped = (plan.partitions[1],) + plan.partitions[2:]
    with pytest.raises(ValidationError):
        rebuilt(plan, skipped)


def test_plan_rejects_duplicate_occurrence_across_partitions() -> None:
    plan = partition(policy(), run(WS_A, 4))
    dup = plan.partitions[1].model_copy(update={"indexes": (2, 3)})
    with pytest.raises(ValidationError):
        rebuilt(plan, (plan.partitions[0], dup))


def test_partition_rejects_unsorted_or_empty_indexes() -> None:
    for indexes in ((), (2, 1), (1, 1)):
        with pytest.raises(ValidationError):
            Partition(workset=WS_A, ordinal=0, indexes=indexes, total_bytes=1)


def test_partition_rejects_wrong_workset_schema() -> None:
    other = ResultRef("ws-a", "collected_selection", "1")
    with pytest.raises(ValidationError):
        Partition(workset=other, ordinal=0, indexes=(0,), total_bytes=1)
    with pytest.raises(A2ContractError):
        partition(policy(), [item(other, 0)])


def test_over_limit_inputs_are_rejected() -> None:
    with pytest.raises(A2ContractError, match="item limit"):
        partition(
            policy(max_items_per_workset=3, max_partitions_per_workset=3),
            run(WS_A, 4),
        )
    with pytest.raises(A2ContractError, match="partition limit"):
        partition(policy(max_partitions_per_workset=2), run(WS_A, 7))
    with pytest.raises(A2ContractError, match="byte limit"):
        partition(policy(), [item(WS_A, 0, size=101)])
    many = [r for n in range(5) for r in run(ResultRef(f"w{n}", WS_A.kind, "1"), 1)]
    with pytest.raises(A2ContractError, match="too many worksets"):
        partition(policy(), many)


def test_exact_limits_are_accepted() -> None:
    plan = partition(policy(), run(WS_A, 10, size=10))
    check(len(plan.partitions) == 4, "10 items at 3 per partition")
    plan = partition(policy(), [item(WS_A, 0, size=100)])
    check(plan.partitions[0].total_bytes == 100, "byte limit is inclusive")


@pytest.mark.parametrize(
    "changes",
    [
        {"max_worksets_per_call": 0},
        {"max_items_per_workset": 0},
        {"max_items_per_partition": 0},
        {"max_partitions_per_workset": 0},
        {"max_bytes_per_partition": 0},
        {"max_items_per_workset": -1},
        {"max_bytes_per_partition": -5},
        {"max_worksets_per_call": HARD_MAX_WORKSETS + 1},
        {"max_items_per_workset": HARD_MAX_ITEMS + 1},
        {"max_bytes_per_partition": HARD_MAX_PARTITION_BYTES + 1},
        {"max_items_per_partition": 11},
        {"max_partitions_per_workset": 11},
        {"max_items_per_partition": True},
        {"max_bytes_per_partition": 1.5},
        {"policy_version": ""},
        {"provisional": False},
        {"unknown_limit": 1},
    ],
)
def test_bad_policy_limits_are_rejected(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        policy(**changes)


def test_policy_is_frozen_and_provisional() -> None:
    value = policy()
    check(value.provisional is True, "ceilings must be marked provisional")
    check(PROVISIONAL_POLICY.provisional is True, "default is provisional")
    with pytest.raises(ValidationError):
        value.max_items_per_partition = 4  # type: ignore[misc]


@pytest.mark.parametrize(
    "items",
    [
        [],
        [item(WS_A, 1), item(WS_A, 0)],
        [item(WS_A, 0), item(WS_A, 0)],
        [item(WS_B, 0), item(WS_A, 0)],
        [item(WS_A, 0), item(WS_B, 0), item(WS_A, 1)],
    ],
)
def test_unsorted_duplicate_or_empty_input_is_rejected(
    items: list[PartitionItem],
) -> None:
    with pytest.raises(A2ContractError):
        partition(policy(), items)


def test_non_item_input_is_rejected() -> None:
    with pytest.raises(A2ContractError):
        partition(policy(), [(WS_A, 0, 1)])  # type: ignore[list-item]


def test_error_messages_carry_no_identifiers() -> None:
    secret = ResultRef("alice@example.com", WS_A.kind, "1")
    with pytest.raises(A2ContractError) as info:
        partition(policy(), [item(secret, 1), item(secret, 0)])
    check("alice" not in str(info.value), "identifier leaked")


def test_determinism_and_canonical_bytes() -> None:
    items = run(WS_A, 8, size=7) + run(WS_B, 5, size=9)
    first = partition(policy(), items)
    second = partition(policy(), list(items))
    check(first == second, "same input, same plan")
    check(first.plan_sha256 == second.plan_sha256, "same digest")
    check(first.model_dump_json() == second.model_dump_json(), "same bytes")


def test_digest_changes_with_policy_and_input() -> None:
    base = partition(policy(), run(WS_A, 4))
    other_policy = partition(policy(max_items_per_partition=2), run(WS_A, 4))
    other_input = partition(policy(), run(WS_A, 3))
    check(base.plan_sha256 != other_policy.plan_sha256, "policy must change digest")
    check(base.plan_sha256 != other_input.plan_sha256, "input must change digest")
    version = policy(policy_version="partition-test-2")
    check(version.digest() != policy().digest(), "version must change digest")


def test_check_within_rejects_other_policy_and_limits() -> None:
    plan = partition(policy(), run(WS_A, 7))
    with pytest.raises(A2ContractError, match="another policy"):
        plan.check_within(policy(policy_version="partition-test-2"))
    tighter = policy(max_items_per_partition=2)
    with pytest.raises(A2ContractError):
        plan.check_within(tighter)


def test_provisional_default_plans_a_full_workset() -> None:
    plan = partition(PROVISIONAL_POLICY, run(WS_A, HARD_MAX_ITEMS, size=1))
    check(len(plan.partitions) == HARD_MAX_ITEMS // 64, "64 items per partition")
    plan.check_within(PROVISIONAL_POLICY)


def test_plan_rejects_descending_indexes_across_partitions() -> None:
    plan = partition(policy(max_items_per_partition=2), run(WS_A, 4))
    first, second = plan.partitions
    low = first.model_copy(update={"indexes": (2, 3)})
    high = second.model_copy(update={"indexes": (0, 1)})
    with pytest.raises(ValidationError):
        rebuilt(plan, (low, high))
