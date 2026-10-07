# Topic 01 Engineering Validation

This directory contains **research engineering**, not msgloom production code.

It continues Topic 01 after Academic Rounds 1 and 2. It does not wait for or use production mailbox data. The initial evidence base is synthetic/adversarial and deterministic so ground truth is known exactly.

## Goals now

- **E1** — define and exercise a joint benchmark contract for message ancestry, quotation occurrences, source spans, unique content, decision-bearing spans, missing information and ambiguity.
- **E2** — measure preservation and quotation occurrence -> source-span behavior on controlled fixtures.
- **E3** — replay the same histories under different arrival orders and measure correction/retraction and final-state consistency.
- **E4** — evaluate Topic-01-specific confidence/abstention plumbing for structural relations on held-out synthetic cases.

## Explicit non-goals

- No production mailbox or user data.
- No claim of production representativeness.
- No semantic answer/agreement scope; that is Topic 04.
- No general reliability/calibration literature programme; that is Topic 10.
- No product architecture approval or production implementation.
- No Raspberry Pi performance benchmark yet (E6).
- No code/data/license reproduction work until a concrete external method is selected (E5).

## Layout

- `src/topic01_validation/` — research harness only.
- `fixtures/` — deterministic synthetic cases and gold annotations.
- `tests/` — standard-library `unittest` tests for the harness.
- `results/` — reproducible experiment outputs.
- `audit/` — manifests, hashes and run metadata.

See `PLAN.md`, `DEFERRED.md`, and `RESULTS.md` for scope, hand-offs and findings.
