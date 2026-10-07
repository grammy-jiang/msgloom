"""Synthetic process, persistence, timeout, and cancellation tests."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from msgloom.ai import (
    AIRunner,
    AnalysisAttempt,
    AnalysisResponse,
    AttemptLimits,
    AttemptStatus,
    RuntimeIsolation,
    TraceEvent,
    TrustedPolicy,
)
from msgloom.contracts import AttemptIdentity, VersionRef


def _ref(kind: str, identity: str) -> VersionRef:
    return VersionRef(kind, identity, "1")


def _attempt(timeout: float = 2.0, output: int = 4096) -> AnalysisAttempt:
    return AnalysisAttempt(
        AttemptIdentity("attempt-1"),
        (_ref("prepared", "input-1"),),
        _ref("context", "context-1"),
        _ref("prompt", "prompt-1"),
        _ref("schema", "schema-1"),
        _ref("model", "model-1"),
        "synthetic input",
        "synthetic context",
        "trusted prompt",
        AttemptLimits(timeout, 100, 100, 100, output, 8, 1024, 2, 700),
    )


def _runner(storage_root: Path) -> AIRunner:
    policy = TrustedPolicy(
        {_ref("schema", "schema-1"): {"type": "object"}},
        {_ref("model", "model-1"): "synthetic-model"},
    )
    runtime = RuntimeIsolation(
        Path(sys.executable),
        Path("/usr/bin/bwrap"),
        (Path("/usr"),),
        Path("/bin/true"),
        {"AWS_REGION": "synthetic-region"},
        storage_root,
        0.1,
    )
    return AIRunner(policy, runtime)


class _Sink:
    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    async def write(self, event: TraceEvent) -> None:
        await asyncio.sleep(0)
        self.events.append(event)


def _patch_command(
    monkeypatch: pytest.MonkeyPatch,
    script: Path,
) -> None:
    monkeypatch.setattr(
        "msgloom.ai.runner.build_sandbox_command",
        lambda _runtime, _worker, _state, _work: [sys.executable, str(script)],
    )


def test_result_waits_for_trace_and_child_env_is_exact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Trace persistence completes before a structured result is returned."""
    script = tmp_path / "success.py"
    script.write_text(
        "import json, os, sys\n"
        "json.load(sys.stdin)\n"
        "print(json.dumps({'type':'trace','kind':'system',"
        "'name':'init','text':'init','data':{}}), flush=True)\n"
        "out={'home':os.environ.get('HOME'),"
        "'source_secret':os.environ.get('SYNTHETIC_SOURCE_SECRET'),"
        "'region':os.environ.get('AWS_REGION')}\n"
        "print(json.dumps({'type':'final','ok':True,"
        "'structured_output':out}), flush=True)\n"
    )
    _patch_command(monkeypatch, script)
    monkeypatch.setenv("SYNTHETIC_SOURCE_SECRET", "must-not-cross-boundary")
    sink = _Sink()
    response = asyncio.run(_runner(tmp_path).run(_attempt(), sink))
    if not response.acceptable_for_semantic_validation:
        pytest.fail("complete structured output should reach parent validation")
    if len(sink.events) != 1:
        pytest.fail("trace write was not awaited before return")
    expected = {
        "home": "/state",
        "source_secret": None,
        "region": "synthetic-region",
    }
    if response.structured_output != expected:
        pytest.fail("AI child environment was not the exact minimal environment")


