"""Host-portable tests for the scratch Kedro recipe and the opt-in gate.

None of these tests installs Kedro or opens a network connection. They check
the path refusals, the hash-pinned requirements file, the command lines, the
environment allowlist and the pytest gate. Two tests start a child pytest
process to prove the gate and to prove that default collection does not
import Kedro.
"""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / "scripts" / "research"


def _load(name: str) -> ModuleType:
    path = RESEARCH / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        pytest.fail(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


env_mod = _load("a2_f0_scratch_kedro_env")


def _child(args: list[str], extra: dict[str, str]) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("A2_F0_")}
    env.update(extra)
    env["PYTHONPATH"] = f"{RESEARCH}{os.pathsep}{ROOT}"
    return subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )


@pytest.mark.parametrize("inside", ["", "sub/venv", ".venv"])
def test_refuses_path_inside_a_repository(tmp_path: Path, inside: str) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(env_mod.ScratchEnvError):
        env_mod.check_venv_path(repo / inside, (repo,))


def test_refuses_any_dot_venv_component(tmp_path: Path) -> None:
    with pytest.raises(env_mod.ScratchEnvError):
        env_mod.check_venv_path(tmp_path / ".venv" / "x", ())


def test_refuses_interpreter_prefix(tmp_path: Path) -> None:
    with pytest.raises(env_mod.ScratchEnvError):
        env_mod.check_venv_path(tmp_path / "py", (), (tmp_path,))


def test_refuses_foreign_non_empty_directory(tmp_path: Path) -> None:
    (tmp_path / "keep.txt").write_text("data")
    with pytest.raises(env_mod.ScratchEnvError):
        env_mod.check_venv_path(tmp_path, ())


def test_refuses_empty_argument() -> None:
    with pytest.raises(env_mod.ScratchEnvError):
        env_mod.check_venv_path("", ())


def test_accepts_new_path_and_own_directory(tmp_path: Path) -> None:
    fresh = tmp_path / "fresh"
    if env_mod.check_venv_path(fresh, (ROOT,)) != fresh.resolve():
        pytest.fail("fresh path was altered")
    (tmp_path / env_mod.MARKER_FILE).write_text("{}")
    if env_mod.check_venv_path(tmp_path, ()) != tmp_path.resolve():
        pytest.fail("own directory was refused")


def test_real_guard_refuses_this_repository_and_its_venv() -> None:
    for candidate in (ROOT / "scratch", ROOT / ".venv", Path(sys.prefix)):
        with pytest.raises(env_mod.ScratchEnvError):
            env_mod.guarded_path(candidate)


def test_cli_requires_a_venv_argument() -> None:
    done = subprocess.run(
        [sys.executable, "-B", str(RESEARCH / "a2_f0_scratch_kedro_env.py"), "build"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if done.returncode == 0:
        pytest.fail("CLI accepted a missing venv argument")


def _requirement_blocks() -> list[str]:
    text = env_mod.REQUIREMENTS.read_text()
    body = "\n".join(
        line for line in text.splitlines() if not line.startswith("#")
    ).replace("\\\n", " ")
    return [" ".join(line.split()) for line in body.splitlines() if line.strip()]


def test_requirements_pin_kedro_and_hash_every_entry() -> None:
    entries = _requirement_blocks()
    names = {entry.split("==")[0] for entry in entries}
    if not {"kedro", "kedro-telemetry"} <= names:
        pytest.fail(f"missing top-level pins: {sorted(names)}")
    if not any(entry.startswith("kedro==1.7.0 ") for entry in entries):
        pytest.fail("kedro is not pinned to 1.7.0")
    for entry in entries:
        if not re.match(r"^[A-Za-z0-9_.\-]+==\S+ (; .+? )?--hash=sha256:", entry):
            pytest.fail(f"entry lacks pin and hash: {entry[:60]}")
        if len(re.findall(r"--hash=sha256:[0-9a-f]{64}\b", entry)) < 1:
            pytest.fail(f"entry has no valid hash: {entry[:60]}")
        if "://" in entry or "@" in entry:
            pytest.fail(f"entry names a URL or VCS source: {entry[:60]}")


def test_install_command_enforces_hashes_and_wheels_only() -> None:
    create, install = env_mod.build_commands(Path("/x/venv"))
    for flag in ("--no-config", "--python"):
        if flag not in create:
            pytest.fail(f"venv command lacks {flag}")
    for flag in ("--require-hashes", "--only-binary", "--no-deps", "--no-config"):
        if flag not in install:
            pytest.fail(f"install command lacks {flag}")
    if "--extra-index-url" in install or "--index-url" in install:
        pytest.fail("install command adds an index")
    if install[install.index("--default-index") + 1] != env_mod.PYPI_INDEX:
        pytest.fail("default index is not PyPI")


def test_environment_allowlist_drops_secrets() -> None:
    source = {"PATH": "/bin", "GITHUB_TOKEN": "s", "UV_INDEX_X_PASSWORD": "p"}
    result = env_mod.scrubbed_environment(source, {"A": "1"})
    if result != {"PATH": "/bin", "A": "1"}:
        pytest.fail(f"unexpected environment: {result}")


def test_gate_deselects_scratch_tests_without_opt_in() -> None:
    done = _child(
        ["-p", "a2_f0_pytest_gate", "-q", "tests/research/a2_f0_kedro_integration.py"],
        {},
    )
    if "9 deselected" not in done.stdout or " passed" in done.stdout:
        pytest.fail(f"gate did not deselect: {done.stdout[-300:]}")
    if "skipped" in done.stdout:
        pytest.fail("deselection reported skips")


def test_opt_in_without_interpreter_fails_loudly() -> None:
    done = _child(
        ["-p", "a2_f0_pytest_gate", "-q", "tests/research/a2_f0_kedro_integration.py"],
        {"A2_F0_KEDRO_OPT_IN": "1"},
    )
    if done.returncode == 0 or " passed" in done.stdout or "skipped" in done.stdout:
        pytest.fail(f"missing interpreter did not fail: {done.stdout[-300:]}")
    if "NOT VERIFIED" not in done.stdout:
        pytest.fail("failure message is missing")


def test_default_collection_does_not_import_kedro() -> None:
    code = (
        "import sys, pytest\n"
        "code = pytest.main(['-q', '--collect-only', '-p', 'no:cacheprovider',"
        " 'tests/research'])\n"
        "print('KEDRO_IMPORTED=' + str(any(m == 'kedro' or "
        "m.startswith('kedro.') for m in sys.modules)))\n"
        "print('EXIT=' + str(int(code)))\n"
    )
    done = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=ROOT,
        env={k: v for k, v in os.environ.items() if not k.startswith("A2_F0_")},
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    if "KEDRO_IMPORTED=False" not in done.stdout or "EXIT=0" not in done.stdout:
        pytest.fail(f"default collection result: {done.stdout[-400:]}")
    if "a2_f0_kedro_integration" in done.stdout:
        pytest.fail("default collection picked up the scratch Kedro tests")
