"""Execution tests for finite container deployment qualification."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import signal
import subprocess
import time
import zipfile
from pathlib import Path
from types import ModuleType

import pytest

from deployment.qualification import (
    Runner,
    Target,
    docker_run_argv,
    stage_context,
    validate_lock,
    validate_resources,
    validate_seccomp_profile,
    validate_targets,
    wheel_metadata,
)
from deployment.release import (
    ReleaseInputError,
    required_dependencies,
)

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = ROOT / "deployment" / "Dockerfile"
SCRIPT = ROOT / "scripts" / "qualify_container_package.py"
PYTHON = ROOT / ".venv" / "bin" / "python"
RESOURCE = "msgloom:reporting/templates/report.html.j2"


def _script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("container_qualifier", SCRIPT)
    if spec is None or spec.loader is None:
        pytest.fail("container qualification script is not importable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _digest(character: str = "a") -> str:
    return "sha256:" + character * 64


def _targets() -> tuple[Target, ...]:
    return tuple(
        Target(version, f"python:{version}-slim-bookworm@{_digest(str(index + 1))}")
        for index, version in enumerate(("3.12", "3.13", "3.14"))
    )


def _wheel(path: Path, requirements: tuple[str, ...] = ()) -> None:
    metadata = [
        "Metadata-Version: 2.4",
        "Name: msgloom",
        "Version: 0.1.0",
        *[f"Requires-Dist: {value}" for value in requirements],
        "",
    ]
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("msgloom/__init__.py", "")
        archive.writestr("msgloom/reporting/templates/report.html.j2", "synthetic")
        archive.writestr(
            "msgloom-0.1.0.dist-info/METADATA",
            "\n".join(metadata),
        )


def test_direct_script_help_works_without_pythonpath(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    completed = subprocess.run(
        [str(PYTHON), str(SCRIPT), "--help"],
        cwd=tmp_path,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=10,
    )
    if completed.returncode != 0 or "--runtime-lock" not in completed.stdout:
        pytest.fail(f"direct CLI invocation failed: {completed.stdout!r}")


def test_targets_require_exact_official_tag_order_and_digest() -> None:
    validate_targets(_targets())
    bad = list(_targets())
    bad[0] = Target("3.12", f"python:3.12.14-slim-bookworm@{_digest()}")
    with pytest.raises(ReleaseInputError, match="exact official"):
        validate_targets(tuple(bad))
    with pytest.raises(ReleaseInputError, match="ordered"):
        validate_targets(tuple(reversed(_targets())))


def test_wheel_filename_metadata_resources_and_markers(tmp_path: Path) -> None:
    wheel = tmp_path / "msgloom-0.1.0-py3-none-any.whl"
    _wheel(
        wheel,
        (
            "sqlalchemy>=2; python_version >= '3.12'",
            "winonly==1; sys_platform == 'win32'",
            "optional==1; extra == 'website'",
            "patchdep==1; python_full_version == '3.13.7'",
            "optionalpatch==1; extra == 'foo' and python_full_version == '3.13.7'",
        ),
    )
    metadata = wheel_metadata(wheel)
    if metadata.filename != wheel.name or metadata.version != "0.1.0":
        pytest.fail("wheel filename/version evidence was not exact")
    if validate_resources(metadata, (RESOURCE,)) != (RESOURCE,):
        pytest.fail("exact resource evidence was not retained")
    with pytest.raises(ReleaseInputError, match="at least one"):
        validate_resources(metadata, ())
    with pytest.raises(ReleaseInputError, match="relative/path"):
        validate_resources(metadata, ("msgloom:../secret",))
    required = required_dependencies(metadata, _targets())
    if required != {"patchdep", "sqlalchemy"}:
        pytest.fail(f"irrelevant markers became mandatory: {required!r}")
    invalid = tmp_path / "msgloom.whl"
    shutil.copyfile(wheel, invalid)
    with pytest.raises(ReleaseInputError, match="filename"):
        wheel_metadata(invalid)
    native = tmp_path / "msgloom-0.1.0-cp313-cp313-linux_aarch64.whl"
    shutil.copyfile(wheel, native)
    with pytest.raises(ReleaseInputError, match="universal"):
        wheel_metadata(native)


def test_release_inputs_have_finite_size_and_count_bounds(tmp_path: Path) -> None:
    wheel = tmp_path / "msgloom-0.1.0-py3-none-any.whl"
    with wheel.open("wb") as stream:
        stream.truncate(512 * 1024 * 1024 + 1)
    with pytest.raises(ReleaseInputError, match="512 MiB"):
        wheel_metadata(wheel)

    lock = tmp_path / "runtime.txt"
    with lock.open("wb") as stream:
        stream.truncate(4 * 1024 * 1024 + 1)
    with pytest.raises(ReleaseInputError, match="4 MiB"):
        validate_lock(lock, set())

    resources = tuple(f"msgloom:synthetic/{index}" for index in range(129))
    from deployment.release import validate_resource_specs

    with pytest.raises(ReleaseInputError, match="too many"):
        validate_resource_specs(resources)


def test_lock_rejects_directives_urls_and_covers_active_dependencies(
    tmp_path: Path,
) -> None:
    lock = tmp_path / "runtime.txt"
    lock.write_text(
        "sqlalchemy==2.0.54 --hash=sha256:" + "a" * 64 + "\n",
        encoding="utf-8",
    )
    if validate_lock(lock, {"sqlalchemy"}) != {"sqlalchemy"}:
        pytest.fail("valid exact lock entry was not retained")
    for bad in (
        "--index-url https://example.invalid/simple\n",
        "-e ../source\n",
        "demo @ https://example.invalid/demo.whl\n",
        "demo==1.0\n",
    ):
        lock.write_text(bad, encoding="utf-8")
        with pytest.raises(ReleaseInputError):
            validate_lock(lock, set())


def test_stage_preserves_valid_wheel_filename_and_digest_boundary(
    tmp_path: Path,
) -> None:
    wheel = tmp_path / "msgloom-0.1.0-py3-none-any.whl"
    _wheel(wheel)
    lock = tmp_path / "runtime.txt"
    lock.write_text("", encoding="utf-8")
    root = tmp_path / "out"
    root.mkdir()
    context = stage_context(root, DOCKERFILE, wheel, lock)
    names = sorted(item.name for item in context.iterdir())
    expected = [
        "Dockerfile",
        "Dockerfile.dockerignore",
        "msgloom-0.1.0-py3-none-any.whl",
        "runtime-requirements.txt",
    ]
    if names != expected:
        pytest.fail(f"build context was broader than admitted: {names!r}")


def test_seccomp_profile_must_be_confining_regular_json(tmp_path: Path) -> None:
    good = tmp_path / "seccomp.json"
    good.write_text(
        json.dumps(
            {
                "defaultAction": "SCMP_ACT_ERRNO",
                "syscalls": [{"names": ["read"], "action": "SCMP_ACT_ALLOW"}],
            }
        ),
        encoding="utf-8",
    )
    if validate_seccomp_profile(good) != good.resolve():
        pytest.fail("valid seccomp profile path changed unexpectedly")
    good.write_text(
        json.dumps({"defaultAction": "SCMP_ACT_ALLOW", "syscalls": [{}]}),
        encoding="utf-8",
    )
    with pytest.raises(ReleaseInputError, match="SCMP_ACT_ERRNO"):
        validate_seccomp_profile(good)


def test_docker_invocation_has_finite_least_privilege_limits(tmp_path: Path) -> None:
    profile = tmp_path / "seccomp.json"
    profile.write_text("{}", encoding="utf-8")
    command = docker_run_argv(
        "synthetic-image",
        "owned-container",
        "owned-volume",
        "print('ok')",
        profile,
    )
    joined = " ".join(command)
    required = (
        "--network none",
        "--read-only",
        "--memory 2g",
        "--memory-swap 2g",
        "--cpus 2.0",
        "--pids-limit 256",
        "--security-opt no-new-privileges",
        "--cap-drop ALL",
        "type=volume,src=owned-volume,dst=/var/lib/msgloom",
    )
    for fragment in required:
        if fragment not in joined:
            pytest.fail(f"container boundary missing: {fragment}")
    for fragment in ("--privileged", "/var/run/docker.sock", "/home/", "--userns=host"):
        if fragment in joined:
            pytest.fail(f"forbidden container surface present: {fragment}")


def test_runner_bounds_live_output_and_returns_timeout_evidence(tmp_path: Path) -> None:
    result = Runner().run(
        [
            str(PYTHON),
            "-c",
            "import sys,time;print('x'*20000);sys.stdout.flush();time.sleep(2)",
        ],
        cwd=tmp_path,
        timeout=1,
    )
    if result.returncode != 124 or not result.timed_out:
        pytest.fail(f"timeout was not evidence: {result!r}")
    if len(result.output) > 1600 or "timeout after 1s" not in result.output:
        pytest.fail("timeout output was not bounded and retained")


def _wait_pid_gone(pid: int, timeout: float = 1.0) -> bool:
    """Wait finitely for one synthetic child process to disappear."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not Path(f"/proc/{pid}").exists():
            return True
        time.sleep(0.02)
    return not Path(f"/proc/{pid}").exists()


