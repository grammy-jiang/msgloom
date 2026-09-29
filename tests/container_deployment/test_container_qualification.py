"""Synthetic tests for finite container deployment qualification."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import zipfile
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import cast

import pytest

from deployment.qualification import (
    Check,
    CommandResult,
    QualificationError,
    Runner,
    Target,
    docker_run_argv,
    evidence_json,
    sanitize,
    stage_context,
    validate_lock,
    validate_targets,
    wheel_metadata,
)

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = ROOT / "deployment" / "Dockerfile"
SCRIPT = ROOT / "scripts" / "qualify_container_package.py"


def _script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("container_qualifier", SCRIPT)
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


def _wheel(path: Path) -> None:
    metadata = (
        "Metadata-Version: 2.4\n"
        "Name: msgloom\n"
        "Version: 0.1.0\n"
        "Requires-Dist: claude-agent-sdk==0.2.161\n"
        "Requires-Dist: sqlalchemy>=2.0.54,<2.1\n"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("msgloom/__init__.py", "")
        archive.writestr("msgloom/templates/report.txt", "synthetic")
        archive.writestr("msgloom/prompts/triage.txt", "synthetic")
        archive.writestr("msgloom/migrations/001.sql", "select 1;")
        archive.writestr("msgloom-0.1.0.dist-info/METADATA", metadata)


def test_targets_require_exact_order_official_variant_and_digest() -> None:
    validate_targets(_targets())
    bad = list(_targets())
    bad[1] = Target("3.13", "python:3.13-slim-bookworm")
    with pytest.raises(QualificationError, match="sha256"):
        validate_targets(tuple(bad))
    with pytest.raises(QualificationError, match="ordered"):
        validate_targets(tuple(reversed(_targets())))


def test_lock_requires_hashes_exact_versions_and_direct_dependency_coverage(
    tmp_path: Path,
) -> None:
    lock = tmp_path / "runtime.txt"
    lock.write_text(
        "claude-agent-sdk==0.2.161 --hash=sha256:" + "a" * 64 + "\n"
        "sqlalchemy==2.0.54 --hash=sha256:" + "b" * 64 + "\n",
        encoding="utf-8",
    )
    locked = validate_lock(lock, {"claude-agent-sdk", "sqlalchemy"})
    if locked != {"claude-agent-sdk", "sqlalchemy"}:
        pytest.fail(f"unexpected locked dependency set: {locked!r}")
    lock.write_text(
        "prefect==3.0.0 --hash=sha256:" + "c" * 64 + "\n",
        encoding="utf-8",
    )
    with pytest.raises(QualificationError, match="forbidden"):
        validate_lock(lock, set())


def test_wheel_metadata_records_direct_dependencies_and_required_resources(
    tmp_path: Path,
) -> None:
    wheel = tmp_path / "msgloom.whl"
    _wheel(wheel)
    dependencies, resources, version = wheel_metadata(wheel)
    if dependencies != {"claude-agent-sdk", "sqlalchemy"}:
        pytest.fail(f"unexpected wheel dependencies: {dependencies!r}")
    if resources != (
        "msgloom/templates/",
        "msgloom/prompts/",
        "msgloom/migrations/",
    ):
        pytest.fail(f"unexpected resource evidence: {resources!r}")
    if version != "0.1.0":
        pytest.fail(f"unexpected wheel version: {version!r}")


def test_staged_build_context_contains_only_explicit_artifacts(tmp_path: Path) -> None:
    wheel = tmp_path / "input.whl"
    wheel.write_bytes(b"synthetic-wheel")
    lock = tmp_path / "runtime.txt"
    lock.write_text(
        "demo==1.0 --hash=sha256:" + "d" * 64 + "\n",
        encoding="utf-8",
    )
    root = tmp_path / "out"
    root.mkdir()
    context = stage_context(root, DOCKERFILE, wheel, lock)
    names = sorted(item.name for item in context.iterdir())
    expected = [
        "Dockerfile",
        "Dockerfile.dockerignore",
        "msgloom.whl",
        "runtime-requirements.txt",
    ]
    if names != expected:
        pytest.fail(f"build context was broader than admitted: {names!r}")


def test_docker_invocation_is_nonprivileged_offline_and_volume_scoped(
    tmp_path: Path,
) -> None:
    profile = tmp_path / "bwrap-seccomp.json"
    profile.write_text("{}", encoding="utf-8")
    command = docker_run_argv(
        "synthetic-image",
        "owned-container",
        "owned-volume",
        "print('ok')",
        profile,
    )
    joined = " ".join(command)
    required = (
        "--network none",
        "--read-only",
        "--security-opt no-new-privileges",
        "--cap-drop ALL",
        "type=volume,src=owned-volume,dst=/var/lib/msgloom",
    )
    for fragment in required:
        if fragment not in joined:
            pytest.fail(f"container security boundary missing: {fragment}")
    forbidden = ("--privileged", "/var/run/docker.sock", "/home/", "--userns=host")
    for fragment in forbidden:
        if fragment in joined:
            pytest.fail(f"forbidden container escape surface present: {fragment}")


def test_sanitizer_bounds_output_and_redacts_paths_and_tokens() -> None:
    value = (
        "/home/private/repo token=synthetic-sensitive-value "
        + "x" * 5000
        + " /var/auth/cache"
    )
    cleaned = sanitize(value)
    if "synthetic-sensitive-value" in cleaned:
        pytest.fail("sanitizer leaked credential-shaped output")
    if "/home/private" in cleaned or "/var/auth" in cleaned:
        pytest.fail("sanitizer leaked host paths")
    if len(cleaned) > 1600:
        pytest.fail("sanitized command output exceeded evidence bound")


def test_runner_timeout_does_not_echo_arguments_or_private_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = tmp_path / "private" / "tool"

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired([str(secret), "--token=secret"], 7)

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(QualificationError) as caught:
        Runner().run([str(secret), "--token=secret"], cwd=tmp_path, timeout=7)
    message = str(caught.value)
    if message != "timeout after 7s: tool":
        pytest.fail(f"unexpected bounded timeout diagnostic: {message!r}")


def test_evidence_records_exact_image_wheel_platform_and_statuses() -> None:
    target = _targets()[0]
    result = evidence_json(
        [Check("imports", "pass", "ok"), Check("cli", "pending", "not integrated")],
        target=target,
        image_id="sha256:image",
        wheel_hash="f" * 64,
        wheel_version="0.1.0",
        platform_data={"architecture": "aarch64", "python": "3.12.14"},
    )
    if result["base_image"] != target.base_image:
        pytest.fail("base image evidence was not exact")
    if result["image_digest"] != "sha256:image":
        pytest.fail("image digest evidence was not exact")
    if result["wheel_sha256"] != "f" * 64:
        pytest.fail("wheel digest evidence was not exact")
    if result["platform"] != {"architecture": "aarch64", "python": "3.12.14"}:
        pytest.fail("platform evidence was not exact")
    checks = cast(list[dict[str, object]], result["checks"])
    if checks[1]["status"] != "pending":
        pytest.fail("pending gate was mislabeled")


class _LifecycleRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def run(
        self, command: list[str], *, cwd: Path, timeout: int = 300
    ) -> CommandResult:
        del cwd, timeout
        self.commands.append(command)
        if command[:3] == ["docker", "image", "inspect"]:
            return CommandResult(0, "sha256:owned-image")
        if command[:3] == ["docker", "volume", "create"]:
            return CommandResult(0, command[-1])
        if command[:2] == ["docker", "run"]:
            code = command[-1]
            if '"architecture"' in code:
                return CommandResult(
                    0,
                    json.dumps(
                        {
                            "architecture": "aarch64",
                            "python": "3.12.14",
                            "version": "0.1.0",
                            "entry_points": [],
                            "resources": {
                                "templates": False,
                                "prompts": False,
                                "migrations": False,
                            },
                        }
                    ),
                )
            return CommandResult(0, "ok")
        return CommandResult(0, "ok")


def test_target_lifecycle_cleans_only_invocation_owned_objects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _script()
    names = iter(
        (
            "msgloom-qual-owned",
            "msgloom-qual-imports",
            "msgloom-qual-persist1",
            "msgloom-qual-persist2",
        )
    )
    monkeypatch.setattr(module, "unique_name", lambda prefix: next(names))
    runner = _LifecycleRunner()
    result = module._qualify_target(
        target=_targets()[0],
        wheel=tmp_path / "wheel",
        wheel_hash="a" * 64,
        wheel_version="0.1.0",
        context=tmp_path,
        output_root=tmp_path,
        runner=runner,
        seccomp=None,
        skip_isolation=True,
        daemon_architecture="aarch64",
    )
    cleanup = [command for command in runner.commands if "rm" in command]
    expected = [
        ["docker", "volume", "rm", "-f", "msgloom-qual-owned-data"],
        ["docker", "image", "rm", "-f", "msgloom-qual-owned"],
    ]
    if cleanup != expected:
        pytest.fail(f"cleanup escaped invocation ownership: {cleanup!r}")
    statuses = {check["name"]: check["status"] for check in result["checks"]}
    if statuses["entrypoint-help"] != "pending":
        pytest.fail("missing entrypoint was mislabeled green")
    if statuses["package-resources"] != "pending":
        pytest.fail("missing package resources were mislabeled green")
    if statuses["parser-isolation"] != "pending":
        pytest.fail("disabled isolation preflight was mislabeled green")


def test_dockerfile_installs_only_wheel_lock_and_runtime_os_packages() -> None:
    text = DOCKERFILE.read_text(encoding="utf-8")
    required = (
        "python -m pip install --no-cache-dir --only-binary=:all: --require-hashes",
        "python -m pip install --no-cache-dir --no-deps /tmp/msgloom.whl",
        "bubblewrap",
        "USER 10001:10001",
        'VOLUME ["/var/lib/msgloom"]',
    )
    for fragment in required:
        if fragment not in text:
            pytest.fail(f"Dockerfile missing deployment contract: {fragment}")
    forbidden = (
        "pip install -e",
        "COPY . ",
        "Prefect",
        "fastmcp",
        "/var/run/docker.sock",
        ".env",
    )
    for fragment in forbidden:
        if fragment in text:
            pytest.fail(f"Dockerfile contains forbidden deployment surface: {fragment}")


def test_cli_requires_all_three_targets_and_external_output(tmp_path: Path) -> None:
    module = _script()
    args = SimpleNamespace(
        target=_targets()[:2],
        source_root=tmp_path / "source",
        output_root=tmp_path / "out",
        seccomp_profile=None,
    )
    with pytest.raises(QualificationError, match="ordered"):
        module.qualify(args, runner=_LifecycleRunner())
