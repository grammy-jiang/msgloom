# Phase 1 claim reconciliation API

Delivery recovery uses an explicit provider-neutral persistence operation. It
does not infer provider state, call a provider, or grant authority from source
text. The caller validates provider evidence and supplies exact ResultRef
values.

## Ownership and decisions

ReconciliationRequest binds a bounded ReconciliationIdentity, the exact
ClaimToken, one closed ExternalEffectState decision, and at most 32 unique
evidence references. Definite ACCEPTED, CONFIRMED, or REJECTED decisions
require evidence. An inconclusive decision is explicitly UNKNOWN.

Phase1Persistence.reconcile_external_effect() runs one BEGIN IMMEDIATE
transaction. It validates every evidence result through the registered result
and semantic-data contracts, requires the target token to remain the exact
current owner, appends immutable reconciliation proof, and changes retry gating
atomically. It never changes the original ClaimAttempt row.

PENDING or UNKNOWN can resolve to UNKNOWN, ACCEPTED, CONFIRMED, or REJECTED.
ACCEPTED can only refine to CONFIRMED. REJECTED removes the current claim so a
distinct retry attempt may acquire the scope. ACCEPTED, CONFIRMED, and UNKNOWN
retain a blocking current claim. Elapsed lease time alone never resolves
uncertainty.

Exact replay of one reconciliation identity and the same request returns the
saved result, including after a rejected scope was released. Reusing an
identity with different bytes fails. A stale token cannot resolve or release a
replacement owner, and two facades serialize opposed decisions so only one can
win.

## Restart inspection

Phase1Persistence.inspect_claim(claim_key, history_limit=100) returns a
ClaimInspection with the current exact token/effect/expiry, immutable attempt
history, immutable reconciliation history, and a history_truncated flag. The
limit is closed to 1 through 100. Delivery therefore does not need direct SQL
or private store access after restart.

A terminal attempt with UNKNOWN remains visible as UNKNOWN after later
reconciliation. This separation is deliberate: reconciliation records what was
learned later instead of rewriting what the original submission attempt knew.

## Schema and cancellation

The baseline already used neutral schema version 2. Reconciliation adds the
phase1_reconciliations table, so this lane advances the schema to version 3 and
contains an explicit version-2-to-version-3 additive migration. The migration
creates only the new table and updates schema metadata in one immediate
transaction; existing data is preserved. Other table sets or versions fail
closed rather than being recreated.

The async facade uses the existing accepted-write draining contract.
Cancellation, including repeated cancellation, is delayed until the accepted
SQLite reconciliation transaction has physically completed. Close therefore
cannot race a still-running accepted reconciliation write.
