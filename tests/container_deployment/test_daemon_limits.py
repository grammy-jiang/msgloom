"""Reject unsupported resource enforcement before any container work."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from deployment.process import CommandResult
from tests.container_deployment.test_qualification_execution import (
    PYTHON,
    RESOURCE,
    _script,
    _targets,
)


@pytest.mark.parametrize("skip_isolation", [False, True])
@pytest.mark.parametrize(
    "resource_output",
    [
        '{"memory":false,"swap":false,"cpu_quota":true,"pids":true}',
        '{"memory":"true","swap":true,"cpu_quota":true,"pids":true}',
        '{"memory":true,"swap":true,"cpu_quota":true}',
        "not-json",
    ],
)
def test_unsupported_daemon_never_starts_release_or_container_work(
    tmp_path: Path, resource_output: str, skip_isolation: bool
) -> None:
    class LimitedRunner:
        def run(self, command: list[str], *, cwd: Path, timeout: int = 300):
            del cwd, timeout
            if command[:2] != ["docker", "info"]:
                pytest.fail("unsupported daemon started package or container work")
            output = (
                "aarch64" if command[-1] == "{{.Architecture}}" else resource_output
            )
            return CommandResult(0, output)

    args = SimpleNamespace(
        target=_targets(),
        source_root=tmp_path / "source",
        output_root=tmp_path / "out",
        env_python=PYTHON,
        uv=Path("/unused/uv"),
        runtime_lock=tmp_path / "runtime.txt",
        require_resource=[RESOURCE],
        seccomp_profile=None,
        skip_isolation_preflight=skip_isolation,
    )
    report = _script().qualify(args, runner=LimitedRunner())
    saved = json.loads((args.output_root / "container-qualification.json").read_text())
    if saved != report:
        pytest.fail("failed resource gate was not durable")
    if report["release_checks"][0]["status"] != "fail":
        pytest.fail("unsupported resource limits passed qualification")
    if report["host_checks"][0]["name"] != "daemon-resource-limits":
        pytest.fail("resource capability failure was not identified")
    if report["host_checks"][0]["status"] != "fail":
        pytest.fail("resource capability failure was not retained")
    if any(item["checks"][0]["status"] != "pending" for item in report["targets"]):
        pytest.fail("unexecuted container targets were not pending")