def _deadline_starts_after_ready(
    monkeypatch: pytest.MonkeyPatch,
    ready: Path,
) -> None:
    """Start the test deadline only after the synthetic phase is ready."""
    import deployment.process as process_module

    real_monotonic = time.monotonic

    def after_ready(timeout: float) -> float:
        barrier_deadline = real_monotonic() + 2.0
        while not ready.exists() and real_monotonic() < barrier_deadline:
            time.sleep(0.01)
        return real_monotonic() + timeout

    monkeypatch.setattr(process_module, "_deadline_after", after_ready)


def test_runner_deadline_cannot_be_starved_by_continuous_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ready = tmp_path / "noisy.ready"
    _deadline_starts_after_ready(monkeypatch, ready)
    code = (
        "import os;from pathlib import Path;"
        f"Path({str(ready)!r}).write_text('ready');"
        "chunk=b'x'*4096;"
        "\nwhile True: os.write(1,chunk)"
    )
    start = time.monotonic()
    result = Runner().run(
        [str(PYTHON), "-c", code],
        cwd=tmp_path,
        timeout=0.1,
    )
    elapsed = time.monotonic() - start
    if not ready.exists():
        pytest.fail("continuous-output phase never reached its readiness barrier")
    if result.returncode != 124 or not result.timed_out or elapsed >= 3.0:
        pytest.fail(
            f"continuous output starved deadline checks: {result!r}, {elapsed=}"
        )


