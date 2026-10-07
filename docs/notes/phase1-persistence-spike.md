# Phase 1 persistence spike

**Lane:** W-P1-FOUNDATION
**Date:** 2026-09-29
**Scope:** provider-neutral Phase 1 stage results, outcomes, and work claims only.

## Accepted manager decision

Use bounded, awaited `asyncio.to_thread` calls over synchronous SQLAlchemy 2.0.54
for the first provider-neutral Phase 1 tables. Keep these tables under one
`msgloom.persistence` schema owner and do not migrate or rewrite the proven A1
catalog.

The manager accepted this boundary after reviewing the R2 lifecycle repairs,
reproducing 40 focused tests and clean Pyright/live LSP diagnostics, and running
the equivalent-transaction comparison below. The initial Application uses a
separate SQLite file from A1. Each schema has one owner.

The implementation uses one async semaphore by default, explicit SQLite
`BEGIN IMMEDIATE` transactions for writes, and cancellation draining: once a
thread-backed database call starts, caller cancellation is delayed until the
physical call finishes. This makes the durable state known before a claim can
be released or the persistence resource can close.

No `aiosqlite` dependency is added to `pyproject.toml` or `uv.lock`.
Provider-neutral contracts remain standard-library dataclasses and protocols
until the manager-owned Pydantic dependency gate.

## Compared paths

1. **Implemented candidate:** SQLAlchemy 2.0.54 synchronous engine behind a
   bounded awaited `asyncio.to_thread` facade.
2. **Spike alternative:** SQLAlchemy 2.0.54 `AsyncEngine` with
   `sqlite+aiosqlite`, using a temporary isolated venv containing aiosqlite
   0.22.1. The shared project venv was not modified.

Both paths used file-backed SQLite and short transactions. The benchmark used
synthetic IDs and payloads only.

## Manager acceptance measurements

The manager found that the original benchmark used driver autocommit for the
synchronous candidate and a transaction for the async candidate. Those timing
figures were not a like-for-like comparison. The original worker artifact,
phase1-persistence-spike-measurements.json, is retained as historical evidence
and is not the basis for the decision.

The executable scripts/phase1-persistence-spike.py now uses explicit
``BEGIN IMMEDIATE`` / ``COMMIT`` / ``ROLLBACK`` boundaries for both candidates.
The manager reran three trials on this Raspberry Pi using SQLAlchemy 2.0.54 and
aiosqlite 0.22.1 in an isolated environment. The raw results are in
phase1-persistence-acceptance.json. Each trial used 80 sequential writes,
60 contended writes, a duplicate-claim race, a 2 ms event-loop heartbeat, and
cancellation while a writer waited behind a SQLite lock.

| Metric, median of three runs | sync SQLAlchemy + awaited thread | AsyncEngine + aiosqlite |
| --- | ---: | ---: |
| 80 sequential writes | 0.3143 s | 0.3734 s |
| 60 contended writes | 0.2151 s | 0.2915 s |
| Maximum heartbeat delay | 4.321 ms | 2.408 ms |
| Duplicate claim race | 1 acquired / 1 blocked | 1 acquired / 1 blocked |
| Cancellation return | 0.1840 s | 0.1694 s |
| Write after cancellation | drained and committed | rolled back |

These small trials establish correctness and local feasibility. They do not
establish a general throughput advantage. Both candidates kept the event loop
responsive. The chosen synchronous boundary reuses the tested A1 execution
shape and needs no new driver dependency. Its explicit drain rule makes the
physical write outcome known before cancellation returns or resources close.

Reproduce the comparison in an isolated environment with:

    python scripts/phase1-persistence-spike.py --runs 3 \
      --output docs/notes/phase1-persistence-acceptance.json

The production claim and cancellation regressions test the actual store and
facade; the benchmark alone is not their proof. Future stages must await their
writes and must not release dependent work before durable acceptance. A future
migration to an async driver requires separate correctness and migration tests.

## Transactional claims and ordering

`phase1_work_claims` has one current row per logical claim key.
`phase1_claim_attempts` retains attempt history. Claim acquisition:

- runs under `BEGIN IMMEDIATE`;
- validates every required result is already durable;
- rejects an input unless it is explicitly marked acceptable;
- excludes duplicate owners across independent processes;
- allows an expired safe claim to be superseded;
- prevents an old claim token from releasing a newer owner;
- preserves unknown, pending, accepted, or confirmed external-effect state so a
  stale submission cannot be blindly retried.

Preparation, triage, report build, and report submission have distinct
`ClaimKind` values. No daemon, queue, or generic workflow engine is added.

## Schema ownership and reopening

The neutral owner creates only `phase1_*` tables and records schema version 1
in `phase1_schema_metadata`. Reopening requires the exact expected neutral
table set and version. A partial or different neutral schema fails visibly;
there is no automatic migration on import.

This lane adds no A1 metadata, columns, migrations, or `CatalogService`
behavior. For initial integration, a separate Application database URL is the
smallest ownership boundary; if the manager later chooses one physical SQLite
file, A1 and Phase 1 must still retain disjoint table ownership and SQLite
writer serialization. Two owners must never manage the same table set.

## Contract map for downstream lanes

- `msgloom.contracts.OperationRequest`: execution identity, caller,
  `PhaseCapability`, exact target version refs, authority ref, and
  transport-neutral string parameters.
- `msgloom.contracts.OperationOutcome`: exact execution/capability, terminal
  status, result refs, limitations, failures, and external-effect state.
- `msgloom.contracts.StageResult`: immutable result identity/kind/schema,
  result lineage, source/prepared/topic versions, configuration/code/rule/
  prompt/model/context versions, attempt identity, diagnostics, limitations,
  failures, terminal status, and explicit acceptability.
- `ResultSchemaRegistry`: exact kind/version allowlist. Unknown required
  schemas fail; a reviewed downstream producer extends the registry explicitly.
- `Phase1Persistence.append_result()`: append-only result interface.
- `Phase1Persistence.acquire_claim()`: durable ordered-stage gate. Parser-prep
  should claim preparation work only after its declared source/result inputs are
  durable and should finish the claim only after all result writes have been
  awaited.
- `EvidenceReader` and `ResultProducer`: narrow test-double-compatible
  protocols; they contain no CLI, SDK, Scrapy, or ORM types.
- `Application.run()`: the sole async application entry point. It is awaited
  by a caller already inside an event loop. A4/A6/A7 are rejected and the
  blocked outcome is saved before any handler factory can run. Enabled
  capabilities are deny-by-default unless an exact TrustedAdmission binding
  matches caller, authority reference, and capability. A future CLI constructs
  those bindings from trusted configuration or approval state; request strings
  never create authority.

Current registered result kinds are `prepared@1`, `triage@1`, `report@1`,
and `report_submission@1`. Parser-prep should propose any more granular
preparation result kinds to the manager and extend the registry explicitly
rather than storing an unknown schema.

## Component-layout integration note

After the foundation contract review, add entries for `msgloom/contracts/`,
`msgloom/application/`, and `msgloom/persistence/` to
`docs/component-layout.md`. This worker intentionally does not edit that
shared document. The entries should state that these packages are
provider-neutral, that the Application owns no event loop or scheduler, and
that Phase 1 persistence owns only the new neutral tables.
