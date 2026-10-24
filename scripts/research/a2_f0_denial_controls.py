"""Executable denial controls for a possible Kedro bridge (research).

This module is research code. It is not part of the shipped package. It
imports no Kedro module, so the checks run in the project interpreter. The
Kedro-dependent checks live in ``a2_f0_kedro_probe.py``.

Each control rejects by raising :exc:`GateError`, or it returns findings:

* :func:`scan_source` and :func:`scan_tree` find forbidden Kedro surface in
  Python source (CLI, session, ``load_versions``, ``from_config``,
  ``kedro_datasets``, hook entry points).
* :func:`scan_project_metadata` finds Kedro console scripts and entry points
  in ``pyproject.toml``.
* :func:`check_catalog_datasets`, :func:`check_pipeline_names` and
  :func:`check_load_version` form the static dataset allowlist.
* :func:`safe_join` rejects unsafe dataset paths.
* :func:`controlled_environment` builds the telemetry opt-out environment.
* :func:`scan_pii` scans captured log text for message content patterns.
* :func:`sanitized_node` stops raw node input from reaching exception text.

The source scan is a name-based ``ast`` walk. It does not follow ``getattr``
or ``importlib`` calls except for string constants that name a forbidden
module. A human review rule still has to cover dynamic access.
"""

from __future__ import annotations

import ast
import hashlib
import os
import re
import tomllib
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

ALLOWED_DATASET_TYPES = frozenset({"kedro.io.memory_dataset.MemoryDataset"})
"""Exact ``module.qualname`` values. A subclass is not allowed."""

FORBIDDEN_NAMES = frozenset(
    {
        "from_config",
        "load_versions",
        "save_version",
        "parse_dataset_definition",
        "KedroSession",
        "ServiceSession",
        "bootstrap_project",
        "AbstractVersionedDataset",
    }
)
FORBIDDEN_KEDRO_IMPORT_NAMES = frozenset({"Version", "load_obj"})
FORBIDDEN_MODULE_PREFIXES = (
    "kedro.framework.cli",
    "kedro.framework.session",
    "kedro.framework.startup",
    "kedro.framework.hooks.manager",
    "kedro.server",
    "kedro.__main__",
    "kedro_datasets",
    "kedro_telemetry",
)
KEDRO_ENTRY_POINT_GROUPS = frozenset(
    {
        "kedro.hooks",
        "kedro.cli_hooks",
        "kedro.project_commands",
        "kedro.global_commands",
        "kedro.init",
        "kedro.line_magic",
        "kedro.environment_variables",
    }
)
TELEMETRY_OFF_ENVIRONMENT = {
    "DO_NOT_TRACK": "1",
    "KEDRO_DISABLE_TELEMETRY": "1",
}
RUNTIME_FORBIDDEN_MODULES = (
    "kedro.framework.cli",
    "kedro.framework.session",
    "kedro.framework.startup",
    "kedro.server",
    "kedro_datasets",
    "kedro_telemetry",
)
"""Modules that must not be in ``sys.modules`` after the bridge imports."""
DISABLE_HOOKS_FOR_PLUGINS = ("kedro-telemetry",)

_PII_PATTERNS = {
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "phone": re.compile(
        r"(?<![\w/.-])(?:\+\d{1,3}[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]?\d{3,4}(?![\w/])"
    ),
    "street_address": re.compile(
        r"\b\d{1,5}\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+"
        r"(?:Street|St|Road|Rd|Avenue|Ave|Lane|Ln|Drive|Dr)\b"
    ),
    "message_body_key": re.compile(
        r"""["']?(?:body|bodyPreview|subject|content|uniqueBody)["']?\s*[:=]\s*"""
    ),
    "bearer_token": re.compile(r"Bearer\s+[A-Za-z0-9._~+/-]{12,}"),
}


class GateError(Exception):
    """Raised when a denial control rejects its input."""


