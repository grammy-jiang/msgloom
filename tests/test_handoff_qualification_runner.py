"""Prove qualification evidence fails closed with harmless subprocesses."""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from scripts.handoff_qualification import (
    cached_precommit,
    execution,
    live_lsp,
    process_boundary,
)


def _equal(actual: object, expected: object) -> None:
    """Compare observable results using an explicit pytest failure."""
    if actual != expected:
        pytest.fail(f"expected {expected!r}; got {actual!r}")


def _git(root: Path, *args: str) -> str:
    """Run a bounded Git command in an isolated fixture repository."""
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    return result.stdout.strip()


@pytest.fixture
def repository(tmp_path: Path) -> tuple[Path, str]:
    """Create one committed candidate without using the real checkout."""
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-q")
    (root / "tracked.txt").write_text("initial\n")
    _git(root, "add", "tracked.txt")
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


def _gate(name: str = "fake", code: str = "print('harmless')", **kwargs):
    """Create a gate using the current test interpreter."""
    return execution.Gate(name, (sys.executable, "-c", code), **kwargs)


def _run(repository, tmp_path: Path, gates, **kwargs):
    """Execute only explicit fake commands against a temporary repository."""
    root, sha = repository
    output = tmp_path / "evidence"
    result = execution.run_plan(root, output, sha, sha, gates, **kwargs)
    saved = json.loads((output / "manifest.json").read_text())
    _equal(result, saved)
    return result


@pytest.mark.linux_cgroup_v2
def test_nonzero_preserves_stderr_and_does_not_retry(
    repository, tmp_path: Path
) -> None:
    """A nonzero exit remains failed and later independent gates can run."""
    code = "import sys; print('failure detail', file=sys.stderr); sys.exit(7)"
    result = _run(repository, tmp_path, [_gate(code=code), _gate("later")])
    first = result["gates"][0]
    if first["status"] != "failed" or first["exit_code"] != 7:
        pytest.fail("nonzero gate was promoted to success")
    if "failure detail" not in Path(first["stderr"]).read_text():
        pytest.fail("failure stderr was lost")
    if first["attempts"] != 1 or result["status"] != "failed":
        pytest.fail("failed execution was retried or accepted")
    _equal(result["gates"][1]["status"], "passed")


@pytest.mark.linux_cgroup_v2
@pytest.mark.parametrize(
    "command",
    [
        ("/missing/qualification-executable",),
        (sys.executable, "-c", "raise SystemExit(69)"),
    ],
)
def test_missing_executable_is_unavailable(repository, tmp_path: Path, command) -> None:
    """Absence is durable evidence, never a zero-exit substitute."""
    gate = execution.Gate("missing", command)
    result = _run(repository, tmp_path, [gate])
    _equal(result["gates"][0]["status"], "unavailable")
    if result["status"] == "automated_passed":
        pytest.fail("an unavailable gate was accepted")


@pytest.mark.linux_cgroup_v2
def test_dependency_failure_blocks_dependent_gate(repository, tmp_path: Path) -> None:
    """A failed runtime probe prevents its suite from executing."""
    marker = tmp_path / "must-not-exist"
    result = _run(
        repository,
        tmp_path,
        [
            _gate("runtime", "raise SystemExit(4)"),
            _gate(
                "suite",
                f"open({str(marker)!r}, 'w').close()",
                dependencies=("runtime",),
            ),
        ],
    )
    if marker.exists() or result["gates"][1]["status"] != "blocked":
        pytest.fail("suite executed after its prerequisite failed")


@pytest.mark.linux_cgroup_v2
@pytest.mark.parametrize("mutation", ["worktree", "head", "untracked"])
def test_candidate_mutation_stops_remaining_gates(
    repository, tmp_path: Path, mutation: str
) -> None:
    """A commit or uncommitted candidate change invalidates evidence."""
    if mutation == "head":
        code = (
            "import subprocess; subprocess.run(['git','-c','user.name=Fixture',"
            "'-c','user.email=fixture@example.test','commit','--allow-empty',"
            "'-qm','changed'],check=True)"
        )
    else:
        name = "tracked.txt" if mutation == "worktree" else "new.py"
        code = f"open({name!r}, 'w').write('changed')"
    result = _run(repository, tmp_path, [_gate(code=code), _gate("later")])
    _equal(result["status"], "candidate_changed")
    _equal(result["gates"][1]["status"], "not_run")


