"""Bubblewrap command construction and descendant-safe process cleanup."""

from __future__ import annotations

import asyncio
import os
import signal
from pathlib import Path

from msgloom.ai.policy import RuntimeIsolation


def _parents(path: Path) -> tuple[Path, ...]:
    result: list[Path] = []
    current = path.parent
    while current != Path("/"):
        result.append(current)
        current = current.parent
    return tuple(reversed(result))


def build_sandbox_command(
    runtime: RuntimeIsolation,
    worker: Path,
    state_dir: Path,
    work_dir: Path,
) -> list[str]:
    """Build a minimal namespace with no host home or project mount."""
    if not runtime.bubblewrap_executable.is_file():
        raise RuntimeError("required bubblewrap executable is unavailable")
    trusted = (
        *runtime.runtime_roots,
        runtime.python_executable,
        runtime.cli_path,
    )
    for path in trusted:
        if not path.exists():
            raise RuntimeError(f"required trusted runtime path unavailable: {path}")
    base_dirs = {Path("/app"), Path("/work"), Path("/state"), Path("/tmp")}
    dirs = set(base_dirs)
    for path in trusted:
        dirs.update(_parents(path))
    command = [
        str(runtime.bubblewrap_executable),
        "--die-with-parent",
        "--new-session",
        "--unshare-all",
        "--share-net",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
        "--dir",
        "/app",
        "--dir",
        "/work",
        "--dir",
        "/state",
    ]
    extra_dirs = sorted(
        dirs - base_dirs,
        key=lambda path: (len(path.parts), str(path)),
    )
    for directory in extra_dirs:
        command.extend(["--dir", str(directory)])
    mounted: set[Path] = set()
    for path in trusted:
        if any(parent in mounted for parent in path.parents):
            continue
        command.extend(["--ro-bind", str(path), str(path)])
        mounted.add(path)
    command.extend(
        [
            "--bind",
            str(state_dir),
            "/state",
            "--bind",
            str(work_dir),
            "/work",
            "--ro-bind",
            str(worker),
            "/app/worker.py",
            "--chdir",
            "/work",
            str(runtime.python_executable),
            "/app/worker.py",
        ]
    )
    return command


def _signal_group(pid: int, sig: signal.Signals) -> None:
    try:
        os.killpg(pid, sig)
    except ProcessLookupError:
        pass


def _group_exists(pid: int) -> bool:
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


async def _wait_group_gone(pid: int, seconds: float) -> bool:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + seconds
    while _group_exists(pid):
        if loop.time() >= deadline:
            return False
        await asyncio.sleep(min(0.01, max(0.0, deadline - loop.time())))
    return True


async def terminate_and_reap(
    process: asyncio.subprocess.Process,
    grace_seconds: float,
) -> None:
    """Terminate the accepted process group and reap the direct child.

    The process group is signalled even when its leader already exited. This
    closes inherited pipes held by descendants and prevents a successful
    direct-child exit from orphaning accepted work.
    """
    pid = process.pid
    _signal_group(pid, signal.SIGTERM)
    direct_wait = asyncio.create_task(process.wait())
    group_gone = await _wait_group_gone(pid, grace_seconds)
    if not group_gone:
        _signal_group(pid, signal.SIGKILL)
        await _wait_group_gone(pid, grace_seconds)
    await direct_wait


async def finish_uncancellable[T](task: asyncio.Task[T]) -> bool:
    """Drain accepted cleanup or durable work despite repeated cancellation."""
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
    task.result()
    return cancelled
