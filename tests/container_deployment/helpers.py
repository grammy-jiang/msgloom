"""Shared synthetic Docker daemon capability evidence."""

from deployment.process import CommandResult


def daemon_result(command: list[str]) -> CommandResult:
    """Return enforced resource limits for a supported synthetic daemon."""
    output = (
        "aarch64"
        if command[-1] == "{{.Architecture}}"
        else ('{"memory":true,"swap":true,"cpu_quota":true,"pids":true}')
    )
    return CommandResult(0, output)