@pytest.mark.linux_cgroup_v2
def test_timeout_preserves_partial_logs(repository, tmp_path: Path) -> None:
    """Timeout retains emitted evidence and leaves later gates unexecuted."""
    child_code = (
        "import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); "
        "time.sleep(30)"
    )
    code = (
        "import subprocess,sys,time; "
        f"p=subprocess.Popen([sys.executable,'-c',{child_code!r}]); "
        "print(p.pid,flush=True); print('partial',flush=True); time.sleep(30)"
    )
    result = _run(repository, tmp_path, [_gate(code=code, timeout=0.3), _gate("later")])
    gate = result["gates"][0]
    if gate["status"] != "timed_out" or result["status"] != "interrupted":
        pytest.fail("timeout was accepted or hidden")
    if "partial" not in Path(gate["stdout"]).read_text():
        pytest.fail("partial stdout disappeared")
    _equal(result["gates"][1]["status"], "not_run")
    child = int(Path(gate["stdout"]).read_text().splitlines()[0])
    state = Path(f"/proc/{child}/stat")
    deadline = time.monotonic() + 0.5
    while state.exists() and time.monotonic() < deadline:
        if state.read_text().rsplit(")", 1)[1].split()[0] == "Z":
            break
        time.sleep(0.01)
    if state.exists() and state.read_text().rsplit(")", 1)[1].split()[0] != "Z":
        os.kill(child, signal.SIGKILL)
        pytest.fail("timeout left a SIGTERM-ignoring child running")


@pytest.mark.linux_cgroup_v2
def test_signal_interruption_is_durable(repository, tmp_path: Path) -> None:
    """An interrupted child cannot leave a success-shaped manifest."""
    code = f"import os,signal; os.kill(os.getpid(), {signal.SIGTERM})"
    result = _run(repository, tmp_path, [_gate(code=code), _gate("later")])
    _equal(result["gates"][0]["status"], "interrupted")
    _equal(result["gates"][1]["status"], "not_run")


@pytest.mark.linux_cgroup_v2
def test_complete_manifest_never_claims_external_review(
    repository, tmp_path: Path
) -> None:
    """Successful fake gates retain identity, artifacts and blockers."""
    root, sha = repository
    result = _run(repository, tmp_path, [_gate(), _gate("second")])
    _equal(result["status"], "automated_passed")
    if result["candidate_sha"] != sha or result["base_sha"] != sha:
        pytest.fail("exact candidate/base identity is missing")
    _equal(result["qualification_status"], "blocked")
    _equal(result["external_review"]["status"], "required")
    for gate in result["gates"]:
        for key in (
            "command",
            "started_at",
            "finished_at",
            "exit_code",
            "stdout",
            "stderr",
            "artifacts",
            "attempts",
        ):
            if key not in gate:
                pytest.fail(f"missing gate evidence field: {key}")
    _equal((root / "completion.json").exists(), False)


@pytest.mark.linux_cgroup_v2
@pytest.mark.parametrize("kind", ["missing", "malformed", "skipped", "failure"])
def test_required_junit_must_be_complete(repository, tmp_path: Path, kind: str) -> None:
    """Zero exit alone cannot prove tests executed successfully."""
    xml = {
        "missing": None,
        "malformed": "<testsuite",
        "skipped": '<testsuite><testcase name="x"><skipped/></testcase></testsuite>',
        "failure": '<testsuite><testcase name="x"><failure/></testcase></testsuite>',
    }[kind]
    target = tmp_path / "junit.xml"
    code = "pass" if xml is None else f"open({str(target)!r}, 'w').write({xml!r})"
    result = _run(repository, tmp_path, [_gate(code=code, junit=str(target))])
    if result["gates"][0]["status"] == "passed":
        pytest.fail(f"incomplete JUnit evidence accepted: {kind}")


