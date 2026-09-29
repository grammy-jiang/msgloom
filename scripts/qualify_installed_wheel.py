"""Build and qualify one installed msgloom wheel without source fallback."""

from __future__ import annotations

import argparse
import copy
import gzip
import json
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath

RUNTIME_ROOTS = ("msgloom", "message_ingest", "microsoft_graph")
BUILD_BACKEND = "setuptools.build_meta"
BUILD_REQUIREMENTS = ["setuptools==84.0.0"]
FORBIDDEN_RUNTIME = ("fastmcp", "prefect")


class QualificationError(RuntimeError):
    """Report a finite package qualification failure."""


@dataclass(frozen=True, slots=True)
class QualificationRequest:
    """Inputs supplied by the qualification owner."""

    source_root: Path
    output_root: Path
    env_python: Path
    uv: Path
    required_cli: tuple[str, ...]
    required_resource: tuple[str, ...]


def _run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run one bounded command without shell interpolation."""
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def _validate_request_paths(request: QualificationRequest) -> None:
    """Keep all generated artifacts outside the source checkout."""
    source = request.source_root.resolve()
    output = request.output_root.resolve()
    if source == output or source in output.parents:
        raise QualificationError("output root must be outside the source checkout")


def _source_epoch(source_root: Path) -> int:
    """Return the deterministic timestamp of the source revision."""
    completed = _run(
        ["git", "-C", str(source_root), "log", "-1", "--format=%ct"],
        cwd=source_root,
    )
    try:
        epoch = int(completed.stdout.strip())
    except ValueError as exc:
        raise QualificationError("source revision timestamp is invalid") from exc
    if epoch < 0:
        raise QualificationError("source revision timestamp is invalid")
    return epoch


def _stage_tracked_source(request: QualificationRequest) -> Path:
    """Copy only tracked build inputs beneath the caller output root."""
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(request.source_root),
            "ls-files",
            "-z",
            "--",
            "pyproject.toml",
            "MANIFEST.in",
            *RUNTIME_ROOTS,
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    relative_paths = [
        item.decode("utf-8") for item in completed.stdout.split(b"\0") if item
    ]
    required = {"pyproject.toml", "MANIFEST.in"}
    if not required <= set(relative_paths):
        raise QualificationError("tracked build metadata is incomplete")
    stage = request.output_root / "source"
    stage.mkdir()
    for name in relative_paths:
        relative = _safe_member(name)
        source = request.source_root.joinpath(*relative.parts)
        mode = source.lstat().st_mode
        if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
            raise QualificationError(f"tracked build input is not regular: {name}")
        destination = stage.joinpath(*relative.parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination, follow_symlinks=False)
    _validate_project(stage)
    return stage


def _validate_project(source_root: Path) -> None:
    """Reject an unexpected build backend before invoking build code."""
    project_file = source_root / "pyproject.toml"
    with project_file.open("rb") as stream:
        project = tomllib.load(stream)
    build = project.get("build-system")
    if not isinstance(build, dict):
        raise QualificationError("build-system table is required")
    if build.get("build-backend") != BUILD_BACKEND:
        raise QualificationError("unexpected build backend")
    if build.get("requires") != BUILD_REQUIREMENTS:
        raise QualificationError("unexpected build requirements")
    if (source_root / "setup.py").exists() or (source_root / "setup.cfg").exists():
        raise QualificationError("setup scripts are not admitted")


def _safe_member(name: str) -> PurePosixPath:
    """Return a normalized archive member or reject traversal."""
    member = PurePosixPath(name)
    if member.is_absolute() or ".." in member.parts or not member.parts:
        raise QualificationError(f"unsafe archive member: {name!r}")
    return member


def _sdist_relative(name: str) -> PurePosixPath:
    """Strip the one required source-distribution root directory."""
    member = _safe_member(name)
    if len(member.parts) < 2:
        raise QualificationError(f"sdist member lacks root: {name!r}")
    return PurePosixPath(*member.parts[1:])


def _allowed_sdist(relative: PurePosixPath) -> bool:
    """Return whether one sdist member belongs to the rebuild allowlist."""
    if str(relative) in {
        "pyproject.toml",
        "MANIFEST.in",
        "PKG-INFO",
        "setup.cfg",
    }:
        return True
    first = relative.parts[0]
    if first in RUNTIME_ROOTS:
        return True
    return first.endswith(".egg-info")


def inspect_sdist(path: Path) -> tuple[str, ...]:
    """Validate sdist paths, member types, and the rebuild allowlist."""
    names: list[str] = []
    with tarfile.open(path, mode="r:*") as archive:
        roots: set[str] = set()
        for member in archive.getmembers():
            normalized = _safe_member(member.name)
            roots.add(normalized.parts[0])
            if len(normalized.parts) == 1:
                if not member.isdir():
                    raise QualificationError("sdist root must be a directory")
                continue
            relative = _sdist_relative(member.name)
            if member.issym() or member.islnk():
                raise QualificationError("sdist links are not admitted")
            if not (member.isdir() or member.isfile()):
                raise QualificationError("sdist special members are not admitted")
            if not _allowed_sdist(relative):
                raise QualificationError(f"sdist member outside allowlist: {relative}")
            names.append(str(relative))
        if len(roots) != 1:
            raise QualificationError("sdist must have exactly one root")
    required = {"pyproject.toml", "MANIFEST.in"}
    if not required <= set(names):
        raise QualificationError("sdist is not sufficient to rebuild")
    return tuple(sorted(names))


def _normalize_sdist(path: Path, epoch: int) -> None:
    """Rewrite an inspected sdist with deterministic archive metadata."""
    entries: list[tuple[tarfile.TarInfo, bytes | None]] = []
    with tarfile.open(path, mode="r:*") as source:
        for member in sorted(source.getmembers(), key=lambda item: item.name):
            data = None
            if member.isfile():
                stream = source.extractfile(member)
                if stream is None:
                    raise QualificationError("sdist file content is unavailable")
                data = stream.read()
            entries.append((copy.copy(member), data))

    temporary = path.with_name(f".{path.name}.normalized")
    with (
        temporary.open("wb") as raw,
        gzip.GzipFile(
            filename="",
            mode="wb",
            fileobj=raw,
            mtime=epoch,
        ) as compressed,
        tarfile.open(
            fileobj=compressed,
            mode="w",
            format=tarfile.PAX_FORMAT,
        ) as target,
    ):
        for member, data in entries:
            member.uid = 0
            member.gid = 0
            member.uname = ""
            member.gname = ""
            member.mtime = epoch
            member.pax_headers = {}
            target.addfile(
                member,
                None if data is None else BytesIO(data),
            )
    temporary.replace(path)


def _allowed_wheel(member: PurePosixPath) -> bool:
    """Return whether one wheel member belongs to runtime or metadata."""
    first = member.parts[0]
    if first in RUNTIME_ROOTS:
        return True
    return first.startswith("msgloom-") and first.endswith(".dist-info")


def inspect_wheel(path: Path) -> tuple[str, ...]:
    """Validate wheel paths and reject non-runtime payloads."""
    names: list[str] = []
    metadata_text = ""
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            member = _safe_member(info.filename)
            if not _allowed_wheel(member):
                raise QualificationError(f"wheel member outside allowlist: {member}")
            names.append(str(member))
            if member.name == "METADATA" and ".dist-info" in member.parts[0]:
                metadata_text = archive.read(info).decode("utf-8")
    if not metadata_text:
        raise QualificationError("wheel METADATA is missing")
    lowered = metadata_text.lower()
    for package in FORBIDDEN_RUNTIME:
        if f"requires-dist: {package}" in lowered:
            raise QualificationError(f"forbidden normal runtime dependency: {package}")
    return tuple(sorted(names))


def _one_artifact(directory: Path, suffix: str) -> Path:
    """Return the single artifact with the requested suffix."""
    matches = sorted(directory.glob(f"*{suffix}"))
    if len(matches) != 1:
        raise QualificationError(
            f"expected one {suffix} artifact, found {len(matches)}"
        )
    return matches[0]


def build_artifacts(request: QualificationRequest) -> tuple[Path, Path]:
    """Build an sdist, inspect it, then build the exact wheel from it."""
    _validate_project(request.source_root)
    epoch = _source_epoch(request.source_root)
    source_stage = _stage_tracked_source(request)
    sdist_dir = request.output_root / "sdist"
    wheel_dir = request.output_root / "wheel"
    sdist_dir.mkdir(parents=True, exist_ok=False)
    wheel_dir.mkdir(parents=True, exist_ok=False)
    common = [
        str(request.uv),
        "build",
        "--offline",
        "--no-progress",
        "--no-python-downloads",
        "--no-config",
    ]
    build_env = os.environ.copy()
    build_env["SOURCE_DATE_EPOCH"] = str(epoch)
    build_env.pop("PYTHONPATH", None)
    _run(
        common + ["--sdist", "--out-dir", str(sdist_dir), str(source_stage)],
        cwd=request.output_root,
        env=build_env,
    )
    sdist = _one_artifact(sdist_dir, ".tar.gz")
    inspect_sdist(sdist)
    _normalize_sdist(sdist, epoch)
    inspect_sdist(sdist)
    _run(
        common + ["--wheel", "--out-dir", str(wheel_dir), str(sdist)],
        cwd=request.output_root,
        env=build_env,
    )
    wheel = _one_artifact(wheel_dir, ".whl")
    inspect_wheel(wheel)
    return sdist, wheel


def _validate_env_python(env_python: Path) -> None:
    """Require an existing isolated virtual-environment interpreter."""
    if not env_python.is_file():
        raise QualificationError("isolated environment Python is missing")
    probe = _run(
        [
            str(env_python),
            "-I",
            "-c",
            (
                "import json,sys;"
                "print(json.dumps({'prefix':sys.prefix,"
                "'base_prefix':sys.base_prefix}))"
            ),
        ],
        cwd=env_python.parent,
    )
    data = json.loads(probe.stdout)
    if data["prefix"] == data["base_prefix"]:
        raise QualificationError("supplied Python is not isolated")


def _probe_code(
    required_cli: Iterable[str],
    required_resource: Iterable[str],
) -> str:
    """Create the isolated installed-import probe."""
    payload = {
        "roots": RUNTIME_ROOTS,
        "forbidden": FORBIDDEN_RUNTIME,
        "cli": tuple(required_cli),
        "resources": tuple(required_resource),
    }
    return f"""
