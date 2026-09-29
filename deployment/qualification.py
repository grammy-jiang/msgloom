"""Runtime probes and evidence helpers for container qualification."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal
from uuid import uuid4

from deployment.process import CommandResult, Runner
from deployment.release import (
    Target,
    WheelMetadata,
    required_dependencies,
    sha256_file,
    stage_context,
    validate_lock,
    validate_resource_specs,
    validate_resources,
    validate_seccomp_profile,
    validate_targets,
    wheel_metadata,
)

COMMAND_TIMEOUT_SECONDS = 300
OUTPUT_LIMIT = 1600
CONTAINER_MEMORY = "2g"
CONTAINER_CPUS = "2.0"
CONTAINER_PIDS = "256"
_SECRET = re.compile(
    r"(?i)(authorization|bearer|password|secret|token|api[_-]?key)"
    r"([=: ]+)([^\s,;]+)"
)
_PATH = re.compile(r"(?<![A-Za-z0-9_.-])/(?:[^\s'\"]+)")


class QualificationError(RuntimeError):
    """Report a finite deployment qualification failure."""


@dataclass(frozen=True, slots=True)
class Check:
    """Bounded machine-readable evidence for one qualification gate."""

    name: str
    status: Literal["pass", "fail", "pending"]
    detail: str


def sanitize(value: str) -> str:
    """Redact likely paths and credential-shaped values, then bound output."""
    redacted = _SECRET.sub(r"\1\2<redacted>", value)
    redacted = _PATH.sub("<path>", redacted)
    redacted = redacted.replace("\x00", "")
    return redacted[-OUTPUT_LIMIT:]


def container_probe_code(expected_resources: tuple[str, ...]) -> str:
    """Return the import/resource/native probe run with networking disabled."""
    return f"""
import importlib
import importlib.metadata
import importlib.resources
import json
import platform
import socket
import subprocess
import threading

expected_resources = {expected_resources!r}
def blocked(*args, **kwargs):
    raise RuntimeError("import attempted process or network startup")

subprocess.Popen = blocked
socket.socket.connect = blocked
threads = {{item.ident for item in threading.enumerate()}}
for name in ("msgloom", "message_ingest", "microsoft_graph"):
    importlib.import_module(name)
for name in ("openpyxl", "pypdfium2", "docx", "python_calamine", "lxml"):
    importlib.import_module(name)
if threads != {{item.ident for item in threading.enumerate()}}:
    raise RuntimeError("import started a background thread")
dist = importlib.metadata.distribution("msgloom")
eps = sorted(ep.name for ep in dist.entry_points if ep.group == "console_scripts")
resources = {{}}
for value in expected_resources:
    package, resource = value.split(":", 1)
    resources[value] = importlib.resources.files(package).joinpath(resource).is_file()
print(json.dumps({{
    "architecture": platform.machine(),
    "os": platform.system(),
    "platform": platform.platform(),
    "python": platform.python_version(),
    "version": dist.version,
    "entry_points": eps,
    "resources": resources,
}}))
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
    config=ParserConfig(profile="mime-html-v1", settings=()),
    limits=ParserLimits(10.0, 268435456, 1048576, 65536, 64),
)
result = asyncio.run(parse_isolated(request, content))
if not result.blocks:
    raise RuntimeError("synthetic parser returned no blocks")
print("parser-isolation-ok")
"""


def ai_probe_code(storage_root: str = "/var/lib/msgloom") -> str:
    """Return offline SDK/CLI startup through the reviewed sandbox constructor."""
    template = r"""
import json
import subprocess
import sys
import sysconfig
from pathlib import Path
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
root = Path(__STORAGE_ROOT__)
root.mkdir(parents=True, exist_ok=True)
state = root / "ai-state"
work = root / "ai-work"
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
    root,
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
    return template.replace("__STORAGE_ROOT__", repr(storage_root))


def docker_run_argv(
    image: str,
    name: str,
    volume: str,
    code: str,
    seccomp_profile: Path | None,
) -> list[str]:
    """Build one finite least-privilege container invocation."""
    command = [
        "docker",
        "run",
        "--rm",
        "--name",
        name,
        "--network",
        "none",
        "--read-only",
        "--memory",
        CONTAINER_MEMORY,
        "--memory-swap",
        CONTAINER_MEMORY,
        "--cpus",
        CONTAINER_CPUS,
        "--pids-limit",
        CONTAINER_PIDS,
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


__all__ = [
    "Check",
    "CommandResult",
    "QualificationError",
    "Runner",
    "Target",
    "WheelMetadata",
    "ai_probe_code",
    "container_probe_code",
    "docker_run_argv",
    "entrypoint_help_probe_code",
    "evidence_json",
    "parser_probe_code",
    "persistence_probe_code",
    "required_dependencies",
    "sanitize",
    "sha256_file",
    "stage_context",
    "unique_name",
    "validate_lock",
    "validate_resource_specs",
    "validate_resources",
    "validate_seccomp_profile",
    "validate_targets",
    "wheel_metadata",
]
