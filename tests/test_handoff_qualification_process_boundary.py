"""Exercise gate ownership across process-group and session escape."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.handoff_qualification import execution


def _equal(actual: object, expected: object) -> None:
    """Fail explicitly when observable values differ."""
    if actual != expected:
        pytest.fail(f"expected {expected!r}; got {actual!r}")


def _git(root: Path, *args: str) -> str:
    """Run one bounded Git command in an isolated fixture repository."""
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return result.stdout.strip()


@pytest.fixture
def repository(tmp_path: Path) -> tuple[Path, str]:
    """Create one exact committed candidate for runner tests."""
    root = tmp_path / "repository"
    root.mkdir()
    (root / "tracked.txt").write_text("fixture\n")
    _git(root, "init", "-q")
    _git(root, "add", ".")
    _git(
        root,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.test",
        "commit",
        "-qm",
        "fixture",
    )
    return root, _git(root, "rev-parse", "HEAD")


def _alive(pid: int) -> bool:
    """Return whether a PID names a live, non-zombie process."""
    path = Path(f"/proc/{pid}/stat")
    if not path.exists():
        return False
    try:
        return path.read_text().rsplit(")", 1)[1].split()[0] != "Z"
    except (OSError, IndexError):
        return False


def _kill(pid: int) -> None:
    """Bound fixture cleanup to the exact recorded PID."""
    if not _alive(pid):
        return
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _escaped_child_parent(*, interrupt_runner: bool = False) -> str:
    """Build a real parent that starts a SIGTERM-resistant new session."""
    child = (
        "import signal,time; "
        "signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(30)"
    )
    suffix = (
        "import os,signal; os.kill(os.getppid(),signal.SIGTERM); time.sleep(30)"
        if interrupt_runner
        else ""
    )
    return (
        "import subprocess,sys,time; "
        f"p=subprocess.Popen([sys.executable,'-c',{child!r}],start_new_session=True); "
        "print(p.pid,flush=True); "
        f"{suffix}"
    )


def _child_pid(record: dict) -> int:
    """Read the fixture child PID from retained gate stdout."""
    return int(Path(record["stdout"]).read_text().splitlines()[0])


def test_parent_exit_cleans_new_session_child_without_touching_unrelated(
    repository: tuple[Path, str],
    tmp_path: Path,
) -> None:
    """Normal exit fails hard when a gate-owned new-session child survives."""
    root, sha = repository
    unrelated = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        start_new_session=True,
    )
    child = None
    try:
        gates = [
            execution.Gate(
                "escaped",
                (sys.executable, "-c", _escaped_child_parent()),
            ),
            execution.Gate("later", (sys.executable, "-c", "print('later')")),
        ]
        result = execution.run_plan(
            root,
            tmp_path / "evidence",
            sha,
            sha,
            gates,
        )
        first = result["gates"][0]
        child = _child_pid(first)
        _equal(first["status"], "failed")
        _equal(first.get("hard_stop"), True)
        _equal(result["gates"][1]["status"], "not_run")
        survivor = next(row for row in first["owned_survivors"] if row["pid"] == child)
        if (
            survivor["start_time"] <= 0
            or survivor["session"] != child
            or survivor["process_group"] != child
        ):
            pytest.fail("escaped child identity evidence is incomplete")
        if _alive(child):
            pytest.fail("new-session descendant survived normal gate cleanup")
        if unrelated.poll() is not None:
            pytest.fail("runner cleanup touched an unrelated pre-existing process")
    finally:
        if child is not None:
            _kill(child)
        if unrelated.poll() is None:
            unrelated.kill()
        unrelated.wait(timeout=5)


def test_timeout_cleans_sigterm_resistant_new_session_child(
    repository: tuple[Path, str],
    tmp_path: Path,
) -> None:
    """Timeout cleanup owns descendants even after they call setsid()."""
    root, sha = repository
    child = None
    code = _escaped_child_parent() + "time.sleep(30)"
    try:
        gates = [
            execution.Gate("timeout", (sys.executable, "-c", code), timeout=0.3),
            execution.Gate("later", (sys.executable, "-c", "print('later')")),
        ]
        result = execution.run_plan(
            root,
            tmp_path / "timeout-evidence",
            sha,
            sha,
            gates,
        )
        first = result["gates"][0]
        child = _child_pid(first)
        _equal(first["status"], "timed_out")
        _equal(result["status"], "interrupted")
        _equal(result["gates"][1]["status"], "not_run")
        owned = {row["pid"]: row for row in first["owned_on_timeout"]}
        if child not in owned or owned[child]["start_time"] <= 0:
            pytest.fail("timeout evidence omitted the owned escaped child")
        if _alive(child):
            pytest.fail("timeout left a new-session descendant alive")
    finally:
        if child is not None:
            _kill(child)


def test_runner_interruption_cleans_new_session_child(
    repository: tuple[Path, str],
    tmp_path: Path,
) -> None:
    """Runner interruption tears down the same gate ownership boundary."""
    root, sha = repository
    child = None
    try:
        gates = [
            execution.Gate(
                "interrupt",
                (
                    sys.executable,
                    "-c",
                    _escaped_child_parent(interrupt_runner=True),
                ),
            ),
            execution.Gate("later", (sys.executable, "-c", "print('later')")),
        ]
        result = execution.run_plan(
            root,
            tmp_path / "interrupt-evidence",
            sha,
            sha,
            gates,
        )
        first = result["gates"][0]
        child = _child_pid(first)
        _equal(first["status"], "interrupted")
        _equal(result["status"], "interrupted")
        _equal(result["gates"][1]["status"], "not_run")
        owned = {row["pid"]: row for row in first["owned_on_interrupt"]}
        if child not in owned or owned[child]["start_time"] <= 0:
            pytest.fail("interrupt evidence omitted the owned escaped child")
        if _alive(child):
            pytest.fail("runner interruption left a new-session descendant alive")
    finally:
        if child is not None:
            _kill(child)
