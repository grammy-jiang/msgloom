"""Lifecycle regressions for one owned AI attempt deadline and process group."""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from msgloom.ai import (
    AIRunner,
    AnalysisAttempt,
    AttemptLimits,
    AttemptStatus,
    RuntimeIsolation,
    TraceEvent,
    TrustedPolicy,
)
from msgloom.contracts import AttemptIdentity, VersionRef


def _ref(kind: str, identity: str) -> VersionRef:
    return VersionRef(kind, identity, "1")


def _attempt(timeout: float) -> AnalysisAttempt:
    return AnalysisAttempt(
        AttemptIdentity(f"lifecycle-{timeout}"),
        (_ref("prepared", "input"),),
        _ref("context", "context"),
        _ref("prompt", "prompt"),
        _ref("schema", "schema"),
        _ref("model", "model"),
        "synthetic",
        "",
        "prompt",
        AttemptLimits(timeout, 100, 100, 100, 4096, 8, 1024, 2, 700),
    )


def _runner(root: Path, grace: float = 0.05) -> AIRunner:
    return AIRunner(
        TrustedPolicy(
            {_ref("schema", "schema"): {"type": "object"}},
            {_ref("model", "model"): "synthetic-model"},
        ),
        RuntimeIsolation(
            Path(sys.executable),
            Path("/usr/bin/bwrap"),
            (Path("/usr"),),
            Path("/bin/true"),
            {},
            root,
            grace,
        ),
    )


class _Sink:
    async def write(self, event: TraceEvent) -> None:
        await asyncio.sleep(0)


def _patch_script(monkeypatch: pytest.MonkeyPatch, script: Path) -> None:
    monkeypatch.setattr(
        "msgloom.ai.runner.build_sandbox_command",
        lambda *_args: [sys.executable, str(script)],
    )


