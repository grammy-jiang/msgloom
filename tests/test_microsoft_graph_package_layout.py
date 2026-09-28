"""Lock Microsoft Graph infrastructure outside product-specific ingestion."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import microsoft_graph
from microsoft_graph import auth, middlewares


def test_public_package_surfaces_are_explicit() -> None:
    if microsoft_graph.__all__ != ["GRAPH_HOST", "GRAPH_ROOT", "PROVIDER_ID"]:
        pytest.fail(f"Unexpected microsoft_graph exports: {microsoft_graph.__all__!r}")
    if "MicrosoftGraphAuthSession" not in auth.__all__:
        pytest.fail("Expected auth package to expose MicrosoftGraphAuthSession")
    if "MicrosoftGraphDeviceCodeAuthMiddleware" not in middlewares.__all__:
        pytest.fail("Expected downloader auth middleware in public middleware surface")


def test_graph_package_does_not_depend_on_message_ingest() -> None:
    root = Path(__file__).parents[1] / "microsoft_graph"
    forbidden = ("message_ingest",)
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            module = None
            if isinstance(node, ast.ImportFrom):
                module = node.module
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(forbidden):
                        pytest.fail(f"{path} imports product module {alias.name}")
            if module is not None and module.startswith(forbidden):
                pytest.fail(f"{path} imports product module {module}")


def test_legacy_message_ingest_provider_package_is_gone() -> None:
    legacy = Path(__file__).parents[1] / "message_ingest" / "providers"
    if legacy.exists():
        pytest.fail(f"Legacy provider package still exists: {legacy}")
