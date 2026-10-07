"""
Execute a fixed gate plan once and retain fail-closed evidence.

Commands run serially without a shell or retries. Each attempt gets separate
stdout/stderr files. The manifest is saved before launch and after every gate;
a killed runner therefore leaves running/not-run evidence, never success.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import signal
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from . import process_boundary
from .evidence import inspect_artifacts

EXTERNAL_REVIEW = {
    "status": "required",
    "model": "GPT-6 Astra/max",
    "scope": "independent full original-base to exact-candidate review",
}


@dataclass(frozen=True)
class Gate:
    """Describe one immutable command and its evidence requirements."""

    name: str
    command: tuple[str, ...]
    timeout: float = 3600
    dependencies: tuple[str, ...] = ()
    env: tuple[tuple[str, str], ...] = ()
    junit: str | None = None
    coverage: str | None = None
    contracts: bool = False
    runtime: bool = False
    required_artifacts: tuple[str, ...] = ()
    unavailable: str | None = None


def _now() -> str:
    return datetime.now(UTC).isoformat()


def git(root: Path, *args: str) -> str:
    """Read candidate state with a bounded Git invocation."""
    return subprocess.check_output(
        ["git", "-C", str(root), *args],
        text=True,
        stderr=subprocess.PIPE,
        timeout=30,
    ).strip()


def lock_path(root: Path) -> Path:
    """Share one advisory lock across worktrees of the same repository."""
    common = git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    digest = hashlib.sha256(common.encode()).hexdigest()[:24]
    return Path("/tmp") / f"msgloom-handoff-{digest}.lock"


def _bound(root: Path, candidate: str) -> bool:
    return git(root, "rev-parse", "HEAD") == candidate and not git(
        root, "status", "--porcelain", "--untracked-files=all"
    )


def save_manifest(output: Path, result: dict) -> None:
    """Atomically replace the manifest after flushing its durable contents."""
    staging = output / "manifest.tmp"
    with staging.open("w") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    staging.replace(output / "manifest.json")


def environment(root: Path, runtime: Path, gate: Gate) -> dict[str, str]:
    """Keep executable discovery while excluding inherited secrets/addopts."""
    runtime.mkdir(parents=True, exist_ok=True)
    env = {
        key: os.environ[key] for key in ("PATH", "LANG", "LC_ALL") if key in os.environ
    }
    env.update(
        {
            "PYTHONPATH": str(root),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1",
            "XDG_CACHE_HOME": str(runtime / "cache"),
            "RUFF_CACHE_DIR": str(runtime / "ruff-cache"),
            "XDG_CONFIG_HOME": str(runtime / "config"),
            "XDG_DATA_HOME": str(runtime / "data"),
            "XDG_STATE_HOME": str(runtime / "state"),
            "TMPDIR": str(runtime),
            "PRE_COMMIT_HOME": str(runtime / "pre-commit-home"),
            "UV_OFFLINE": "1",
            "UV_NO_SYNC": "1",
            "UV_PYTHON_DOWNLOADS": "never",
            "MSGLOOM_DATA_DIR": str(runtime / "acquisition"),
            "MSGLOOM_RAW_EVIDENCE_DIR": str(runtime / "raw"),
            "MSGLOOM_DATABASE_URL": f"sqlite:///{runtime / 'catalog.sqlite3'}",
            "MSGLOOM_MS_TOKEN_CACHE": str(runtime / "unused-token-cache.json"),
            "MSGLOOM_MS_ALLOW_INTERACTIVE_AUTH": "0",
        }
    )
    env.update(gate.env)
    return env


def _execute(
    root: Path,
    output: Path,
    gate: Gate,
    record: dict,
    manifest: dict,
) -> None:
    directory = output / gate.name
    directory.mkdir()
    stdout = directory / "stdout.log"
    stderr = directory / "stderr.log"
    record.update(stdout=str(stdout), stderr=str(stderr), attempts=1)
    save_manifest(output, manifest)
    process = None
    boundary = None
    started = time.monotonic()
    try:
        with stdout.open("wb") as out, stderr.open("wb") as err:
            env = environment(root, directory / "runtime", gate)
            if coverage_file := env.get("COVERAGE_FILE"):
                Path(coverage_file).parent.mkdir(parents=True, exist_ok=True)
            boundary = process_boundary.create(gate.name)
            record["ownership_boundary"] = {
                "kind": "cgroup_v2",
                "path": str(boundary),
            }
            ready_read, ready_write = os.pipe()
            release_read = release_write = -1
            try:
                release_read, release_write = os.pipe()
                command = process_boundary.wrapped_command(
                    boundary, gate.command, ready_write, release_read
                )
                process = subprocess.Popen(
                    command,
                    cwd=root,
                    env=env,
                    stdout=out,
                    stderr=err,
                    start_new_session=True,
                    pass_fds=(ready_write, release_read),
                )
                os.close(ready_write)
                ready_write = -1
                os.close(release_read)
                release_read = -1
                process_boundary.wait_ready(ready_read, process)
                record["pid"] = process.pid
                save_manifest(output, manifest)
                # Only published linkage permits user code. Closing the pipe
                # on any failure (or recorder death) denies admission.
                os.write(release_write, b"1")
            finally:
                os.close(ready_read)
                for descriptor in (ready_write, release_read, release_write):
                    if descriptor >= 0:
                        os.close(descriptor)
            record["exit_code"] = process_boundary.wait(boundary, process, gate.timeout)
            record["status"] = (
                "passed"
                if process.returncode == 0
                else "unavailable"
                if process.returncode == 69
                else "interrupted"
                if process.returncode < 0
                else "failed"
            )
            cleanup = process_boundary.cleanup(boundary, process)
            if cleanup.initial:
                record["owned_survivors"] = cleanup.initial_json()
                reason = "gate parent exited with surviving owned descendants"
                if cleanup.remaining:
                    record["cleanup_remaining"] = cleanup.remaining_json()
                    reason += "; cleanup incomplete"
                record.update(status="failed", hard_stop=True, reason=reason)
    except FileNotFoundError as exc:
        record.update(status="unavailable", reason=str(exc))
        if process is not None and boundary is not None:
            cleanup = process_boundary.cleanup(boundary, process)
            record["exit_code"] = process.returncode
            if cleanup.remaining:
                record["hard_stop"] = True
                record["cleanup_remaining"] = cleanup.remaining_json()
    except subprocess.TimeoutExpired:
        record.update(status="timed_out", reason="gate timeout; no retry")
        if process is not None and boundary is not None:
            cleanup = process_boundary.cleanup(boundary, process)
            record["exit_code"] = process.returncode
            if cleanup.initial:
                record["owned_on_timeout"] = cleanup.initial_json()
            if cleanup.remaining:
                record["hard_stop"] = True
                record["cleanup_remaining"] = cleanup.remaining_json()
                record["reason"] += "; cleanup incomplete"
    except KeyboardInterrupt:
        record.update(status="interrupted", reason="runner interrupted")
        if process is not None and boundary is not None:
            cleanup = process_boundary.cleanup(boundary, process)
            record["exit_code"] = process.returncode
            if cleanup.initial:
                record["owned_on_interrupt"] = cleanup.initial_json()
            if cleanup.remaining:
                record["hard_stop"] = True
                record["cleanup_remaining"] = cleanup.remaining_json()
                record["reason"] += "; cleanup incomplete"
    except OSError as exc:
        record.update(status="failed", hard_stop=True, reason=str(exc))
        if process is not None and boundary is not None:
            cleanup = process_boundary.cleanup(boundary, process)
            record["exit_code"] = process.returncode
            if cleanup.remaining:
                record["cleanup_remaining"] = cleanup.remaining_json()
    finally:
        process_boundary.discard_empty(boundary)
        record["duration_seconds"] = round(time.monotonic() - started, 3)
        record["finished_at"] = _now()
        inspect_artifacts(gate, record, root)


def _preflight(root: Path, base: str, candidate: str) -> None:
    for value in (base, candidate):
        if not re.fullmatch(r"[0-9a-f]{40}", value):
            raise ValueError("base and candidate must be exact 40-character SHAs")
    if git(root, "rev-parse", "--show-toplevel") != str(root):
        raise ValueError("source root must be the repository root")
    if not _bound(root, candidate):
        raise ValueError("candidate HEAD mismatch or non-clean worktree")
    process_boundary.check_supported()
    subprocess.run(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", base, candidate],
        check=True,
        timeout=30,
        capture_output=True,
    )


def competing_tests() -> list[int]:
    """Detect existing pytest/tox processes without reading credentials."""
    ancestors = {os.getpid()}
    pid = os.getppid()
    while pid > 1:
        ancestors.add(pid)
        try:
            pid = int(
                Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[1]
            )
        except (OSError, ValueError, IndexError):
            break
    matches = []
    for path in Path("/proc").glob("[0-9]*/cmdline"):
        pid = int(path.parent.name)
        if pid in ancestors:
            continue
        try:
            args = path.read_bytes().split(b"\0")
            if any(
                Path(os.fsdecode(arg)).name in {"pytest", "py.test", "tox"}
                for arg in args[:4]
            ):
                matches.append(pid)
        except OSError:
            continue
    return matches


def run_plan(
    root: Path,
    output: Path,
    base: str,
    candidate: str,
    gates: list[Gate],
    *,
    guard_host: bool = False,
) -> dict:
    """Record one invocation; external review always remains outstanding."""
    root, output = root.resolve(), output.resolve()
    if output == root or root in output.parents:
        raise ValueError("evidence must be outside the candidate checkout")
    names = [gate.name for gate in gates]
    if not gates or len(set(names)) != len(names):
        raise ValueError("a nonempty plan with unique gates is required")
    seen = set()
    for gate in gates:
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", gate.name):
            raise ValueError("unsafe gate name")
        if not gate.command or gate.timeout <= 0:
            raise ValueError("gate command and positive timeout are required")
        if not set(gate.dependencies) <= seen:
            raise ValueError("gate dependencies must precede the gate")
        seen.add(gate.name)
    output.mkdir(parents=True, exist_ok=False)
    result = {
        "schema_version": 1,
        "base_sha": base,
        "candidate_sha": candidate,
        "source_root": str(root),
        "started_at": _now(),
        "finished_at": None,
        "status": "running",
        "qualification_status": "blocked",
        "external_review": dict(EXTERNAL_REVIEW),
        "versions": {},
        "gates": [
            {
                **json.loads(json.dumps(asdict(gate))),
                "command": list(gate.command),
                "status": "not_run",
                "started_at": None,
                "finished_at": None,
                "exit_code": None,
                "stdout": None,
                "stderr": None,
                "attempts": 0,
                "hard_stop": False,
                "artifacts": [],
            }
            for gate in gates
        ],
    }
    save_manifest(output, result)
    previous_handler = signal.getsignal(signal.SIGTERM)

    def interrupt(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupt)
    try:
        _preflight(root, base, candidate)
        with (
            process_boundary.child_subreaper(),
            lock_path(root).open("a") as lock,
        ):
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            for gate, record in zip(gates, result["gates"], strict=True):
                if not _bound(root, candidate):
                    result["status"] = "candidate_changed"
                    break
                if guard_host and (busy := competing_tests()):
                    result.update(status="blocked", reason=f"active test PIDs: {busy}")
                    break
                statuses = {item["name"]: item["status"] for item in result["gates"]}
                if gate.unavailable:
                    record.update(status="unavailable", reason=gate.unavailable)
                elif any(statuses[name] != "passed" for name in gate.dependencies):
                    record.update(status="blocked", reason="prerequisite not passed")
                else:
                    record.update(status="running", started_at=_now())
                    save_manifest(output, result)
                    _execute(root, output, gate, record, result)
                    if gate.runtime and record["status"] == "passed":
                        result["versions"][gate.name] = json.loads(
                            Path(record["stdout"]).read_text(),
                        )
                save_manifest(output, result)
                if not _bound(root, candidate):
                    result["status"] = "candidate_changed"
                    break
                if record.get("hard_stop"):
                    result["status"] = "failed"
                    break
                if record["status"] in {"interrupted", "timed_out"}:
                    result["status"] = "interrupted"
                    break
            if result["status"] == "running":
                result["status"] = (
                    "automated_passed"
                    if all(r["status"] == "passed" for r in result["gates"])
                    else "failed"
                )
    except KeyboardInterrupt:
        result.update(status="interrupted", reason="interrupted between gates")
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        result.update(status="blocked", reason=str(exc))
    finally:
        signal.signal(signal.SIGTERM, previous_handler)
        result["finished_at"] = _now()
        try:
            result["observed_head_after"] = git(root, "rev-parse", "HEAD")
            result["observed_status_after"] = git(root, "status", "--porcelain")
            if result["status"] == "automated_passed" and not _bound(root, candidate):
                result["status"] = "candidate_changed"
        except (OSError, subprocess.SubprocessError):
            result["status"] = "blocked"
        save_manifest(output, result)
    return result