def test_storage_work_is_inside_deadline_but_drained(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Accepted storage work finishes even when it carries past the deadline."""
    runner = _runner(tmp_path)
    original = runner._prepare_storage

    def slow_storage(attempt: AnalysisAttempt) -> tuple[Path, Path]:
        time.sleep(0.08)
        return original(attempt)

    monkeypatch.setattr(runner, "_prepare_storage", slow_storage)
    started = time.monotonic()
    response = asyncio.run(runner.run(_attempt(0.03), _Sink()))
    elapsed = time.monotonic() - started
    if response.status is not AttemptStatus.TIMED_OUT:
        pytest.fail("storage delay outside the attempt deadline was accepted")
    if elapsed < 0.07:
        pytest.fail("accepted storage work was abandoned after timeout")


async def _cancel_initial_drain(root: Path, script: Path) -> bool:
    real_create = asyncio.create_subprocess_exec
    entered = asyncio.Event()
    processes: list[asyncio.subprocess.Process] = []

    class Stdin:
        def write(self, _data: bytes) -> None:
            return None

        async def drain(self) -> None:
            entered.set()
            await asyncio.Event().wait()

        def close(self) -> None:
            return None

        async def wait_closed(self) -> None:
            return None

    class Process:
        def __init__(self, process: asyncio.subprocess.Process) -> None:
            self._process = process
            self.stdin = Stdin()

        def __getattr__(self, name: str) -> object:
            return getattr(self._process, name)

    async def create(*args: Any, **kwargs: Any) -> Process:
        process = await real_create(*args, **kwargs)
        processes.append(process)
        return Process(process)

    with (
        patch(
            "msgloom.ai.runner.build_sandbox_command",
            return_value=[sys.executable, str(script)],
        ),
        patch("msgloom.ai.runner.asyncio.create_subprocess_exec", create),
    ):
        task = asyncio.create_task(_runner(root).run(_attempt(2), _Sink()))
        await asyncio.wait_for(entered.wait(), 1)
        task.cancel()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, 2)
    return processes[0].returncode is None


def test_repeated_cancel_during_initial_stdin_reaps_child(tmp_path: Path) -> None:
    """Cancellation cannot return while initial IPC still owns a live child."""
    script = tmp_path / "stdin.py"
    script.write_text("import time\ntime.sleep(60)\n")
    alive = asyncio.run(_cancel_initial_drain(tmp_path, script))
    if alive:
        pytest.fail("initial stdin cancellation returned with a live child")


def test_parent_exit_with_descendant_pipe_holder_is_reaped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A dead group leader cannot leave descendants holding IPC pipes."""
    pid_file = tmp_path / "descendant.pid"
    script = tmp_path / "descendant.py"
    script.write_text(
        "import json,subprocess,sys\n"
        "json.load(sys.stdin)\n"
        "child=subprocess.Popen(['sleep','60'])\n"
        f"open({str(pid_file)!r},'w').write(str(child.pid))\n"
        "print(json.dumps({'type':'final','ok':True,"
        "'structured_output':{'value':'synthetic'}}),flush=True)\n"
    )
    _patch_script(monkeypatch, script)
    response = asyncio.run(_runner(tmp_path).run(_attempt(2), _Sink()))
    if response.status is not AttemptStatus.COMPLETE:
        pytest.fail(f"valid parent result was lost: {response!r}")
    pid = int(pid_file.read_text())
    if Path(f"/proc/{pid}").exists():
        pytest.fail("descendant survived after its process-group leader exited")


def test_sigterm_ignoring_child_is_killed_after_grace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Timeout escalates to SIGKILL and reaps a SIGTERM-ignoring worker."""
    pid_file = tmp_path / "ignore.pid"
    script = tmp_path / "ignore.py"
    script.write_text(
        "import json,os,signal,sys,time\n"
        "json.load(sys.stdin)\n"
        "signal.signal(signal.SIGTERM,signal.SIG_IGN)\n"
        f"open({str(pid_file)!r},'w').write(str(os.getpid()))\n"
        "time.sleep(60)\n"
    )
    _patch_script(monkeypatch, script)
    response = asyncio.run(_runner(tmp_path, 0.03).run(_attempt(0.15), _Sink()))
    if response.status is not AttemptStatus.TIMED_OUT:
        pytest.fail("SIGTERM-ignoring child did not time out")
    if pid_file.exists():
        pid = int(pid_file.read_text())
        if Path(f"/proc/{pid}").exists():
            pytest.fail("SIGTERM-ignoring child survived cleanup")


async def _cancel_spawn_acceptance(root: Path, script: Path) -> bool:
    real_create = asyncio.create_subprocess_exec
    accepted = asyncio.Event()
    release = asyncio.Event()
    processes: list[asyncio.subprocess.Process] = []

    async def create(*args: Any, **kwargs: Any) -> asyncio.subprocess.Process:
        process = await real_create(*args, **kwargs)
        processes.append(process)
        accepted.set()
        await release.wait()
        return process

    with (
        patch(
            "msgloom.ai.runner.build_sandbox_command",
            return_value=[sys.executable, str(script)],
        ),
        patch("msgloom.ai.runner.asyncio.create_subprocess_exec", create),
    ):
        task = asyncio.create_task(_runner(root).run(_attempt(2), _Sink()))
        await asyncio.wait_for(accepted.wait(), 1)
        task.cancel()
        task.cancel()
        await asyncio.sleep(0.02)
        if task.done():
            pytest.fail("runner returned before accepted spawn ownership resolved")
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, 2)
    return processes[0].returncode is None


def test_repeated_cancel_drains_accepted_spawn_before_return(tmp_path: Path) -> None:
    """An accepted but not yet handed-off spawn is owned through cancellation."""
    script = tmp_path / "spawn.py"
    script.write_text("import time\ntime.sleep(60)\n")
    alive = asyncio.run(_cancel_spawn_acceptance(tmp_path, script))
    if alive:
        pytest.fail("spawn cancellation returned with an accepted child alive")


class _BarrierSink:
    """Hold one durable write until the test releases its acceptance barrier."""

    def __init__(self) -> None:
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.events: list[TraceEvent] = []

    async def write(self, event: TraceEvent) -> None:
        self.entered.set()
        await self.release.wait()
        self.events.append(event)


async def _late_sink_after_exit(
    root: Path,
    script: Path,
) -> tuple[AttemptStatus, int, int]:
    real_create = asyncio.create_subprocess_exec
    processes: list[asyncio.subprocess.Process] = []
    expired = False
    sink = _BarrierSink()

    async def create(*args: Any, **kwargs: Any) -> asyncio.subprocess.Process:
        process = await real_create(*args, **kwargs)
        processes.append(process)
        return process

    def controlled_remaining(_deadline: float) -> float:
        return 0.0 if expired else 1.0

    with (
        patch(
            "msgloom.ai.runner.build_sandbox_command",
            return_value=[sys.executable, str(script)],
        ),
        patch("msgloom.ai.runner.asyncio.create_subprocess_exec", create),
        patch("msgloom.ai.runner.remaining", controlled_remaining),
    ):
        task = asyncio.create_task(_runner(root).run(_attempt(2), sink))
        await asyncio.wait_for(sink.entered.wait(), 1)
        process = processes[0]
        await asyncio.wait_for(process.wait(), 1)
        expired = True
        sink.release.set()
        response = await asyncio.wait_for(task, 2)
    return response.status, response.trace_count, len(sink.events)


def test_late_sink_after_child_exit_is_durable_but_not_accepted(
    tmp_path: Path,
) -> None:
    """A durable trace finishing after the deadline cannot admit output."""
    script = tmp_path / "late-sink.py"
    script.write_text(
        "import json,sys\n"
        "json.load(sys.stdin)\n"
        "print(json.dumps({'type':'trace','kind':'system',"
        "'name':'saved','text':'saved','data':{}}),flush=True)\n"
        "print(json.dumps({'type':'final','ok':True,"
        "'structured_output':{'value':'synthetic'}}),flush=True)\n"
    )
    status, trace_count, saved = asyncio.run(_late_sink_after_exit(tmp_path, script))
    if status is not AttemptStatus.TIMED_OUT:
        pytest.fail("late durable sink completion admitted a successful result")
    if trace_count != 2 or saved != 2:
        pytest.fail("late sink and timeout diagnostic were not durably sequenced")


async def _delayed_cleanup_crosses_deadline(
    root: Path,
    script: Path,
) -> AttemptStatus:
    entered = asyncio.Event()
    release = asyncio.Event()
    expired = False
    from msgloom.ai.lifecycle import cleanup_owned as real_cleanup

    async def delayed_cleanup(*args: Any, **kwargs: Any) -> bool:
        entered.set()
        await release.wait()
        return await real_cleanup(*args, **kwargs)

    def controlled_remaining(_deadline: float) -> float:
        return 0.0 if expired else 1.0

    with (
        patch(
            "msgloom.ai.runner.build_sandbox_command",
            return_value=[sys.executable, str(script)],
        ),
        patch("msgloom.ai.runner.cleanup_owned", delayed_cleanup),
        patch("msgloom.ai.runner.remaining", controlled_remaining),
    ):
        task = asyncio.create_task(_runner(root).run(_attempt(2), _Sink()))
        await asyncio.wait_for(entered.wait(), 1)
        expired = True
        release.set()
        response = await asyncio.wait_for(task, 2)
    return response.status


def test_cleanup_crossing_acceptance_deadline_rejects_result(tmp_path: Path) -> None:
    """Cleanup time is part of the same result-acceptance deadline."""
    script = tmp_path / "cleanup.py"
    script.write_text(
        "import json,sys\n"
        "json.load(sys.stdin)\n"
        "print(json.dumps({'type':'final','ok':True,"
        "'structured_output':{'value':'synthetic'}}),flush=True)\n"
    )
    status = asyncio.run(_delayed_cleanup_crosses_deadline(tmp_path, script))
    if status is not AttemptStatus.TIMED_OUT:
        pytest.fail("cleanup crossing the original deadline admitted output")


def test_timely_trace_and_cleanup_remain_acceptable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Normal durable completion before the deadline remains successful."""
    script = tmp_path / "timely.py"
    script.write_text(
        "import json,sys\n"
        "json.load(sys.stdin)\n"
        "print(json.dumps({'type':'trace','kind':'system',"
        "'name':'saved','text':'saved','data':{}}),flush=True)\n"
        "print(json.dumps({'type':'final','ok':True,"
        "'structured_output':{'value':'synthetic'}}),flush=True)\n"
    )
    _patch_script(monkeypatch, script)
    response = asyncio.run(_runner(tmp_path).run(_attempt(2), _Sink()))
    if response.status is not AttemptStatus.COMPLETE:
        pytest.fail("timely durable output was not accepted")


async def _pipe_pressure_spawn_cancel(root: Path, script: Path) -> bool:
    real_create = asyncio.create_subprocess_exec
    accepted = asyncio.Event()
    release = asyncio.Event()
    processes: list[asyncio.subprocess.Process] = []

    async def create(*args: Any, **kwargs: Any) -> asyncio.subprocess.Process:
        process = await real_create(*args, **kwargs)
        processes.append(process)
        accepted.set()
        await release.wait()
        return process

    with (
        patch(
            "msgloom.ai.runner.build_sandbox_command",
            return_value=[sys.executable, str(script)],
        ),
        patch("msgloom.ai.runner.asyncio.create_subprocess_exec", create),
    ):
        task = asyncio.create_task(_runner(root).run(_attempt(2), _Sink()))
        await asyncio.wait_for(accepted.wait(), 1)
        await asyncio.sleep(0.05)
        task.cancel()
        task.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, 2)
    return processes[0].returncode is None


