"""Qualify the exact sdist-built msgloom wheel in clean Docker images."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deployment.qualification import (
    QualificationError,
    Runner,
    Target,
    required_dependencies,
    sanitize,
    sha256_file,
    stage_context,
    validate_lock,
    validate_resource_specs,
    validate_resources,
    validate_seccomp_profile,
    validate_targets,
    wheel_metadata,
)
from deployment.release import ReleaseInputError
from deployment.target import (
    _host_checks,
    _qualify_target,
)

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
    resources: tuple[str, ...],
    runner: Runner,
) -> Path:
    """Use the existing package helper; never build a parallel wheel."""
    command = [
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
    ]
    for resource in resources:
        command.extend(["--require-resource", resource])
    result = runner.run(command, cwd=ROOT)
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


def _write_report(output_root: Path, report: dict[str, object]) -> None:
    """Atomically persist the latest bounded qualification evidence."""
    target = output_root / "container-qualification.json"
    temporary = output_root / ".container-qualification.json.tmp"
    temporary.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(target)


def _pending_target(target: Target, detail: str) -> dict[str, object]:
    """Return truthful evidence for a target not yet completed."""
    return {
        "python_target": target.python,
        "base_image": target.base_image,
        "checks": [
            {
                "name": "target-qualification",
                "status": "pending",
                "detail": detail,
            }
        ],
    }


def qualify(
    args: argparse.Namespace,
    runner: Runner | None = None,
) -> dict[str, object]:
    """Run serial qualification with durable partial lifecycle evidence."""
    selected = runner or Runner()
    targets = tuple(args.target)
    try:
        validate_targets(targets)
    except ReleaseInputError as exc:
        raise QualificationError(str(exc)) from exc
    source_root = args.source_root.resolve()
    output_root = args.output_root.resolve()
    if source_root == output_root or source_root in output_root.parents:
        raise QualificationError("output root must be outside source checkout")
    if output_root.exists():
        raise QualificationError("output root must not already exist")
    try:
        seccomp = (
            None
            if args.seccomp_profile is None
            else validate_seccomp_profile(args.seccomp_profile)
        )
    except ReleaseInputError as exc:
        raise QualificationError(str(exc)) from exc
    resources = tuple(args.require_resource)
    try:
        validate_resource_specs(resources)
    except ReleaseInputError as exc:
        raise QualificationError(str(exc)) from exc

    output_root.mkdir(parents=True)
    report: dict[str, object] = {
        "release_checks": [
            {
                "name": "qualification-execution",
                "status": "pending",
                "detail": "qualification started",
            }
        ],
        "host_checks": [
            {
                "name": "host-preflight",
                "status": "pending",
                "detail": "not executed",
            }
        ],
        "targets": [_pending_target(target, "not executed") for target in targets],
    }
    _write_report(output_root, report)
    release_checks = cast(list[dict[str, object]], report["release_checks"])
    results = cast(list[dict[str, object]], report["targets"])
    context: Path | None = None
    active_target: int | None = None
    active_stage = "Docker daemon preflight"
    original: Exception | KeyboardInterrupt | None = None
    expected_failure = False

    try:
        daemon = selected.run(
            ["docker", "info", "--format", "{{.Architecture}}"],
            cwd=ROOT,
        )
        if daemon.returncode or not daemon.output.strip():
            raise QualificationError("Docker daemon architecture is unavailable")
        daemon_architecture = daemon.output.strip()
        if daemon_architecture not in {"aarch64", "arm64"}:
            raise QualificationError("Docker daemon is not native ARM64")

        active_stage = "package qualification"
        package_output = output_root / "package"
        wheel = _package_wheel(
            source_root=source_root,
            output_root=package_output,
            env_python=args.env_python,
            uv=args.uv,
            resources=resources,
            runner=selected,
        )
        metadata = wheel_metadata(wheel)
        validate_resources(metadata, resources)
        required = required_dependencies(metadata, targets)
        validate_lock(args.runtime_lock, required)
        wheel_hash = sha256_file(wheel)
        context = stage_context(output_root, DOCKERFILE, wheel, args.runtime_lock)
        release_checks.append(
            {"name": "release-inputs", "status": "pass", "detail": "validated"}
        )
        report.update(
            {
                "wheel_filename": metadata.filename,
                "wheel_sha256": wheel_hash,
                "wheel_version": metadata.version,
                "required_resources": list(resources),
            }
        )
        _write_report(output_root, report)

        active_stage = "host preflight"
        report["host_checks"] = [
            {
                "name": "host-preflight",
                "status": "pending",
                "detail": "execution started",
            }
        ]
        _write_report(output_root, report)
        report["host_checks"] = [
            asdict(check)
            for check in _host_checks(
                selected,
                args.env_python,
                output_root,
                args.skip_isolation_preflight,
            )
        ]
        _write_report(output_root, report)

        for index, target in enumerate(targets):
            active_target = index
            active_stage = f"target {target.python}"
            results[index] = _pending_target(target, "execution started")
            _write_report(output_root, report)

            def persist_partial(
                value: dict[str, object],
                target_index: int = index,
            ) -> None:
                results[target_index] = value
                _write_report(output_root, report)

            results[index] = _qualify_target(
                target=target,
                wheel_hash=wheel_hash,
                wheel_filename=metadata.filename,
                wheel_version=metadata.version,
                resources=resources,
                context=context,
                output_root=output_root,
                runner=selected,
                seccomp=seccomp,
                skip_isolation=args.skip_isolation_preflight,
                daemon_architecture=daemon_architecture,
                partial_evidence=persist_partial,
            )
            active_target = None
            _write_report(output_root, report)
        release_checks[0] = {
            "name": "qualification-execution",
            "status": "pass",
            "detail": "qualification execution completed",
        }
    except (
        QualificationError,
        ReleaseInputError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        original = exc
        expected_failure = True
    except (Exception, KeyboardInterrupt) as exc:  # noqa: BLE001 - preserve evidence
        original = exc
    finally:
        if original is not None:
            detail = sanitize(str(original)) or type(original).__name__
            release_checks[0] = {
                "name": "qualification-execution",
                "status": "fail",
                "detail": f"{active_stage}: {detail}",
            }
            if active_target is not None:
                current = results[active_target]
                checks = cast(list[dict[str, object]], current.get("checks", []))
                if checks and checks[0].get("name") == "target-qualification":
                    target = targets[active_target]
                    results[active_target] = {
                        "python_target": target.python,
                        "base_image": target.base_image,
                        "checks": [
                            {
                                "name": "target-qualification",
                                "status": "fail",
                                "detail": (
                                    "execution interrupted before target evidence "
                                    "completed"
                                ),
                            }
                        ],
                    }
        if context is not None:
            try:
                shutil.rmtree(context)
            except OSError as exc:
                release_checks.append(
                    {
                        "name": "context-cleanup",
                        "status": "fail",
                        "detail": sanitize(str(exc)) or type(exc).__name__,
                    }
                )
        _write_report(output_root, report)

    if original is not None and not expected_failure:
        raise original.with_traceback(original.__traceback__)
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--env-python", required=True, type=Path)
    parser.add_argument("--uv", required=True, type=Path)
    parser.add_argument("--runtime-lock", required=True, type=Path)
    parser.add_argument("--target", required=True, action="append", type=_target)
    parser.add_argument("--require-resource", action="append", default=[])
    parser.add_argument("--seccomp-profile", type=Path)
    parser.add_argument("--skip-isolation-preflight", action="store_true")
    return parser


def _statuses(report: dict[str, object]) -> list[str]:
    statuses: list[str] = []
    for key in ("release_checks", "host_checks"):
        for check in cast(list[dict[str, object]], report.get(key, [])):
            statuses.append(str(check.get("status", "fail")))
    for target in cast(list[dict[str, object]], report.get("targets", [])):
        for check in cast(list[dict[str, object]], target.get("checks", [])):
            statuses.append(str(check.get("status", "fail")))
    return statuses


def main() -> int:
    """Run deployment qualification from explicit caller-owned paths."""
    try:
        report = qualify(_parser().parse_args())
    except (QualificationError, OSError, ValueError, json.JSONDecodeError) as exc:
        print("container qualification failed: " + sanitize(str(exc)), file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    statuses = _statuses(report)
    if "fail" in statuses:
        return 1
    if "pending" in statuses:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
