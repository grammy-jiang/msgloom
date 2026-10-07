"""Real bubblewrap namespace checks using only synthetic local files."""

from __future__ import annotations

import json
import subprocess
import sys
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
        "import json,sys\n"
        "from pathlib import Path\n"
        f"print(json.dumps({{'visible': Path({str(sentinel)!r}).exists(),"
        "'python':list(sys.version_info[:2])}))\n"
    )
    # Managed interpreters may live outside /usr. Mount their standard library
    # while keeping the synthetic host sentinel outside the trusted roots.
    roots = tuple(
        dict.fromkeys(
            (
                Path(sys.base_prefix),
                Path(sys.base_exec_prefix),
                Path("/usr"),
                Path("/lib"),
            )
        )
    )
    runtime = RuntimeIsolation(
        Path(sys.executable).resolve(),
        Path("/usr/bin/bwrap"),
        roots,
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
    if result != {"visible": False, "python": list(sys.version_info[:2])}:
        pytest.fail("namespace exposed the sentinel or used another Python")


def test_missing_isolation_fails_closed(tmp_path: Path) -> None:
    """A missing bubblewrap executable is not silently bypassed."""
    runtime = RuntimeIsolation(
        Path(sys.executable).resolve(),
        tmp_path / "missing-bwrap",
        (Path("/usr"),),
        Path("/bin/true"),
        {},
        tmp_path,
    )
    with pytest.raises(RuntimeError, match="bubblewrap"):
        build_sandbox_command(runtime, tmp_path / "worker.py", tmp_path, tmp_path)
