# A2 v2 schema migration plan (C0-11a): PROVISIONAL / RESEARCH

Status: PROVISIONAL. Research only. This note is a plan for review by the
database owner. It does not migrate any database. It changes no A1 file.

Supervisor override: the manifest names `docs/decisions/a2-v2-schema-migration.md`.
This note lives at `docs/notes/a2-v2-db-schema-migration.md` instead.

Code that follows this plan: `msgloom/persistence/a2_schema.py` (C0-11b).
Tests: `tests/persistence/test_a2_schema.py`.

## Decision

1. Migrate from schema 4 to schema **5** on the **main version axis**.
   Keep `preparation_proof_revision = 1`. Add two A2 metadata keys.
2. Run the migration only through an explicit, operator-gated function.
   Opening a database never creates an A2 table and never writes metadata.
3. Do not migrate the user's database in this stage. The stage uses only
   disposable SQLite files under `tmp_path`.
4. Treat every unknown, older or partial shape as an error. Never repair.
5. Roll back by restoring a verified backup with the old schema 4 binary.
   `git revert` does not roll back a database.

## Facts: the existing schema 4

Source: `msgloom/persistence/schema_store.py` at base commit `8d903b5`.
This note only reads that file.

| Item | Value |
| --- | --- |
| Main version key | `phase1_schema_metadata.schema_version`, text |
| Revision key | `phase1_schema_metadata.preparation_proof_revision`, text |
| Current pair | `schema_version = "4"` and `preparation_proof_revision = "1"` |
| Legacy marker keys | `preparation_proof_legacy_terminal:<result_id>` (value: scope key) |
| Candidate-v4 digest | `3cf62de248147e6897146c95b8fd03c8de9e6633845698b9d9332aaff26fd181` |
| Table prefix | `phase1_`; ASCII case folds; other case is a different name |

The candidate-v4 digest covers 10 tables and their explicit indexes. It
hashes `CreateTable` and `CreateIndex` output with whitespace collapsed.
Tables sort by name. Indexes sort by name inside each table. Joiner is
`"\n"`. The digest is the reviewed definition from commit `8dfad67`. A change
to the SQLAlchemy models makes `initialize_schema` raise
`IncompatibleSchemaError`. This stops silent redefinition by subtraction.

### Recognized states of `initialize_schema`

| Table set | `schema_version` | revision | Action today |
| --- | --- | --- | --- |
| none of `phase1_*` | n/a | n/a | create all, write `4` and `1` |
| v2 (6 tables) | `2` | absent | migrate to `4` and `1` |
| v3 (7 tables, adds `phase1_reconciliations`) | `3` | absent | migrate |
| candidate-v4 (10 tables, adds 3 intake tables) | `4` | absent | add proof tables, write `1` |
| expected (12 tables, adds 2 proof tables) | `4` | `1` | open, no write |
| anything else | any | any | `IncompatibleSchemaError` |

Every named table passes a structure check before any version is read. The
check covers columns, nullability, primary key, unique, indexes, CHECK text,
absence of foreign keys, and BINARY collation of columns and index keys. The
function also refuses an owned trigger, an owned-name view, and an occupied
creation name.

### Risk found: open runs the migration

`Phase1Store.__init__` calls `initialize_schema(self.engine)` on every open.
That call creates tables on an empty file and migrates older versions. If
A2 DDL enters that path, deploying new code upgrades the production database
on first open. The old binary then rejects the database: `existing` holds an
unknown `phase1_*` table set. This is the main hazard of the programme.

## Comparison: main version axis or metadata revision axis

| Question | Main version `5` | New revision key, version stays `4` |
| --- | --- | --- |
| Old binary on a migrated file | Rejects (table set unknown) | Rejects (table set unknown) |
| Can one value tell the shape? | Yes: `5` means the v5 table set | No: `4` now has two table sets |
| Pinned matrix size | One more row | Product of version and two revisions |
| Detects half migration | A `4` file with A2 tables is an error | Needs extra cross-checks |
| Code change in A1 | One new exact state | One new exact state |
| Precedent | v2 to v3 to v4 | `preparation_proof_revision` |

