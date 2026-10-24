"""
Explicit, operator-driven schema 4 to schema 5 migration of a SQLite file.

CANDIDATE/RESEARCH (C0-11c). See ``docs/notes/a2-v2-db-migration-tooling.md``
for the operator procedure and the rollback plan. Nothing here runs unless a
caller invokes it with an explicit path and an explicit confirmation flag.
No store, ``open`` or ``__init__`` function calls this module. This module
is not registered as a console script and is not wired into the CLI yet.

The module wraps :func:`msgloom.persistence.a2_schema.migrate_schema4_to_v5`.
That function owns the DDL, the exact schema detection and the single
``BEGIN IMMEDIATE`` transaction. This module adds the steps that function
leaves to the operator gate:

1. Require the confirmation flag. Fail before any file access.
2. Classify the file read only. A schema 5 file is a no-op (idempotent).
3. Copy the file with the SQLite online backup API into a caller-given
   directory. Verify the copy: integrity check, exact schema 4, equal
   logical dump, stable SHA-256 of the file bytes.
4. Re-check that the source did not change after the copy.
5. Build the :class:`~msgloom.persistence.a2_schema.MigrationGate` from the
   verified values only and run the migration.
6. Re-open the file and require exact schema 5 and a clean integrity check.

:func:`restore_backup` is the rollback helper. It checks the SHA-256 the
operator recorded, verifies the backup is exact schema 4 and copies it over
the target with the backup API. Writes made after the migration are lost.

Failure handling: every refusal raises
:exc:`~msgloom.persistence.a2_schema.A2SchemaError` with a short reason
code. Messages and output never contain a path, a row value, a key or SQL
text from the file under inspection. The tool never logs.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sqlite3
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from msgloom.persistence import a2_schema
from msgloom.persistence.a2_schema import (
    SCHEMA4_DIGEST,
    A2SchemaError,
    MigrationGate,
    SchemaState,
    classify_schema,
    connect_existing,
    migrate_schema4_to_v5,
)

CONFIRM_MIGRATE_FLAG = "--confirm-migrate-to-schema5"
CONFIRM_RESTORE_FLAG = "--confirm-restore"
BACKUP_SUFFIX = ".schema4-backup.sqlite"
_HEX64_RE = re.compile(r"[0-9a-f]{64}")
_CHUNK = 1 << 20
_OK = [("ok",)]


@dataclass(frozen=True)
class MigrationResult:
    """
    Outcome of :func:`migrate_database`.

    ``status`` is ``migrated`` or ``already-migrated``. For an already
    migrated file no backup is taken, so both backup fields are ``None``.
    """

    status: str
    backup_path: Path | None = None
    backup_sha256: str | None = None


def _read_only(path: Path) -> sqlite3.Connection:
    """Open an existing file read only. Never create a file."""
    if not path.is_file():
        raise A2SchemaError("database-file-missing")
    try:
        return sqlite3.connect(
            f"{path.resolve().as_uri()}?mode=ro",
            uri=True,
            timeout=a2_schema.BUSY_TIMEOUT_SECONDS,
            isolation_level=None,
        )
    except sqlite3.Error:
        raise A2SchemaError("database-open-failed") from None


def file_sha256(path: Path) -> str:
    """Return the SHA-256 of the file bytes as 64 lowercase hex characters."""
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(_CHUNK):
                digest.update(chunk)
    except OSError:
        raise A2SchemaError("file-unreadable") from None
    return digest.hexdigest()


def _inspect(path: Path) -> tuple[SchemaState, str, bool]:
    """Return the state, the logical dump digest and the integrity result."""
    db = _read_only(path)
    try:
        state = classify_schema(db)
        digest = hashlib.sha256()
        for line in db.iterdump():
            digest.update(line.encode())
            digest.update(b"\n")
        intact = db.execute("PRAGMA integrity_check").fetchall() == _OK
    except sqlite3.Error:
        raise A2SchemaError("database-unreadable") from None
    finally:
        db.close()
    return state, digest.hexdigest(), intact


def _require_schema4_intact(path: Path) -> str:
    """Return the logical digest of an intact, exact schema 4 file."""
    state, digest, intact = _inspect(path)
    if not intact:
        raise A2SchemaError("integrity-check-failed")
    if state is not SchemaState.SCHEMA4:
        raise A2SchemaError("not-schema4")
    return digest


def _copy(source: sqlite3.Connection, target: sqlite3.Connection) -> None:
    try:
        source.backup(target)
        target.execute("PRAGMA journal_mode = DELETE")
    except sqlite3.Error:
        raise A2SchemaError("backup-copy-failed") from None


def _write_backup(source: Path, destination: Path) -> None:
    """Create ``destination`` exclusively (mode 0600) and copy into it."""
    try:
        os.close(os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
    except FileExistsError:
        raise A2SchemaError("backup-exists") from None
    except OSError:
        raise A2SchemaError("backup-create-failed") from None
    reader = _read_only(source)
    try:
        writer = sqlite3.connect(destination, isolation_level=None)
        try:
            _copy(reader, writer)
        finally:
            writer.close()
    finally:
        reader.close()


def create_backup(source: Path, backup_dir: Path) -> tuple[Path, str]:
    """
    Copy an exact schema 4 file into ``backup_dir`` and verify the copy.

    Return ``(backup_path, sha256)``. The directory must exist. The backup
    file name derives from the source name and never overwrites a file. The
    copy uses the SQLite online backup API, so a live source is safe to
    read. Verification needs an intact exact schema 4 copy with the same
    logical dump as the source and byte-stable content. On any failure the
    partial copy is removed.
    """
    if not backup_dir.is_dir():
        raise A2SchemaError("backup-dir-missing")
    destination = backup_dir / f"{source.name}{BACKUP_SUFFIX}"
    if destination.resolve() == source.resolve():
        raise A2SchemaError("backup-is-source")
    before = _require_schema4_intact(source)
    _write_backup(source, destination)
    try:
        first = file_sha256(destination)
        if _require_schema4_intact(destination) != before:
            raise A2SchemaError("backup-mismatch")
        if file_sha256(destination) != first:
            raise A2SchemaError("backup-unstable")
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return destination, first


def _require_confirmed(confirm: bool) -> None:
    if confirm is not True:
        raise A2SchemaError("confirmation-required")


def migrate_database(
    path: Path, backup_dir: Path, *, confirm: bool = False
) -> MigrationResult:
    """
    Back up and migrate one schema 4 file to schema 5. Never implicit.

    ``confirm`` must be ``True``. ``path`` must name an existing file. The
    caller must stop all writers first. A schema 5 file returns
    ``already-migrated`` and is not touched. Unknown, partial, altered or
    older schemas raise :exc:`A2SchemaError` before any write. A failure in
    the migration transaction leaves the file schema 4 and byte-identical.
    """
    _require_confirmed(confirm)
    target = Path(path)
    state, _, _ = _inspect(target)
    if state is SchemaState.SCHEMA5:
        return MigrationResult("already-migrated")
    backup_path, backup_sha = create_backup(target, Path(backup_dir))
    if _require_schema4_intact(target) != _require_schema4_intact(backup_path):
        raise A2SchemaError("source-changed-after-backup")
    gate = MigrationGate(backup_sha256=backup_sha, schema4_digest=SCHEMA4_DIGEST)
    db = connect_existing(target)
    try:
        migrate_schema4_to_v5(db, gate)
    finally:
        db.close()
    final, _, intact = _inspect(target)
    if final is not SchemaState.SCHEMA5 or not intact:
        raise A2SchemaError("post-migration-check")
    return MigrationResult("migrated", backup_path, backup_sha)


def restore_backup(
    backup_path: Path,
    target: Path,
    expected_sha256: str,
    *,
    confirm: bool = False,
) -> None:
    """
    Roll back by copying a verified schema 4 backup over ``target``.

    ``expected_sha256`` is the digest that :func:`create_backup` returned.
    The function refuses when the digest differs or when the backup is not
    an intact exact schema 4 file. It needs the explicit ``confirm`` flag
    and exclusive access to ``target``: stop every writer first. Any write
    made after the migration is lost. The restored file must again be an
    intact exact schema 4 file with the logical dump of the backup.
    """
    _require_confirmed(confirm)
    if not _HEX64_RE.fullmatch(expected_sha256):
        raise A2SchemaError("restore-digest-shape")
    backup = Path(backup_path)
    destination = Path(target)
    if not backup.is_file():
        raise A2SchemaError("backup-file-missing")
    if not destination.parent.is_dir():
        raise A2SchemaError("restore-dir-missing")
    if destination.exists() and destination.resolve() == backup.resolve():
        raise A2SchemaError("backup-is-source")
    if file_sha256(backup) != expected_sha256:
        raise A2SchemaError("backup-digest-mismatch")
    expected = _require_schema4_intact(backup)
    reader = _read_only(backup)
    try:
        writer = sqlite3.connect(
            destination, isolation_level=None, timeout=a2_schema.BUSY_TIMEOUT_SECONDS
        )
        try:
            _copy(reader, writer)
        finally:
            writer.close()
    finally:
        reader.close()
    if _require_schema4_intact(destination) != expected:
        raise A2SchemaError("restore-mismatch")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="a2_schema_migration",
        description="Explicit A2 schema 4 to schema 5 migration of one file.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    migrate = commands.add_parser("migrate", help="back up, then migrate")
    migrate.add_argument("--db", required=True, type=Path)
    migrate.add_argument("--backup-dir", required=True, type=Path)
    migrate.add_argument(CONFIRM_MIGRATE_FLAG, action="store_true", dest="confirm")
    restore = commands.add_parser("restore", help="restore a verified backup")
    restore.add_argument("--db", required=True, type=Path)
    restore.add_argument("--backup", required=True, type=Path)
    restore.add_argument("--backup-sha256", required=True)
    restore.add_argument(CONFIRM_RESTORE_FLAG, action="store_true", dest="confirm")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """
    Run the explicit tool. Return ``0`` on success and ``1`` on a refusal.

    Argument errors exit with status ``2`` through :mod:`argparse`. Output
    carries status words, reason codes and the backup digest only. It never
    prints a path, a row value or SQL text.
    """
    args = _parser().parse_args(list(sys.argv[1:] if argv is None else argv))
    try:
        if args.command == "migrate":
            result = migrate_database(args.db, args.backup_dir, confirm=args.confirm)
            print(f"status={result.status}")
            if result.backup_sha256 is not None:
                print(f"backup_sha256={result.backup_sha256}")
            return 0
        restore_backup(args.backup, args.db, args.backup_sha256, confirm=args.confirm)
        print("status=restored")
    except A2SchemaError as error:
        print(f"refused: {error.reason}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
