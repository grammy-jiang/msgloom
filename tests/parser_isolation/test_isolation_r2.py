"""R2 lifecycle, storage, and runtime regressions for parser isolation."""

from __future__ import annotations

import asyncio
import hashlib
import os
import threading
import time
from pathlib import Path
from typing import Any, cast

import pytest

import msgloom.preparation.isolation.runner as isolation_runner
from msgloom.preparation import (
    DocumentFormat,
    ParserConfig,
    ParserIdentity,
    ParserLimits,
    ParserOutput,
    ParserProvenance,
    ParserRequest,
    SavedByteReference,
)
from msgloom.preparation.isolation import (
    ParserIsolationError,
    ParserOutputError,
    ParserTimeoutError,
)
from msgloom.preparation.isolation.registry import RegistryEntry, TrustedRegistry
from msgloom.preparation.isolation.runner import _parse_isolated, _read_output

_FIXTURE = Path(__file__).with_name("fixture_backend.py")
_IDENTITY = ParserIdentity("msgloom.synthetic-fixture", "1", "synthetic-safe-fixture-1")
_REGISTRY = TrustedRegistry(
    (
        RegistryEntry(
            formats=(DocumentFormat.TEXT,),
            module="fixture_backend",
            identity=_IDENTITY,
            fixture_file=_FIXTURE,
        ),
    )
)


def _request(
    *,
    settings: tuple[tuple[str, str], ...] = (),
    wall_time: float = 5.0,
    output_bytes: int = 64 * 1024,
) -> ParserRequest:
    content = b"synthetic content"
    return ParserRequest(
        source=SavedByteReference(
            reference="blob:r2-isolation",
            sha256=hashlib.sha256(content).hexdigest(),
            byte_count=len(content),
        ),
        detected_format=DocumentFormat.TEXT,
        parser=_IDENTITY,
        config=ParserConfig(profile="synthetic", settings=settings),
        limits=ParserLimits(
            wall_time_seconds=wall_time,
            memory_bytes=256 * 1024 * 1024,
            decompressed_bytes=1024 * 1024,
            output_bytes=output_bytes,
            container_members=64,
        ),
    )


def test_late_synchronous_validation_cannot_return_a_successful_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A blocked event loop cannot cancel its overdue timer into success."""
    request = _request(wall_time=0.01)

    async def delayed_result(*_args: object) -> ParserOutput:
        # A synchronous decoder can occupy the loop until its timeout callback
        # is overdue. asyncio.timeout alone can miss this acceptance boundary.
        time.sleep(0.05)  # noqa: ASYNC251 - model a blocking native decoder
        return ParserOutput(
            provenance=ParserProvenance.from_request(request),
            blocks=(),
            limitations=(),
        )

    monkeypatch.setattr(isolation_runner, "_run_isolated", delayed_result)

    async def exercise() -> None:
        with pytest.raises(ParserTimeoutError):
            await _parse_isolated(request, b"synthetic content", _REGISTRY)

    asyncio.run(exercise())


@pytest.mark.parametrize("late_failure", [False, True])
def test_cancelled_file_preparation_is_drained_before_return(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    late_failure: bool,
) -> None:
    """Cancellation cannot outlive accepted file-system worker ownership."""
    entered = threading.Event()
    release = threading.Event()
    roots: list[Path] = []
    real_prepare = isolation_runner._prepare_files

    def prepare(root: Path, content: bytes) -> tuple[Path, Path]:
        entered.set()
        release.wait(timeout=5)
        if late_failure:
            raise ValueError("synthetic late file preparation failure")
        return real_prepare(root, content)

    def make_root(*, prefix: str) -> str:
        root = tmp_path / f"{prefix}owned"
        root.mkdir()
        roots.append(root)
        return str(root)

    monkeypatch.setattr(isolation_runner, "_prepare_files", prepare)
    monkeypatch.setattr(isolation_runner.tempfile, "mkdtemp", make_root)

    async def exercise() -> None:
        task = asyncio.create_task(
            _parse_isolated(_request(), b"synthetic content", _REGISTRY)
        )
        deadline = asyncio.get_running_loop().time() + 2
        while not entered.is_set() and asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(0.005)
        if not entered.is_set():
            pytest.fail("file preparation did not enter its controlled barrier")
        task.cancel()
        task.cancel()
        await asyncio.sleep(0.05)
        if task.done():
            pytest.fail("cancelled parse returned while file worker still owned work")
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(exercise())
    if any(root.exists() for root in roots):
        pytest.fail("temporary parser storage survived drained cancellation")


def test_wall_deadline_includes_process_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The wall ceiling starts before sandbox process creation completes."""

    async def slow_spawn(argv: list[str]) -> asyncio.subprocess.Process:
        del argv
        await asyncio.sleep(1)
        pytest.fail("startup sleep should have been cancelled by wall deadline")

    monkeypatch.setattr(isolation_runner, "_spawn_process", slow_spawn)
    request = _request(wall_time=0.05)
    with pytest.raises(ParserTimeoutError, match="wall-time"):
        asyncio.run(_parse_isolated(request, b"synthetic content", _REGISTRY))


