"""Finite Docker qualification primitives for an installed msgloom wheel."""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import zipfile
from dataclasses import asdict, dataclass
from email.parser import Parser
from pathlib import Path
from typing import Literal
from uuid import uuid4

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
RESOURCE_PREFIXES = (
    "msgloom/templates/",
    "msgloom/prompts/",
    "msgloom/migrations/",
)
COMMAND_TIMEOUT_SECONDS = 300
OUTPUT_LIMIT = 1600
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
_SECRET = re.compile(
    r"(?i)(authorization|bearer|password|secret|token|api[_-]?key)"
    r"([=: ]+)([^\s,;]+)"
)
_PATH = re.compile(r"(?<![A-Za-z0-9_.-])/(?:[^\s'\"]+)")


class QualificationError(RuntimeError):
    """Report a finite deployment qualification failure."""


@dataclass(frozen=True, slots=True)
class Target:
    """One required Python image pinned to an immutable digest."""

    python: str
    base_image: str


@dataclass(frozen=True, slots=True)
class Check:
    """Bounded machine-readable evidence for one qualification gate."""

    name: str
    status: Literal["pass", "fail", "pending"]
    detail: str


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Sanitized bounded command result."""

    returncode: int
    output: str


def sanitize(value: str) -> str:
    """Redact likely paths and credential-shaped values, then bound output."""
    redacted = _SECRET.sub(r"\1\2<redacted>", value)
    redacted = _PATH.sub("<path>", redacted)
    redacted = redacted.replace("\x00", "")
    return redacted[-OUTPUT_LIMIT:]


class Runner:
    """Run bounded argv-only subprocesses without exposing command arguments."""

    def run(
        self,
        command: list[str],
        *,
        cwd: Path,
        timeout: int = COMMAND_TIMEOUT_SECONDS,
    ) -> CommandResult:
        """Run one command and return only bounded sanitized output."""
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            name = Path(command[0]).name
            raise QualificationError(f"timeout after {timeout}s: {name}") from None
        return CommandResult(completed.returncode, sanitize(completed.stdout))


def validate_targets(targets: tuple[Target, ...]) -> None:
    """Require exactly one digest-pinned official image per Python target."""
    if tuple(target.python for target in targets) != REQUIRED_PYTHONS:
        raise QualificationError("targets must be ordered 3.12, 3.13, 3.14")
    for target in targets:
        prefix = f"python:{target.python}"
        image, separator, digest = target.base_image.partition("@")
        if not separator or not _DIGEST.fullmatch(digest):
            raise QualificationError("base image must be pinned by sha256 digest")
        if not image.startswith(prefix) or "-slim-bookworm" not in image:
            raise QualificationError(
                f"Python {target.python} must use official slim-bookworm image"
            )


def sha256_file(path: Path) -> str:
    """Return the content digest of one regular artifact."""
    if not path.is_file() or path.is_symlink():
        raise QualificationError("qualification artifact must be a regular file")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wheel_metadata(wheel: Path) -> tuple[set[str], tuple[str, ...], str]:
    """Read direct dependency names, resources, and version from the wheel."""
    with zipfile.ZipFile(wheel) as archive:
        names = tuple(archive.namelist())
        metadata_names = [
            name
            for name in names
            if name.endswith(".dist-info/METADATA") and "/" in name
        ]
        if len(metadata_names) != 1:
            raise QualificationError("wheel must contain exactly one METADATA")
        metadata = Parser().parsestr(
            archive.read(metadata_names[0]).decode("utf-8", errors="strict")
        )
    dependencies: set[str] = set()
    for requirement in metadata.get_all("Requires-Dist", []):
        name = re.split(r"[ <>=!~;\[]", requirement, maxsplit=1)[0]
        dependencies.add(name.lower().replace("_", "-"))
    version = metadata.get("Version")
    if not version:
        raise QualificationError("wheel version metadata is missing")
    resources = tuple(
        prefix
        for prefix in RESOURCE_PREFIXES
        if any(name.startswith(prefix) and not name.endswith("/") for name in names)
    )
    return dependencies, resources, version


def validate_lock(lock: Path, required: set[str]) -> set[str]:
    """Require hash-locked exact runtime requirements covering direct deps."""
    text = lock.read_text(encoding="utf-8")
    if "-e " in text or "--editable" in text or " @ " in text:
        raise QualificationError("runtime lock cannot contain editable or URL installs")
    logical = text.replace("\\\n", " ")
    locked: set[str] = set()
    for raw in logical.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "--")):
            continue
        match = re.match(r"([A-Za-z0-9_.-]+)==([^\s]+)", line)
        if match is None or "--hash=sha256:" not in line:
            raise QualificationError("runtime lock entries must be exact and hashed")
        name = match.group(1).lower().replace("_", "-")
        if name in FORBIDDEN_LOCK_NAMES:
            raise QualificationError(f"forbidden deployment dependency: {name}")
        locked.add(name)
    missing = required - locked
    if missing:
        raise QualificationError(
            "runtime lock misses wheel dependencies: " + ",".join(sorted(missing))
        )
    return locked


def stage_context(
    root: Path,
    dockerfile: Path,
    wheel: Path,
    lock: Path,
) -> Path:
    """Stage only recipe, lock, and exact wheel beneath a fresh directory."""
    context = root / "build-context"
    context.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(dockerfile, context / "Dockerfile")
    shutil.copyfile(lock, context / "runtime-requirements.txt")
    shutil.copyfile(wheel, context / "msgloom.whl")
    ignore = dockerfile.with_name("Dockerfile.dockerignore")
    if not ignore.is_file():
        raise QualificationError("Dockerfile-specific ignore file is missing")
    shutil.copyfile(ignore, context / "Dockerfile.dockerignore")
    return context


def container_probe_code() -> str:
    """Return the import/resource/native probe run with networking disabled."""
    return r"""