def test_runner_deadline_applies_after_output_closes(tmp_path: Path) -> None:
    start = time.monotonic()
    result = Runner().run(
        [
            str(PYTHON),
            "-c",
            "import os,time;os.close(1);os.close(2);time.sleep(2)",
        ],
        cwd=tmp_path,
        timeout=0.1,
    )
    elapsed = time.monotonic() - start
    if result.returncode != 124 or not result.timed_out or elapsed >= 0.8:
        pytest.fail(f"closed-output process escaped deadline: {result!r}, {elapsed=}")


def test_runner_deadline_applies_to_inherited_output_descendant(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pid_file = tmp_path / "inherited.pid"
    _deadline_starts_after_ready(monkeypatch, pid_file)
    code = (
        "import subprocess,sys;from pathlib import Path;"
        "p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(2)']);"
        f"Path({str(pid_file)!r}).write_text(str(p.pid))"
    )
    start = time.monotonic()
    result = Runner().run(
        [str(PYTHON), "-c", code],
        cwd=tmp_path,
        timeout=0.2,
    )
    elapsed = time.monotonic() - start
    if result.returncode != 124 or not result.timed_out or elapsed >= 3.0:
        pytest.fail(f"inherited pipe escaped deadline: {result!r}, {elapsed=}")
    if not pid_file.exists():
        pytest.fail("synthetic inherited-pipe descendant did not start")
    if not _wait_pid_gone(int(pid_file.read_text(encoding="utf-8"))):
        pytest.fail("owned inherited-pipe descendant survived timeout cleanup")


def test_runner_kills_descendant_that_ignores_group_sigterm(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pid_file = tmp_path / "ignores-term.pid"
    ready_file = tmp_path / "ignores-term.ready"
    _deadline_starts_after_ready(monkeypatch, ready_file)
    child_code = (
        "import signal,time;from pathlib import Path;"
        "signal.signal(signal.SIGTERM,signal.SIG_IGN);"
        f"Path({str(ready_file)!r}).write_text('ready');time.sleep(5)"
    )
    code = (
        "import signal,subprocess,sys,time;from pathlib import Path;"
        "signal.signal(signal.SIGTERM,lambda *_:sys.exit(0));"
        f"p=subprocess.Popen([sys.executable,'-c',{child_code!r}]);"
        f"Path({str(pid_file)!r}).write_text(str(p.pid));time.sleep(5)"
    )
    start = time.monotonic()
    result = Runner().run(
        [str(PYTHON), "-c", code],
        cwd=tmp_path,
        timeout=0.2,
    )
    elapsed = time.monotonic() - start
    if result.returncode != 124 or not result.timed_out or elapsed >= 3.0:
        pytest.fail(f"SIGTERM-resistant descendant escaped cleanup: {elapsed=}")
    if not pid_file.exists() or not ready_file.exists():
        pytest.fail("synthetic descendant did not install its SIGTERM handler")
    pid = int(pid_file.read_text(encoding="utf-8"))
    if not _wait_pid_gone(pid):
        pytest.fail("SIGTERM-resistant owned descendant survived SIGKILL cleanup")


def test_runner_cancellation_cleans_owned_process_group(tmp_path: Path) -> None:
    pid_file = tmp_path / "owned-child.pid"
    child = (
        "from pathlib import Path;import os,time;"
        f"Path({str(pid_file)!r}).write_text(str(os.getpid()));"
        "time.sleep(5)"
    )
    wrapper = (
        "from pathlib import Path;from deployment.process import Runner;"
        "import sys;"
        f"Runner().run([sys.executable,'-c',{child!r}],"
        f"cwd=Path({str(tmp_path)!r}),timeout=10)"
    )
    process = subprocess.Popen(
        [str(PYTHON), "-c", wrapper],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    deadline = time.monotonic() + 2
    while not pid_file.exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    if not pid_file.exists():
        process.kill()
        pytest.fail("synthetic owned child did not start")
    child_pid = int(pid_file.read_text(encoding="utf-8"))
    process.send_signal(signal.SIGINT)
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        pytest.fail("cancelled runner did not return finitely")
    if process.returncode == 0:
        pytest.fail("synthetic cancellation unexpectedly succeeded")
    if not _wait_pid_gone(child_pid):
        pytest.fail("cancelled runner left its owned child process alive")


def test_real_local_container_timeout_is_removed_if_image_present(
    tmp_path: Path,
) -> None:
    image = "debian:trixie"
    present = subprocess.run(
        ["docker", "image", "inspect", image],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=10,
    )
    if present.returncode:
        pytest.skip("no already-present harmless Docker image")
    name = "msgloom-qual-pytest-timeout"
    subprocess.run(
        ["docker", "rm", "-f", name],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=10,
    )
    result = Runner().run(
        [
            "docker",
            "run",
            "--rm",
            "--name",
            name,
            "--network",
            "none",
            image,
            "sleep",
            "30",
        ],
        cwd=tmp_path,
        timeout=1,
    )
    if result.returncode != 124:
        pytest.fail(f"container timeout was not recorded: {result!r}")
    inspect = subprocess.run(
        ["docker", "container", "inspect", name],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=10,
    )
    if inspect.returncode == 0:
        pytest.fail("timed-out invocation-owned container remained running")
