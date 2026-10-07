"""Lock Microsoft Graph infrastructure outside product-specific ingestion."""

from __future__ import annotations

import ast
import importlib
import subprocess
import sys
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


def test_public_components_use_canonical_packages() -> None:
    components = {
        "microsoft_graph.spiders": {
            "MicrosoftGraphSpider": "graph",
            "GraphObjectSpider": "resources",
            "GraphCollectionSpider": "resources",
        },
        "microsoft_graph.spiders.outlook": {
            "OutlookMailboxSpider": "mailbox",
            "OutlookMailSpider": "mail",
            "OutlookCalendarSpider": "calendar",
        },
        "microsoft_graph.middlewares": {
            "MicrosoftGraphDelegatedAuthMiddleware": "authentication",
            "MicrosoftGraphDeviceCodeAuthMiddleware": "authentication",
            "MicrosoftGraphInteractiveAuthMiddleware": "authentication",
            "MicrosoftGraphErrorMiddleware": "errors",
            "PrivacySafeRetryMiddleware": "retry",
            "MicrosoftGraphDiagnosticsMiddleware": "diagnostics",
        },
        "microsoft_graph.items": {"GraphResourceItem": "graph"},
    }
    for package, exports in components.items():
        module = importlib.import_module(package)
        if set(module.__all__) != set(exports):
            pytest.fail(f"Unexpected exports from {package}: {module.__all__!r}")
        for name, filename in exports.items():
            component = getattr(module, name)
            if component.__module__ != f"{package}.{filename}":
                pytest.fail(f"{package}.{name} must be defined in {filename}")


def test_graph_components_have_no_nested_scrapy_package() -> None:
    legacy = Path(__file__).parents[1] / "microsoft_graph" / "scrapy"
    if legacy.exists():
        pytest.fail(f"Redundant Scrapy package still exists: {legacy}")


def test_graph_package_does_not_depend_on_message_ingest() -> None:
    root = Path(__file__).parents[1] / "microsoft_graph"
    forbidden = ("message_ingest", "sqlalchemy")
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


def test_framework_imports_work_when_consumer_and_sqlalchemy_are_unavailable():
    code = """
import importlib
import importlib.abc
import pkgutil
import sys

class ForbidConsumer(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"message_ingest", "sqlalchemy"}:
            raise ImportError(f"Forbidden framework dependency: {fullname}")

sys.meta_path.insert(0, ForbidConsumer())
import microsoft_graph
for module in pkgutil.walk_packages(microsoft_graph.__path__, "microsoft_graph."):
    importlib.import_module(module.name)
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if result.returncode:
        pytest.fail(result.stderr)


def test_protocol_imports_work_when_scrapy_is_unavailable():
    code = """
import importlib
import importlib.abc
import pkgutil
import sys

class ForbidScrapy(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] == "scrapy":
            raise ImportError(f"Forbidden protocol dependency: {fullname}")

sys.meta_path.insert(0, ForbidScrapy())
import microsoft_graph.protocol
for module in pkgutil.walk_packages(
    microsoft_graph.protocol.__path__, "microsoft_graph.protocol."
):
    importlib.import_module(module.name)
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if result.returncode:
        pytest.fail(result.stderr)
