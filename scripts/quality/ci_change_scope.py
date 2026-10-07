"""
Choose the safe docs-only CI path from a trusted Git diff.

Unknown events, unavailable commits, empty diffs, or suspicious filenames
always run the complete suite. Only text files under docs/ are eligible.
This tool deliberately does not decide whether any test is skippable.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

_SHA = re.compile(r"[0-9a-f]{40}", re.ASCII)
_DOC_SUFFIXES = frozenset({".md", ".rst", ".txt"})


def docs_only(paths: list[str]) -> bool:
    """Accept a nonempty set of strictly scoped documentation changes."""
    if not paths:
        return False
    for raw in paths:
        parts = raw.replace("\\", "/").split("/")
        if (
            len(parts) < 2
            or parts[0] != "docs"
            or any(part in {"", ".", ".."} for part in parts)
            or Path(parts[-1]).suffix.lower() not in _DOC_SUFFIXES
        ):
            return False
    return True


def changed_paths(root: Path, base: str, head: str) -> list[str] | None:
    """Read every changed path without rename collapsing or shell parsing."""
    if not _SHA.fullmatch(base) or not _SHA.fullmatch(head):
        return None
    command = [
        "git",
        "-C",
        str(root),
        "diff",
        "--name-only",
        "--no-renames",
        "-z",
        base,
        head,
        "--",
    ]
    try:
        result = subprocess.run(command, capture_output=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode or not result.stdout:
        return None
    try:
        paths = result.stdout.decode("utf-8", errors="surrogateescape").split("\0")
    except UnicodeError:
        return None
    if paths[-1] != "":
        return None
    return paths[:-1]


def classify(event: str, base: str, head: str, root: Path) -> bool:
    """Enable the fast path only with affirmative eligible Git evidence."""
    if event not in {"push", "pull_request"}:
        return False
    paths = changed_paths(root, base, head)
    return paths is not None and docs_only(paths)


def main(argv: list[str] | None = None) -> int:
    """Write a single GitHub Actions step output for the change scope."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    fast = classify(args.event, args.base, args.head, args.root)
    print(
        f"CI change scope: {'docs-only' if fast else 'full test matrix'}",
        file=sys.stderr,
    )
    print(f"docs_only={str(fast).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
