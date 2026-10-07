"""Check the final diagnostic deadline and accepted cleanup failure gate."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from msgloom.ai import AttemptStatus, TraceEvent
from msgloom.ai.sandbox import terminate_and_reap
from tests.ai_boundary.test_lifecycle_repair import _attempt, _runner, _Sink


def _script(root: Path, *, stderr: bool) -> Path:
    path = root / "synthetic_worker.py"
    diagnostic = "sys.stderr.write('synthetic diagnostic')\n" if stderr else ""
    path.write_text(
        "import json,sys\njson.load(sys.stdin)\n"
        + diagnostic
        + "print(json.dumps({'type':'final','ok':True,"
        "'structured_output':{'synthetic':True}}),flush=True)\n"
    )
    return path


def test_late_stderr_diagnostic_cannot_authorize_output(tmp_path: Path) -> None:
    """Even a parent diagnostic is durable work inside the acceptance deadline."""

    async def exercise() -> None:
        entered = asyncio.Event()
        release = asyncio.Event()
        expired = False
        saved: list[TraceEvent] = []

        class Sink:
            async def write(self, event: TraceEvent) -> None:
                entered.set()
                await release.wait()
                saved.append(event)

        script = _script(tmp_path, stderr=True)
        with (
            patch(
                "msgloom.ai.runner.build_sandbox_command",
                return_value=[sys.executable, str(script)],
            ),
            patch(
                "msgloom.ai.runner.remaining",
                side_effect=lambda _deadline: 0.0 if expired else 1.0,
            ),
        ):
            task = asyncio.create_task(_runner(tmp_path).run(_attempt(5), Sink()))
            await asyncio.wait_for(entered.wait(), 3)
            expired = True
            release.set()
            response = await asyncio.wait_for(task, 3)
        if response.status is not AttemptStatus.TIMED_OUT:
            pytest.fail("diagnostic persistence after deadline admitted output")
        if response.acceptable_for_semantic_validation:
            pytest.fail("late diagnostic output remained semantically eligible")
        if [event.sequence for event in saved] != list(range(response.trace_count)):
            pytest.fail("diagnostic deadline changed the durable trace sequence")
        if not saved or saved[0].name != "child-stderr":
            pytest.fail("the synthetic stderr diagnostic did not reach its sink")

    asyncio.run(exercise())


def test_cleanup_failure_cannot_be_ignored_after_other_work_drains(
    tmp_path: Path,
) -> None:
    """A failed cleanup gate propagates after reaping the synthetic child."""

    async def exercise() -> None:
        reaped: list[asyncio.subprocess.Process] = []

        async def fail_after_reaping(
            process: asyncio.subprocess.Process, grace: float
        ) -> None:
            await terminate_and_reap(process, grace)
            reaped.append(process)
            raise RuntimeError("synthetic_cleanup_failure")

        script = _script(tmp_path, stderr=False)
        with (
            patch(
                "msgloom.ai.runner.build_sandbox_command",
                return_value=[sys.executable, str(script)],
            ),
            patch("msgloom.ai.lifecycle.terminate_and_reap", fail_after_reaping),
            pytest.raises(RuntimeError, match="synthetic_cleanup_failure"),
        ):
            await _runner(tmp_path).run(_attempt(5), _Sink())
        if len(reaped) != 1 or reaped[0].returncode is None:
            pytest.fail("cleanup failure left an accepted child running")

    asyncio.run(exercise())
