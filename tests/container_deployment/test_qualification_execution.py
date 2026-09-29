"""Execution and failure-evidence tests for container qualification."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import cast

import pytest

from deployment.qualification import (
    QualificationError,
    Runner,
    Target,
    validate_resources,
    wheel_metadata,
)

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = ROOT / "deployment" / "Dockerfile"
SCRIPT = ROOT / "scripts" / "qualify_container_package.py"
PYTHON = ROOT / ".venv" / "bin" / "python"
RESOURCE = "msgloom:reporting/templates/report.html.j2"


def _script() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "container_qualifier_execution", SCRIPT
    )
    if spec is None or spec.loader is None:
        pytest.fail("container qualification script is not importable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _digest(character: str = "a") -> str:
    return "sha256:" + character * 64


def _targets() -> tuple[Target, ...]:
    return tuple(
        Target(version, f"python:{version}-slim-bookworm@{_digest(str(index + 1))}")
        for index, version in enumerate(("3.12", "3.13", "3.14"))
    )


def test_real_sdist_built_wheel_installs_by_valid_filename(tmp_path: Path) -> None:
    uv = shutil.which("uv")
    if uv is None:
        pytest.fail("uv is required for package qualification tests")
    source = tmp_path / "mini"
    template = source / "src/msgloom/reporting/templates/report.html.j2"
    template.parent.mkdir(parents=True)
    (source / "src/msgloom/__init__.py").write_text("", encoding="utf-8")
    template.write_text("synthetic", encoding="utf-8")
    (source / "pyproject.toml").write_text(
        "[build-system]\n"
        'requires=["setuptools==84.0.0"]\n'
        'build-backend="setuptools.build_meta"\n'
        "[project]\n"
        'name="msgloom"\n'
        'version="0.0.1"\n'
        "[tool.setuptools.packages.find]\n"
        'where=["src"]\n'
        "[tool.setuptools.package-data]\n"
        'msgloom=["reporting/templates/*.j2"]\n',
        encoding="utf-8",
    )
    sdist_dir = tmp_path / "sdist"
    wheel_dir = tmp_path / "wheel"
    subprocess.run(
        [
            uv,
            "build",
            "--offline",
            "--no-progress",
            "--no-config",
            "--sdist",
            "--out-dir",
            str(sdist_dir),
            str(source),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=30,
    )
    sdist = next(sdist_dir.glob("*.tar.gz"))
    subprocess.run(
        [
            uv,
            "build",
            "--offline",
            "--no-progress",
            "--no-config",
            "--wheel",
            "--out-dir",
            str(wheel_dir),
            str(sdist),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=30,
    )
    wheel = next(wheel_dir.glob("*.whl"))
    metadata = wheel_metadata(wheel)
    validate_resources(metadata, (RESOURCE,))
    venv = tmp_path / "venv"
    subprocess.run(
        [sys.executable, "-m", "venv", str(venv)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=30,
    )
    installed_python = venv / "bin/python"
    subprocess.run(
        [
            str(installed_python),
            "-m",
            "pip",
            "install",
            "--no-index",
            "--no-deps",
            str(wheel),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=30,
    )
    probe = subprocess.run(
        [
            str(installed_python),
            "-I",
            "-c",
            (
                "import importlib.metadata,importlib.resources;"
                "d=importlib.metadata.distribution('msgloom');"
                "p=importlib.resources.files('msgloom').joinpath("
                "'reporting/templates/report.html.j2');"
                "print(d.version,p.is_file())"
            ),
        ],
        cwd=tmp_path,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=10,
    )
    if probe.stdout.strip() != "0.0.1 True":
        pytest.fail(f"isolated installed wheel probe failed: {probe.stdout!r}")


def test_failed_execution_persists_machine_readable_evidence(tmp_path: Path) -> None:
    module = _script()

    class FailingRunner:
        def run(self, command: list[str], *, cwd: Path, timeout: int = 300):
            del cwd, timeout
            from deployment.process import CommandResult

            if command[:2] == ["docker", "info"]:
                return CommandResult(0, "aarch64")
            return CommandResult(124, "synthetic timeout", True)

    args = SimpleNamespace(
        target=_targets(),
        source_root=tmp_path / "source",
        output_root=tmp_path / "out",
        env_python=PYTHON,
        uv=Path(shutil.which("uv") or "/missing/uv"),
        runtime_lock=tmp_path / "runtime.txt",
        require_resource=[RESOURCE],
        seccomp_profile=None,
        skip_isolation_preflight=True,
    )
    report = module.qualify(args, runner=FailingRunner())
    evidence = args.output_root / "container-qualification.json"
    if not evidence.is_file():
        pytest.fail("failed qualification did not persist evidence")
    release = report["release_checks"]
    if not isinstance(release, list) or release[-1]["status"] != "fail":
        pytest.fail(f"failed execution was not machine-readable: {report!r}")
    targets = report["targets"]
    if not isinstance(targets, list) or len(targets) != 3:
        pytest.fail(f"unexecuted matrix was not explicit: {report!r}")
    if any(target["checks"][0]["status"] != "pending" for target in targets):
        pytest.fail(f"unexecuted targets were not pending: {report!r}")


def test_target_build_failure_returns_partial_evidence_and_cleans(
    tmp_path: Path,
) -> None:
    from deployment.process import CommandResult
    from deployment.target import _qualify_target

    class BuildFailRunner:
        def __init__(self) -> None:
            self.commands: list[list[str]] = []

        def run(self, command: list[str], *, cwd: Path, timeout: int = 300):
            del cwd, timeout
            self.commands.append(command)
            if command[:2] == ["docker", "build"]:
                return CommandResult(124, "synthetic build timeout", True)
            return CommandResult(1, "No such object")

    runner = BuildFailRunner()
    result = _qualify_target(
        target=_targets()[0],
        wheel_hash="a" * 64,
        wheel_filename="msgloom-0.1.0-py3-none-any.whl",
        wheel_version="0.1.0",
        resources=(RESOURCE,),
        context=tmp_path,
        output_root=tmp_path,
        runner=cast(Runner, runner),
        seccomp=None,
        skip_isolation=True,
        daemon_architecture="aarch64",
    )
    checks = result.get("checks")
    if not isinstance(checks, list) or checks[0]["status"] != "fail":
        pytest.fail(f"target failure evidence was incomplete: {result!r}")
    cleanup = [command[:3] for command in runner.commands[1:]]
    if cleanup != [["docker", "volume", "rm"], ["docker", "image", "rm"]]:
        pytest.fail(f"target cleanup was incomplete: {runner.commands!r}")


def test_cleanup_attempts_image_after_volume_cleanup_error(tmp_path: Path) -> None:
    from deployment.process import CommandResult
    from deployment.target import _cleanup

    class CleanupRunner:
        def __init__(self) -> None:
            self.commands: list[list[str]] = []

        def run(self, command: list[str], *, cwd: Path, timeout: int = 300):
            del cwd, timeout
            self.commands.append(command)
            if command[:3] == ["docker", "volume", "rm"]:
                raise OSError("synthetic cleanup failure")
            return CommandResult(0, "")

    runner = CleanupRunner()
    checks = _cleanup(cast(Runner, runner), tmp_path, "owned-volume", "owned-image")
    if len(runner.commands) != 2 or runner.commands[1][:3] != ["docker", "image", "rm"]:
        pytest.fail("one cleanup failure skipped a remaining owned object")
    if len(checks) != 1 or checks[0].name != "cleanup-volume":
        pytest.fail(f"cleanup failure evidence was not independent: {checks!r}")


def test_dockerfile_installs_exact_filename_without_source_checkout() -> None:
    text = DOCKERFILE.read_text(encoding="utf-8")
    required = (
        "ARG WHEEL_FILENAME",
        "COPY ${WHEEL_FILENAME} /tmp/${WHEEL_FILENAME}",
        'python -m pip install --no-cache-dir --no-deps "/tmp/$WHEEL_FILENAME"',
        "bubblewrap",
        "USER 10001:10001",
        'VOLUME ["/var/lib/msgloom"]',
    )
    for fragment in required:
        if fragment not in text:
            pytest.fail(f"Dockerfile missing deployment contract: {fragment}")
    for fragment in (
        "msgloom.whl",
        "pip install -e",
        "COPY . ",
        "/var/run/docker.sock",
    ):
        if fragment in text:
            pytest.fail(f"Dockerfile contains forbidden deployment surface: {fragment}")


def test_cli_requires_all_three_targets_before_execution(tmp_path: Path) -> None:
    module = _script()
    args = SimpleNamespace(
        target=_targets()[:2],
        source_root=tmp_path / "source",
        output_root=tmp_path / "out",
        seccomp_profile=None,
    )
    with pytest.raises(QualificationError, match="ordered"):
        module.qualify(args, runner=Runner())
