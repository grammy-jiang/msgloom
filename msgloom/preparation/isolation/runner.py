"""Awaited Linux process boundary for synchronous document parsers."""

from __future__ import annotations

import asyncio
import os
import select
import shutil
import signal
import stat
import sys
import sysconfig
import tempfile
import time
from contextlib import suppress
from pathlib import Path

from msgloom.preparation.contracts import ParserOutput, ParserProvenance, ParserRequest
from msgloom.preparation.isolation.registry import (
    PRODUCTION_REGISTRY,
    RegistryEntry,
    TrustedRegistry,
)
from msgloom.preparation.isolation.request_wire import encode_request
from msgloom.preparation.isolation.validation import (
    validate_format_content,
    verify_saved_bytes,
)
from msgloom.preparation.isolation.wire import decode_output

_BWRAP = Path("/usr/bin/bwrap")
_REQUEST_BYTES = 64 * 1024
_SANDBOX_RESULT = "result.json"


class ParserIsolationError(RuntimeError):
    """Base failure that never includes source bytes or parser diagnostics."""


class ParserIsolationUnavailable(ParserIsolationError):
    """Required Linux isolation or trusted parser code is unavailable."""


class ParserTimeoutError(ParserIsolationError):
    """The parser exceeded its configured wall-time ceiling."""


class ParserOutputError(ParserIsolationError):
    """The isolated process produced no acceptable bounded output."""


async def parse_isolated(request: ParserRequest, content: bytes) -> ParserOutput:
    """Parse saved bytes in the closed production parser registry.

    The coroutine verifies saved-byte identity before launch, awaits all worker
    lifecycle work, and returns only strictly decoded output with exact request
    provenance. It never persists data or marks an Application attempt
    complete.
    """
    return await _parse_isolated(request, content, PRODUCTION_REGISTRY)


async def _parse_isolated(
    request: ParserRequest,
    content: bytes,
    registry: TrustedRegistry,
) -> ParserOutput:
    entry = registry.resolve(request.detected_format)
    if request.parser != entry.identity:
        raise ParserIsolationError("parser identity does not match trusted registry")
    loop = asyncio.get_running_loop()
    deadline = loop.time() + request.limits.wall_time_seconds
    request_payload = encode_request(request)
    if len(request_payload) > _REQUEST_BYTES:
        raise ParserIsolationError("parser request exceeds IPC ceiling")

    temp_root = Path(tempfile.mkdtemp(prefix="msgloom-parser-"))
    try:
        try:
            async with asyncio.timeout_at(deadline):
                output = await _run_isolated(
                    request, content, entry, request_payload, temp_root
                )
        except TimeoutError:
            raise ParserTimeoutError(
                "isolated parser exceeded wall-time limit"
            ) from None
    finally:
        await _await_owned(asyncio.to_thread(shutil.rmtree, temp_root))
    if loop.time() >= deadline:
        raise ParserTimeoutError("isolated parser exceeded wall-time limit")
    return output


async def _run_isolated(
    request: ParserRequest,
    content: bytes,
    entry: RegistryEntry,
    request_payload: bytes,
    temp_root: Path,
) -> ParserOutput:
    await _await_owned(asyncio.to_thread(_preflight, request, content))
    input_path, output_path = await _await_owned(
        asyncio.to_thread(_prepare_files, temp_root, content)
    )
    argv = _sandbox_argv(entry, input_path, output_path, request)
    process: asyncio.subprocess.Process | None = None
    try:
        process = await _spawn_process(argv)
        if process.stdin is None:
            raise ParserIsolationError("parser IPC pipe was not created")
        process.stdin.write(request_payload)
        await process.stdin.drain()
        process.stdin.close()
        await process.stdin.wait_closed()
        return_code = await process.wait()
        if return_code != 0:
            raise ParserIsolationError("isolated parser process failed")
        payload = await _await_owned(
            asyncio.to_thread(
                _read_output,
                output_path,
                request.limits.output_bytes,
            )
        )
        try:
            output = decode_output(payload)
        except (TypeError, ValueError):
            raise ParserOutputError("isolated parser returned invalid output") from None
        if output.provenance != ParserProvenance.from_request(request):
            raise ParserOutputError("isolated parser provenance does not match request")
        return output
    except asyncio.CancelledError:
        if process is not None:
            await _cleanup_process(process)
        raise
    except ParserIsolationError:
        if process is not None:
            await _cleanup_process(process)
        raise
    except Exception:  # noqa: BLE001 - opaque lifecycle boundary
        if process is not None:
            await _cleanup_process(process)
        raise ParserIsolationError("isolated parser lifecycle failed") from None


async def _await_owned(awaitable):
    task = asyncio.ensure_future(awaitable)
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
    result = task.result()
    if cancelled:
        raise asyncio.CancelledError
    return result


async def _cleanup_process(process: asyncio.subprocess.Process) -> None:
    task = asyncio.create_task(_kill_and_reap(process))
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            continue
    task.result()