@pytest.mark.linux_cgroup_v2
def test_junit_counts_and_artifact_hashes_are_recorded(
    repository, tmp_path: Path
) -> None:
    """Executed testcase counts and immutable log digests are retained."""
    xml = '<testsuite><testcase classname="tests.test_a" name="test_ok"/></testsuite>'
    target = tmp_path / "results.xml"
    code = f"open({str(target)!r}, 'w').write({xml!r})"
    result = _run(repository, tmp_path, [_gate(code=code, junit=str(target))])
    gate = result["gates"][0]
    if gate["counts"]["tests"] != 1 or gate["status"] != "passed":
        pytest.fail("successful test count was not preserved")
    if not all(len(item["sha256"]) == 64 for item in gate["artifacts"]):
        pytest.fail("artifact digest is absent")


def test_dirty_or_wrong_candidate_is_blocked_before_commands(
    repository, tmp_path: Path
) -> None:
    """Preflight cannot run commands against an unbound candidate."""
    root, _sha = repository
    (root / "tracked.txt").write_text("dirty")
    marker = tmp_path / "marker"
    result = _run(
        repository, tmp_path, [_gate(code=f"open({str(marker)!r}, 'w').close()")]
    )
    if result["status"] != "blocked" or marker.exists():
        pytest.fail("dirty preflight ran a command")
    _equal(result["gates"][0]["status"], "not_run")


@pytest.mark.linux_cgroup_v2
def test_existing_output_is_never_overwritten(repository, tmp_path: Path) -> None:
    """A second invocation cannot retry into the old evidence directory."""
    _run(repository, tmp_path, [_gate()])
    with pytest.raises(FileExistsError):
        _run(repository, tmp_path, [_gate()])


@pytest.mark.linux_cgroup_v2
def test_shared_lock_blocks_competing_runner(repository, tmp_path: Path) -> None:
    """A separate process holding the repository lock prevents execution."""
    import fcntl

    root, _sha = repository
    lock = execution.lock_path(root)
    with lock.open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = _run(repository, tmp_path, [_gate()])
    _equal(result["status"], "blocked")


