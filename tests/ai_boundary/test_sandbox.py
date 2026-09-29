"""Real bubblewrap namespace checks using only synthetic local files."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from msgloom.ai import RuntimeIsolation
from msgloom.ai.sandbox import build_sandbox_command


def test_bubblewrap_hides_unmounted_host_sentinel(tmp_path: Path) -> None:
    """The isolated worker cannot observe an arbitrary host path."""
    sentinel = tmp_path / "forbidden-settings-sentinel"
    sentinel.write_text("synthetic forbidden host content")
    worker = tmp_path / "worker.py"
    worker.write_text(
        "import json\n"
        "from pathlib import Path\n"
        f"print(json.dumps({{'visible': Path({str(sentinel)!r}).exists()}}))\n"
    )
    runtime = RuntimeIsolation(
        Path("/usr/bin/python3.13"),
        Path("/usr/bin/bwrap"),
        (Path("/usr"), Path("/lib")),
        Path("/bin/true"),
        {},
        tmp_path,
    )
    state = tmp_path / "state"
    work = tmp_path / "work"
    state.mkdir()
    work.mkdir()
    command = build_sandbox_command(runtime, worker, state, work)
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env={
            "HOME": "/state",
            "PATH": "/usr/bin:/bin",
            "PYTHONNOUSERSITE": "1",
        },
        timeout=5,
    )
    if completed.returncode != 0:
        pytest.fail(f"bubblewrap synthetic check failed: {completed.stderr}")
    result = json.loads(completed.stdout)
    if result != {"visible": False}:
        pytest.fail("host sentinel was visible inside the AI namespace")


def test_missing_isolation_fails_closed(tmp_path: Path) -> None:
    """A missing bubblewrap executable is not silently bypassed."""
    runtime = RuntimeIsolation(
        Path("/usr/bin/python3.13"),
        tmp_path / "missing-bwrap",
        (Path("/usr"),),
        Path("/bin/true"),
        {},
        tmp_path,
    )
    with pytest.raises(RuntimeError, match="bubblewrap"):
        build_sandbox_command(runtime, tmp_path / "worker.py", tmp_path, tmp_path)