def test_malformed_and_oversized_output_stay_failed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed child output never becomes a semantic fallback."""
    script = tmp_path / "malformed.py"
    script.write_text("print('not-json', flush=True)\n")
    _patch_command(monkeypatch, script)
    response = asyncio.run(_runner(tmp_path).run(_attempt(output=32), _Sink()))
    if response.status is not AttemptStatus.FAILED:
        pytest.fail("malformed worker output must remain failed")
    if response.failure_code != "ipc-failure":
        pytest.fail("malformed output has the wrong failure classification")


async def _controlled_timeout_case(
    runner: AIRunner,
    attempt: AnalysisAttempt,
    sink: _Sink,
    pid_file: Path,
) -> AnalysisResponse:
    expired = False

    def controlled_remaining(_deadline: float) -> float:
        return 0.0 if expired else 1.0

    async def wait_for_startup_barrier() -> None:
        while not pid_file.exists():
            await asyncio.sleep(0)

    with patch("msgloom.ai.runner.remaining", controlled_remaining):
        task = asyncio.create_task(runner.run(attempt, sink))
        await asyncio.wait_for(wait_for_startup_barrier(), 1)
        expired = True
        return await asyncio.wait_for(task, 2)


def test_timeout_rejects_partial_result_and_reaps_group(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A terminal-looking partial result cannot survive the timeout gate."""
    pid_file = tmp_path / "child.pid"
    script = tmp_path / "timeout.py"
    script.write_text(
        "import json, subprocess, sys, time\n"
        "json.load(sys.stdin)\n"
        "child=subprocess.Popen(['sleep','60'])\n"
        f"open({str(pid_file)!r},'w').write(str(child.pid))\n"
        "print(json.dumps({'type':'final','ok':True,"
        "'structured_output':{'value':'too-early'}}), flush=True)\n"
        "time.sleep(60)\n"
    )
    _patch_command(monkeypatch, script)
    response = asyncio.run(
        _controlled_timeout_case(
            _runner(tmp_path),
            _attempt(timeout=10),
            _Sink(),
            pid_file,
        )
    )
    if response.status is not AttemptStatus.TIMED_OUT:
        pytest.fail("result emitted before timeout must still be rejected")
    attempt_dirs = [path for path in tmp_path.iterdir() if path.is_dir()]
    if len(attempt_dirs) != 1:
        pytest.fail("attempt storage was not preserved after timeout")
    if not (attempt_dirs[0] / "state").is_dir():
        pytest.fail("isolated state directory was not preserved")
    if not (attempt_dirs[0] / "work").is_dir():
        pytest.fail("isolated work directory was not preserved")
    pid = int(pid_file.read_text())
    if Path(f"/proc/{pid}").exists():
        pytest.fail("timeout left a descendant process alive")


class _BlockingSink:
    def __init__(self) -> None:
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.completed = False
        self.event: TraceEvent | None = None

    async def write(self, event: TraceEvent) -> None:
        self.event = event
        self.entered.set()
        await self.release.wait()
        self.completed = True


async def _cancel_case(runner: AIRunner, attempt: AnalysisAttempt, sink: _BlockingSink):
    task = asyncio.create_task(runner.run(attempt, sink))
    await asyncio.wait_for(sink.entered.wait(), 1)
    task.cancel()
    task.cancel()
    await asyncio.sleep(0)
    sink.release.set()
    with pytest.raises(asyncio.CancelledError):
        await task


def test_repeated_cancel_drains_accepted_trace_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repeated cancellation cannot abandon an accepted trace write."""
    script = tmp_path / "cancel.py"
    script.write_text(
        "import json, sys, time\n"
        "json.load(sys.stdin)\n"
        "print(json.dumps({'type':'trace','kind':'system',"
        "'name':'started','text':'started'}), flush=True)\n"
        "time.sleep(60)\n"
    )
    _patch_command(monkeypatch, script)
    sink = _BlockingSink()
    asyncio.run(_cancel_case(_runner(tmp_path), _attempt(), sink))
    if not sink.completed:
        pytest.fail("accepted trace persistence was abandoned on cancellation")


def test_structured_output_byte_limit_is_enforced(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A valid-looking terminal object over the byte bound remains failed."""
    script = tmp_path / "oversized.py"
    script.write_text(
        "import json, sys\n"
        "json.load(sys.stdin)\n"
        "print(json.dumps({'type':'final','ok':True,"
        "'structured_output':{'value':'x'*200}}), flush=True)\n"
    )
    _patch_command(monkeypatch, script)
    response = asyncio.run(_runner(tmp_path).run(_attempt(output=64), _Sink()))
    if response.status is not AttemptStatus.FAILED:
        pytest.fail("oversized structured output must remain failed")
    if response.failure_code != "ipc-failure":
        pytest.fail("oversized output has the wrong failure classification")
