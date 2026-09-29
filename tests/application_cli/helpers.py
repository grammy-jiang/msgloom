"""Synthetic helpers for scheduler-free operator CLI tests."""

from __future__ import annotations

import json
from pathlib import Path


def minimal_config(path: Path, capabilities: tuple[str, ...] = ("a2_prepare",)) -> Path:
    """Write one explicit minimal operator configuration."""
    values = ", ".join(json.dumps(item) for item in capabilities)
    path.write_text(
        "\n".join(
            (
                'code_version = "cli-test"',
                "",
                "[storage]",
                'sqlite_path = "state/phase1.sqlite3"',
                "",
                "[[admissions]]",
                'caller = "operator-cli"',
                'authority_ref = "owner-approved"',
                f"capabilities = [{values}]",
                "",
            )
        ),
        encoding="utf-8",
    )
    return path


def invoke(module_root: Path, *arguments: str):
    """Run the real module entrypoint from an arbitrary working directory."""
    import os
    import subprocess
    import sys

    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(module_root)
    return subprocess.run(
        [sys.executable, "-m", "msgloom.cli", *arguments],
        cwd=module_root.parent,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
