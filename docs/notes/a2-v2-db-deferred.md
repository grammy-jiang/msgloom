# A2 v2 database work deferred past C0-11b and C0-12a

Status: PROVISIONAL. Research only. This note lists what the A2 database
stage does not do yet. It changes no database.

## 1. The migration gate is not the real gate

`MigrationGate.backup_sha256` in `msgloom/persistence/a2_schema.py` is only
shape-checked. The check accepts 64 lowercase hex characters. The function
`migrate_schema4_to_v5` never reads a backup file. A valid-looking digest is
not proof that a backup exists or that it matches the database.

The real operator gate is the later C0-11c CLI. That CLI is not implemented
in this stage. The CLI must do these steps before it calls the migration:

1. Take or locate the backup of the schema 4 database.
2. Hash the backup file and verify that it opens as schema 4.
3. Show the pinned `SCHEMA4_DIGEST` to the operator for confirmation.
4. Build `MigrationGate` from the verified values only.

Until then, no code path may call `migrate_schema4_to_v5` on a user
database. Tests call it only on files under `tmp_path`.

## 2. Old store modules are not integrated

Integration into the old store modules is a later, controlled step. These
modules are protected in this stage and stay unchanged:

- `schema_store.py`: `initialize_schema` accepts only schema 4
  (`_SCHEMA_VERSION = "4"`). It raises `IncompatibleSchemaError` for any
  other file. It needs a reviewed rule for a schema 5 file. The rule must
  accept the exact shape from `classify_schema`, never create or repair
  A2 tables, and keep the schema 4 digest check.
- `store.py`: `Phase1Store` opens through `initialize_schema`. It needs a
  decision on which schema versions it may open. It needs a call to
  `require_schema5` where A2 writers run.
- `intake_store.py`: intake admission and pending completion run in
  `Phase1Store` transactions. They need hooks that call the A2 claim and
  accepted-stage checks in the same transaction.
- `async_store.py`: the async facade needs awaited wrappers for each new
  A2 operation.
- `intake_completion.py`: the terminal lineage proof needs to read the
  accepted-stage proof and the A2 receipt for A2 results.

Each change needs its own review, its own tests, and a backup and rollback
plan that follows `docs/notes/a2-v2-db-schema-migration.md`.

## 3. Test paths differ from the manifest

The manifest names `tests/a2_kedro/test_c0_11b.py` and
`tests/a2_kedro/test_c0_12a.py`. The workflow allowlist for this stage
does not include `tests/a2_kedro/`. The tests therefore live in
`tests/persistence/test_a2_*.py`:

- `test_a2_schema*.py`: C0-11a and C0-11b (schema, migration, races).
- `test_a2_acceptance_models.py`: C0-12a (accepted-stage records).
- `test_a2_transactions.py`: rollback on a failed `COMMIT` and on any
  `BaseException`.

A later step can move or mirror these tests to the manifest paths.

## 4. Transaction failure handling (done in this stage)

Both transaction helpers use `msgloom/persistence/a2_txn.py`. The helper
`rollback_quietly` rolls back on a best-effort basis. It never replaces the
original exception, also when the connection is closed or the transaction
already ended.
