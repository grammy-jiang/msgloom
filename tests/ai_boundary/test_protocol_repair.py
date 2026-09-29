"""Regression tests for strict AI worker protocol and durable trace failures."""

from __future__ import annotations

import asyncio
import math
import sys
from pathlib import Path

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
from msgloom.ai.ipc import decode_event
from msgloom.contracts import AttemptIdentity, VersionRef


def _ref(kind: str, identity: str) -> VersionRef:
    return VersionRef(kind, identity, "1")


def _attempt(
    *,
    timeout: float = 2.0,
    trace_events: int = 8,
    trace_bytes: int = 1024,
) -> AnalysisAttempt:
    return AnalysisAttempt(
        AttemptIdentity("repair-attempt"),
        (_ref("prepared", "input"),),
        _ref("context", "context"),
        _ref("prompt", "prompt"),
        _ref("schema", "schema"),
        _ref("model", "model"),
        "synthetic input",
        "",
        "trusted prompt",
        AttemptLimits(
            timeout,
            100,
            100,
            100,
            4096,
            trace_events,
            trace_bytes,
            2,
            700,
        ),
    )


def _runner(root: Path) -> AIRunner:
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
            0.05,
        ),
    )


def _patch_script(
    monkeypatch: pytest.MonkeyPatch,
    script: Path,
) -> None:
    monkeypatch.setattr(
        "msgloom.ai.runner.build_sandbox_command",
        lambda *_args: [sys.executable, str(script)],
    )


class _Sink:
    def __init__(self, fail_at: int | None = None) -> None:
        self.events: list[TraceEvent] = []
        self.fail_at = fail_at

    async def write(self, event: TraceEvent) -> None:
        if self.fail_at is not None and len(self.events) == self.fail_at:
            raise OSError("synthetic-private-value-must-not-escape")
        self.events.append(event)


@pytest.mark.parametrize(
    "payload",
    [
        b'{"type":"final","ok":true,"structured_output":{"x":NaN}}',
        b'{"type":"final","ok":true,"ok":true,"structured_output":{}}',
        b'{"type":"final","ok":true,"structured_output":{},"extra":1}',
        b'{"type":"trace","kind":"system","name":"x","text":1,"data":{}}',
    ],
)
def test_decoder_rejects_nonfinite_duplicate_unknown_and_wrong_types(
    payload: bytes,
) -> None:
    """Malformed protocol values never cross into accepted output."""
    with pytest.raises((TypeError, ValueError)):
        decode_event(payload)


def test_limits_require_finite_positive_deadlines(tmp_path: Path) -> None:
    """NaN/Infinity cannot disable elapsed timeout or cleanup grace."""
    with pytest.raises(ValueError, match="finite"):
        _attempt(timeout=math.nan)
    with pytest.raises(ValueError, match="finite"):
        RuntimeIsolation(
            Path(sys.executable),
            Path("/usr/bin/bwrap"),
            (Path("/usr"),),
            Path("/bin/true"),
            {},
            tmp_path,
            math.inf,
        )


def test_nonzero_exit_rejects_earlier_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A success-shaped terminal event cannot override process failure."""
    script = tmp_path / "exit7.py"
    script.write_text(
        "import json,sys\n"
        "json.load(sys.stdin)\n"
        "print(json.dumps({'type':'final','ok':True,"
        "'structured_output':{'value':'synthetic'}}),flush=True)\n"
        "sys.exit(7)\n"
    )
    _patch_script(monkeypatch, script)
    response = asyncio.run(_runner(tmp_path).run(_attempt(), _Sink()))
    if response.status is not AttemptStatus.FAILED:
        pytest.fail("nonzero worker exit was accepted")
    if response.failure_code != "worker-exit":
        pytest.fail("nonzero worker exit lost its failure classification")


def test_final_then_trace_is_out_of_order_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No trace event may appear after the one terminal IPC event."""
    script = tmp_path / "order.py"
    script.write_text(
        "import json,sys\n"
        "json.load(sys.stdin)\n"
        "print(json.dumps({'type':'final','ok':True,"
        "'structured_output':{}}),flush=True)\n"
        "print(json.dumps({'type':'trace','kind':'system','name':'late',"
        "'text':'late','data':{}}),flush=True)\n"
    )
    _patch_script(monkeypatch, script)
    response = asyncio.run(_runner(tmp_path).run(_attempt(), _Sink()))
    if response.failure_code != "ipc-failure":
        pytest.fail("out-of-order worker event was not rejected")


def test_failed_sink_preserves_exact_prior_durable_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed durable write cannot permit acceptance or rewrite sequence."""
    script = tmp_path / "sink.py"
    script.write_text(
        "import json,sys\n"
        "json.load(sys.stdin)\n"
        "for n in range(2):\n"
        " print(json.dumps({'type':'trace','kind':'system','name':str(n),"
        "'text':'synthetic','data':{}}),flush=True)\n"
        "print(json.dumps({'type':'final','ok':True,"
        "'structured_output':{}}),flush=True)\n"
    )
    _patch_script(monkeypatch, script)
    sink = _Sink(fail_at=1)
    response = asyncio.run(_runner(tmp_path).run(_attempt(), sink))
    if response.failure_code != "trace-persistence-failure":
        pytest.fail("failed trace sink did not fail the attempt")
    if response.trace_count != 1 or len(sink.events) != 1:
        pytest.fail("failed sink changed the exact prior durable count")
    if sink.events[0].sequence != 0:
        pytest.fail("durable trace sequence history was rewritten")
    if "synthetic-private-value" in (response.failure_detail or ""):
        pytest.fail("opaque sink exception text escaped into diagnostics")


def test_diagnostic_never_exceeds_declared_trace_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A diagnostic that cannot fit is not counted as durably persisted."""
    script = tmp_path / "bad.py"
    script.write_text("print('bad',flush=True)\n")
    _patch_script(monkeypatch, script)
    sink = _Sink()
    response = asyncio.run(_runner(tmp_path).run(_attempt(trace_bytes=1), sink))
    if response.failure_code != "ipc-failure":
        pytest.fail("malformed IPC lost its failure classification")
    if response.trace_count != 0 or sink.events:
        pytest.fail("oversized diagnostic was counted as persisted")
