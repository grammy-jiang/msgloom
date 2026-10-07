"""Packaging contract for the real installed operator command."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest


def test_project_script_points_at_the_single_sync_entrypoint() -> None:
    """The package metadata exposes exactly the reviewed msgloom CLI callable."""
    root = Path(__file__).parents[2]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    scripts = project["project"].get("scripts", {})
    if scripts.get("msgloom") != "msgloom.cli:main":
        pytest.fail("project script does not expose msgloom.cli:main")
