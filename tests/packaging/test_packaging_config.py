"""Validate the static package and tox qualification contract."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import cast

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _project() -> dict[str, object]:
    with (ROOT / "pyproject.toml").open("rb") as stream:
        return cast(dict[str, object], tomllib.load(stream))


def _table(value: object, detail: str) -> dict[str, object]:
    if not isinstance(value, dict):
        pytest.fail(f"{detail} must be a TOML table")
    return cast(dict[str, object], value)


def _require_equal(actual: object, expected: object, detail: str) -> None:
    if actual != expected:
        pytest.fail(f"{detail}: expected {expected!r}, got {actual!r}")


def test_build_backend_and_development_pins_are_exact() -> None:
    """Keep build and qualification tooling out of runtime dependencies."""
    project = _project()
    _require_equal(
        project["build-system"],
        {
            "requires": ["setuptools==84.0.0"],
            "build-backend": "setuptools.build_meta",
        },
        "build backend",
    )
    groups = _table(project["dependency-groups"], "dependency groups")
    dev = set(cast(list[str], groups["dev"]))
    for requirement in (
        "tox==4.64.4",
        "tox-uv==1.36.0",
        "pytest-xdist==3.8.0",
        "pytest-cov==7.1.0",
    ):
        if requirement not in dev:
            pytest.fail(f"missing exact development pin: {requirement}")
    _require_equal(
        groups["compat-fastmcp4"],
        ["fastmcp==4.0.10"],
        "FastMCP compatibility group",
    )
    metadata = _table(project["project"], "project metadata")
    runtime = cast(list[str], metadata["dependencies"])
    for name in ("tox", "pytest-cov", "pytest-xdist", "fastmcp", "prefect"):
        if any(item.lower().startswith(name) for item in runtime):
            pytest.fail(f"development-only dependency leaked into runtime: {name}")


def test_package_discovery_and_entry_points_are_closed() -> None:
    """Package only the three tested runtime roots and exactly one CLI."""
    project = _project()
    tool = _table(project["tool"], "tool configuration")
    setuptools = _table(tool["setuptools"], "setuptools configuration")
    packages = _table(setuptools["packages"], "package configuration")
    find = _table(packages["find"], "package discovery")
    _require_equal(
        find["include"],
        [
            "msgloom",
            "msgloom.*",
            "message_ingest",
            "message_ingest.*",
            "microsoft_graph",
            "microsoft_graph.*",
        ],
        "package include roots",
    )
    metadata = _table(project["project"], "project metadata")
    _require_equal(
        metadata.get("scripts"),
        {"msgloom": "msgloom.cli:main"},
        "console script entry points",
    )


def test_tox_matrix_is_locked_wheel_mode_with_bounded_workers() -> None:
    """Keep interpreter and compatibility environments explicit."""
    project = _project()
    tool = _table(project["tool"], "tool configuration")
    tox = _table(tool["tox"], "tox configuration")
    _require_equal(
        tox["env_list"],
        [
            "py312",
            "py313",
            "py314",
            "py312-fastmcp4",
            "py313-fastmcp4",
            "py314-fastmcp4",
        ],
        "tox environment list",
    )
    _require_equal(tox["skip_missing_interpreters"], False, "missing interpreter")
    base = _table(tox["env_run_base"], "tox run base")
    _require_equal(base["runner"], "uv-venv-lock-runner", "tox runner")
    _require_equal(base["package"], "wheel", "tox package mode")
    _require_equal(base["dependency_groups"], ["dev"], "tox dependency groups")
    _require_equal(base["uv_sync_locked"], True, "locked uv sync")
    base_env = _table(base["set_env"], "tox base environment")
    _require_equal(
        base_env["COVERAGE_FILE"],
        "{env_dir}/.coverage",
        "per-environment coverage data",
    )
    commands = cast(list[list[str]], base["commands"])
    if "-n" not in commands[0] or "4" not in commands[0]:
        pytest.fail("parallel test command must bound xdist at four workers")
    if commands[1][commands[1].index("-n") + 1] != "0":
        pytest.fail("exclusive-state test command must disable xdist")
    for command in commands:
        marker_index = command.index("-m", command.index("-m") + 1)
        marker = command[marker_index + 1]
        if "not fastmcp_compat" not in marker:
            pytest.fail("normal tox command must exclude FastMCP compatibility")
    for version in ("py312", "py313", "py314"):
        environments = _table(tox["env"], "tox environments")
        compat = _table(
            environments[f"{version}-fastmcp4"],
            f"{version} FastMCP environment",
        )
        _require_equal(
            compat["dependency_groups"],
            ["dev", "compat-fastmcp4"],
            f"{version} FastMCP groups",
        )
        compat_env = _table(compat["set_env"], f"{version} FastMCP environment")
        _require_equal(
            compat_env["MSGLOOM_FASTMCP_COMPAT"],
            "1",
            f"{version} FastMCP opt-in",
        )
        _require_equal(
            compat_env["COVERAGE_FILE"],
            "{env_dir}/.coverage",
            f"{version} coverage data",
        )
        compat_command = cast(list[list[str]], compat["commands"])[0]
        marker_index = compat_command.index("-m", compat_command.index("-m") + 1)
        marker = compat_command[marker_index + 1]
        if marker != "fastmcp_compat":
            pytest.fail(f"{version} compatibility test marker is not required")
        if "--cov-branch" not in compat_command:
            pytest.fail(f"{version} compatibility coverage is not branch-aware")
        if not any("coverage.xml" in item for item in compat_command):
            pytest.fail(f"{version} compatibility coverage artifact is missing")