import importlib
import importlib.metadata
import importlib.resources
import importlib.util
import json
import os, pathlib, socket, subprocess, sys, threading

config = {payload!r}
def blocked_startup(*args, **kwargs):
    raise RuntimeError("package import attempted external startup")
subprocess.Popen = blocked_startup
os.system = blocked_startup
socket.socket.connect = blocked_startup
cwd = pathlib.Path.cwd().resolve()
before = set(cwd.iterdir())
prefix = pathlib.Path(sys.prefix).resolve()
paths = {{}}
threads = {{item.ident for item in threading.enumerate()}}
for name in config["roots"]:
    module = importlib.import_module(name)
    location = pathlib.Path(module.__file__).resolve()
    if prefix not in location.parents:
        raise RuntimeError(f"source fallback for {{name}}: {{location}}")
    paths[name] = str(location)
for name in config["forbidden"]:
    if importlib.util.find_spec(name) is not None:
        raise RuntimeError(f"forbidden package installed: {{name}}")
entry_points = {{
    item.name for item in importlib.metadata.entry_points(group="console_scripts")
    if item.dist and item.dist.name == "msgloom"
}}
missing_cli = set(config["cli"]) - entry_points
if missing_cli:
    raise RuntimeError(f"required CLI missing: {{sorted(missing_cli)}}")
