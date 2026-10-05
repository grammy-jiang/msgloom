"""Own one qualification gate with a Linux cgroup-v2 boundary."""

from __future__ import annotations

import argparse
import ctypes
import os
import select
import signal
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path

_CGROUP_ROOT = Path("/sys/fs/cgroup")
_PR_SET_CHILD_SUBREAPER = 36
_PR_GET_CHILD_SUBREAPER = 37


@dataclass(frozen=True)
class ProcessIdentity:
    """Bind PID, session, process group and start time for safe signaling."""

    pid: int
    process_group: int
    session: int
    start_time: int


@dataclass(frozen=True)
class CleanupReport:
    """Describe owned processes seen before and after bounded cleanup."""

    initial: tuple[ProcessIdentity, ...]
    remaining: tuple[ProcessIdentity, ...]

    def initial_json(self) -> list[dict[str, int]]:
        """Return manifest-safe initial identities."""
        return [asdict(item) for item in self.initial]

    def remaining_json(self) -> list[dict[str, int]]:
        """Return manifest-safe remaining identities."""
        return [asdict(item) for item in self.remaining]


def _stat_identity(pid: int) -> ProcessIdentity | None:
    """Read one PID identity from procfs with kernel start-time safety."""
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return ProcessIdentity(
            pid=pid,
            process_group=int(fields[2]),
            session=int(fields[3]),
            start_time=int(fields[19]),
        )
    except (OSError, ValueError, IndexError):
        return None


def _current_cgroup() -> Path:
    """Resolve this process's unified cgroup-v2 directory."""
    for line in Path("/proc/self/cgroup").read_text().splitlines():
        hierarchy, _controllers, relative = line.split(":", 2)
        if hierarchy == "0":
            path = (_CGROUP_ROOT / relative.lstrip("/")).resolve()
            if not (path / "cgroup.controllers").is_file():
                raise OSError("unified cgroup-v2 control files are unavailable")
            return path
    raise OSError("process is not attached to a unified cgroup-v2 hierarchy")


def _rmdir_tree(path: Path) -> None:
    """Remove empty nested cgroups deepest-first, then the gate cgroup."""
    directories = [entry for entry in path.rglob("*") if entry.is_dir()]
    for directory in sorted(
        directories, key=lambda item: len(item.parts), reverse=True
    ):
        directory.rmdir()
    path.rmdir()


def check_supported() -> None:
    """Fail closed unless this host delegates a writable cgroup-v2 child."""
    parent = _current_cgroup()
    probe = parent / f"msgloom-boundary-probe-{os.getpid()}"
    try:
        probe.mkdir()
        if not (probe / "cgroup.kill").exists():
            raise OSError("cgroup.kill is unavailable for the delegated hierarchy")
    finally:
        if probe.exists():
            _rmdir_tree(probe)


def create(name: str) -> Path:
    """Create a fresh gate cgroup below the runner's delegated cgroup."""
    parent = _current_cgroup()
    boundary = parent / f"msgloom-gate-{os.getpid()}-{name}"
    boundary.mkdir()
    if not (boundary / "cgroup.kill").exists():
        _rmdir_tree(boundary)
        raise OSError("cgroup.kill is unavailable for the gate boundary")
    return boundary


def wrapped_command(
    boundary: Path, command: tuple[str, ...], ready_fd: int
) -> tuple[str, ...]:
    """Wrap a gate so it enters the cgroup before executing user code."""
    return (
        sys.executable,
        str(Path(__file__).resolve()),
        "--enter",
        str(boundary),
        "--ready-fd",
        str(ready_fd),
        "--",
        *command,
    )


def wait_ready(read_fd: int, process: subprocess.Popen, timeout: float = 5) -> None:
    """Require cgroup admission before the gate command can execute."""
    readable, _, _ = select.select([read_fd], [], [], timeout)
    if not readable:
        raise OSError("gate cgroup admission timed out")
    marker = os.read(read_fd, 1)
    if marker != b"1":
        process.poll()
        raise OSError("gate failed before cgroup ownership was established")


def _all_members(boundary: Path) -> tuple[ProcessIdentity, ...]:
    """Return every process identity in the gate cgroup subtree."""
    identities: dict[tuple[int, int], ProcessIdentity] = {}
    files = [boundary / "cgroup.procs", *boundary.rglob("cgroup.procs")]
    for path in files:
        try:
            pids = path.read_text().split()
        except OSError:
            continue
        for value in pids:
            identity = _stat_identity(int(value))
            if identity is not None:
                identities[(identity.pid, identity.start_time)] = identity
    return tuple(sorted(identities.values(), key=lambda item: item.pid))


