# A2 Kedro v2: C0 contract and isolated store (CANDIDATE/RESEARCH)

Status: candidate code. It is not production-ready. Nothing here is wired
into dispatch, schema autoload, `Phase1Store`, Intake or A1 readers. Kedro is
not imported.

## What the code provides

| Capability | Module |
| --- | --- |
| Bounded canonical JSON, strict decode, domain-separated SHA-256 | `msgloom/a2_kedro/contracts/codec.py` |
| Closed `(kind, version)` allowlist; `prepared@1` is read-only history | `msgloom/a2_kedro/contracts/schema_ids.py` |
| Frozen source roots; read-only A1 occurrence adapter and ordinal proof | `msgloom/a2_kedro/contracts/source.py` |
| Input-only logical key, ordered upstream lineage, attempt proof, stage metadata digest, status/limitations digest | `msgloom/a2_kedro/contracts/identity.py` |
| `a2_input_disposition@1` held record with explicit `repair_class` | `msgloom/a2_kedro/contracts/held.py` |
| `a2_completion_receipt@2` structure; held-only terminal INCOMPLETE | `msgloom/a2_kedro/contracts/receipt.py` |
| Accepted-stage record and pure append-or-verify decision | `msgloom/persistence/a2_acceptance_models.py` |
| Own DDL (`a2c0_*` tables, CHECK constraints) | `msgloom/persistence/a2_sqlite_ddl.py` |
| Isolated SQLite append-or-verify store | `msgloom/persistence/a2_sqlite_store.py` |

## Behavior

- The logical key is `a2-accepted:` plus a domain-separated SHA-256 of
  frozen inputs only. It excludes output digest, time, execution, attempt
  and node name. Retries by any worker compute the same key.
- Every upstream reference must be an accepted key with an approved
  kind and version. Order is part of the key.
- Attempt identity (`AttemptProof`) is stored beside the accepted stage.
  It keeps only a SHA-256 of the claim token.
- The stage metadata digest covers status, limitation set, input refs,
  versions, lineage and the semantic-data reference. Two results with equal
  payload bytes and different status or limitations conflict.
- Replay compares integrity fields only. The first writer proof stays
  stored. A conflict commits an attempt row, raises, and leaves the
  accepted row unchanged. Conflict reports name fields, not values.
- `ReadOnlyOccurrenceAdapter` only calls `read_entry`. The ordinal proof
  must match exactly one ordinal and the saved selection digest must equal
  the re-read digest. Role comes from the proven ordinal.
- A workset with intake-held entries, any A2-held root or any INCOMPLETE
  root yields a receipt that must be INCOMPLETE. A held-only workset is a
  valid terminal INCOMPLETE receipt.
- `A2ResearchStore.create` accepts only a path that does not exist.
  `open_existing` accepts only a file with the store marker. Writers use
  `BEGIN IMMEDIATE`; compare and insert share one transaction. SQL CHECK
  constraints reject malformed keys, digests and statuses.

## Limits of the earlier prototypes

The read-only prototypes `c0_contract_prototype.py` and
`c0_atomic_acceptance_prototype.py` informed this code. They had these
limits, which this code changes or leaves open:

- The prototype key covered inputs but its replay compared only output ref,
  payload SHA and byte count. It did not compare status, limitations or a
  stage metadata digest. This code does.
- The prototype had no separate attempt record and no writer claim proof.
- The prototype accepted any upstream `ResultRef`. This code requires an
  accepted key and an approved kind/version, and rejects `prepared@1`.
- The prototype receipt model did not carry an intake-held count. The
  held rule lived only in `validate_against`, not in the model itself.
- The prototype transaction used private `Phase1Store` internals and
  `require_claim_publication`. This code does not use them and therefore
  also does not check a live claim.
- The prototype verifier imported A1 types directly. This code reads
  through a small protocol and a snapshot dataclass. It still mirrors the
  Intake ordinal formula (`_identity("selection", ...)`). A public A1
  verifier is needed before production.

## Not done (open items)

- Live claim, `required_inputs` and plan checks inside the transaction.
- Check that stored semantic-data bytes match `canonical_sha256`.
- Reachability check of the upstream chain at publish time.
- Async facade, `Phase1Persistence` semaphore and cancel drain.
- Final table names, migration, producer binding and schema marker. These
  belong to the database owner (C0-11a to C0-11e).
- Frozen wire names. `docs/decisions/a2-v2-schema-ids.md` (C0-00) is not
  written. Names here are provisional.
- Content-bearing `prepared@2`, parse, zone and relation models (C0-03 to
  C0-07) and transition fact fields beyond `IntakeTransition`.
- Registry factory (C0-21a) and `triage_input@2` (C0-17).
- Baseline roots take a caller-supplied selection digest. A verified
  baseline loader is open.

## Future guarded hooks for old persistence

These changes are intentionally not made. Each needs the database owner.

1. `schema_store.initialize_schema`: no automatic creation of A2 tables on
   ordinary open. Add an explicit maintenance command that creates the
   final tables and a schema/producer marker.
2. `Phase1Store` publish path: a v2 branch that accepts an `a2-accepted:`
   claim namespace beside `prepare:` and verifies `required_inputs`, plan
   and original publisher claim inside `BEGIN IMMEDIATE`.
3. `intake_completion.py` and `intake_store.finalize_...`: a versioned
   `finalize_a2_intake_workset_v2` that writes the receipt row and the
   workset terminal update in one transaction. The v1 finalizer must
   refuse a v2-bound workset. The v2 finalizer must refuse a v1-owned one.
4. `async_store.py`: thin delegating methods for the new store, using the
   existing semaphore and cancel-drain path, so the module stays below 500
   lines.
5. `ResultSchemaRegistry` and `SemanticDataRegistry`: a new v2 factory with
   an explicit closed allowlist. Do not change `phase1()`.

## Verification

Focused tests live in `tests/a2_kedro/`. They use `tmp_path` SQLite only and
make no assumption about host OS or interpreter path. Run:

```text
python -m pytest tests/a2_kedro -q
ruff check msgloom/a2_kedro msgloom/persistence/a2_*.py tests/a2_kedro
pyright msgloom/a2_kedro msgloom/persistence/a2_*.py tests/a2_kedro
```