def test_wall_deadline_includes_stdin_ipc_and_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A blocked stdin drain is timed and still transfers cleanup ownership."""
    cleaned = False
    timer: asyncio.Timeout | None = None

    def controlled_timeout(_deadline: float) -> asyncio.Timeout:
        # Start expiry at the IPC barrier. Host load must not move this test's
        # deadline into preflight, where no process exists to clean up.
        nonlocal timer
        timer = asyncio.Timeout(None)
        return timer

    class SlowStdin:
        def write(self, payload: bytes) -> None:
            del payload

        async def drain(self) -> None:
            if timer is None:
                pytest.fail("stdin IPC started without the enclosing timeout")
            timer.reschedule(asyncio.get_running_loop().time())
            await asyncio.Future()

        def close(self) -> None:
            return None

        async def wait_closed(self) -> None:
            return None

    class FakeProcess:
        stdin = SlowStdin()
        returncode = None
        pid = 999999

    async def spawn(argv: list[str]) -> Any:
        del argv
        return FakeProcess()

    async def cleanup(process: Any) -> None:
        nonlocal cleaned
        del process
        cleaned = True

    monkeypatch.setattr(isolation_runner, "_spawn_process", spawn)
    monkeypatch.setattr(isolation_runner, "_cleanup_process", cleanup)
    monkeypatch.setattr(isolation_runner.asyncio, "timeout_at", controlled_timeout)
    with pytest.raises(ParserTimeoutError, match="wall-time"):
        asyncio.run(
            _parse_isolated(_request(wall_time=0.05), b"synthetic content", _REGISTRY)
        )
    if not cleaned:
        pytest.fail("timed-out stdin IPC did not transfer process cleanup")


def test_broken_input_pipe_reaps_live_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ordinary IPC failure cannot leave the accepted subprocess unowned."""
    real_create = asyncio.create_subprocess_exec
    spawned: list[int] = []

    async def short_child(*args: Any, **kwargs: Any) -> asyncio.subprocess.Process:
        del args
        process = await real_create(
            "/bin/sh",
            "-c",
            "exec 0<&-; sleep 0.05",
            stdin=kwargs["stdin"],
            stdout=kwargs["stdout"],
            stderr=kwargs["stderr"],
            start_new_session=kwargs["start_new_session"],
        )
        spawned.append(process.pid)
        return process

    monkeypatch.setattr(isolation_runner.asyncio, "create_subprocess_exec", short_child)
    with pytest.raises(ParserIsolationError):
        asyncio.run(_parse_isolated(_request(), b"synthetic content", _REGISTRY))
    if not spawned:
        pytest.fail("synthetic broken-pipe child was not started")
    if Path(f"/proc/{spawned[0]}").exists():
        pytest.fail("broken-pipe child survived parser lifecycle failure")


def test_output_mount_blocks_file_fanout() -> None:
    """Only the fixed result file is writable outside bounded scratch tmpfs."""
    request = _request(settings=(("mode", "fanout"),))
    output = asyncio.run(_parse_isolated(request, b"synthetic content", _REGISTRY))
    text = cast(Any, output.blocks[0]).text
    if text != "fanout-created=0":
        pytest.fail(f"parser created writable output siblings: {text}")


def test_output_reader_rejects_hardlink(tmp_path: Path) -> None:
    """A multiply linked result file is rejected before bytes are decoded."""
    result = tmp_path / "result.json"
    result.write_bytes(b"{}")
    os.link(result, tmp_path / "alias")
    with pytest.raises(ParserOutputError, match="safe regular file"):
        _read_output(result, 128)


def test_repeated_cancellation_reaps_real_descendants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repeated cancellation cannot interrupt kill/reap ownership."""
    real_create = asyncio.create_subprocess_exec
    spawned: list[int] = []

    async def capture(*args: Any, **kwargs: Any) -> asyncio.subprocess.Process:
        process = await real_create(*args, **kwargs)
        spawned.append(process.pid)
        return process

    monkeypatch.setattr(isolation_runner.asyncio, "create_subprocess_exec", capture)

    async def exercise() -> set[int]:
        request = _request(
            settings=(("mode", "spawn"), ("token", "r2-repeat-cancel")),
            wall_time=10,
        )
        task = asyncio.create_task(
            _parse_isolated(request, b"synthetic content", _REGISTRY)
        )
        descendants: set[int] = set()
        deadline = asyncio.get_running_loop().time() + 5
        while asyncio.get_running_loop().time() < deadline:
            if spawned:
                descendants = _descendants(spawned[0])
                if len(descendants) >= 3:
                    break
            await asyncio.sleep(0.01)
        if len(descendants) < 3:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            pytest.fail("real sandbox descendants did not start")
        task.cancel()
        for _ in range(8):
            await asyncio.sleep(0)
            task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        return descendants

    descendants = asyncio.run(exercise())
    survivors = [pid for pid in descendants if Path(f"/proc/{pid}").exists()]
    if survivors:
        pytest.fail(f"descendants survived repeated cancellation: {survivors}")


def test_non_system_runtime_is_mounted_minimally(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A uv-managed runtime is mounted by base prefix, not assumed in /usr."""
    runtime = tmp_path / "uv-python" / "cpython-3.14-linux-aarch64-gnu"
    executable = runtime / "bin" / "python3.14"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"synthetic executable")
    (runtime / "lib").mkdir()
    input_path = tmp_path / "input"
    output_path = tmp_path / "result.json"
    input_path.write_bytes(b"synthetic content")
    output_path.write_bytes(b"")
    monkeypatch.setattr(isolation_runner.sys, "executable", str(executable))
    monkeypatch.setattr(isolation_runner.sys, "base_prefix", str(runtime))

    argv = isolation_runner._sandbox_argv(
        _REGISTRY.resolve(DocumentFormat.TEXT),
        input_path,
        output_path,
        _request(),
    )
    expected_runtime = str(runtime.resolve())
    if expected_runtime not in argv:
        pytest.fail("non-system runtime base was not mounted")
    if "/runtime/bin/python3.14" not in argv:
        pytest.fail("sandbox did not execute the mounted trusted interpreter")
    if str(runtime.parent.resolve()) in argv:
        pytest.fail("sandbox mounted a broader runtime parent than required")


def _descendants(root_pid: int) -> set[int]:
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
    return descendants