@dataclass(frozen=True)
class Finding:
    """One forbidden construct found by a scan."""

    path: str
    line: int
    name: str


def type_key(value: object) -> str:
    """Return ``module.qualname`` for the exact type of ``value``."""
    cls = type(value)
    return f"{cls.__module__}.{cls.__qualname__}"


def check_catalog_datasets(
    datasets: Mapping[str, object],
    allowed_names: frozenset[str],
    allowed_types: frozenset[str] = ALLOWED_DATASET_TYPES,
) -> None:
    """Reject unknown names, unknown dataset types and versioned datasets.

    Type matching is exact. ``isinstance`` is not used, so a subclass of an
    allowed type is rejected.
    """
    for name, dataset in datasets.items():
        if name not in allowed_names:
            raise GateError(f"unknown dataset name: {name!r}")
        if type_key(dataset) not in allowed_types:
            raise GateError(f"dataset type not allowed: {type_key(dataset)}")
        mro_names = {cls.__name__ for cls in type(dataset).__mro__}
        if "AbstractVersionedDataset" in mro_names:
            raise GateError(f"versioned dataset not allowed: {name!r}")
        if getattr(dataset, "_version", None) is not None:
            raise GateError(f"dataset carries a version: {name!r}")


def pipeline_dataset_names(nodes: Iterable[Any]) -> set[str]:
    """Collect every input and output name used by pipeline nodes."""
    names: set[str] = set()
    for node in nodes:
        names.update(node.inputs)
        names.update(node.outputs)
    return names


def check_pipeline_names(nodes: Iterable[Any], allowed_names: frozenset[str]) -> None:
    """Reject a pipeline that uses a dataset name outside the allowlist.

    Kedro runs such a pipeline and creates an implicit in-memory dataset for
    an unknown output. This check must run before the runner starts.
    """
    unknown = sorted(pipeline_dataset_names(nodes) - allowed_names)
    if unknown:
        raise GateError(f"pipeline uses unlisted dataset names: {unknown}")


def check_load_version(version: object) -> None:
    """Reject any ``version`` argument. Versioned loads are not allowed."""
    if version is not None:
        raise GateError("a version argument is not allowed")


def safe_join(base: Path, relative: str) -> Path:
    """Join a constant relative path to ``base`` or raise :exc:`GateError`.

    Rejected: empty, NUL, absolute, backslash, drive-letter, glob and
    ``..`` inputs, and any real path (symlinks resolved) outside ``base``.
    The relative part must be a constant, never message content.
    """
    if not relative or "\x00" in relative:
        raise GateError("empty path or NUL byte")
    if relative.startswith(("/", "\\")) or "\\" in relative:
        raise GateError("absolute path or backslash")
    if re.match(r"^[A-Za-z]:", relative):
        raise GateError("drive-letter path")
    if any(char in relative for char in "*?["):
        raise GateError("glob character in path")
    if ".." in PurePosixPath(relative).parts:
        raise GateError("parent traversal")
    real_base = Path(os.path.realpath(base))
    candidate = Path(os.path.realpath(real_base / relative))
    if candidate != real_base and real_base not in candidate.parents:
        raise GateError("path escapes the base directory")
    return candidate


def controlled_environment(base: Mapping[str, str]) -> dict[str, str]:
    """Return ``base`` plus the telemetry opt-out variables."""
    return {**base, **TELEMETRY_OFF_ENVIRONMENT}


