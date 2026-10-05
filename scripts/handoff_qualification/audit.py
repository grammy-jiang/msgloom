"""
Check runtime, reverse imports and declared coverage against real evidence.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib
import importlib.metadata
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SPIDERS = (
    "microsoft_profile",
    "microsoft_todo_discover",
    "microsoft_todo_sync",
    "microsoft_contacts_discover",
    "microsoft_contacts_sync",
    "microsoft_contacts_delta",
    "microsoft_onedrive_discover",
    "microsoft_onedrive_delta",
    "microsoft_onedrive_content",
    "outlook_discover",
    "outlook_folder_delta",
    "outlook_delta",
    "outlook_full",
    "outlook_calendar_discover",
    "outlook_calendar_window",
    "outlook_calendar_delta",
    "outlook_calendar_full",
)
DESIGN = "docs/superpowers/specs/2026-10-03-a1-a2-handoff-contract-design.md"


def runtime(expected: str, fastmcp: bool) -> dict:
    """Require the pinned framework and intended existing interpreter."""
    actual = ".".join(str(n) for n in sys.version_info[:3])
    versions = {
        name: importlib.metadata.version(name)
        for name in ("scrapy", "pytest", "pytest-cov", "pytest-xdist", "ruff")
    }
    expected_python = "3.13.5" if expected == "3.13" else expected + "."
    matches = (
        actual == expected_python
        if expected == "3.13"
        else actual.startswith(expected_python)
    )
    if not matches:
        raise ValueError(f"Python mismatch: {actual}; required {expected_python}")
    if versions["scrapy"] != "2.19.0":
        raise ValueError("Scrapy must remain exactly 2.19.0")
    for name, required in (
        ("pytest-cov", "7.1.0"),
        ("pytest-xdist", "3.8.0"),
        ("ruff", "0.16.9"),
    ):
        if versions[name] != required:
            raise ValueError(f"{name} must remain {required}")
    if not versions["pytest"].startswith("8."):
        raise ValueError("pytest must satisfy the committed >=8,<9 constraint")
    if fastmcp:
        versions["fastmcp"] = importlib.metadata.version("fastmcp")
        if versions["fastmcp"] != "4.0.10":
            raise ValueError("FastMCP must remain exactly 4.0.10")
    return {
        "python": actual,
        "executable": sys.executable,
        "packages": versions,
        "scrapy_module": importlib.import_module("scrapy").__file__,
    }


def reverse_imports(root: Path) -> None:
    """
    Reject A1 imports of A2 and transport imports of application packages.

    Literal dynamic imports are included. Computed dynamic imports in A1 are
    held for manual review rather than assumed to preserve the boundary.
    Existing shared ``msgloom.configuration`` imports remain permitted.
    """
    findings = []
    for directory, forbidden in (
        ("message_ingest", ("msgloom",)),
        ("microsoft_graph", ("message_ingest", "msgloom")),
    ):
        for path in (root / directory).rglob("*.py"):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [f"{node.module}.{alias.name}" for alias in node.names]
                elif isinstance(node, ast.Call):
                    func = node.func
                    dynamic = (
                        isinstance(func, ast.Name) and func.id == "__import__"
                    ) or (
                        isinstance(func, ast.Attribute) and func.attr == "import_module"
                    )
                    if dynamic:
                        if (
                            node.args
                            and isinstance(node.args[0], ast.Constant)
                            and isinstance(node.args[0].value, str)
                        ):
                            names = [node.args[0].value]
                        else:
                            findings.append(f"{path}:{node.lineno}: dynamic import")
                if any(
                    name.split(".")[0] in forbidden
                    and not (
                        directory == "message_ingest"
                        and (
                            name == "msgloom.configuration"
                            or name.startswith("msgloom.configuration.")
                        )
                    )
                    for name in names
                ):
                    line = getattr(node, "lineno", 0)
                    findings.append(f"{path}:{line}: forbidden import")
    if findings:
        raise ValueError("\n".join(findings))


def validate_coverage(
    data: dict,
    installed: set[str],
    passed: set[tuple[str, str]],
    base: str,
    candidate: str,
) -> None:
    """
    Bind all matrix rows to passing JUnit cases for this exact candidate.

    This checks traceability, not test adequacy. Independent review must verify
    each case exercises the claimed real Scrapy path or end-to-end scenario.
    """
    if data.get("base_sha") != base or data.get("candidate_sha") != candidate:
        raise ValueError("coverage map belongs to another base or candidate")
    if installed != set(SPIDERS):
        raise ValueError("installed Microsoft Spider set is not the exact 17")
    for section, expected in (
        ("spiders", set(SPIDERS)),
        ("scenarios", {str(i) for i in range(1, 14)}),
    ):
        rows = data.get(section)
        if not isinstance(rows, dict) or set(rows) != expected:
            raise ValueError(f"incomplete or extra {section} coverage rows")
        for name, nodes in rows.items():
            if not isinstance(nodes, list) or not nodes:
                raise ValueError(f"no executed test mapping for {name}")
            for node in nodes:
                if not isinstance(node, str) or "::" not in node:
                    raise ValueError(f"invalid test node for {name}")
                path, *parts = node.split("::")
                if not path.startswith("tests/") or not path.endswith(".py"):
                    raise ValueError(f"invalid test path for {name}")
                module = path[:-3].replace("/", ".")
                classname = ".".join([module, *parts[:-1]])
                if (classname, parts[-1]) not in passed:
                    raise ValueError(f"mapped case did not pass: {node}")


def snapshot_validated_coverage_map(
    map_path: Path,
    evidence: Path,
    installed: set[str],
    passed: set[tuple[str, str]],
    base: str,
    candidate: str,
) -> dict:
    """Validate then retain the exact coverage-map bytes in fresh evidence."""
    content = map_path.read_bytes()
    try:
        data = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid coverage map: {exc}") from exc
    if not isinstance(data, dict):
        raise TypeError("coverage map must be a JSON object")
    validate_coverage(data, installed, passed, base, candidate)
    target = evidence / "spider_coverage" / "coverage-map.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise ValueError("retained coverage map already exists") from exc
    return {
        "path": str(target),
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def coverage(
    root: Path,
    map_path: Path,
    evidence: Path,
    base: str,
    sha: str,
) -> dict:
    """Check loader/design matrix and exact candidate JUnit provenance."""
    from scrapy.spiderloader import SpiderLoader
    from scrapy.utils.project import get_project_settings

    installed = set(SpiderLoader.from_settings(get_project_settings()).list())
    design = (root / DESIGN).read_text()
    design_names = set(re.findall(r"^\| ([a-z_]+) \|", design, re.MULTILINE))
    if not set(SPIDERS) <= design_names:
        raise ValueError("the committed design does not contain the exact matrix")
    manifest = json.loads((evidence / "manifest.json").read_text())
    if manifest["candidate_sha"] != sha or manifest["base_sha"] != base:
        raise ValueError("manifest identity differs from coverage request")
    passed = set()
    for name in ("a1", "normal313"):
        gate = next(row for row in manifest["gates"] if row["name"] == name)
        if gate["status"] != "passed":
            raise ValueError(f"{name} execution is not passed")
        report = Path(gate["junit"])
        digest = hashlib.sha256(report.read_bytes()).hexdigest()
        if not any(
            artifact["path"] == str(report) and artifact["sha256"] == digest
            for artifact in gate["artifacts"]
        ):
            raise ValueError("JUnit artifact hash no longer matches manifest")
        for case in ET.parse(report).getroot().iter("testcase"):
            unsuccessful = any(
                case.find(tag) is not None for tag in ("failure", "error", "skipped")
            )
            if not unsuccessful:
                passed.add((case.get("classname", ""), case.get("name", "")))
    retained = snapshot_validated_coverage_map(
        map_path,
        evidence,
        installed,
        passed,
        base,
        sha,
    )
    return {
        "spiders": sorted(installed),
        "scenarios": 13,
        "coverage_map": retained,
        "coverage_map_sha256": retained["sha256"],
        "test_adequacy": "requires independent exact-candidate review",
    }


def _docstring_nodes(tree: ast.AST) -> list[ast.Expr]:
    """Return literal expression nodes that are Python docstrings."""
    containers = (
        ast.Module,
        ast.ClassDef,
        ast.FunctionDef,
        ast.AsyncFunctionDef,
    )
    expressions = []
    for node in ast.walk(tree):
        if not isinstance(node, containers) or not node.body:
            continue
        first = node.body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            expressions.append(first)
    return expressions


def _python_style(path: Path) -> list[str]:
    """Check repository structural and prose rules for one Python file."""
    source = path.read_text()
    lines = source.splitlines()
    violations = []
    if len(lines) >= 500:
        violations.append(f"{path}: module has {len(lines)} lines; limit is 499")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"{path}:{exc.lineno}: syntax error: {exc.msg}"]
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            violations.append(f"{path}:{node.lineno}: Python assert prohibited")
    for expression in _docstring_nodes(tree):
        start = expression.lineno
        end = expression.end_lineno or start
        block = lines[start - 1 : end]
        if end > start:
            if block[0].strip() not in {'"""', "'''"}:
                violations.append(
                    f"{path}:{start}: multiline docstring opening quote "
                    "must be separate"
                )
            if block[-1].strip() not in {'"""', "'''"}:
                violations.append(
                    f"{path}:{end}: multiline docstring closing quote must be separate"
                )
        for offset, line in enumerate(block, start):
            if len(line) > 79:
                violations.append(
                    f"{path}:{offset}: docstring prose is {len(line)} columns"
                )
    for number, line in enumerate(lines, 1):
        if line.lstrip().startswith("#") and len(line) > 79:
            violations.append(f"{path}:{number}: comment prose is {len(line)} columns")
    return violations