import importlib
import importlib.metadata
import importlib.resources
import json
import platform
import socket
import subprocess
import threading

def blocked(*args, **kwargs):
    raise RuntimeError("import attempted process or network startup")

subprocess.Popen = blocked
socket.socket.connect = blocked
threads = {item.ident for item in threading.enumerate()}
for name in ("msgloom", "message_ingest", "microsoft_graph"):
    importlib.import_module(name)
for name in ("openpyxl", "pypdfium2", "docx", "python_calamine", "lxml"):
    importlib.import_module(name)
if threads != {item.ident for item in threading.enumerate()}:
    raise RuntimeError("import started a background thread")
dist = importlib.metadata.distribution("msgloom")
eps = sorted(ep.name for ep in dist.entry_points if ep.group == "console_scripts")
resources = {}
root = importlib.resources.files("msgloom")
for name in ("templates", "prompts", "migrations"):
    item = root.joinpath(name)
    resources[name] = item.is_dir() and any(item.iterdir())
print(json.dumps({
    "architecture": platform.machine(),
    "os": platform.system(),
    "platform": platform.platform(),
    "python": platform.python_version(),
    "version": dist.version,
    "entry_points": eps,
    "resources": resources,
}))
"""


def entrypoint_help_probe_code() -> str:
    """Return an in-process help probe that blocks startup side effects."""
    return r"""
import importlib.metadata
import socket
import subprocess
import sys
import threading

def blocked(*args, **kwargs):
    raise RuntimeError("help attempted process or network startup")

subprocess.Popen = blocked
socket.socket.connect = blocked
threads = {item.ident for item in threading.enumerate()}
entries = [
    ep for ep in importlib.metadata.distribution("msgloom").entry_points
    if ep.group == "console_scripts" and ep.name == "msgloom"
]
if len(entries) != 1:
    raise RuntimeError("installed msgloom entrypoint is not unique")
entry = entries[0].load()
sys.argv = ["msgloom", "--help"]
try:
    entry()
except SystemExit as exc:
    if exc.code not in (None, 0):
        raise
if threads != {item.ident for item in threading.enumerate()}:
    raise RuntimeError("help started a background thread")
print("entrypoint-help-ok")
"""


def persistence_probe_code(expect_existing: bool) -> str:
    """Return a real Phase1Persistence open/close restart probe."""
    return f"""
import asyncio
from pathlib import Path
from msgloom.persistence import Phase1Persistence

path = Path("/var/lib/msgloom/qualification.sqlite3")
if {expect_existing!r} and not path.is_file():
    raise RuntimeError("persistent SQLite file missing after restart")

async def main():
    store = await Phase1Persistence.open(
        "sqlite:////var/lib/msgloom/qualification.sqlite3"
    )
    await store.close()

asyncio.run(main())
print("persistence-ok")
"""


def parser_probe_code() -> str:
    """Return a synthetic text parse through the reviewed parser API."""
    return r"""
import asyncio
import hashlib
from msgloom.preparation import (
    DocumentFormat, ParserConfig, ParserLimits, ParserRequest, SavedByteReference
)
from msgloom.preparation.isolation import parse_isolated
from msgloom.preparation.isolation.registry import PRODUCTION_REGISTRY

