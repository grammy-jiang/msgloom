"""Cyclopts operator CLI with one synchronous event-loop entrypoint."""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Literal

from cyclopts import App
from cyclopts.exceptions import CycloptsError

from .models import CliRequest, ReplayStage, StageName
from .runner import CliResult, run_request

app = App(
    name="msgloom",
    help="Finite scheduler-free Phase 1 operator commands.",
)
config_app = App(help="Inspect or validate universal msgloom configuration.")
report_app = App(help="Build, submit, or reconcile saved reports.")
app.command(config_app, name="config")
app.command(report_app, name="report")


def _execution_request(
    action: Literal["execute", "replay"],
    stage: StageName | ReplayStage,
    config: Path,
    invocation: Path,
    mounted_secret_dir: Path | None,
    allow_secret_environment: tuple[str, ...],
    allow_secret_file: tuple[str, ...],
) -> CliRequest:
    return CliRequest(
        action=action,
        stage=stage,
        config_file=str(config),
        invocation_file=str(invocation),
        mounted_secret_dir=(
            None if mounted_secret_dir is None else str(mounted_secret_dir)
        ),
        allowed_secret_environment=allow_secret_environment,
        allowed_secret_files=allow_secret_file,
    )


@config_app.command(name="inspect")
def config_inspect(
    *,
    config: Path | None = None,
    mounted_secret_dir: Path | None = None,
) -> CliRequest:
    """Inspect one redacted universal configuration without constructing adapters."""
    return CliRequest(
        action="config-inspect",
        config_file=None if config is None else str(config),
        mounted_secret_dir=(
            None if mounted_secret_dir is None else str(mounted_secret_dir)
        ),
    )


@config_app.command(name="validate")
def config_validate(
    *,
    config: Path | None = None,
    mounted_secret_dir: Path | None = None,
) -> CliRequest:
    """Validate the XDG-default or one explicit universal configuration."""
    return CliRequest(
        action="config-validate",
        config_file=None if config is None else str(config),
        mounted_secret_dir=(
            None if mounted_secret_dir is None else str(mounted_secret_dir)
        ),
    )


@app.command
def status(config: Path, execution: str) -> CliRequest:
    """Read one saved terminal outcome without creating or migrating storage."""
    return CliRequest(
        action="status",
        config_file=str(config),
        execution=execution,
    )


@app.command
def prepare(
    config: Path,
    invocation: Path,
    *,
    mounted_secret_dir: Path | None = None,
) -> CliRequest:
    """Run one exact finite A2 preparation invocation."""
    return _execution_request(
        "execute",
        StageName.PREPARE,
        config,
        invocation,
        mounted_secret_dir,
        (),
        (),
    )


@app.command(name="prepare-scheduled")
def prepare_scheduled(config: Path, invocation: Path) -> CliRequest:
    """Run one finite configured intake and exact replay cycle."""
    return _execution_request(
        "execute", StageName.PREPARE_SCHEDULED, config, invocation, None, (), ()
    )


@app.command
def triage(
    config: Path,
    invocation: Path,
    *,
    mounted_secret_dir: Path | None = None,
    allow_secret_environment: tuple[str, ...] = (),
    allow_secret_file: tuple[str, ...] = (),
) -> CliRequest:
    """Run one exact finite A3 invocation with explicit credential allowlists."""
    return _execution_request(
        "execute",
        StageName.TRIAGE,
        config,
        invocation,
        mounted_secret_dir,
        allow_secret_environment,
        allow_secret_file,
    )


@report_app.command(name="build")
def report_build(
    config: Path,
    invocation: Path,
    *,
    mounted_secret_dir: Path | None = None,
) -> CliRequest:
    """Build one report from exact saved A3 inputs."""
    return _execution_request(
        "execute",
        StageName.REPORT_BUILD,
        config,
        invocation,
        mounted_secret_dir,
        (),
        (),
    )


@report_app.command(name="submit")
def report_submit(
    config: Path,
    invocation: Path,
    *,
    mounted_secret_dir: Path | None = None,
    allow_secret_environment: tuple[str, ...] = (),
    allow_secret_file: tuple[str, ...] = (),
) -> CliRequest:
    """Submit only through an explicitly composed trusted report transport."""
    return _execution_request(
        "execute",
        StageName.REPORT_SUBMIT,
        config,
        invocation,
        mounted_secret_dir,
        allow_secret_environment,
        allow_secret_file,
    )


@report_app.command(name="reconcile")
def report_reconcile(config: Path, invocation: Path) -> CliRequest:
    """Reconcile exact durable provider evidence without sending."""
    return _execution_request(
        "execute",
        StageName.REPORT_RECONCILE,
        config,
        invocation,
        None,
        (),
        (),
    )


@app.command
def replay(
    stage: ReplayStage,
    config: Path,
    invocation: Path,
    *,
    mounted_secret_dir: Path | None = None,
    allow_secret_environment: tuple[str, ...] = (),
    allow_secret_file: tuple[str, ...] = (),
) -> CliRequest:
    """Replay one selected downstream stage; report submission is excluded."""
    return _execution_request(
        "replay",
        stage,
        config,
        invocation,
        mounted_secret_dir,
        allow_secret_environment,
        allow_secret_file,
    )


def main(tokens: Iterable[str] | None = None) -> int:
    """Parse synchronously, then own the CLI's one and only asyncio.run."""
    try:
        request = app(
            tokens,
            exit_on_error=False,
            result_action="return_value",
        )
    except CycloptsError:
        _print(CliResult(2, {"status": "error", "code": "cli_invalid"}))
        return 2
    if request is None or isinstance(request, int):
        return 0 if request is None else request
    if not isinstance(request, CliRequest):
        _print(CliResult(2, {"status": "error", "code": "cli_invalid"}))
        return 2
    try:
        result = asyncio.run(run_request(request))
    except KeyboardInterrupt:
        result = CliResult(130, {"status": "error", "code": "cancelled"})
    _print(result)
    return result.exit_code


def _print(result: CliResult) -> None:
    sys.stdout.write(result.render() + "\n")
