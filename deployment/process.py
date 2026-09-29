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
_TERMINATION_GRACE_SECONDS = 2.0
_CLEANUP_TIMEOUT_SECONDS = 15


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


def _terminate_group(process: subprocess.Popen[bytes]) -> None:
    """Terminate and reap one invocation-owned host process group."""
    if process.poll() is not None:
        process.wait()
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        process.wait()
        return
    try:
        process.wait(timeout=_TERMINATION_GRACE_SECONDS)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


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
        timeout: int = 300,
    ) -> CommandResult:
        """Run one command without retaining unbounded output."""
        container = _container_name(command)
        try:
            result = self._execute(command, cwd=cwd, timeout=timeout)
        except BaseException:
            if container is not None:
                self._remove_container(container, cwd)
            raise
        if container is None or (result.returncode == 0 and not result.timed_out):
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
        timeout: int,
    ) -> CommandResult:
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
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        chunks: deque[bytes] = deque()
        size = 0
        deadline = time.monotonic() + timeout
        timed_out = False
        try:
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0 and process.poll() is None:
                    timed_out = True
                    _terminate_group(process)
                    remaining = 0
                events = selector.select(min(max(remaining, 0), 0.1))
                for key, _ in events:
                    value = os.read(key.fd, _READ_CHUNK)
                    if value:
                        size = _tail_append(chunks, size, value)
                    else:
                        selector.unregister(key.fileobj)
                if process.poll() is not None and not events:
                    value = os.read(process.stdout.fileno(), _READ_CHUNK)
                    if value:
                        size = _tail_append(chunks, size, value)
                    else:
                        try:
                            selector.unregister(process.stdout)
                        except KeyError:
                            pass
            if process.poll() is None:
                process.wait()
        except BaseException:
            _terminate_group(process)
            raise
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
        except (OSError, RuntimeError) as exc:
            return (f"container cleanup failed: {type(exc).__name__}",)
        if result.returncode == 0 or "No such container" in result.output:
            return ()
        detail = result.output.strip() or f"docker rm returned {result.returncode}"
        return (f"container cleanup failed: {detail}",)
