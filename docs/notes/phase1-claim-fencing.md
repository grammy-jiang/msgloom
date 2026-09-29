# Phase 1 claim-bound publication

**Scope:** durable claim fencing for Phase 1 result publication.

## Public API

Operation handlers that acquire a durable claim must pass that exact token when
publishing results:

```python
claim = await persistence.acquire_claim(
    claim_key,
    ClaimKind.PREPARE,
    execution,
    attempt,
    required_inputs=inputs,
)

await persistence.append_result(result, claim=claim)
await persistence.append_result_with_data(
    semantic_result,
    semantic_value,
    claim=claim,
)
```

Both append methods retain `claim=None` for explicit seed, immutable evidence,
and compatibility writes that do not represent claim-owned operation
publication. Those calls are not claim fenced. A2, A3, report-build, and
report-submit operation handlers must supply their acquired claim. This change
does not imply that every existing or future caller has already adopted the
fence.

`append_result_with_data()` also retains `require_new=True`. Claim
validation, semantic insertion, and result insertion execute in the same
`BEGIN IMMEDIATE` writer transaction. A stale, expired, reclaimed, terminal,
or execution-mismatched claim therefore leaves neither a result nor newly
inserted semantic bytes.

## Ownership and lineage

A publication token must still be the exact current durable owner: claim key,
opaque token, claim kind, execution, and enclosing attempt metadata must match
the current claim row. Its lease must be active and its claim-attempt history
must not be terminal.

The published `StageResult.execution` must equal the claim execution. The
result attempt is deliberately not required to equal `ClaimToken.attempt`.
This permits a bounded child AI attempt to retain its own attempt identity
while remaining fenced by the enclosing operation execution. Persistence does
not import AI, triage, reporting, or preparation policy to infer lineage.

Lease seconds accept finite non-negative `int` or `float` values except
`bool`. NaN, infinities, negative values, and booleans fail before claim
acquisition. Zero remains valid and intentionally creates an immediately
expired lease for deterministic expiry tests.

The async facade continues to drain every accepted thread-backed transaction
through cancellation. It does not release or dispose persistence ownership
while accepted work is still running.

## External effects

A report-submission claim whose lease expires while its durable external effect
is still `NOT_STARTED` (or another safe-retry state) cannot start a new
external effect or finish as though it still owned the operation.

External submission must persist `PENDING` while the lease is active before
the external action can become uncertain. If that already-started effect
outlives the lease, the same token may still record reconciliation such as
`UNKNOWN`, `REJECTED`, `ACCEPTED`, or `CONFIRMED`, and may finish the
attempt. This exception records the outcome of an effect that was already
started; it does not renew ownership or authorize another submission.

`PENDING`, `UNKNOWN`, `ACCEPTED`, and `CONFIRMED` continue to block
automatic reclaim. Finishing with an uncertain/non-retry-safe effect preserves
the durable claim row for reconciliation. No provider delivery behavior is
implemented here.