async def _spawn_process(argv: list[str]) -> asyncio.subprocess.Process:
    spawn_task = asyncio.create_task(
        asyncio.create_subprocess_exec(
            *argv,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            start_new_session=True,
        )
    )
    try:
        return await _await_owned(spawn_task)
    except asyncio.CancelledError:
        process: asyncio.subprocess.Process | None = None
        if spawn_task.done() and not spawn_task.cancelled():
            with suppress(Exception):
                process = spawn_task.result()
        if process is not None:
            await _cleanup_process(process)
        raise


def _preflight(request: ParserRequest, content: bytes) -> None:
    verify_saved_bytes(request, content)
    validate_format_content(request, content, deep=False)


def _prepare_files(root: Path, content: bytes) -> tuple[Path, Path]:
    input_dir = root / "input"
    output_dir = root / "output"
    input_dir.mkdir(mode=0o700)
    output_dir.mkdir(mode=0o700)
    input_path = input_dir / "content"
    output_path = output_dir / _SANDBOX_RESULT
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    for path, payload, mode in (
        (input_path, content, 0o400),
        (output_path, b"", 0o600),
    ):
        fd = os.open(path, flags, mode)
        try:
            with os.fdopen(fd, "wb", closefd=False) as stream:
                stream.write(payload)
            os.close(fd)
            fd = -1
        finally:
            if fd >= 0:
                os.close(fd)
    return input_path, output_path


