"""Lock repository-wide Python source conventions."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_PYTHON_ROOTS = (
    "msgloom",
    "message_ingest",
    "microsoft_graph",
    "scripts",
    "tests",
)


def test_python_files_do_not_use_assert_statements() -> None:
    """Require explicit runtime/test failures instead of optimized-away asserts."""

    violations: list[str] = []
    for root_name in _PYTHON_ROOTS:
        root = _REPOSITORY_ROOT / root_name
        for path in sorted(root.rglob("*.py")):
            tree = ast.parse(path.read_text(), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Assert):
                    relative = path.relative_to(_REPOSITORY_ROOT)
                    violations.append(f"{relative}:{node.lineno}")

    if violations:
        pytest.fail(
            "Python assert statements are forbidden; use explicit failures:\n"
            + "\n".join(violations)
        )
