"""Bounded subprocess execution for deployment qualification."""

from __future__ import annotations

import os
import selectors
import signal
import subprocess
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

OUTPUT_LIMIT = 1600
_READ_CHUNK = 4096
_RAW_TAIL_LIMIT = OUTPUT_LIMIT * 4
_TERMINATION_GRACE_SECONDS = 0.2
_DRAIN_GRACE_SECONDS = 0.2
_CLEANUP_TIMEOUT_SECONDS = 15
_SELECT_SLICE_SECONDS = 0.05
_READ_BURST_CHUNKS = 16


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Sanitized bounded command evidence."""

    returncode: int
    output: str
    timed_out: bool = False
    cleanup_errors: tuple[str, ...] = ()


def _tail_append(chunks: deque[bytes], size: int, value: bytes) -> int:
    """Append bytes while retaining only a finite tail."""
    chunks.append(value)
    size += len(value)
    while size > _RAW_TAIL_LIMIT and chunks:
        first = chunks[0]
        excess = size - _RAW_TAIL_LIMIT
        if excess < len(first):
            chunks[0] = first[excess:]
            return _RAW_TAIL_LIMIT
        chunks.popleft()
        size -= len(first)
    return size


def _deadline_after(timeout: float) -> float:
    """Return the absolute production lifetime deadline."""
    return time.monotonic() + timeout


def _group_exists(pgid: int) -> bool:
    """Return whether the invocation-owned process group still exists."""
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _signal_group(pgid: int, sig: signal.Signals) -> None:
    """Signal only the process group created for this invocation."""
    try:
        os.killpg(pgid, sig)
    except ProcessLookupError:
        pass


def _wait_owned_group(
    process: subprocess.Popen[bytes],
    deadline: float,
) -> bool:
    """Wait only until the deadline for leader and owned group exit."""
    while time.monotonic() < deadline:
        leader_done = process.poll() is not None
        if leader_done and not _group_exists(process.pid):
            return True
        time.sleep(min(_SELECT_SLICE_SECONDS, max(deadline - time.monotonic(), 0)))
    return process.poll() is not None and not _group_exists(process.pid)


def _terminate_group(process: subprocess.Popen[bytes]) -> None:
    """Terminate and reap one invocation-owned host process group."""
    _signal_group(process.pid, signal.SIGTERM)
    grace = time.monotonic() + _TERMINATION_GRACE_SECONDS
    if not _wait_owned_group(process, grace):
        _signal_group(process.pid, signal.SIGKILL)
        kill_deadline = time.monotonic() + _TERMINATION_GRACE_SECONDS
        _wait_owned_group(process, kill_deadline)
    if process.poll() is None:
        try:
            process.wait(timeout=_TERMINATION_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            _signal_group(process.pid, signal.SIGKILL)
            try:
                process.wait(timeout=_TERMINATION_GRACE_SECONDS)
            except subprocess.TimeoutExpired:
                return


def _cleanup_after_interrupt(process: subprocess.Popen[bytes]) -> None:
    """Best-effort idempotent cleanup while preserving caller cancellation."""
    try:
        _terminate_group(process)
    except (Exception, KeyboardInterrupt):  # noqa: BLE001 - lifecycle cleanup
        try:
            _signal_group(process.pid, signal.SIGKILL)
        except (Exception, KeyboardInterrupt):  # noqa: BLE001 - lifecycle cleanup
            return
        try:
            process.wait(timeout=_TERMINATION_GRACE_SECONDS)
        except (Exception, KeyboardInterrupt):  # noqa: BLE001 - lifecycle cleanup
            return


def _container_name(command: list[str]) -> str | None:
    """Return the explicit name of a Docker run invocation."""
    if len(command) < 2 or Path(command[0]).name != "docker":
        return None
    if command[1] != "run":
        return None
    try:
        index = command.index("--name")
    except ValueError:
        return None
    if index + 1 >= len(command):
        return None
    return command[index + 1]


class Runner:
    """Run argv-only subprocesses with finite output and owned cleanup."""

    def run(
        self,
        command: list[str],
        *,
        cwd: Path,
        timeout: float = 300,
    ) -> CommandResult:
        """Run one command without retaining unbounded output."""
        container = _container_name(command)
        try:
            result = self._execute(command, cwd=cwd, timeout=timeout)
        except (Exception, KeyboardInterrupt):
            if container is not None:
                self._remove_container(container, cwd)
            raise
        if container is None:
            return result
        cleanup = self._remove_container(container, cwd)
        return CommandResult(
            result.returncode,
            result.output,
            result.timed_out,
            cleanup,
        )

    def _execute(
        self,
        command: list[str],
        *,
        cwd: Path,
        timeout: float,
    ) -> CommandResult:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        if process.stdout is None:
            _terminate_group(process)
            raise RuntimeError("subprocess output pipe is unavailable")
        os.set_blocking(process.stdout.fileno(), False)
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        chunks: deque[bytes] = deque()
        size = 0
        deadline = _deadline_after(timeout)
        timed_out = False
        pipe_eof = False
        try:
            while True:
                leader_done = process.poll() is not None
                group_done = leader_done and not _group_exists(process.pid)
                if leader_done and pipe_eof and group_done:
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    timed_out = True
                    _terminate_group(process)
                    break
                events = selector.select(min(remaining, _SELECT_SLICE_SECONDS))
                for key, _ in events:
                    for _ in range(_READ_BURST_CHUNKS):
                        if time.monotonic() >= deadline:
                            break
                        try:
                            value = os.read(key.fd, _READ_CHUNK)
                        except BlockingIOError:
                            break
                        if value:
                            size = _tail_append(chunks, size, value)
                            continue
                        pipe_eof = True
                        try:
                            selector.unregister(key.fileobj)
                        except KeyError:
                            pass
                        break
                if not selector.get_map():
                    time.sleep(min(remaining, _SELECT_SLICE_SECONDS))
            drain_deadline = time.monotonic() + _DRAIN_GRACE_SECONDS
            while not pipe_eof and time.monotonic() < drain_deadline:
                try:
                    value = os.read(process.stdout.fileno(), _READ_CHUNK)
                except BlockingIOError:
                    time.sleep(_SELECT_SLICE_SECONDS)
                    continue
                if not value:
                    pipe_eof = True
                    break
                size = _tail_append(chunks, size, value)
            if process.poll() is None:
                _terminate_group(process)
        except (Exception, KeyboardInterrupt) as exc:  # noqa: BLE001 - preserve evidence
            _cleanup_after_interrupt(process)
            raise exc.with_traceback(exc.__traceback__)
        finally:
            selector.close()
            process.stdout.close()
        returncode = 124 if timed_out else process.returncode
        if returncode is None:
            raise RuntimeError("subprocess was not reaped")
        output = b"".join(chunks).decode("utf-8", errors="replace")
        if timed_out:
            output += f"\ntimeout after {timeout}s: {Path(command[0]).name}"
        from deployment.qualification import sanitize

        return CommandResult(returncode, sanitize(output), timed_out)

    def _remove_container(self, name: str, cwd: Path) -> tuple[str, ...]:
        """Remove exactly one named invocation-owned container."""
        try:
            result = self._execute(
                ["docker", "rm", "-f", name],
                cwd=cwd,
                timeout=_CLEANUP_TIMEOUT_SECONDS,
            )
        except (OSError, RuntimeError, ValueError) as exc:
            return (f"container cleanup failed: {type(exc).__name__}",)
        if result.returncode == 0 or "No such container" in result.output:
            return ()
        detail = result.output.strip() or f"docker rm returned {result.returncode}"
        return (f"container cleanup failed: {detail}",)