def _imports_kedro(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(
            alias.name.split(".")[0] == "kedro" for alias in node.names
        ):
            return True
        if (
            isinstance(node, ast.ImportFrom)
            and (node.module or "").split(".")[0] == "kedro"
        ):
            return True
    return False


def _forbidden_module(name: str) -> bool:
    return name.startswith(FORBIDDEN_MODULE_PREFIXES)


def scan_source(source: str, path: str = "<string>") -> list[Finding]:
    """Return forbidden Kedro constructs found in ``source``."""
    tree = ast.parse(source)
    uses_kedro = _imports_kedro(tree)
    found: list[Finding] = []

    def add(node: ast.AST, name: str) -> None:
        found.append(Finding(path, getattr(node, "lineno", 0), name))

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_NAMES:
            add(node, node.attr)
        elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            add(node, node.id)
        elif isinstance(node, ast.keyword) and node.arg in FORBIDDEN_NAMES:
            add(node, str(node.arg))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if _forbidden_module(alias.name):
                    add(node, alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if _forbidden_module(module):
                add(node, module)
            for alias in node.names:
                if alias.name in FORBIDDEN_NAMES:
                    add(node, alias.name)
                if _forbidden_module(f"{module}.{alias.name}"):
                    add(node, f"{module}.{alias.name}")
                if module.startswith("kedro") and (
                    alias.name in FORBIDDEN_KEDRO_IMPORT_NAMES
                ):
                    add(node, alias.name)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if _forbidden_module(node.value):
                add(node, node.value)
        elif (
            uses_kedro
            and isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"load", "save", "exists"}
            and any(k.arg == "version" for k in node.keywords)
        ):
            add(node, f"{node.func.attr}(version=)")
    return found


def scan_tree(root: Path, packages: Iterable[str]) -> list[Finding]:
    """Scan every ``.py`` file under ``root / package`` for each package."""
    found: list[Finding] = []
    for package in packages:
        for path in sorted((root / package).rglob("*.py")):
            source = path.read_text(encoding="utf-8")
            found.extend(scan_source(source, str(path.relative_to(root))))
    return found


def scan_project_metadata(pyproject_text: str) -> list[str]:
    """Return Kedro CLI, hook or project-section findings in ``pyproject``."""
    data = tomllib.loads(pyproject_text)
    project = data.get("project", {})
    findings: list[str] = []
    for table in ("scripts", "gui-scripts"):
        for script, target in project.get(table, {}).items():
            if script == "kedro" or str(target).startswith("kedro"):
                findings.append(f"{table}: {script} = {target}")
    for group, entries in project.get("entry-points", {}).items():
        if group in KEDRO_ENTRY_POINT_GROUPS:
            findings.append(f"entry-points group: {group}")
        for name, target in entries.items():
            if str(target).startswith(("kedro", "kedro_")):
                findings.append(f"entry-points {group}: {name} = {target}")
    if "kedro" in data.get("tool", {}):
        findings.append("tool.kedro section present")
    return findings


def scan_pii(text: str) -> dict[str, list[str]]:
    """Return message-content pattern hits in captured log text."""
    hits: dict[str, list[str]] = {}
    for label, pattern in _PII_PATTERNS.items():
        if matches := [m.group(0) for m in pattern.finditer(text)]:
            hits[label] = matches
    return hits


class NodeFailure(Exception):
    """Sanitized node failure. The text carries a fixed code only."""


class _Sanitizer:
    """Context manager that replaces any ``Exception`` with a fixed code.

    A context manager avoids a broad ``except`` clause. ``__exit__`` raises
    :exc:`NodeFailure` with ``from None``, so the original text is hidden
    from logs and from formatted tracebacks.
    """

    def __init__(self, name: str) -> None:
        self._name = name

    def __enter__(self) -> None:
        return None

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object,
    ) -> bool:
        if exc_type is None or not issubclass(exc_type, Exception):
            return False
        digest = hashlib.sha256(exc_type.__qualname__.encode()).hexdigest()
        raise NodeFailure(f"node {self._name} failed: code {digest[:8]}") from None


def sanitized_node(name: str, func: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap ``func`` so a failure never exposes its input or message text.

    The raised text has the node name and a short hash of the exception
    type. The original exception is suppressed, so Kedro logs and tracebacks
    do not print it.
    """

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        with _Sanitizer(name):
            return func(*args, **kwargs)

    return wrapper