def _sandbox_argv(
    entry: RegistryEntry,
    input_path: Path,
    output_path: Path,
    request: ParserRequest,
) -> list[str]:
    if sys.platform != "linux" or not _BWRAP.is_file():
        raise ParserIsolationUnavailable(
            "required Linux bubblewrap isolation unavailable"
        )
    python, runtime_mounts, runtime_path = _sandbox_runtime()
    msgloom_dir = Path(__file__).resolve().parents[2]
    site_packages = Path(sysconfig.get_paths()["purelib"]).resolve()
    if not site_packages.is_dir():
        raise ParserIsolationUnavailable("qualified parser dependencies unavailable")
    _verify_parser_code(entry, msgloom_dir)

    python_path = "/app:/site"
    fixture_mounts: list[str] = []
    if entry.fixture_file is not None:
        fixture = entry.fixture_file.resolve(strict=True)
        if not fixture.is_file():
            raise ParserIsolationUnavailable("trusted fixture parser unavailable")
        fixture_mounts = [
            "--dir",
            "/fixture",
            "--ro-bind",
            str(fixture),
            "/fixture/fixture_backend.py",
        ]
        python_path = f"/fixture:{python_path}"

    tmp_bytes = max(
        1024 * 1024, min(request.limits.memory_bytes // 4, 64 * 1024 * 1024)
    )
    return [
        str(_BWRAP),
        "--unshare-user",
        "--unshare-ipc",
        "--unshare-pid",
        "--unshare-net",
        "--unshare-uts",
        "--unshare-cgroup-try",
        "--disable-userns",
        "--die-with-parent",
        "--new-session",
        "--clearenv",
        "--setenv",
        "PATH",
        runtime_path,
        "--setenv",
        "HOME",
        "/nonexistent",
        "--setenv",
        "PYTHONPATH",
        python_path,
        "--setenv",
        "PYTHONDONTWRITEBYTECODE",
        "1",
        "--setenv",
        "PYTHONNOUSERSITE",
        "1",
        "--setenv",
        "PYTHONUTF8",
        "1",
        "--setenv",
        "PWD",
        "/tmp",
        "--setenv",
        "LC_CTYPE",
        "C.UTF-8",
        "--ro-bind",
        "/usr",
        "/usr",
        *runtime_mounts,
        "--symlink",
        "usr/bin",
        "/bin",
        "--symlink",
        "usr/lib",
        "/lib",
        "--symlink",
        "usr/lib",
        "/lib64",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--size",
        str(tmp_bytes),
        "--tmpfs",
        "/tmp",
        "--dir",
        "/app",
        "--ro-bind",
        str(msgloom_dir),
        "/app/msgloom",
        "--dir",
        "/site",
        "--ro-bind",
        str(site_packages),
        "/site",
        "--dir",
        "/input",
        "--ro-bind",
        str(input_path),
        "/input/content",
        "--ro-bind",
        str(output_path.parent),
        "/output",
        "--bind",
        str(output_path),
        "/output/result.json",
        *fixture_mounts,
        "--chdir",
        "/tmp",
        str(python),
        "-S",
        "-m",
        "msgloom.preparation.isolation.worker",
        entry.module,
        entry.identity.name,
        entry.identity.version,
        entry.identity.backend or "",
    ]


def _sandbox_runtime() -> tuple[Path, list[str], str]:
    try:
        executable = Path(sys.executable).resolve(strict=True)
        base_prefix = Path(sys.base_prefix).resolve(strict=True)
    except OSError:
        raise ParserIsolationUnavailable("sandbox Python runtime unavailable") from None
    if executable.is_relative_to("/usr"):
        return executable, [], "/usr/bin"
    try:
        relative = executable.relative_to(base_prefix)
    except ValueError:
        raise ParserIsolationUnavailable(
            "sandbox Python runtime is outside its trusted base"
        ) from None
    if not relative.parts or relative.parts[0] != "bin":
        raise ParserIsolationUnavailable("sandbox Python runtime layout is unsupported")
    if not (base_prefix / "lib").is_dir():
        raise ParserIsolationUnavailable("sandbox Python runtime library unavailable")
    sandbox_executable = Path("/runtime") / relative
    mounts = ["--dir", "/runtime", "--ro-bind", str(base_prefix), "/runtime"]
    return sandbox_executable, mounts, "/runtime/bin:/usr/bin"


def _verify_parser_code(entry: RegistryEntry, msgloom_dir: Path) -> None:
    if entry.fixture_file is not None:
        return
    prefix = "msgloom.preparation.parsers."
    if not entry.module.startswith(prefix):
        raise ParserIsolationUnavailable(
            "trusted parser module is outside parser package"
        )
    leaf = entry.module.removeprefix(prefix)
    if not leaf or "." in leaf:
        raise ParserIsolationUnavailable("trusted parser module path is invalid")
    module_file = msgloom_dir / "preparation" / "parsers" / f"{leaf}.py"
    if not module_file.is_file():
        raise ParserIsolationUnavailable("trusted parser module unavailable")


async def _kill_and_reap(process: asyncio.subprocess.Process) -> None:
    if process.returncode is not None:
        return
    pidfds = await asyncio.to_thread(_open_descendant_pidfds, process.pid)
    try:
        for pidfd in pidfds:
            try:
                signal.pidfd_send_signal(pidfd, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if process.returncode is None:
            process.kill()
        await process.wait()
        if pidfds and not await asyncio.to_thread(_wait_pidfds, pidfds, 2.0):
            raise ParserIsolationError("isolated parser descendants did not terminate")
    finally:
        for pidfd in pidfds:
            os.close(pidfd)


def _open_descendant_pidfds(root_pid: int) -> list[int]:
    parents: dict[int, int] = {}
    for path in Path("/proc").iterdir():
        if not path.name.isdigit():
            continue
        try:
            stat_text = (path / "stat").read_text(encoding="ascii")
            rest = stat_text[stat_text.rindex(")") + 2 :].split()
            parents[int(path.name)] = int(rest[1])
        except (FileNotFoundError, PermissionError, ProcessLookupError, ValueError):
            continue
    descendants: set[int] = set()
    frontier = {root_pid}
    while frontier:
        children = {pid for pid, parent in parents.items() if parent in frontier}
        children -= descendants
        if not children:
            break
        descendants.update(children)
        frontier = children

    pidfds: list[int] = []
    for pid in descendants:
        try:
            pidfds.append(os.pidfd_open(pid))
        except ProcessLookupError:
            continue
    return pidfds


def _wait_pidfds(pidfds: list[int], seconds: float) -> bool:
    """Wait for reaping, retaining ownership while exited zombies remain."""
    poller = select.poll()
    for pidfd in pidfds:
        # Readability marks exit; only hangup confirms reaping.
        poller.register(pidfd, 0)
    remaining = set(pidfds)
    deadline = time.monotonic() + seconds
    while remaining:
        milliseconds = max(0, int((deadline - time.monotonic()) * 1000))
        if milliseconds == 0:
            return False
        for pidfd, event in poller.poll(milliseconds):
            if event & select.POLLHUP:
                remaining.discard(pidfd)
                poller.unregister(pidfd)
    return True


def _read_output(path: Path, limit: int) -> bytes:
    try:
        before = os.lstat(path)
    except FileNotFoundError:
        raise ParserOutputError("isolated parser produced no output") from None
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise ParserOutputError("isolated parser output is not a safe regular file")
    if before.st_size > limit:
        raise ParserOutputError("isolated parser output exceeds output-byte ceiling")
    flags = os.O_RDONLY | os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError:
        raise ParserOutputError(
            "isolated parser output cannot be opened safely"
        ) from None
    try:
        current = os.fstat(fd)
        if (
            not stat.S_ISREG(current.st_mode)
            or current.st_nlink != 1
            or current.st_ino != before.st_ino
            or current.st_dev != before.st_dev
            or current.st_size > limit
        ):
            raise ParserOutputError("isolated parser output changed before validation")
        chunks: list[bytes] = []
        remaining = limit + 1
        while remaining:
            chunk = os.read(fd, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        if len(payload) > limit:
            raise ParserOutputError(
                "isolated parser output exceeds output-byte ceiling"
            )
        return payload
    finally:
        os.close(fd)
