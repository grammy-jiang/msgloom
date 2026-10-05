"""Run pre-commit 4.6.2 using only already provisioned hook environments.

The in-process guards prohibit clone/bootstrap and environment installation.
They retain the committed hook selection, revisions, arguments and exit codes.
Unknown adapter versions are unavailable until their installation seams are
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
    """Read an existing cache row without creating its database or repository."""
    database = directory / "db.db"
    if not database.is_file():
        raise RuntimeError("pre-commit cache is unavailable; install prohibited")
    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as connection:
        row = connection.execute(
            "SELECT path FROM repos WHERE repo = ? AND ref = ?",
            (key, ref),
        ).fetchone()
    if row is None or not Path(row[0]).is_dir():
        raise RuntimeError("cached hook repository missing; clone prohibited")
    return row[0]


def main() -> int:
    """Apply bootstrap guards before invoking the real pre-commit run command."""
    try:
        if importlib.metadata.version("pre-commit") != "4.6.2":
            raise RuntimeError("cached pre-commit adapter requires reviewed 4.6.2")
        store = importlib.import_module("pre_commit.store")
        repository = cast(Any, importlib.import_module("pre_commit.repository"))
        entrypoint = importlib.import_module("pre_commit.main")
        cache = Path(
            os.environ.get(
                "PRE_COMMIT_HOME",
                str(Path.home() / ".cache/pre-commit"),
            )
        ).resolve()
        if not (cache / "db.db").is_file():
            raise RuntimeError("existing PRE_COMMIT_HOME required; no bootstrap")

        def cached(self, repo, ref, deps, make_strategy):
            return cached_repository(
                Path(self.directory),
                self.db_repo_name(repo, deps),
                ref,
            )

        def no_install(hook):
            raise RuntimeError(
                f"hook environment unavailable: {hook.id}; install prohibited",
            )

        store.Store._new_repo = cached
        repository._hook_install = no_install
        print("pre-commit 4.6.2; existing-cache-only; no installation", flush=True)
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
