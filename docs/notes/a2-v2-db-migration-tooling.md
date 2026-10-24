# A2 v2 migration tooling (C0-11c to C0-11e): PROVISIONAL / RESEARCH

Status: PROVISIONAL. Research only. This note describes a tool. It does not
migrate any real database. Tests use only files under `tmp_path`.

Code: `msgloom/persistence/a2_schema_migration.py`.
Tests: `tests/persistence/test_a2_schema_migrations.py` (C0-11c smoke and
C0-11d) and `tests/persistence/test_a2_compat_open.py` (C0-11e).
Plan: `docs/notes/a2-v2-db-schema-migration.md`.

## Placement differs from the manifest

The manifest task C0-11c names `schema_store.py` and
`msgloom/cli/a2_schema_migration.py`. This stage may not edit
`schema_store.py`, and the CLI path is outside the allowlist. The migration
is therefore a standalone module. It has `main(argv)` for a later CLI
wrapper. It has no console-script entry and nothing imports it.

## What the tool does

`migrate_database(path, backup_dir, *, confirm=False)`:

1. Refuse unless `confirm is True` (CLI flag `--confirm-migrate-to-schema5`).
2. Classify the file read only with `a2_schema.classify_schema`. A schema 5
   file returns `already-migrated`. Nothing is written and no backup is made.
3. Refuse every unknown, partial, altered, older (v2, v3) or foreign shape.
   The reason code comes from `classify_schema`, for example
   `unreviewed-table-set`, `schema4-definition-mismatch` or
   `view-or-trigger-present`. No backup is made for a refused file.
4. Copy the file into `backup_dir` with the SQLite online backup API. The
   directory must exist. The copy never overwrites a file and has mode 0600.
5. Verify the copy: `PRAGMA integrity_check` is `ok`, the copy is exact
   schema 4, its logical dump equals the source dump, and its SHA-256 is
   stable across a re-read. A failure removes the partial copy.
6. Compare the source dump with the backup again. A change in between gives
   `source-changed-after-backup`.
7. Build `MigrationGate` from the verified SHA-256 and the pinned
   `SCHEMA4_DIGEST`. Call `migrate_schema4_to_v5`. That function runs the DDL
   in one `BEGIN IMMEDIATE` transaction and rolls back on any exception,
   `BaseException` and failed `COMMIT`.
8. Re-open the file. Require exact schema 5 and a clean integrity check.

Errors are `A2SchemaError` with a reason code only. Output has no path, row
value, key or SQL text. The tool never logs.

## Operator procedure

1. Stop all A1 and A2 writers. The tool detects a change between backup and
   migration. It cannot stop a writer in the last instant before the lock.
2. Choose an empty backup directory. A retry after a failure needs a fresh
   directory, because the tool never overwrites a backup.
3. Run `main(["migrate", "--db", DB, "--backup-dir", DIR,
   "--confirm-migrate-to-schema5"])`. Record the printed `backup_sha256`.
4. Deploy a binary that accepts schema 5 (not yet available, see below).

## Rollback plan

`restore_backup(backup_path, target, expected_sha256, *, confirm=True)` (CLI
`restore ... --confirm-restore`):

1. Stop all writers, including the schema 5 binary.
2. Check the SHA-256 of the backup file against the recorded value.
3. Check that the backup is intact and exact schema 4.
4. Copy the backup over the target with the backup API.
5. Check that the target is intact, exact schema 4, with the backup dump.
6. Start the old schema 4 binary.

Writes made after the migration are lost. Export A2 rows first if needed.
There is no automatic downgrade. `git revert` does not roll back a file.

## Behavior findings

- `Phase1Store(database_url, registry)` is the open path. It calls
  `initialize_schema` and then `chmod` on the directory (0700) and file
  (0600). On a schema 4 file it changes no table, index, `user_version` or
  metadata row. The logical dump digest is identical before and after.
  Permission bits can change, as today.
- On a schema 5 file, `Phase1Store` raises `IncompatibleSchemaError` with the
  text `unreviewed neutral table set`. The file stays unchanged. This is the
  expected "old binary" result. Behavior was recorded, not changed.
- The test suite uses the real `initialize_schema` as the old-binary guard.
  It rejects the migrated file. After `restore_backup` it accepts the file.
- None of the five protected store modules mentions `a2_schema`. The tests
  check this, so open cannot reach the migration.
- A concurrent writer that holds `BEGIN IMMEDIATE` makes the migration fail
  with `migration-lock-failed`. The file stays unchanged. The backup stays.

## Later controlled integration

Not done in this stage. One database owner does these steps with review:

1. Move or wrap `main` as `msgloom/cli/a2_schema_migration.py`. Register a
   console script only after owner review.
2. Add the exact schema 5 state to `initialize_schema` in `schema_store.py`
   (validate, never write). Until then every store open refuses schema 5.
3. Update `store.py`, `intake_store.py`, `async_store.py` and
   `intake_completion.py` as listed in the migration plan.
4. Rerun the C0-11e tests. Their schema 5 refusal test must change then.

## Open items

- The pinned schema 4 digest is unverified against a real production file.
  Verify it read only in the owner stage. The tool fails closed.
- Live databases in WAL mode: the backup API is safe. Restore needs
  exclusive access. A restore over a file with open readers is expected to
  fail with `backup-copy-failed`. This case is not tested.
- The logical dump comparison reads the whole file several times. This is
  acceptable for the current size. Revisit for very large files.