content = b"synthetic deployment parser probe"
entry = PRODUCTION_REGISTRY.resolve(DocumentFormat.TEXT)
request = ParserRequest(
    source=SavedByteReference(
        reference="blob:synthetic-deployment",
        sha256=hashlib.sha256(content).hexdigest(),
        byte_count=len(content),
    ),
    detected_format=DocumentFormat.TEXT,
    parser=entry.identity,
    config=ParserConfig(profile="deployment-preflight", settings=()),
    limits=ParserLimits(10.0, 268435456, 1048576, 65536, 64),
)
result = asyncio.run(parse_isolated(request, content))
if not result.blocks:
    raise RuntimeError("synthetic parser returned no blocks")
print("parser-isolation-ok")
"""


def ai_probe_code() -> str:
    """Return offline SDK/CLI startup through the reviewed sandbox constructor."""
    return r"""
import json
import subprocess
import sys
import sysconfig
from pathlib import Path
import claude_agent_sdk
from msgloom.ai import RuntimeIsolation
from msgloom.ai.sandbox import build_sandbox_command

site = Path(sysconfig.get_path("purelib"))
cli = site / "claude_agent_sdk" / "_bundled" / "claude"
worker = Path("/tmp/msgloom-ai-offline.py")
worker.write_text(
    "import json,subprocess\n"
    "from pathlib import Path\n"
    "import claude_agent_sdk\n"
    "cli=Path(claude_agent_sdk.__file__).parent/'_bundled'/'claude'\n"
    "p=subprocess.run([str(cli),'--version'],capture_output=True,text=True,timeout=10)\n"
    "print(json.dumps({'rc':p.returncode,'version':bool(p.stdout.strip())}))\n"
)
state = Path("/var/lib/msgloom/ai-state")
work = Path("/var/lib/msgloom/ai-work")
state.mkdir(exist_ok=True)
work.mkdir(exist_ok=True)
runtime = RuntimeIsolation(
    Path(sys.executable),
    Path("/usr/bin/bwrap"),
    tuple(
        dict.fromkeys(
            (Path(sys.prefix), Path("/usr/local"), Path("/usr"), Path("/lib"))
        )
    ),
    cli,
    {},
    Path("/var/lib/msgloom"),
    0.2,
)
env = {
    "HOME": "/state",
    "CLAUDE_CONFIG_DIR": "/state/claude",
    "XDG_CONFIG_HOME": "/state/config",
    "XDG_CACHE_HOME": "/state/cache",
    "TMPDIR": "/tmp",
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "PYTHONNOUSERSITE": "1",
}
p = subprocess.run(
    build_sandbox_command(runtime, worker, state, work),
    capture_output=True,
    text=True,
    timeout=20,
    env=env,
)
if p.returncode:
    raise RuntimeError("offline AI sandbox startup failed")
value = json.loads(p.stdout)
if value != {"rc": 0, "version": True}:
    raise RuntimeError("offline SDK/CLI version probe failed")
print("ai-isolation-ok")
"""


def docker_run_argv(
    image: str,
    name: str,
    volume: str,
    code: str,
    seccomp_profile: Path | None,
) -> list[str]:
    """Build the common least-privilege container invocation."""
    command = [
        "docker",
        "run",
        "--rm",
        "--name",
        name,
        "--network",
        "none",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,nosuid,nodev,size=64m",
        "--security-opt",
        "no-new-privileges",
        "--cap-drop",
        "ALL",
        "--mount",
        f"type=volume,src={volume},dst=/var/lib/msgloom",
    ]
    if seccomp_profile is not None:
        if seccomp_profile.name == "unconfined":
            raise QualificationError("unconfined seccomp is forbidden")
        command.extend(["--security-opt", f"seccomp={seccomp_profile}"])
    command.extend([image, "python", "-I", "-c", code])
    return command


def evidence_json(
    checks: list[Check],
    *,
    target: Target,
    image_id: str,
    wheel_hash: str,
    wheel_version: str,
    platform_data: dict[str, object],
) -> dict[str, object]:
    """Assemble exact bounded evidence for one target."""
    return {
        "python_target": target.python,
        "base_image": target.base_image,
        "image_id": image_id,
        "image_digest": image_id,
        "wheel_sha256": wheel_hash,
        "wheel_version": wheel_version,
        "platform": platform_data,
        "checks": [asdict(check) for check in checks],
    }


def unique_name(prefix: str) -> str:
    """Return an invocation-owned Docker object name."""
    return f"msgloom-qual-{prefix}-{uuid4().hex[:12]}"
