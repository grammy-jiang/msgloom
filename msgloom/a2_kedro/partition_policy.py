"""
Versioned, bounded partition policy for A2 v2 Workset scope (C0-16).

A partition is a bounded run of selected occurrences of one Workset. The
policy fixes finite limits. The planner is a pure function of the policy
and the ordered input. It never reads a clock, a random source or the
host.

Rules:

* A partition holds occurrences of exactly one Workset ref. Partitions
  never merge across different Workset refs.
* Input must be strictly increasing by ``(workset, index)``. The planner
  rejects unsorted or duplicate input. It never sorts for the caller.
* Fill is sequential and greedy, so one input gives one plan. A new
  partition starts when the next occurrence would exceed an item or byte
  limit of the policy.
* Partition ordinals are contiguous from 0 inside one Workset. They are
  the ``partition_ordinal`` of the stage identity.
* Every limit is finite and at least 1. A single occurrence larger than
  the byte limit is rejected. The planner cannot split an occurrence.

CANDIDATE/RESEARCH, PROVISIONAL: every resource ceiling here, including
the byte limit, is a placeholder. P1/P2 profiling on the Pi must replace
them. See ``docs/notes/a2-v2-contract-c0-16.md``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated, Literal

from pydantic import Field, model_validator

from msgloom.a2_kedro.contracts.codec import (
    A2ContractError,
    A2Model,
    Digest,
    Text,
    domain_sha256,
)
from msgloom.a2_kedro.contracts.header import LIMITS
from msgloom.a2_kedro.contracts.source import Index
from msgloom.contracts import ResultRef

POLICY_DOMAIN = "a2-partition-policy@1"
PLAN_DOMAIN = "a2-partition-plan@1"

#: Hard ceilings that no policy may exceed. PROVISIONAL until profiling.
HARD_MAX_WORKSETS = 64
HARD_MAX_ITEMS = LIMITS["max_roots"]
HARD_MAX_PARTITION_BYTES = 64 * 1024 * 1024

Count = Annotated[int, Field(ge=1, le=HARD_MAX_ITEMS)]


def _key(ref: ResultRef) -> tuple[str, str, str]:
    return (ref.result_id, ref.kind, ref.schema_version)


def _is_workset(ref: ResultRef) -> bool:
    return (ref.kind, ref.schema_version) == ("preparation_intake_workset", "1")


class PartitionPolicy(A2Model):
    """
    Finite, versioned limits for partitioning one or more Worksets.

    ``provisional`` is always true today. It marks every ceiling as a
    placeholder that P1/P2 profiling must replace.
    """

    policy_version: Text
    max_worksets_per_call: Annotated[int, Field(ge=1, le=HARD_MAX_WORKSETS)]
    max_items_per_workset: Count
    max_items_per_partition: Count
    max_partitions_per_workset: Count
    max_bytes_per_partition: Annotated[int, Field(ge=1, le=HARD_MAX_PARTITION_BYTES)]
    provisional: Literal[True] = True

    @model_validator(mode="after")
    def _consistent(self) -> PartitionPolicy:
        if self.max_items_per_partition > self.max_items_per_workset:
            raise A2ContractError("partition item limit exceeds workset limit")
        if self.max_partitions_per_workset > self.max_items_per_workset:
            raise A2ContractError("partition count limit exceeds workset limit")
        return self

    def digest(self) -> str:
        """Return the domain-separated digest of this policy."""
        return domain_sha256(POLICY_DOMAIN, self.model_dump(mode="json"))


#: Provisional default. Not a profiled or recommended production value.
PROVISIONAL_POLICY = PartitionPolicy(
    policy_version="partition-policy-1-provisional",
    max_worksets_per_call=8,
    max_items_per_workset=HARD_MAX_ITEMS,
    max_items_per_partition=64,
    max_partitions_per_workset=HARD_MAX_ITEMS,
    max_bytes_per_partition=16 * 1024 * 1024,
)


class PartitionItem(A2Model):
    """One selected occurrence to place: its Workset, index and byte size."""

    workset: ResultRef
    index: Index
    size_bytes: Annotated[int, Field(ge=0, le=HARD_MAX_PARTITION_BYTES)]


class Partition(A2Model):
    """A bounded run of occurrences of exactly one Workset."""

    workset: ResultRef
    ordinal: Index
    indexes: tuple[Index, ...]
    total_bytes: Annotated[int, Field(ge=0, le=HARD_MAX_PARTITION_BYTES)]

    @model_validator(mode="after")
    def _ordered(self) -> Partition:
        if not _is_workset(self.workset):
            raise A2ContractError("partition workset schema mismatch")
        if not self.indexes:
            raise A2ContractError("partition is empty")
        if any(a >= b for a, b in zip(self.indexes, self.indexes[1:], strict=False)):
            raise A2ContractError("partition indexes are not strictly increasing")
        return self

    def fingerprint(self) -> dict[str, object]:
        """Return the plain data that the plan digest covers."""
        return {
            "workset": list(_key(self.workset)),
            "ordinal": self.ordinal,
            "indexes": list(self.indexes),
            "total_bytes": self.total_bytes,
        }


def plan_digest(policy_sha256: str, partitions: tuple[Partition, ...]) -> str:
    """Return the plan identity over the policy digest and the partitions."""
    return domain_sha256(
        PLAN_DOMAIN,
        {
            "policy_sha256": policy_sha256,
            "partitions": [part.fingerprint() for part in partitions],
        },
    )


class PartitionPlan(A2Model):
    """The complete ordered partition list produced under one policy."""

    policy_version: Text
    policy_sha256: Digest
    partitions: tuple[Partition, ...]
    plan_sha256: Digest

    @model_validator(mode="after")
    def _closed(self) -> PartitionPlan:
        if not self.partitions:
            raise A2ContractError("plan has no partitions")
        seen: set[tuple[str, str, str]] = set()
        previous: tuple[str, str, str] | None = None
        expected = 0
        used: set[int] = set()
        last = -1
        for part in self.partitions:
            key = _key(part.workset)
            if key != previous:
                if previous is not None and key < previous:
                    raise A2ContractError("plan worksets are not sorted")
                if key in seen:
                    raise A2ContractError("plan splits a workset run")
                seen.add(key)
                previous, expected, used, last = key, 0, set(), -1
            if part.ordinal != expected:
                raise A2ContractError("partition ordinals are not contiguous")
            if used.intersection(part.indexes):
                raise A2ContractError("occurrence appears in two partitions")
            if part.indexes[0] <= last:
                raise A2ContractError("partition indexes are not ascending")
            used.update(part.indexes)
            last = part.indexes[-1]
            expected += 1
        if self.plan_sha256 != plan_digest(self.policy_sha256, self.partitions):
            raise A2ContractError("plan identity does not match its partitions")
        return self

    def check_within(self, policy: PartitionPolicy) -> None:
        """Raise :exc:`A2ContractError` unless the plan obeys ``policy``."""
        if (self.policy_version, self.policy_sha256) != (
            policy.policy_version,
            policy.digest(),
        ):
            raise A2ContractError("plan was made under another policy")
        per_workset: dict[tuple[str, str, str], list[Partition]] = {}
        for part in self.partitions:
            per_workset.setdefault(_key(part.workset), []).append(part)
            if len(part.indexes) > policy.max_items_per_partition:
                raise A2ContractError("partition exceeds item limit")
            if part.total_bytes > policy.max_bytes_per_partition:
                raise A2ContractError("partition exceeds byte limit")
        if len(per_workset) > policy.max_worksets_per_call:
            raise A2ContractError("plan exceeds workset limit")
        for parts in per_workset.values():
            if len(parts) > policy.max_partitions_per_workset:
                raise A2ContractError("plan exceeds partition limit")
            if sum(len(p.indexes) for p in parts) > policy.max_items_per_workset:
                raise A2ContractError("plan exceeds workset item limit")


def _check_input(
    policy: PartitionPolicy, items: Sequence[PartitionItem]
) -> dict[tuple[str, str, str], list[PartitionItem]]:
    if not items:
        raise A2ContractError("nothing to partition")
    groups: dict[tuple[str, str, str], list[PartitionItem]] = {}
    previous: tuple[tuple[str, str, str], int] | None = None
    for item in items:
        if not isinstance(item, PartitionItem):
            raise A2ContractError("input is not a partition item")
        if not _is_workset(item.workset):
            raise A2ContractError("item workset schema mismatch")
        current = (_key(item.workset), item.index)
        if previous is not None and current <= previous:
            raise A2ContractError("input is unsorted or has a duplicate")
        previous = current
        groups.setdefault(current[0], []).append(item)
    if len(groups) > policy.max_worksets_per_call:
        raise A2ContractError("too many worksets in one call")
    return groups


def _split(policy: PartitionPolicy, run: list[PartitionItem]) -> list[Partition]:
    if len(run) > policy.max_items_per_workset:
        raise A2ContractError("workset exceeds item limit")
    parts: list[Partition] = []
    batch: list[PartitionItem] = []
    size = 0

    def close() -> None:
        parts.append(
            Partition(
                workset=batch[0].workset,
                ordinal=len(parts),
                indexes=tuple(item.index for item in batch),
                total_bytes=size,
            )
        )

    for item in run:
        if item.size_bytes > policy.max_bytes_per_partition:
            raise A2ContractError("occurrence exceeds partition byte limit")
        full = len(batch) >= policy.max_items_per_partition
        over = size + item.size_bytes > policy.max_bytes_per_partition
        if batch and (full or over):
            close()
            batch, size = [], 0
        batch.append(item)
        size += item.size_bytes
    close()
    if len(parts) > policy.max_partitions_per_workset:
        raise A2ContractError("workset exceeds partition limit")
    return parts


def partition(policy: PartitionPolicy, items: Sequence[PartitionItem]) -> PartitionPlan:
    """
    Plan partitions for sorted occurrences under ``policy``.

    The result depends only on the policy and ``items``. Raise
    :exc:`A2ContractError` for empty, unsorted, duplicate or over-limit
    input. Messages carry counts and limits only, never identifiers.
    """
    groups = _check_input(policy, items)
    parts: list[Partition] = []
    for key in groups:
        parts.extend(_split(policy, groups[key]))
    ordered = tuple(parts)
    return PartitionPlan(
        policy_version=policy.policy_version,
        policy_sha256=policy.digest(),
        partitions=ordered,
        plan_sha256=plan_digest(policy.digest(), ordered),
    )