The old binary rejects both options, so neither option gives a free
rollback. The version axis makes the file self-describing. Choose it.

The proof revision stays an independent axis. It records a legacy-hold
decision, not a table-set generation. Do not reuse that axis for A2.

### Target state for schema 5

| Key in `phase1_schema_metadata` | Value |
| --- | --- |
| `schema_version` | `5` |
| `preparation_proof_revision` | `1` (unchanged) |
| `a2_schema_revision` | `1` |
| `a2_producer_marker` | `a2-kedro-v2-schema@1` |

The table set is the 12 expected tables plus the A2 tables listed in
`a2_schema.py`. A2 tables use the `phase1_a2_` prefix. They reference only
each other. No A2 table references an A1 table. No A1 table changes.

## What the migration must recognize exactly

Before any write, the migration reads `sqlite_schema` of the main database.
It accepts only this input:

1. `schema_version = "4"` and `preparation_proof_revision = "1"`.
2. The exact 12 expected table names, with no other `phase1_*` name and no
   `phase1_a2_*` name of any case.
3. The whitespace-collapsed SQL of those 12 tables and their explicit
   indexes, sorted by name and joined by `"\n"`, has SHA-256
   `e7bbda8e66251a36e9fea82fd6ae1ce68539e45f8b0561f4fc541b58490d8657`.
   This is the digest of the SQLAlchemy 2.x SQLite DDL of
   `Phase1Base.metadata` at `8d903b5`. A test rebuilds the digest from the
   live models and from a real file in `tmp_path`, so model drift fails.
4. No trigger and no view anywhere in the main database.
5. Metadata keys are only the two known keys, plus any number of
   `preparation_proof_legacy_terminal:*` keys. Any other key is an error.
6. `PRAGMA foreign_keys` does not change the result. The check reads schema
   text only and does not read user rows.

It rejects, with no write: v2, v3, candidate-v4 (run the A1 migration
first), an empty file, a file with a foreign schema, a partial A2 table set,
a changed A2 table, version `5` without the marker, and any version other
than `4` or `5`. Version `5` with the exact A2 set and marker is "already
migrated" and is also a no-op error for the migration function.

Error messages carry a short reason code only. They never carry a path, a
row value, a key, a claim token or any SQL text from the file.

## Guarded migration steps

All steps run inside one `BEGIN IMMEDIATE` transaction on one connection.
SQLite DDL is transactional, so a failure rolls back the tables too.

1. Check the operator gate (next section). Fail before any lock.
2. `BEGIN IMMEDIATE`.
3. Recognize the schema 4 input exactly. Re-check inside the lock.
4. Check that no `phase1_a2_*` name, index name, view or trigger exists.
5. Run the A2 DDL statements in a fixed order.
6. Update `schema_version` to `5`. Insert the two A2 keys.
7. Recognize the schema 5 output exactly (tables, indexes, keys).
8. `COMMIT`. On any exception, including `BaseException`: `ROLLBACK`.

A process crash before `COMMIT` leaves the file in schema 4. SQLite
recovers the journal on the next open. After `COMMIT` the file is schema 5.

## Operator gate

The function needs an explicit gate value. The gate carries:

- the SHA-256 of the verified backup file (64 lowercase hex);
- the schema 4 digest from the pinned list above, as the operator read it.

The function refuses to run when the backup digest has a wrong shape or the
schema digest differs from the pinned value. It does not read or hash the
backup. It does not take the path of the user's database from any default,
environment variable or settings file. The caller passes an open connection.

Limits of the gate in this stage:

- `backup_sha256` is checked for shape only (64 hex characters). The
  function does not read the backup and cannot prove that the backup
  exists or matches the file. The real operator gate is the maintenance
  CLI (C0-11c). It is not part of this stage. It must verify the backup.
