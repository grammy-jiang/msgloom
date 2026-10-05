"""
Run pre-commit 4.6.2 from a read-only source cache.

The real pre-commit Store owns a per-gate writable metadata sandbox. Repository
lookups are redirected to an already provisioned source cache through read-only
SQLite access. Clone/bootstrap and environment installation remain prohibited.
Unknown adapter versions are unavailable until their mutation seams are
reviewed. This module never changes the installed pre-commit package.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, cast


def cached_repository(directory: Path, key: str, ref: str) -> str:
    """Read one existing cache row without creating files."""
    database = directory / "db.db"
    if not database.is_file():
        raise RuntimeError("pre-commit source cache is unavailable; install prohibited")
    uri = database.resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        row = connection.execute(
            "SELECT path FROM repos WHERE repo = ? AND ref = ?",
            (key, ref),
        ).fetchone()
    if row is None or not Path(row[0]).is_dir():
        raise RuntimeError("cached hook repository missing; clone prohibited")
    return row[0]


def _cache_paths() -> tuple[Path, Path]:
    """Resolve separate source and writable metadata caches."""
    source_value = os.environ.get("PRE_COMMIT_SOURCE_CACHE")
    sandbox_value = os.environ.get("PRE_COMMIT_HOME")
    if not source_value or not sandbox_value:
        raise RuntimeError("source cache and metadata sandbox are required")
    source = Path(source_value).resolve()
    sandbox = Path(sandbox_value).resolve()
    if source == sandbox:
        raise RuntimeError("pre-commit source cache must be read-only isolated")
    if not (source / "db.db").is_file():
        raise RuntimeError("pre-commit source cache is unavailable; install prohibited")
    return source, sandbox


def main() -> int:
    """Run with source-cache lookup and bootstrap guards installed."""
    try:
        if importlib.metadata.version("pre-commit") != "4.6.2":
            raise RuntimeError("cached pre-commit adapter requires reviewed 4.6.2")
        source, sandbox = _cache_paths()
        store = importlib.import_module("pre_commit.store")
        repository = cast(Any, importlib.import_module("pre_commit.repository"))
        entrypoint = importlib.import_module("pre_commit.main")

        def cached(self, repo, ref, deps, make_strategy):
            del make_strategy
            return cached_repository(
                source,
                self.db_repo_name(repo, deps),
                ref,
            )

        def no_install(hook):
            raise RuntimeError(
                f"hook environment unavailable: {hook.id}; install prohibited",
            )

        store.Store._new_repo = cached
        repository._hook_install = no_install
        print(
            "pre-commit 4.6.2; read-only source cache; writable metadata "
            f"sandbox={sandbox}",
            flush=True,
        )
        return entrypoint.main(["run", *sys.argv[1:]])
    except (
        RuntimeError,
        OSError,
        sqlite3.Error,
        importlib.metadata.PackageNotFoundError,
    ) as exc:
        print(f"unavailable: {exc}", file=sys.stderr)
        return 69


if __name__ == "__main__":
    raise SystemExit(main())
