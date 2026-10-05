"""Derive source-suite commands from the committed qualification split."""

from __future__ import annotations

import argparse
import shutil
from dataclasses import asdict
from pathlib import Path

from .execution import EXTERNAL_REVIEW, Gate


def _python(args: argparse.Namespace, label: str) -> str:
    value = getattr(args, "python" + label)
    return str(Path(value).absolute()) if value else f"<python{label}-unavailable>"


def _pytest(
    output: Path,
    name: str,
    python: str,
    prerequisite: str,
    targets: list[str],
    marker: str,
    workers: str,
    group: str,
    *,
    append: bool = False,
    fastmcp: bool = False,
) -> Gate:
    directory = output / name
    coverage = directory / "coverage.xml"
    command = [
        python,
        "-m",
        "pytest",
        "-q",
        "-n",
        workers,
        "-m",
        marker,
        *targets,
        "-o",
        f"cache_dir={directory / 'pytest-cache'}",
        "--basetemp",
        str(directory / "tmp"),
        f"--junitxml={directory / 'junit.xml'}",
        "--cov=msgloom",
    ]
    if not fastmcp:
        command += ["--cov=message_ingest", "--cov=microsoft_graph"]
    command += [
        "--cov-branch",
        "--cov-report=term-missing",
        f"--cov-report=xml:{coverage}",
    ]
    if append:
        command += ["--cov-append"]
    env = [("COVERAGE_FILE", str(output / f"coverage-{group}" / ".coverage"))]
    if fastmcp:
        env.append(("MSGLOOM_FASTMCP_COMPAT", "1"))
    return Gate(
        name,
        tuple(command),
        dependencies=(prerequisite,),
        env=tuple(env),
        junit=str(directory / "junit.xml"),
        coverage=str(coverage),
    )


