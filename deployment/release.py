"""Strict release-input validation for container qualification."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import zipfile
from dataclasses import dataclass
from email.parser import Parser
from pathlib import Path

from packaging.markers import default_environment
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import (
    InvalidWheelFilename,
    canonicalize_name,
    parse_wheel_filename,
)
from packaging.version import InvalidVersion, Version

REQUIRED_PYTHONS = ("3.12", "3.13", "3.14")
FORBIDDEN_LOCK_NAMES = {
    "fastmcp",
    "prefect",
    "pytest",
    "ruff",
    "setuptools",
    "tox",
    "tox-uv",
}
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
_LOCK_LINE = re.compile(
    r"([A-Za-z0-9][A-Za-z0-9_.-]*)==([^\s]+)"
    r"(?:\s+--hash=sha256:[0-9a-f]{64})+\Z"
)


class ReleaseInputError(ValueError):
    """Report invalid deployment release inputs."""


@dataclass(frozen=True, slots=True)
class Target:
    """One required Python image pinned to an immutable digest."""

    python: str
    base_image: str


@dataclass(frozen=True, slots=True)
class WheelMetadata:
    """Validated release metadata read from the exact wheel."""

    filename: str
    version: str
    requirements: tuple[Requirement, ...]
    members: frozenset[str]


def validate_targets(targets: tuple[Target, ...]) -> None:
    """Require one exact digest-pinned official image per Python target."""
    if tuple(target.python for target in targets) != REQUIRED_PYTHONS:
        raise ReleaseInputError("targets must be ordered 3.12, 3.13, 3.14")
    for target in targets:
        image, separator, digest = target.base_image.partition("@")
        expected = f"python:{target.python}-slim-bookworm"
        if image != expected:
            raise ReleaseInputError(
                f"Python {target.python} must use exact official slim-bookworm tag"
            )
        if not separator or not _DIGEST.fullmatch(digest):
            raise ReleaseInputError("base image must be pinned by sha256 digest")


def sha256_file(path: Path) -> str:
    """Return the content digest of one regular artifact."""
    if not path.is_file() or path.is_symlink():
        raise ReleaseInputError("qualification artifact must be a regular file")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wheel_metadata(wheel: Path) -> WheelMetadata:
    """Validate wheel filename, distribution identity, and core metadata."""
    if not wheel.is_file() or wheel.is_symlink():
        raise ReleaseInputError("wheel must be a regular file")
    try:
        wheel_name, wheel_version, _, tags = parse_wheel_filename(wheel.name)
    except InvalidWheelFilename as exc:
        raise ReleaseInputError("wheel filename is invalid") from exc
    if wheel_name != canonicalize_name("msgloom"):
        raise ReleaseInputError("wheel distribution name must be msgloom")
    tag_values = {(tag.interpreter, tag.abi, tag.platform) for tag in tags}
    if tag_values != {("py3", "none", "any")}:
        raise ReleaseInputError("msgloom wheel must be universal py3-none-any")
    with zipfile.ZipFile(wheel) as archive:
        names = tuple(archive.namelist())
        metadata_names = [
            name
            for name in names
            if name.endswith(".dist-info/METADATA") and "/" in name
        ]
        if len(metadata_names) != 1:
            raise ReleaseInputError("wheel must contain exactly one METADATA")
        metadata = Parser().parsestr(
            archive.read(metadata_names[0]).decode("utf-8", errors="strict")
        )
    if canonicalize_name(metadata.get("Name", "")) != canonicalize_name("msgloom"):
        raise ReleaseInputError("wheel metadata distribution name must be msgloom")
    version_text = metadata.get("Version")
    if not version_text:
        raise ReleaseInputError("wheel version metadata is missing")
    try:
        metadata_version = Version(version_text)
    except InvalidVersion as exc:
        raise ReleaseInputError("wheel version metadata is invalid") from exc
    if metadata_version != wheel_version:
        raise ReleaseInputError("wheel filename and metadata versions differ")
    requirements: list[Requirement] = []
    for value in metadata.get_all("Requires-Dist", []):
        try:
            requirements.append(Requirement(value))
        except InvalidRequirement as exc:
            raise ReleaseInputError("wheel dependency metadata is invalid") from exc
    return WheelMetadata(
        wheel.name, str(metadata_version), tuple(requirements), frozenset(names)
    )


def required_dependencies(
    metadata: WheelMetadata,
    targets: tuple[Target, ...],
) -> set[str]:
    """Return direct dependencies active on at least one qualified target."""
    required: set[str] = set()
    for target in targets:
        base: dict[str, str] = {
            key: str(value) for key, value in default_environment().items()
        }
        base.update(
            {
                "extra": "",
                "implementation_name": "cpython",
                "platform_machine": "aarch64",
                "platform_system": "Linux",
                "python_version": target.python,
                "sys_platform": "linux",
            }
        )
        for requirement in metadata.requirements:
            marker = requirement.marker
            if marker is None:
                required.add(canonicalize_name(requirement.name))
                continue
            for patch in range(256):
                environment = dict(base)
                full_version = f"{target.python}.{patch}"
                environment["python_full_version"] = full_version
                environment["implementation_version"] = full_version
                if marker.evaluate(environment):
                    required.add(canonicalize_name(requirement.name))
                    break
    return required


def validate_resource_specs(expected: tuple[str, ...]) -> tuple[str, ...]:
    """Validate exact caller-selected runtime resource identities."""
    if not expected:
        raise ReleaseInputError("at least one runtime resource must be required")
    seen: set[str] = set()
    for value in expected:
        package, separator, resource = value.partition(":")
        if (
            not separator
            or package != "msgloom"
            or not resource
            or resource.startswith("/")
            or ".." in Path(resource).parts
        ):
            raise ReleaseInputError("runtime resource must be msgloom:relative/path")
        if value in seen:
            raise ReleaseInputError("runtime resource requirements must be unique")
        seen.add(value)
    return expected


def validate_resources(
    metadata: WheelMetadata,
    expected: tuple[str, ...],
) -> tuple[str, ...]:
    """Require exact caller-selected runtime resource files in the wheel."""
    validate_resource_specs(expected)
    for value in expected:
        package, _, resource = value.partition(":")
        member = package.replace(".", "/") + "/" + resource
        if member not in metadata.members:
            raise ReleaseInputError(f"required runtime resource missing: {value}")
    return expected


def validate_lock(lock: Path, required: set[str]) -> set[str]:
    """Require exact hashed runtime requirements covering active direct deps."""
    if not lock.is_file() or lock.is_symlink():
        raise ReleaseInputError("runtime lock must be a regular file")
    logical = lock.read_text(encoding="utf-8").replace("\\\n", " ")
    locked: set[str] = set()
    for raw in logical.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-") or "://" in line or " @ " in line:
            raise ReleaseInputError("runtime lock cannot contain directives or URLs")
        match = _LOCK_LINE.fullmatch(line)
        if match is None:
            raise ReleaseInputError("runtime lock entries must be exact and hashed")
        name = canonicalize_name(match.group(1))
        try:
            Version(match.group(2))
        except InvalidVersion as exc:
            raise ReleaseInputError("runtime lock version is invalid") from exc
        if name in locked:
            raise ReleaseInputError("runtime lock contains duplicate package entries")
        if name in FORBIDDEN_LOCK_NAMES:
            raise ReleaseInputError(f"forbidden deployment dependency: {name}")
        locked.add(name)
    missing = required - locked
    if missing:
        raise ReleaseInputError(
            "runtime lock misses wheel dependencies: " + ",".join(sorted(missing))
        )
    return locked


def validate_seccomp_profile(path: Path) -> Path:
    """Validate one explicit confining Docker seccomp JSON profile."""
    if path.is_symlink():
        raise ReleaseInputError("seccomp profile must be a regular file")
    resolved = path.resolve()
    if not resolved.is_file():
        raise ReleaseInputError("seccomp profile must be a regular file")
    if resolved.stat().st_size > 1024 * 1024:
        raise ReleaseInputError("seccomp profile exceeds 1 MiB")
    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ReleaseInputError("seccomp profile must be valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ReleaseInputError("seccomp profile root must be an object")
    action = value.get("defaultAction")
    if action != "SCMP_ACT_ERRNO":
        raise ReleaseInputError("seccomp profile must retain SCMP_ACT_ERRNO default")
    syscalls = value.get("syscalls")
    if not isinstance(syscalls, list) or not syscalls:
        raise ReleaseInputError("seccomp profile must define syscall rules")
    return resolved


def stage_context(
    root: Path,
    dockerfile: Path,
    wheel: Path,
    lock: Path,
) -> Path:
    """Stage recipe, lock, and exact valid wheel beneath a fresh directory."""
    metadata = wheel_metadata(wheel)
    context = root / "build-context"
    context.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(dockerfile, context / "Dockerfile")
    shutil.copyfile(lock, context / "runtime-requirements.txt")
    shutil.copyfile(wheel, context / metadata.filename)
    ignore = dockerfile.with_name("Dockerfile.dockerignore")
    if not ignore.is_file():
        raise ReleaseInputError("Dockerfile-specific ignore file is missing")
    staged_ignore = context / "Dockerfile.dockerignore"
    shutil.copyfile(ignore, staged_ignore)
    with staged_ignore.open("a", encoding="utf-8") as stream:
        stream.write(f"!{metadata.filename}\n")
    return context