def style_violations(paths: list[Path]) -> list[str]:
    """Return explicit repository-style violations for preparation files."""
    violations = []
    for path in paths:
        if path.suffix == ".py":
            violations.extend(_python_style(path))
        elif path.suffix in {".md", ".markdown"}:
            for number, line in enumerate(path.read_text().splitlines(), 1):
                if len(line) > 79:
                    violations.append(f"{path}:{number}: prose is {len(line)} columns")
    return violations


def main() -> int:
    """Expose finite checks as subprocess gates with ordinary exit codes."""
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("runtime", "reverse", "coverage"))
    parser.add_argument("--python-version", default="3.13")
    parser.add_argument("--fastmcp", action="store_true")
    parser.add_argument("--map", type=Path)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--base")
    parser.add_argument("--candidate")
    args = parser.parse_args()
    try:
        if args.action == "runtime":
            result = runtime(args.python_version, args.fastmcp)
        elif args.action == "reverse":
            reverse_imports(Path.cwd())
            result = {"reverse_imports": "passed"}
        else:
            if not all((args.map, args.evidence, args.base, args.candidate)):
                raise ValueError("coverage requires map, evidence, base, candidate")
            result = coverage(
                Path.cwd(),
                args.map,
                args.evidence,
                args.base,
                args.candidate,
            )
    except importlib.metadata.PackageNotFoundError as exc:
        print(f"unavailable runtime dependency: {exc}", file=sys.stderr)
        return 69
    except (
        OSError,
        TypeError,
        ValueError,
        StopIteration,
        KeyError,
        ET.ParseError,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