def _still_owned(boundary: Path, identity: ProcessIdentity) -> bool:
    """Revalidate PID identity and cgroup ownership before signaling."""
    current = _stat_identity(identity.pid)
    if current != identity:
        return False
    try:
        cgroups = Path(f"/proc/{identity.pid}/cgroup").read_text().splitlines()
    except OSError:
        return False
    relative = "/" + str(boundary.relative_to(_CGROUP_ROOT))
    for line in cgroups:
        location = line.split(":", 2)[-1]
        if location == relative or location.startswith(relative + "/"):
            return True
    return False


def _signal_members(
    boundary: Path,
    members: tuple[ProcessIdentity, ...],
    sig: signal.Signals,
) -> None:
    """Signal only identities still proven inside the gate cgroup subtree."""
    for identity in members:
        if not _still_owned(boundary, identity):
            continue
        try:
            os.kill(identity.pid, sig)
        except ProcessLookupError:
            pass


def _reap_known(
    members: tuple[ProcessIdentity, ...],
    *,
    exclude_pid: int | None = None,
) -> None:
    """Reap only recorded descendants that the runner subreaper now owns."""
    for identity in members:
        if identity.pid == exclude_pid or _stat_identity(identity.pid) != identity:
            continue
        try:
            os.waitpid(identity.pid, os.WNOHANG)
        except ChildProcessError:
            continue


def _wait_empty(
    boundary: Path,
    timeout: float,
    process: subprocess.Popen,
) -> tuple[ProcessIdentity, ...]:
    """Wait boundedly for the cgroup subtree to become unpopulated."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        process.poll()
        members = _all_members(boundary)
        _reap_known(members, exclude_pid=process.pid)
        members = _all_members(boundary)
        if not members:
            return ()
        time.sleep(0.01)
    return _all_members(boundary)


def cleanup(boundary: Path, process: subprocess.Popen) -> CleanupReport:
    """Terminate owned processes, reap children, and remove the boundary."""
    initial = _all_members(boundary)
    if initial:
        _signal_members(boundary, initial, signal.SIGTERM)
        remaining = _wait_empty(boundary, 1, process)
        if remaining:
            (boundary / "cgroup.kill").write_text("1")
            remaining = _wait_empty(boundary, 5, process)
    else:
        remaining = ()
    if process.poll() is None:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            (boundary / "cgroup.kill").write_text("1")
            process.wait(timeout=5)
    _reap_known(initial, exclude_pid=process.pid)
    remaining = _all_members(boundary)
    if not remaining:
        _rmdir_tree(boundary)
    return CleanupReport(initial=initial, remaining=remaining)


def discard_empty(boundary: Path | None) -> None:
    """Remove an unused gate boundary without touching populated cgroups."""
    if boundary is not None and boundary.exists() and not _all_members(boundary):
        _rmdir_tree(boundary)


@contextmanager
def child_subreaper() -> Iterator[None]:
    """Reparent orphaned gate descendants here for bounded reaping."""
    libc = ctypes.CDLL(None, use_errno=True)
    previous = ctypes.c_int()
    if libc.prctl(_PR_GET_CHILD_SUBREAPER, ctypes.byref(previous), 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "PR_GET_CHILD_SUBREAPER failed")
    if libc.prctl(_PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "PR_SET_CHILD_SUBREAPER failed")
    try:
        yield
    finally:
        libc.prctl(_PR_SET_CHILD_SUBREAPER, previous.value, 0, 0, 0)


def _enter(boundary: Path, ready_fd: int, command: list[str]) -> int:
    """Move this wrapper into the gate cgroup, acknowledge, then exec."""
    try:
        (boundary / "cgroup.procs").write_text("0")
        os.write(ready_fd, b"1")
        os.close(ready_fd)
        os.execvpe(command[0], command, os.environ)
    except FileNotFoundError as exc:
        print(f"unavailable executable: {exc}", file=sys.stderr)
        return 69
    except OSError as exc:
        print(f"gate cgroup entry failed: {exc}", file=sys.stderr)
        return 70
    return 70


def main() -> int:
    """Internal no-shell cgroup admission wrapper used by the gate runner."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--enter", type=Path, required=True)
    parser.add_argument("--ready-fd", type=int, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("a command is required")
    return _enter(args.enter, args.ready_fd, command)


if __name__ == "__main__":
    raise SystemExit(main())