def test_spawn_cleanup_drains_full_stderr_under_repeated_cancel(
    tmp_path: Path,
) -> None:
    """Pre-consumer pipe pressure cannot deadlock accepted spawn cleanup."""
    script = tmp_path / "stderr-before-stdin.py"
    script.write_text(
        "import sys,time\n"
        "sys.stderr.write('x'*100000)\n"
        "sys.stderr.flush()\n"
        "time.sleep(60)\n"
    )
    alive = asyncio.run(_pipe_pressure_spawn_cancel(tmp_path, script))
    if alive:
        pytest.fail("pipe-pressure spawn cleanup returned with a live child")


async def _pipe_pressure_spawn_timeout(
    root: Path,
    script: Path,
) -> tuple[AttemptStatus, bool]:
    real_create = asyncio.create_subprocess_exec
    accepted = asyncio.Event()
    release = asyncio.Event()
    processes: list[asyncio.subprocess.Process] = []

    async def create(*args: Any, **kwargs: Any) -> asyncio.subprocess.Process:
        process = await real_create(*args, **kwargs)
        processes.append(process)
        accepted.set()
        await release.wait()
        return process

    with (
        patch(
            "msgloom.ai.runner.build_sandbox_command",
            return_value=[sys.executable, str(script)],
        ),
        patch("msgloom.ai.runner.asyncio.create_subprocess_exec", create),
    ):
        task = asyncio.create_task(_runner(root).run(_attempt(0.05), _Sink()))
        await asyncio.wait_for(accepted.wait(), 1)
        await asyncio.sleep(0.08)
        release.set()
        response = await asyncio.wait_for(task, 2)
    return response.status, processes[0].returncode is None


def test_timed_out_spawn_drains_full_stderr_before_reaping(tmp_path: Path) -> None:
    """Timed-out accepted spawn drains pre-consumer stderr while reaping."""
    script = tmp_path / "stderr-timeout.py"
    script.write_text(
        "import sys,time\n"
        "sys.stderr.write('x'*100000)\n"
        "sys.stderr.flush()\n"
        "time.sleep(60)\n"
    )
    status, alive = asyncio.run(_pipe_pressure_spawn_timeout(tmp_path, script))
    if status is not AttemptStatus.TIMED_OUT:
        pytest.fail("pipe-pressure startup did not retain timeout outcome")
    if alive:
        pytest.fail("timed-out pipe-pressure spawn returned with a live child")
