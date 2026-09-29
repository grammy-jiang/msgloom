"""Qualify the exact sdist-built msgloom wheel in clean Docker images."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import cast

from deployment.qualification import (
    Check,
    QualificationError,
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
    sha256_file,
    stage_context,
    unique_name,
    validate_lock,
    validate_targets,
    wheel_metadata,
)

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_HELPER = ROOT / "scripts" / "qualify_installed_wheel.py"
DOCKERFILE = ROOT / "deployment" / "Dockerfile"


def _target(value: str) -> Target:
    python, separator, image = value.partition("=")
    if not separator:
        raise argparse.ArgumentTypeError("target must be VERSION=IMAGE@sha256:DIGEST")
    return Target(python, image)


def _package_wheel(
    *,
    source_root: Path,
    output_root: Path,
    env_python: Path,
    uv: Path,
    runner: Runner,
) -> Path:
    """Use the existing package helper; never build a parallel wheel."""
    result = runner.run(
        [
            str(env_python),
            str(PACKAGE_HELPER),
            "--source-root",
            str(source_root),
            "--output-root",
            str(output_root),
            "--env-python",
            str(env_python),
            "--uv",
            str(uv),
        ],
        cwd=ROOT,
    )
    if result.returncode != 0:
        raise QualificationError("installed-wheel helper failed: " + result.output)
    report = output_root / "qualification.json"
    if not report.is_file():
        raise QualificationError("installed-wheel helper did not write evidence")
    data = json.loads(report.read_text(encoding="utf-8"))
    wheel = Path(data["wheel"])
    if not wheel.is_file() or output_root.resolve() not in wheel.resolve().parents:
        raise QualificationError("installed-wheel helper returned an unsafe wheel path")
    return wheel


def _run_check(
    runner: Runner,
    command: list[str],
    *,
    cwd: Path,
    name: str,
) -> Check:
    result = runner.run(command, cwd=cwd)
    if result.returncode:
        return Check(name, "fail", result.output or "command failed")
    return Check(name, "pass", result.output.strip() or "ok")


def _probe_json(
    runner: Runner,
    image: str,
    volume: str,
    seccomp: Path | None,
    cwd: Path,
) -> tuple[Check, dict[str, object]]:
    command = docker_run_argv(
        image,
        unique_name("imports"),
        volume,
        container_probe_code(),
        seccomp,
    )
    result = runner.run(command, cwd=cwd)
    if result.returncode:
        return Check("installed-runtime", "fail", result.output), {}
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
    code = entrypoint_help_probe_code()
    return _run_check(
        runner,
        docker_run_argv(
            image,
            unique_name("help"),
            volume,
            code,
            seccomp,
        ),
        cwd=cwd,
        name="entrypoint-help",
    )


def _resource_check(platform_data: dict[str, object]) -> Check:
    resources = platform_data.get("resources")
    if not isinstance(resources, dict):
        return Check("package-resources", "fail", "resource evidence is missing")
    missing = sorted(name for name, present in resources.items() if not present)
    if missing:
        return Check(
            "package-resources",
            "pending",
            "wheel resources not yet integrated: " + ",".join(missing),
        )
    return Check("package-resources", "pass", "templates/prompts/migrations present")


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
            image,
            unique_name("parser"),
            volume,
            parser_probe_code(),
            seccomp,
        ),
        cwd=cwd,
        name="parser-isolation",
    )
    ai = _run_check(
        runner,
        docker_run_argv(
            image,
            unique_name("ai"),
            volume,
            ai_probe_code(),
            seccomp,
        ),
        cwd=cwd,
        name="ai-offline-isolation",
    )
    return [parser, ai]


def _persistence_checks(
    runner: Runner,
    image: str,
    volume: str,
    seccomp: Path | None,
    cwd: Path,
) -> Check:
    first = _run_check(
        runner,
        docker_run_argv(
            image,
            unique_name("persist1"),
            volume,
            persistence_probe_code(False),
            seccomp,
        ),
        cwd=cwd,
        name="persistence-first-open",
    )
    if first.status != "pass":
        return Check("persistence-restart", "fail", first.detail)
    second = _run_check(
        runner,
        docker_run_argv(
            image,
            unique_name("persist2"),
            volume,
            persistence_probe_code(True),
            seccomp,
        ),
        cwd=cwd,
        name="persistence-second-open",
    )
    if second.status != "pass":
        return Check("persistence-restart", "fail", second.detail)
    return Check("persistence-restart", "pass", "SQLite reopened from named volume")


def _qualify_target(
    *,
    target: Target,
    wheel: Path,
    wheel_hash: str,
    wheel_version: str,
    context: Path,
    output_root: Path,
    runner: Runner,
    seccomp: Path | None,
    skip_isolation: bool,
    daemon_architecture: str,
) -> dict[str, object]:
    invocation = unique_name(target.python.replace(".", ""))
    image = invocation
    volume = invocation + "-data"
    checks: list[Check] = []
    image_id = ""
    platform_data: dict[str, object] = {}
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
                "--tag",
                image,
                str(context),
            ],
            cwd=output_root,
        )
        if build.returncode:
            checks.append(Check("image-build", "fail", build.output))
            return evidence_json(
                checks,
                target=target,
                image_id=image_id,
                wheel_hash=wheel_hash,
                wheel_version=wheel_version,
                platform_data=platform_data,
            )
        checks.append(Check("image-build", "pass", "digest-pinned image built"))
        inspect = runner.run(
            ["docker", "image", "inspect", "--format", "{{.Id}}", image],
            cwd=output_root,
        )
        if inspect.returncode:
            checks.append(Check("image-identity", "fail", inspect.output))
            return evidence_json(
                checks,
                target=target,
                image_id=image_id,
                wheel_hash=wheel_hash,
                wheel_version=wheel_version,
                platform_data=platform_data,
            )
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
        if created.returncode:
            checks.append(Check("persistent-volume", "fail", created.output))
            return evidence_json(
                checks,
                target=target,
                image_id=image_id,
                wheel_hash=wheel_hash,
                wheel_version=wheel_version,
                platform_data=platform_data,
            )
        checks.append(Check("persistent-volume", "pass", "owned named volume created"))
        runtime, platform_data = _probe_json(
            runner, image, volume, seccomp, output_root
        )
        checks.append(runtime)
        if runtime.status == "pass":
            observed = str(platform_data.get("python", ""))
            if not observed.startswith(target.python + "."):
                checks.append(
                    Check("python-version", "fail", "container Python version mismatch")
                )
            else:
                checks.append(Check("python-version", "pass", observed))
            architecture = str(platform_data.get("architecture", ""))
            if not architecture:
                checks.append(
                    Check("architecture", "fail", "container architecture missing")
                )
            elif architecture != daemon_architecture:
                checks.append(
                    Check(
                        "architecture",
                        "fail",
                        f"container={architecture};daemon={daemon_architecture}",
                    )
                )
            else:
                checks.append(Check("architecture", "pass", architecture))
            platform_data["docker_daemon_architecture"] = daemon_architecture
            checks.append(_resource_check(platform_data))
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
        checks.append(_persistence_checks(runner, image, volume, seccomp, output_root))
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
        return evidence_json(
            checks,
            target=target,
            image_id=image_id,
            wheel_hash=wheel_hash,
            wheel_version=wheel_version,
            platform_data=platform_data,
        )
    finally:
        runner.run(["docker", "volume", "rm", "-f", volume], cwd=output_root)
        runner.run(["docker", "image", "rm", "-f", image], cwd=output_root)


def qualify(
    args: argparse.Namespace, runner: Runner | None = None
) -> dict[str, object]:
    """Run the serial three-version qualification and persist exact evidence."""
    selected = runner or Runner()
    targets = tuple(args.target)
    validate_targets(targets)
    source_root = args.source_root.resolve()
    output_root = args.output_root.resolve()
    if source_root == output_root or source_root in output_root.parents:
        raise QualificationError("output root must be outside source checkout")
    if output_root.exists():
        raise QualificationError("output root must not already exist")
    if args.seccomp_profile is not None:
        seccomp = args.seccomp_profile.resolve()
        if not seccomp.is_file():
            raise QualificationError("seccomp profile is not a regular file")
    else:
        seccomp = None
    daemon = selected.run(
        ["docker", "info", "--format", "{{.Architecture}}"],
        cwd=ROOT,
    )
    if daemon.returncode or not daemon.output.strip():
        raise QualificationError("Docker daemon architecture is unavailable")
    daemon_architecture = daemon.output.strip()
    output_root.mkdir(parents=True)
    package_output = output_root / "package"
    wheel = _package_wheel(
        source_root=source_root,
        output_root=package_output,
        env_python=args.env_python,
        uv=args.uv,
        runner=selected,
    )
    dependencies, resources, wheel_version = wheel_metadata(wheel)
    validate_lock(args.runtime_lock, dependencies)
    wheel_hash = sha256_file(wheel)
    context = stage_context(output_root, DOCKERFILE, wheel, args.runtime_lock)
    results = []
    try:
        for target in targets:
            results.append(
                _qualify_target(
                    target=target,
                    wheel=wheel,
                    wheel_hash=wheel_hash,
                    wheel_version=wheel_version,
                    context=context,
                    output_root=output_root,
                    runner=selected,
                    seccomp=seccomp,
                    skip_isolation=args.skip_isolation_preflight,
                    daemon_architecture=daemon_architecture,
                )
            )
    finally:
        shutil.rmtree(context, ignore_errors=True)
    report = {
        "wheel_sha256": wheel_hash,
        "wheel_version": wheel_version,
        "wheel_resources_present": list(resources),
        "targets": results,
    }
    (output_root / "container-qualification.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--env-python", required=True, type=Path)
    parser.add_argument("--uv", required=True, type=Path)
    parser.add_argument("--runtime-lock", required=True, type=Path)
    parser.add_argument("--target", required=True, action="append", type=_target)
    parser.add_argument("--seccomp-profile", type=Path)
    parser.add_argument("--skip-isolation-preflight", action="store_true")
    return parser


def main() -> int:
    """Run deployment qualification from explicit caller-owned paths."""
    try:
        report = qualify(_parser().parse_args())
    except (QualificationError, OSError, ValueError, json.JSONDecodeError) as exc:
        print("container qualification failed: " + sanitize(str(exc)), file=sys.stderr)
        return 1
    targets = cast(list[dict[str, object]], report["targets"])
    statuses: list[object] = []
    for target in targets:
        checks = cast(list[dict[str, object]], target["checks"])
        statuses.extend(check["status"] for check in checks)
    print(json.dumps(report, indent=2, sort_keys=True))
    if "fail" in statuses:
        return 1
    if "pending" in statuses:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
