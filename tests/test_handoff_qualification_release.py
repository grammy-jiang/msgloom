"""Keep user code behind the durable runner evidence boundary."""

from __future__ import annotations

import json
import os
import select
import subprocess
import sys
import time
from pathlib import Path

import pytest

from scripts.handoff_qualification import execution, process_boundary


@pytest.mark.parametrize("save_error", [None, OSError, FileNotFoundError])
def test_command_waits_for_atomic_linkage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    save_error: type[OSError] | None,
) -> None:
    """A paused or failed atomic replacement must never admit user code."""
    output = tmp_path / "evidence"
    output.mkdir()
    fifo = tmp_path / "executed"
    os.mkfifo(fifo)
    reader = os.open(fifo, os.O_RDONLY | os.O_NONBLOCK)
    record: dict = {"status": "running"}
    manifest = {"status": "running", "gates": [record]}
    real_replace = Path.replace
    seen_before_save = []

    def replace(path: Path, target: Path) -> Path:
        if path.name == "manifest.tmp" and "pid" in record:
            # Hold the actual publication boundary open. The command reports
            # execution through the FIFO; this read is bounded by a watchdog.
            ready, _, _ = select.select([reader], [], [], 0.5)
            seen_before_save.append(bool(ready))
            if save_error is not None:
                raise save_error("injected atomic manifest replacement failure")
        return real_replace(path, target)

    monkeypatch.setattr(Path, "replace", replace)
    code = f"from pathlib import Path; Path({str(fifo)!r}).write_text('executed')"
    gate = execution.Gate("release", (sys.executable, "-c", code), timeout=5)
    try:
        execution._execute(tmp_path, output, gate, record, manifest)
        if seen_before_save != [False]:
            pytest.fail("user command executed before linkage was published")
        expected = (
            "passed"
            if save_error is None
            else "unavailable"
            if save_error is FileNotFoundError
            else "failed"
        )
        if record["status"] != expected:
            pytest.fail(f"expected {expected}, got {record}")
        if save_error is not None:
            if os.read(reader, 100):
                pytest.fail("failed save released the user command")
        else:
            if os.read(reader, 100) != b"executed":
                pytest.fail("successful save did not release the user command")
            saved = json.loads((output / "manifest.json").read_text())["gates"][0]
            for key in ("pid", "ownership_boundary", "stdout", "stderr"):
                if saved.get(key) != record[key]:
                    pytest.fail(f"published linkage is missing {key}")
        if Path(record["ownership_boundary"]["path"]).exists():
            pytest.fail("gate boundary survived bounded cleanup")
    finally:
        os.close(reader)


def test_recorder_death_during_publication_never_executes(tmp_path: Path) -> None:
    """SIGKILL before replacement closes admission without running user code."""
    output = tmp_path / "evidence"
    output.mkdir()
    marker = tmp_path / "executed"
    gate_code = f"from pathlib import Path; Path({str(marker)!r}).touch()"
    driver = f"""
import os, signal
from pathlib import Path
from scripts.handoff_qualification import execution
record = {{'status': 'running'}}
manifest = {{'status': 'running', 'gates': [record]}}
replace = Path.replace
def pause(path, target):
    if path.name == 'manifest.tmp' and 'pid' in record:
        os.kill(os.getpid(), signal.SIGSTOP)
    return replace(path, target)
Path.replace = pause
execution._execute(Path({str(tmp_path)!r}), Path({str(output)!r}),
    execution.Gate('death', ({sys.executable!r}, '-c', {gate_code!r})),
    record, manifest)
"""
    process = subprocess.Popen([sys.executable, "-c", driver])
    boundary = None
    child = None
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            state = Path(f"/proc/{process.pid}/stat").read_text()
            if state.rsplit(")", 1)[1].split()[0] == "T":
                break
            time.sleep(0.01)
        else:
            pytest.fail("recorder did not stop at the publication boundary")
        pending = json.loads((output / "manifest.tmp").read_text())["gates"][0]
        child = pending["pid"]
        boundary = Path(pending["ownership_boundary"]["path"])
        process.kill()
        process.wait(timeout=5)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            stat = Path(f"/proc/{child}/stat")
            if (
                not stat.exists()
                or stat.read_text().rsplit(")", 1)[1].split()[0] == "Z"
            ):
                break
            time.sleep(0.01)
        else:
            pytest.fail("admitted wrapper survived recorder EOF")
        if marker.exists():
            pytest.fail("user command ran without published process linkage")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        if boundary is not None:
            if (boundary / "cgroup.kill").exists():
                (boundary / "cgroup.kill").write_text("1")
            process_boundary.discard_empty(boundary)


@pytest.mark.parametrize("release", [b"", b"0", b"1extra"])
def test_missing_or_invalid_release_never_executes(
    tmp_path: Path, release: bytes
) -> None:
    """An admitted wrapper rejects EOF and malformed release payloads."""
    marker = tmp_path / "executed"
    code = f"from pathlib import Path; Path({str(marker)!r}).touch()"
    boundary = process_boundary.create("invalid-release")
    ready_read, ready_write = os.pipe()
    release_read, release_write = os.pipe()
    process = None
    try:
        process = subprocess.Popen(
            process_boundary.wrapped_command(
                boundary, (sys.executable, "-c", code), ready_write, release_read
            ),
            pass_fds=(ready_write, release_read),
            stderr=subprocess.PIPE,
        )
        os.close(ready_write)
        ready_write = -1
        os.close(release_read)
        release_read = -1
        process_boundary.wait_ready(ready_read, process)
        if release:
            os.write(release_write, release)
        os.close(release_write)
        release_write = -1
        _, stderr = process.communicate(timeout=5)
        if process.returncode != 70 or marker.exists():
            pytest.fail(f"invalid release executed user code: {stderr!r}")
    finally:
        for descriptor in (ready_read, ready_write, release_read, release_write):
            if descriptor >= 0:
                os.close(descriptor)
        if process is not None:
            process_boundary.cleanup(boundary, process)
        else:
            process_boundary.discard_empty(boundary)
