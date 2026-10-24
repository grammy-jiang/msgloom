# A2 v2 contract C0-16: partition policy (PROVISIONAL)

Code: `msgloom/a2_kedro/partition_policy.py`.
Tests: `tests/a2_kedro/test_c0_16.py`.

This note records the research form of the partition and Workset scope
policy. All names and numbers are PROVISIONAL. Nothing is wired into a
graph, a store or a claim.

## Policy

`PartitionPolicy` is a strict frozen model. Fields:

- `policy_version`: text, part of the stage key as
  `partition_policy_version`.
- `max_worksets_per_call` (1 to 64).
- `max_items_per_workset` (1 to 1024, the existing `max_roots`).
- `max_items_per_partition` (1 to 1024, at most the workset limit).
- `max_partitions_per_workset` (1 to 1024, at most the workset limit).
- `max_bytes_per_partition` (1 to 64 MiB).
- `provisional`: always `true`.

Zero, negative, boolean, float and unknown fields are rejected. The policy
digest uses domain `a2-partition-policy@1`.

## Planner

`partition(policy, items) -> PartitionPlan` is a pure function.

- Input is `PartitionItem(workset, index, size_bytes)`. It must be strictly
  increasing by `(workset, index)`. Empty, unsorted and duplicate input is
  rejected. The planner never sorts.
- Fill is sequential and greedy. A new partition starts on the item limit
  or the byte limit. One occurrence above the byte limit is rejected.
- A partition holds one Workset ref. Partitions never merge across
  Worksets. Ordinals are contiguous from 0 per Workset. The ordinal is the
  `partition_ordinal` of the stage identity.
- `PartitionPlan` re-checks sorting, contiguity, no repeated occurrence and
  its digest (`a2-partition-plan@1`). `check_within(policy)` re-checks the
  limits and the policy binding.
- Error messages carry no identifiers.

## Open items

- Every ceiling, including `PROVISIONAL_POLICY`, is a placeholder. P1/P2
  profiling on the Pi must replace it. The default is not a recommendation.
- Empty input is rejected. A held-only Workset has no partition. The
  caller must handle it before it calls `partition`. Decide at C0-20a.
- Byte size per occurrence comes from the caller. The source of that size
  (saved bytes or parsed bytes) is not decided.
- The plan digest and the stage key are separate. C0-10 or C0-21a must bind
  `policy_sha256` into the key, not only `policy_version`.
