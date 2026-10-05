"""Exercise the reviewed Task15 preparation repair boundaries."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import sqlite3
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest
from coverage import Coverage

from scripts.handoff_qualification import audit, execution, plan


def _equal(actual: object, expected: object) -> None:
    """Fail explicitly when observable values differ."""
    if actual != expected:
        pytest.fail(f"expected {expected!r}; got {actual!r}")


def _git(root: Path, *args: str) -> str:
    """Run one bounded Git command in a fixture repository."""
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return result.stdout.strip()


def _commit_fixture(root: Path) -> str:
    """Commit all fixture files and return the exact candidate SHA."""
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
    return _git(root, "rev-parse", "HEAD")


def _alive(pid: int) -> bool:
    """Return whether a process remains live rather than zombie state."""
    path = Path(f"/proc/{pid}/stat")
    if not path.exists():
        return False
    try:
        return path.read_text().rsplit(")", 1)[1].split()[0] != "Z"
    except (OSError, IndexError):
        return False


def _precommit_python() -> str:
    """Resolve the installed pre-commit interpreter without provisioning."""
    executable = shutil.which("pre-commit")
    if not executable:
        pytest.fail("the pinned pre-commit executable is unavailable")
    first = Path(executable).read_text().splitlines()[0]
    if not first.startswith("#!/") or " " in first:
        pytest.fail("pre-commit does not expose a simple interpreter shebang")
    python = first[2:]
    version = subprocess.run(
        [
            python,
            "-c",
            "import importlib.metadata as m; print(m.version('pre-commit'))",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    ).stdout.strip()
    _equal(version, "4.6.2")
    return python


def _tree_state(root: Path) -> dict[str, tuple]:
    """Capture content and mutation-sensitive metadata for a cache tree."""
    state = {}
    for path in [root, *sorted(root.rglob("*"))]:
        metadata = path.lstat()
        digest = (
            hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        )
        state[str(path.relative_to(root))] = (
            stat.S_IMODE(metadata.st_mode),
            metadata.st_size,
            metadata.st_mtime_ns,
            metadata.st_ctime_ns,
            digest,
        )
    return state


def test_generated_pytest_gate_creates_coverage_parent_and_appends(
    tmp_path: Path,
) -> None:
    """Generated normal and exclusive gates share one real coverage file."""
    root = tmp_path / "repository"
    root.mkdir()
    for package in ("msgloom", "message_ingest", "microsoft_graph"):
        directory = root / package
        directory.mkdir()
        (directory / "__init__.py").write_text("")
    (root / "msgloom" / "sample.py").write_text(
        "def normal():\n    return 'normal'\n\n"
        "def exclusive():\n    return 'exclusive'\n"
    )
    tests = root / "tests"
    tests.mkdir()
    (tests / "test_sample.py").write_text(
        "import pytest\n"
        "from msgloom.sample import exclusive, normal\n\n"
        "def test_normal():\n"
        "    if normal() != 'normal': pytest.fail('normal failed')\n\n"
        "@pytest.mark.exclusive_state\n"
        "def test_exclusive():\n"
        "    if exclusive() != 'exclusive': pytest.fail('exclusive failed')\n"
    )
    (root / "pytest.ini").write_text(
        "[pytest]\nmarkers =\n    exclusive_state: serial fixture\n"
        "    fastmcp_compat: compatibility fixture\n"
    )
    sha = _commit_fixture(root)
    output = tmp_path / "evidence"
    wrapper = tmp_path / "python-wrapper"
    wrapper.write_text(
        f"#!{sys.executable}\n"
        "import os,sys\n"
        "from pathlib import Path\n"
        "parent=Path(os.environ['COVERAGE_FILE']).parent\n"
        "if not parent.is_dir(): raise SystemExit(97)\n"
        "os.execv(sys.executable,[sys.executable,*sys.argv[1:]])\n"
    )
    wrapper.chmod(0o755)
    normal = plan._pytest(
        output,
        "normal",
        str(wrapper),
        "runtime",
        ["tests/test_sample.py"],
        "not exclusive_state and not fastmcp_compat",
        "0",
        "tiny",
    )
    exclusive = plan._pytest(
        output,
        "exclusive",
        str(wrapper),
        "normal",
        ["tests/test_sample.py"],
        "exclusive_state and not fastmcp_compat",
        "0",
        "tiny",
        append=True,
    )
    gates = [
        execution.Gate("runtime", (sys.executable, "-c", "print('ready')")),
        normal,
        exclusive,
    ]
    result = execution.run_plan(root, output, sha, sha, gates)
    _equal([row["status"] for row in result["gates"]], ["passed"] * 3)
    data_file = output / "coverage-tiny" / ".coverage"
    if not data_file.is_file():
        pytest.fail("shared coverage data file was not created")
    coverage = Coverage(data_file=str(data_file))
    coverage.load()
    measured = coverage.get_data().lines(str(root / "msgloom" / "sample.py"))
    if not measured or not {2, 5} <= set(measured):
        pytest.fail("exclusive coverage did not append to normal coverage")


def test_parent_exit_with_descendant_hard_stops_and_cleans_group(
    tmp_path: Path,
) -> None:
    """A successful parent cannot leave a surviving gate descendant."""
    root = tmp_path / "repository"
    root.mkdir()
    (root / "tracked.txt").write_text("fixture\n")
    sha = _commit_fixture(root)
    child_code = (
        "import signal,time; "
        "signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(30)"
    )
    parent_code = (
        "import subprocess,sys; "
        f"p=subprocess.Popen([sys.executable,'-c',{child_code!r}]); "
        "print(p.pid, flush=True)"
    )
    gates = [
        execution.Gate("leaky", (sys.executable, "-c", parent_code)),
        execution.Gate("later", (sys.executable, "-c", "print('later')")),
    ]
    result = execution.run_plan(root, tmp_path / "evidence", sha, sha, gates)
    first = result["gates"][0]
    child = int(Path(first["stdout"]).read_text().strip())
    try:
        _equal(first["status"], "failed")
        _equal(first.get("hard_stop"), True)
        _equal(result["gates"][1]["status"], "not_run")
        deadline = time.monotonic() + 1
        while _alive(child) and time.monotonic() < deadline:
            time.sleep(0.01)
        if _alive(child):
            pytest.fail("runner left the SIGTERM-ignoring descendant alive")
    finally:
        if _alive(child):
            try:
                os.killpg(first["pid"], signal.SIGKILL)
            except ProcessLookupError:
                pass


def test_precommit_adapter_preserves_source_cache_metadata(
    tmp_path: Path,
) -> None:
    """Pinned pre-commit writes metadata only to its per-gate sandbox."""
    precommit_python = _precommit_python()
    root = tmp_path / "repository"
    root.mkdir()
    (root / "tracked.txt").write_text("fixture\n")
    (root / ".pre-commit-config.yaml").write_text(
        "repos:\n"
        "  - repo: https://example.invalid/immutable-hooks\n"
        "    rev: v1\n"
        "    hooks:\n"
        "      - id: immutable-system\n"
    )
    _commit_fixture(root)
    source = tmp_path / "source-cache"
    source.mkdir()
    cached_repo = source / "repo-source"
    cached_repo.mkdir()
    (cached_repo / ".pre-commit-hooks.yaml").write_text(
        "- id: immutable-system\n"
        "  name: immutable system\n"
        "  entry: /bin/true\n"
        "  language: system\n"
        "  pass_filenames: false\n"
    )
    with sqlite3.connect(source / "db.db") as database:
        database.executescript(
            "CREATE TABLE repos (repo TEXT NOT NULL, ref TEXT NOT NULL, "
            "path TEXT NOT NULL, PRIMARY KEY (repo, ref));"
            "CREATE TABLE configs (path TEXT NOT NULL PRIMARY KEY);"
        )
        database.execute(
            "INSERT INTO repos VALUES (?, ?, ?)",
            (
                "https://example.invalid/immutable-hooks",
                "v1",
                str(cached_repo),
            ),
        )
    before = _tree_state(source)
    sandbox = tmp_path / "writable-metadata"
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONPATH": str(Path(__file__).resolve().parents[1]),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PRE_COMMIT_SOURCE_CACHE": str(source),
            "PRE_COMMIT_HOME": str(sandbox),
        }
    )
    completed = subprocess.run(
        [
            precommit_python,
            "-m",
            "scripts.handoff_qualification.cached_precommit",
            "--all-files",
        ],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        pytest.fail(f"isolated cached pre-commit failed: {completed.stderr}")
    _equal(_tree_state(source), before)
    if not (sandbox / "db.db").is_file():
        pytest.fail("writable pre-commit metadata sandbox was not created")
    with sqlite3.connect(sandbox / "db.db") as database:
        configs = database.execute("SELECT path FROM configs").fetchall()
    _equal(configs, [(str((root / ".pre-commit-config.yaml").resolve()),)])


def _coverage_data(base: str, candidate: str) -> tuple[dict, set[tuple[str, str]]]:
    """Build one complete traceability map and its passing node set."""
    node = "tests/test_fixture.py::test_complete"
    data = {
        "base_sha": base,
        "candidate_sha": candidate,
        "spiders": {name: [node] for name in audit.SPIDERS},
        "scenarios": {str(index): [node] for index in range(1, 14)},
    }
    return data, {("tests.test_fixture", "test_complete")}


def test_validated_coverage_map_is_snapshotted_before_source_can_change(
    tmp_path: Path,
) -> None:
    """Retained map bytes survive deletion; stale maps fail closed."""
    base, candidate = "a" * 40, "b" * 40
    data, passed = _coverage_data(base, candidate)
    source = tmp_path / "coverage.json"
    original = json.dumps(data, sort_keys=True).encode()
    source.write_bytes(original)
    evidence = tmp_path / "evidence"
    record = audit.snapshot_validated_coverage_map(
        source,
        evidence,
        set(audit.SPIDERS),
        passed,
        base,
        candidate,
    )
    retained = Path(record["path"])
    _equal(retained.read_bytes(), original)
    source.write_text("{}")
    source.unlink()
    _equal(retained.read_bytes(), original)
    _equal(record["bytes"], len(original))
    _equal(record["sha256"], hashlib.sha256(original).hexdigest())

    stale, passed = _coverage_data(base, "c" * 40)
    stale_source = tmp_path / "stale.json"
    stale_source.write_text(json.dumps(stale))
    with pytest.raises(ValueError):
        audit.snapshot_validated_coverage_map(
            stale_source,
            tmp_path / "stale-evidence",
            set(audit.SPIDERS),
            passed,
            base,
            candidate,
        )
    if (tmp_path / "stale-evidence").exists():
        pytest.fail("stale map created retained evidence")

    invalid_source = tmp_path / "invalid.json"
    invalid_source.write_text("{")
    with pytest.raises(ValueError):
        audit.snapshot_validated_coverage_map(
            invalid_source,
            tmp_path / "invalid-evidence",
            set(audit.SPIDERS),
            passed,
            base,
            candidate,
        )
    if (tmp_path / "invalid-evidence").exists():
        pytest.fail("malformed map created retained evidence")


def test_spider_gate_declares_retained_coverage_map(tmp_path: Path) -> None:
    """The generated coverage gate must hash its retained map artifact."""
    parser = plan.parser()
    args = parser.parse_args(
        [
            "--source-root",
            str(Path(__file__).resolve().parents[1]),
            "--output-root",
            str(tmp_path / "evidence"),
            "--base",
            "a" * 40,
            "--candidate",
            "b" * 40,
            "--coverage-map",
            str(tmp_path / "coverage.json"),
        ]
    )
    gate = next(row for row in plan.build_plan(args) if row.name == "spider_coverage")
    expected = str(tmp_path / "evidence" / "spider_coverage" / "coverage-map.json")
    if expected not in gate.required_artifacts:
        pytest.fail("coverage map snapshot is absent from gate artifact requirements")


def test_required_artifact_is_hashed_in_gate_record(tmp_path: Path) -> None:
    """A declared retained artifact gets size and digest evidence."""
    root = tmp_path / "repository"
    root.mkdir()
    (root / "tracked.txt").write_text("fixture\n")
    sha = _commit_fixture(root)
    output = tmp_path / "evidence"
    artifact = output / "map" / "coverage-map.json"
    code = (
        f"from pathlib import Path; Path({str(artifact)!r}).write_bytes(b'exact-map')"
    )
    gate = execution.Gate(
        "map",
        (sys.executable, "-c", code),
        required_artifacts=(str(artifact),),
    )
    result = execution.run_plan(root, output, sha, sha, [gate])
    record = result["gates"][0]
    _equal(record["status"], "passed")
    retained = next(
        item for item in record["artifacts"] if item["path"] == str(artifact)
    )
    _equal(retained["bytes"], len(b"exact-map"))
    _equal(retained["sha256"], hashlib.sha256(b"exact-map").hexdigest())


def test_style_checker_rejects_mechanical_violations(tmp_path: Path) -> None:
    """The explicit checker rejects each mechanical repository rule."""
    python = tmp_path / "bad.py"
    python.write_text(
        '"""Summary shares the opening quote.\nBody.\n"""\n'
        "assert True\n"
        "# " + "x" * 80 + "\n"
    )
    markdown = tmp_path / "bad.md"
    markdown.write_text("x" * 80 + "\n")
    joined = "\n".join(audit.style_violations([python, markdown]))
    for phrase in (
        "multiline docstring opening quote must be separate",
        "Python assert prohibited",
        "comment prose is 82 columns",
        "prose is 80 columns",
    ):
        if phrase not in joined:
            pytest.fail(f"style checker missed: {phrase}")


def test_preparation_files_satisfy_repository_style_rules() -> None:
    """Owned preparation files obey repository structural and prose rules."""
    root = Path(__file__).resolve().parents[1]
    paths = [
        root / "docs/notes/a1-a2-qualification-checklist.md",
        root / "scripts/qualify_a1_a2_handoff.py",
        *sorted((root / "scripts/handoff_qualification").glob("*.py")),
        root / "tests/test_handoff_qualification_runner.py",
        root / "tests/test_handoff_qualification_repairs.py",
    ]
    violations = audit.style_violations(paths)
    if violations:
        pytest.fail("\n".join(violations))