def build_plan(args: argparse.Namespace) -> list[Gate]:
    """Resolve commands without running tests, installing, or creating paths."""
    root = args.source_root.resolve()
    output = args.output_root.resolve()
    normal = "not exclusive_state and not fastmcp_compat"
    serial = "exclusive_state and not fastmcp_compat"
    gates = []
    for version in ("312", "313", "314"):
        for compat in ("", "fastmcp"):
            label = version + compat
            name = "runtime" + label
            python = _python(args, label)
            command = [
                python,
                "-m",
                "scripts.handoff_qualification.audit",
                "runtime",
                "--python-version",
                f"3.{version[1:]}",
            ]
            if compat:
                command.append("--fastmcp")
            gates.append(
                Gate(
                    name,
                    tuple(command),
                    timeout=120,
                    runtime=True,
                    unavailable=None
                    if getattr(args, "python" + label)
                    else f"explicit installed Python environment {label} not supplied",
                )
            )
    python = _python(args, "313")
    a1_targets = [
        str(path.relative_to(root))
        for path in sorted((root / "tests").glob("test_*.py"))
    ] + ["tests/source_reader"]
    gates.append(
        _pytest(
            output,
            "a1",
            python,
            "runtime313",
            a1_targets,
            normal,
            "4",
            "a1",
        )
    )
    for version in ("313", "312", "314"):
        gates.append(
            _pytest(
                output,
                "normal" + version,
                _python(args, version),
                "runtime" + version,
                [],
                normal,
                "4",
                version,
            )
        )
        gates.append(
            _pytest(
                output,
                "exclusive" + version,
                _python(args, version),
                "normal" + version,
                [],
                serial,
                "0",
                version,
                append=True,
            )
        )
        gates.append(
            _pytest(
                output,
                "fastmcp" + version,
                _python(args, version + "fastmcp"),
                "runtime" + version + "fastmcp",
                ["tests/packaging/test_fastmcp_compatibility.py"],
                "fastmcp_compat",
                "0",
                version + "-fastmcp",
                fastmcp=True,
            )
        )
    gates += [
        Gate(
            "scrapy_version",
            (python, "-m", "scrapy", "version", "-v"),
            timeout=120,
            dependencies=("runtime313",),
        ),
        Gate("ruff_version", (python, "-m", "ruff", "--version"), timeout=120),
        Gate("ruff", (python, "-m", "ruff", "check", "."), timeout=300),
        Gate("format", (python, "-m", "ruff", "format", "--check", "."), timeout=300),
        Gate("pyright_version", ("pyright", "--version"), timeout=120),
        Gate(
            "pyright",
            (
                "pyright",
                "--pythonpath",
                python,
                "msgloom",
                "message_ingest",
                "microsoft_graph",
                "tests",
                "scripts/qualify_a1_a2_handoff.py",
                "scripts/handoff_qualification",
            ),
            timeout=600,
            dependencies=("pyright_version", "runtime313"),
        ),
        Gate(
            "contracts",
            (
                python,
                "-m",
                "scrapy",
                "check",
                "-v",
                "-s",
                "MS_GRAPH_AUTH_ENABLED=False",
                "-s",
                "MS_GRAPH_AUTH_ALLOW_INTERACTIVE=False",
            ),
            timeout=300,
            dependencies=("runtime313",),
            contracts=True,
        ),
        Gate(
            "diff",
            ("git", "diff", "--check", args.base or "HEAD", args.candidate or "HEAD"),
            timeout=120,
        ),
        Gate(
            "precommit",
            (
                args.precommit_python or "<precommit-python-unavailable>",
                "-m",
                "scripts.handoff_qualification.cached_precommit",
                "--all-files",
            ),
            timeout=600,
            env=(("PRE_COMMIT_HOME", str(args.precommit_cache.absolute())),),
            unavailable=None
            if args.precommit_python
            else "supply the installed pre-commit interpreter; no bootstrap permitted",
        ),
        Gate(
            "reverse_imports",
            (python, "-m", "scripts.handoff_qualification.audit", "reverse"),
            timeout=120,
            dependencies=("runtime313",),
        ),
        Gate(
            "spider_coverage",
            (
                python,
                "-m",
                "scripts.handoff_qualification.audit",
                "coverage",
                "--map",
                str(args.coverage_map or "<coverage-map-unavailable>"),
                "--evidence",
                str(output),
                "--base",
                args.base or "<base-required>",
                "--candidate",
                args.candidate or "<candidate-required>",
            ),
            timeout=180,
            dependencies=("a1", "normal313"),
            unavailable=None
            if args.coverage_map
            else "17-spider/13-scenario exact-candidate executed-node map required",
        ),
        Gate(
            "live_lsp",
            (
                python,
                "-m",
                "scripts.handoff_qualification.live_lsp",
                "--root",
                str(root),
                "--python",
                python,
                "--base",
                args.base or "HEAD",
                "--candidate",
                args.candidate or "HEAD",
            ),
            timeout=240,
            dependencies=("runtime313",),
        ),
    ]
    return gates


def parser() -> argparse.ArgumentParser:
    """Require explicit execution and bind every supplied runtime by path."""
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--execute", action="store_true")
    cli.add_argument("--source-root", type=Path, default=Path.cwd())
    cli.add_argument("--output-root", type=Path, default=Path("/tmp/handoff-evidence"))
    cli.add_argument("--base")
    cli.add_argument("--candidate")
    cli.add_argument("--coverage-map", type=Path)
    for version in ("312", "313", "314"):
        for compat in ("", "fastmcp"):
            default = (
                str(Path.cwd() / ".venv/bin/python")
                if (version == "313" and not compat)
                else None
            )
            cli.add_argument("--python" + version + compat, default=default)
    executable = shutil.which("pre-commit")
    interpreter = None
    if executable:
        line = Path(executable).read_text().splitlines()[0]
        if line.startswith("#!/") and " " not in line:
            interpreter = line[2:]
    cli.add_argument("--precommit-python", default=interpreter)
    cli.add_argument(
        "--precommit-cache", type=Path, default=Path.home() / ".cache/pre-commit"
    )
    return cli


def listed_plan(gates: list[Gate]) -> dict:
    """Keep the final review visibly separate from automatic gate execution."""
    return {
        "mode": "list_only",
        "gates": [asdict(gate) for gate in gates],
        "external_review": EXTERNAL_REVIEW,
        "qualification_status": "not_executed",
        "scenario_coverage": "all 13 Task15 scenarios required in coverage map",
    }