for value in config["resources"]:
    package, separator, resource = value.partition(":")
    if not separator or not package or not resource:
        raise RuntimeError(f"invalid resource requirement: {{value!r}}")
    target = importlib.resources.files(package).joinpath(resource)
    if not target.is_file():
        raise RuntimeError(f"required resource missing: {{value}}")
after = set(cwd.iterdir())
if after != before:
    raise RuntimeError("package import modified the probe working directory")
if {{item.ident for item in threading.enumerate()}} != threads:
    raise RuntimeError("package import started a background thread")
print(json.dumps({{"paths": paths, "entry_points": sorted(entry_points)}}))
"""


def install_and_probe(
    request: QualificationRequest,
    wheel: Path,
) -> dict[str, object]:
    """Install the exact wheel and probe imports outside the checkout."""
    _validate_env_python(request.env_python)
    probe_dir = request.output_root / "installed-probe"
    probe_dir.mkdir()
    _run(
        [
            str(request.uv),
            "pip",
            "install",
            "--offline",
            "--no-progress",
            "--no-python-downloads",
            "--no-config",
            "--python",
            str(request.env_python),
            "--no-deps",
            "--reinstall",
            str(wheel),
        ],
        cwd=probe_dir,
    )
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    completed = subprocess.run(
        [
            str(request.env_python),
            "-I",
            "-c",
            _probe_code(request.required_cli, request.required_resource),
        ],
        cwd=probe_dir,
        env=env,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return json.loads(completed.stdout)


def qualify(request: QualificationRequest) -> dict[str, object]:
    """Run the finite offline package qualification."""
    _validate_request_paths(request)
    request.output_root.mkdir(parents=True, exist_ok=False)
    sdist, wheel = build_artifacts(request)
    probe = install_and_probe(request, wheel)
    result = {
        "sdist": str(sdist),
        "wheel": str(wheel),
        "installed_probe": probe,
    }
    report = request.output_root / "qualification.json"
    report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--env-python", required=True, type=Path)
    parser.add_argument("--uv", required=True, type=Path)
    parser.add_argument("--require-cli", action="append", default=[])
    parser.add_argument("--require-resource", action="append", default=[])
    return parser


def main() -> int:
    """Run qualification from explicit caller-supplied paths."""
    args = _parser().parse_args()
    request = QualificationRequest(
        source_root=args.source_root.resolve(),
        output_root=args.output_root.resolve(),
        env_python=args.env_python.resolve(),
        uv=args.uv.resolve(),
        required_cli=tuple(args.require_cli),
        required_resource=tuple(args.require_resource),
    )
    try:
        result = qualify(request)
    except (QualificationError, OSError, subprocess.CalledProcessError) as exc:
        print(f"qualification failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