@pytest.mark.linux_cgroup_v2
def test_credentials_and_pytest_overrides_are_not_inherited(
    repository, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Inherited credentials and addopts cannot alter the recorded plan."""
    monkeypatch.setenv("MSGLOOM_MS_CLIENT_ID", "private-placeholder")
    monkeypatch.setenv("PYTEST_ADDOPTS", "--maxfail=1")
    code = (
        "import os; "
        "print(os.environ.get('MSGLOOM_MS_CLIENT_ID')); "
        "print(os.environ.get('PYTEST_ADDOPTS'))"
    )
    result = _run(repository, tmp_path, [_gate(code=code)])
    output = Path(result["gates"][0]["stdout"]).read_text()
    _equal(output, "None\nNone\n")


def test_default_cli_lists_without_creating_runtime_evidence(tmp_path: Path) -> None:
    """The ordinary invocation must not execute any gate."""
    script = Path(__file__).resolve().parents[1] / "scripts/qualify_a1_a2_handoff.py"
    output = tmp_path / "uncreated"
    completed = subprocess.run(
        [sys.executable, str(script), "--output-root", str(output)],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if completed.returncode != 0 or output.exists():
        pytest.fail("default CLI executed gates or failed to list")
    plan = json.loads(completed.stdout)
    names = {gate["name"] for gate in plan["gates"]}
    required = {
        f"{kind}{version}"
        for version in ("312", "313", "314")
        for kind in ("normal", "exclusive", "fastmcp")
    } | {
        "a1",
        "ruff",
        "ruff_version",
        "format",
        "pyright",
        "contracts",
        "diff",
        "precommit",
        "reverse_imports",
        "spider_coverage",
        "live_lsp",
    }
    if not required <= names:
        pytest.fail(f"required gates missing: {sorted(required - names)}")
    _equal(plan["external_review"]["status"], "required")


def test_cached_precommit_never_creates_or_installs_missing_cache(
    tmp_path: Path,
) -> None:
    """Cache absence must remain unavailable without any bootstrap write."""
    location = tmp_path / "absent"
    with pytest.raises(RuntimeError):
        cached_precommit.cached_repository(location, "repo", "revision")
    _equal(location.exists(), False)


@pytest.mark.parametrize("reports", [True, False])
def test_live_lsp_requires_diagnostics_for_every_open_file(
    tmp_path: Path, reports: bool
) -> None:
    """An initialized server without document diagnostics cannot pass."""
    path = tmp_path / "source.py"
    path.write_text("value = 1\n")
    server = tmp_path / "server.py"
    server.write_text(
        "import json,sys\n"
        "def send(data):\n"
        " raw=json.dumps(data).encode()\n"
        " sys.stdout.buffer.write(f'Content-Length: {len(raw)}\\r\\n\\r\\n'.encode()+raw)\n"
        " sys.stdout.buffer.flush()\n"
        "while True:\n"
        " headers={}\n"
        " while True:\n"
        "  line=sys.stdin.buffer.readline()\n"
        "  if not line: sys.exit(0)\n"
        "  if line==b'\\r\\n': break\n"
        "  key,value=line.decode().split(':',1); headers[key.lower()]=value.strip()\n"
        " data=json.loads(sys.stdin.buffer.read(int(headers['content-length'])))\n"
        " if 'id' in data: send({'id':data['id'],'result':{}})\n"
        f" if {reports!r} and data.get('method')=='textDocument/didOpen':\n"
        "  doc=data['params']['textDocument']\n"
        "  send({'method':'textDocument/publishDiagnostics','params':"
        "{'uri':doc['uri'],'version':1,'diagnostics':[]}})\n"
        " if data.get('method')=='exit': sys.exit(0)\n"
    )
    result = live_lsp.diagnose(
        tmp_path,
        sys.executable,
        [path],
        server_command=(sys.executable, str(server)),
        wait_seconds=0.6,
        settle_seconds=0.05,
    )
    if bool(result["missing_files"]) == reports:
        pytest.fail("LSP accepted silence or lost complete live diagnostics")


@pytest.mark.linux_cgroup_v2
def test_missing_coverage_xml_cannot_pass(repository, tmp_path: Path) -> None:
    """Coverage is required in addition to a zero command exit."""
    result = _run(repository, tmp_path, [_gate(coverage=str(tmp_path / "absent.xml"))])
    _equal(result["gates"][0]["status"], "failed")


def test_wrong_exact_candidate_is_blocked(repository, tmp_path: Path) -> None:
    """Even a clean checkout must match the requested full candidate SHA."""
    root, sha = repository
    result = execution.run_plan(root, tmp_path / "wrong", sha, "f" * 40, [_gate()])
    if result["status"] != "blocked" or result["gates"][0]["attempts"] != 0:
        pytest.fail("a different clean HEAD was executed")


@pytest.mark.linux_cgroup_v2
def test_abrupt_runner_loss_leaves_linked_running_evidence(repository, tmp_path):
    """A killed recorder leaves partial logs linked and never marks success."""
    root, sha = repository
    output, marker = tmp_path / "partial", tmp_path / "pid"
    code = (
        "import os,time; from pathlib import Path; "
        f"Path({str(marker)!r}).write_text(str(os.getpid())); "
        "print('partial',flush=True); time.sleep(30)"
    )
    driver = (
        "from pathlib import Path; "
        "from scripts.handoff_qualification.execution import Gate,run_plan; "
        f"run_plan(Path({str(root)!r}),Path({str(output)!r}),{sha!r},{sha!r},"
        f"[Gate('active',({sys.executable!r},'-c',{code!r}))])"
    )
    process = subprocess.Popen([sys.executable, "-c", driver])
    try:
        deadline = time.monotonic() + 10
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        if not marker.exists():
            pytest.fail("fixture gate did not start")
        process.kill()
        process.wait(timeout=5)
        result = json.loads((output / "manifest.json").read_text())
        gate = result["gates"][0]
        if result["status"] != "running" or gate["status"] != "running":
            pytest.fail("abrupt loss was promoted to terminal success")
        if not gate["stdout"] or not gate.get("pid") or gate["attempts"] != 1:
            pytest.fail("running manifest lost its partial artifact/process links")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        if marker.exists():
            try:
                os.killpg(int(marker.read_text()), signal.SIGKILL)
            except ProcessLookupError:
                pass
        manifest = output / "manifest.json"
        if manifest.is_file():
            gate = json.loads(manifest.read_text())["gates"][0]
            boundary = gate.get("ownership_boundary", {}).get("path")
            if boundary:
                deadline = time.monotonic() + 1
                path = Path(boundary)
                while path.exists() and time.monotonic() < deadline:
                    process_boundary.discard_empty(path)
                    if path.exists():
                        time.sleep(0.01)