- Foreign objects that do not use the `phase1_` prefix are tolerated.
  Examples are a table with another prefix and an index on such a table.
  The recognizer checks owned `phase1_` objects only. It still refuses any
  view, any trigger, any extra index on an owned table and any
  `phase1_a2_*` name that is not reviewed.
- The migration reclassifies the file inside the write lock. A change made
  between an earlier read-only check and `BEGIN IMMEDIATE` is refused with
  a reason code. A failure of `COMMIT` rolls back and raises
  `migration-failed`.

No other code path creates A2 tables:

- `require_schema5` checks a file and raises on schema 4. It writes nothing.
- No `open`, `create` or `__init__` function calls the migration.
- The research store (`a2_sqlite_store.py`) still creates only its own
  scratch file with `a2c0_*` tables.

This stage does not run the migration on any real database. A later
maintenance CLI (C0-11c) wraps the function. The owner reviews that CLI.

## Backup and rollback expectations

Before migration (operator checklist, for the later stage):

1. Stop all A1 and A2 writers. Confirm no pending Workset needs the old A2.
2. Take a backup with the SQLite online backup API or `VACUUM INTO`, not by
   copying a live file.
3. Open the backup read-only. Run `PRAGMA integrity_check`. Compare the
   schema 4 digest. Record the backup SHA-256.
4. Restore the backup once into a scratch directory as a rehearsal.

Rollback:

- Before `COMMIT` no action is needed. The file is still schema 4.
- After `COMMIT`, the old binary rejects the file. Stop writers. Restore
  the backup. Start the old schema 4 binary.
- Writes made after the migration are lost on restore. Export A2 rows
  first if they matter. The plan promises no automatic downgrade.
- A forward fix (a reviewed migration to schema 6) is the second option.
- Keep the backup until the owner closes the cutover.

## Later controlled edits in the five protected files

This list is documentation only. No protected file changes in this stage.
One database owner makes these edits, in order, with their own review.

| File | Needed change |
| --- | --- |
| `schema_store.py` | Add an exact schema 5 state to `initialize_schema`. For schema 5 the function must validate and not write. For schema 4 it must not touch A2 names or the version. Extend the trigger, view and name checks to `phase1_a2_*`. Call `a2_schema` for the pinned digest and for migration. Never call the migration from `initialize_schema`. |
| `store.py` | `Phase1Store.__init__` must keep opening schema 4 and schema 5 with no write beyond today's. Expose the recognized state so A2 writers can refuse on schema 4. Chmod behavior stays. |
| `intake_store.py` | The v1 terminal writer must refuse a Workset that has a v2 producer binding. The v2 finalizer must refuse a v1-owned or terminal row. Both checks run in the writer transaction. Legacy-hold reads stay. |
| `async_store.py` | Add awaited facade methods for the v2 writers. Keep v1 methods unchanged. |
| `intake_completion.py` | Keep the v1-only proof. Add a guard that rejects a v2-marked Workset. v2 receipts live in A2 tables, not here. |

Also needed, outside the five files: a maintenance CLI (C0-11c), tests for
open of schema 4 without change (C0-11e), and the DDL failure matrix
(C0-11d).

## Open items and not claimed

- The SQL text of a real production file was not inspected. The pinned
  digest assumes the same SQLAlchemy output as the current models. A real
  file made by older code may differ in whitespace or quoting. The
  recognizer fails closed. Verify the digest read-only in the owner stage.
- The A2 kind and version names in the A2 DDL CHECK are provisional (see
  `docs/decisions/a2-v2-schema-ids.md`). Freeze them before any migration.
- Dispositions, receipts and producer-binding tables are not in this
  stage's DDL. They need their own revision or a schema 6.
- The claim table is a sidecar ledger of winning proofs. It does not replace
  `phase1_work_claims`. Lease and expiry rules belong to the C0-12b owner.
- No claim of production acceptance. No `kedro` dependency is added.
