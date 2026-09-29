"""Per-target Docker lifecycle for deployment qualification."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import cast

from deployment.qualification import (
    Check,
    Runner,
    Target,
    ai_probe_code,
    container_probe_code,
    docker_run_argv,
    entrypoint_help_probe_code,
    evidence_json,
    parser_probe_code,
    persistence_probe_code,
    sanitize,
    unique_name,
)


def _check_result(name: str, result: object) -> Check:
    returncode = cast(int, getattr(result, "returncode", 1))
    output = cast(str, getattr(result, "output", "command result was invalid"))
    cleanup = cast(tuple[str, ...], getattr(result, "cleanup_errors", ()))
    detail = output.strip() or ("ok" if returncode == 0 else "command failed")
    if cleanup:
        detail = sanitize(detail + "; " + "; ".join(cleanup))
    return Check(name, "pass" if returncode == 0 else "fail", detail)


def _run_check(
    runner: Runner,
    command: list[str],
    *,
    cwd: Path,
    name: str,
) -> Check:
    return _check_result(name, runner.run(command, cwd=cwd))


def _probe_json(
    runner: Runner,
    image: str,
    volume: str,
    seccomp: Path | None,
    cwd: Path,
    resources: tuple[str, ...],
) -> tuple[Check, dict[str, object]]:
    result = runner.run(
        docker_run_argv(
            image,
            unique_name("imports"),
            volume,
            container_probe_code(resources),
            seccomp,
        ),
        cwd=cwd,
    )
    check = _check_result("installed-runtime", result)
    if check.status != "pass":
        return check, {}
    try:
        data = json.loads(result.output)
    except json.JSONDecodeError:
        return Check("installed-runtime", "fail", "probe output was not JSON"), {}
    return Check("installed-runtime", "pass", "imports and native parsers loaded"), data


def _help_check(
    runner: Runner,
    image: str,
    volume: str,
    seccomp: Path | None,
    cwd: Path,
    entry_points: object,
) -> Check:
    if not isinstance(entry_points, list) or "msgloom" not in entry_points:
        return Check(
            "entrypoint-help",
            "pending",
            "msgloom console entrypoint is not present in this integration candidate",
        )
    return _run_check(
        runner,
        docker_run_argv(
            image,
            unique_name("help"),
            volume,
            entrypoint_help_probe_code(),
            seccomp,
        ),
        cwd=cwd,
        name="entrypoint-help",
    )


def _resource_check(
    platform_data: dict[str, object],
    expected: tuple[str, ...],
) -> Check:
    resources = platform_data.get("resources")
    if not isinstance(resources, dict):
        return Check("package-resources", "fail", "resource evidence is missing")
    missing = sorted(value for value in expected if resources.get(value) is not True)
    if missing:
        return Check(
            "package-resources",
            "fail",
            "required wheel resources unavailable: " + ",".join(missing),
        )
    return Check("package-resources", "pass", "required runtime resources present")


def _isolation_checks(
    runner: Runner,
    image: str,
    volume: str,
    seccomp: Path | None,
    cwd: Path,
    skip: bool,
) -> list[Check]:
    if skip:
        detail = "explicitly disabled; must run before deployment acceptance"
        return [
            Check("parser-isolation", "pending", detail),
            Check("ai-offline-isolation", "pending", detail),
        ]
    parser = _run_check(
        runner,
        docker_run_argv(
            image, unique_name("parser"), volume, parser_probe_code(), seccomp
        ),
        cwd=cwd,
        name="parser-isolation",
    )
    ai = _run_check(
        runner,
        docker_run_argv(image, unique_name("ai"), volume, ai_probe_code(), seccomp),
        cwd=cwd,
        name="ai-offline-isolation",
    )
    return [parser, ai]


def _persistence_check(
    runner: Runner,
    image: str,
    volume: str,
    seccomp: Path | None,
    cwd: Path,
) -> Check:
    for existing, suffix in ((False, "persist1"), (True, "persist2")):
        check = _run_check(
            runner,
            docker_run_argv(
                image,
                unique_name(suffix),
                volume,
                persistence_probe_code(existing),
                seccomp,
            ),
            cwd=cwd,
            name="persistence-restart",
        )
        if check.status != "pass":
            return check
    return Check("persistence-restart", "pass", "SQLite reopened from named volume")


def _cleanup(
    runner: Runner,
    output_root: Path,
    volume: str,
    image: str,
) -> list[Check]:
    checks: list[Check] = []
    for name, command in (
        ("cleanup-volume", ["docker", "volume", "rm", "-f", volume]),
        ("cleanup-image", ["docker", "image", "rm", "-f", image]),
    ):
        try:
            result = runner.run(command, cwd=output_root)
        except (OSError, RuntimeError, ValueError) as exc:
            checks.append(Check(name, "fail", sanitize(str(exc))))
            continue
        if result.returncode and "No such" not in result.output:
            checks.append(_check_result(name, result))
    return checks


def _qualify_target(
    *,
    target: Target,
    wheel_hash: str,
    wheel_filename: str,
    wheel_version: str,
    resources: tuple[str, ...],
    context: Path,
    output_root: Path,
    runner: Runner,
    seccomp: Path | None,
    skip_isolation: bool,
    daemon_architecture: str,
    partial_evidence: Callable[[dict[str, object]], None] | None = None,
) -> dict[str, object]:
    invocation = unique_name(target.python.replace(".", ""))
    image = invocation
    volume = invocation + "-data"
    checks: list[Check] = []
    image_id = ""
    platform_data: dict[str, object] = {}

    def finish() -> dict[str, object]:
        present = {check.name for check in checks}
        expected = (
            "installed-runtime",
            "python-version",
            "architecture",
            "package-resources",
            "entrypoint-help",
            "persistence-restart",
            "parser-isolation",
            "ai-offline-isolation",
        )
        for name in expected:
            if name not in present:
                checks.append(
                    Check(name, "pending", "not executed after earlier target failure")
                )
        checks.extend(_cleanup(runner, output_root, volume, image))
        return evidence_json(
            checks,
            target=target,
            image_id=image_id,
            wheel_hash=wheel_hash,
            wheel_version=wheel_version,
            platform_data=platform_data,
        )

    try:
        build = runner.run(
            [
                "docker",
                "build",
                "--label",
                f"msgloom.qualification={invocation}",
                "--build-arg",
                f"BASE_IMAGE={target.base_image}",
                "--build-arg",
                f"WHEEL_SHA256={wheel_hash}",
                "--build-arg",
                f"WHEEL_FILENAME={wheel_filename}",
                "--tag",
                image,
                str(context),
            ],
            cwd=output_root,
        )
        checks.append(_check_result("image-build", build))
        if build.returncode:
            return finish()
        inspect = runner.run(
            ["docker", "image", "inspect", "--format", "{{.Id}}", image],
            cwd=output_root,
        )
        checks.append(_check_result("image-identity", inspect))
        if inspect.returncode:
            return finish()
        image_id = inspect.output.strip()
        created = runner.run(
            [
                "docker",
                "volume",
                "create",
                "--label",
                f"msgloom.qualification={invocation}",
                volume,
            ],
            cwd=output_root,
        )
        checks.append(_check_result("persistent-volume", created))
        if created.returncode:
            return finish()
        runtime, platform_data = _probe_json(
            runner, image, volume, seccomp, output_root, resources
        )
        checks.append(runtime)
        if runtime.status == "pass":
            observed = str(platform_data.get("python", ""))
            status = "pass" if observed.startswith(target.python + ".") else "fail"
            checks.append(Check("python-version", status, observed or "missing"))
            architecture = str(platform_data.get("architecture", ""))
            aliases = {"aarch64": "arm64", "arm64": "arm64"}
            status = (
                "pass"
                if aliases.get(architecture) == aliases.get(daemon_architecture)
                else "fail"
            )
            checks.append(
                Check(
                    "architecture",
                    status,
                    architecture or "container architecture missing",
                )
            )
            platform_data["docker_daemon_architecture"] = daemon_architecture
            checks.append(_resource_check(platform_data, resources))
            checks.append(
                _help_check(
                    runner,
                    image,
                    volume,
                    seccomp,
                    output_root,
                    platform_data.get("entry_points"),
                )
            )
        checks.append(_persistence_check(runner, image, volume, seccomp, output_root))
        checks.extend(
            _isolation_checks(
                runner,
                image,
                volume,
                seccomp,
                output_root,
                skip_isolation,
            )
        )
        return finish()
    except (OSError, RuntimeError, ValueError) as exc:
        checks.append(Check("target-execution", "fail", sanitize(str(exc))))
        return finish()
    except (Exception, KeyboardInterrupt):
        checks.append(Check("target-execution", "fail", "execution interrupted"))
        partial = finish()
        if partial_evidence is not None:
            try:
                partial_evidence(partial)
            except OSError:
                pass
        raise


def _host_checks(
    runner: Runner,
    env_python: Path,
    output_root: Path,
    skip: bool,
) -> list[Check]:
    if skip:
        detail = "explicitly disabled; must run before deployment acceptance"
        return [
            Check("host-parser-isolation", "pending", detail),
            Check("host-ai-offline-isolation", "pending", detail),
        ]
    return [
        _run_check(
            runner,
            [str(env_python), "-I", "-c", parser_probe_code()],
            cwd=output_root,
            name="host-parser-isolation",
        ),
        _run_check(
            runner,
            [
                str(env_python),
                "-I",
                "-c",
                ai_probe_code(str(output_root / "host-ai-state")),
            ],
            cwd=output_root,
            name="host-ai-offline-isolation",
        ),
    ]
