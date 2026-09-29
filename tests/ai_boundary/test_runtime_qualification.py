"""Offline qualification of real SDK runtime assembly in Bubblewrap."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from msgloom.ai import RuntimeIsolation
from msgloom.ai.sandbox import build_sandbox_command


def _runtime_roots() -> tuple[Path, ...]:
    """Return explicitly configured roots or this test interpreter runtime."""
    configured = os.environ.get("MSGLOOM_AI_QUALIFICATION_RUNTIMES")
    if configured:
        roots = tuple(Path(item) for item in configured.split(os.pathsep) if item)
        if not roots:
            pytest.fail("configured AI qualification runtime list is empty")
        return roots
    return (Path(sys.prefix),)


_RUNTIME_ROOTS = _runtime_roots()


def _runtime(root: Path, storage: Path) -> RuntimeIsolation:
    python = root / "bin" / "python"
    metadata = subprocess.run(
        [
            str(python),
            "-c",
            (
                "import json,sys,sysconfig;"
                "print(json.dumps({'prefix':sys.prefix,"
                "'purelib':sysconfig.get_path('purelib'),"
                "'executable':sys.executable}))"
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    values = json.loads(metadata.stdout)
    executable = Path(values["executable"])
    prefix = Path(values["prefix"])
    site_packages = Path(values["purelib"])
    cli = site_packages / "claude_agent_sdk" / "_bundled" / "claude"
    base = executable.resolve().parents[1]
    roots = tuple(dict.fromkeys((prefix, base, Path("/lib"))))
    return RuntimeIsolation(
        executable,
        Path("/usr/bin/bwrap"),
        roots,
        cli,
        {},
        storage,
        0.1,
    )


@pytest.mark.parametrize("runtime_root", _RUNTIME_ROOTS)
def test_real_runtime_imports_sdk_and_cli_offline(
    runtime_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Qualified Python roots import SDK and run bundled CLI version offline."""
    if not runtime_root.is_dir():
        pytest.fail(f"qualified runtime root is unavailable: {runtime_root}")
    sentinel = tmp_path / "host-session-sentinel"
    sentinel.write_text("synthetic host-only settings")
    state = tmp_path / "state"
    work = tmp_path / "work"
    state.mkdir()
    work.mkdir()
    worker = tmp_path / "offline_worker.py"
    worker.write_text(
        "import json,os,subprocess\n"
        "from pathlib import Path\n"
        "import claude_agent_sdk\n"
        "cli=Path(claude_agent_sdk.__file__).parent/'_bundled'/'claude'\n"
        "version=subprocess.run([str(cli),'--version'],check=False,"
        "capture_output=True,text=True,timeout=10)\n"
        f"sentinel=Path({str(sentinel)!r}).exists()\n"
        "print(json.dumps({'home':os.environ.get('HOME'),"
        "'source_secret':os.environ.get('SYNTHETIC_SOURCE_SECRET'),"
        "'sentinel':sentinel,'cli_rc':version.returncode,"
        "'cli_version':bool(version.stdout.strip())}))\n"
    )
    runtime = _runtime(runtime_root, tmp_path)
    monkeypatch.setenv("SYNTHETIC_SOURCE_SECRET", "must-not-cross")
    completed = subprocess.run(
        build_sandbox_command(runtime, worker, state, work),
        check=False,
        capture_output=True,
        text=True,
        env={
            "HOME": "/state",
            "CLAUDE_CONFIG_DIR": "/state/claude",
            "XDG_CONFIG_HOME": "/state/config",
            "XDG_CACHE_HOME": "/state/cache",
            "TMPDIR": "/tmp",
            "PATH": "/usr/bin:/bin",
            "PYTHONNOUSERSITE": "1",
        },
        timeout=20,
    )
    if completed.returncode != 0:
        pytest.fail(
            "offline runtime assembly failed without model/auth request: "
            + completed.stderr
        )
    result = json.loads(completed.stdout)
    expected = {
        "home": "/state",
        "source_secret": None,
        "sentinel": False,
        "cli_rc": 0,
        "cli_version": True,
    }
    if result != expected:
        pytest.fail("offline runtime isolation/import/CLI qualification failed")


async def _run_and_reap(command: list[str]) -> int | None:
    from msgloom.ai.sandbox import terminate_and_reap

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={
            "HOME": "/state",
            "CLAUDE_CONFIG_DIR": "/state/claude",
            "XDG_CONFIG_HOME": "/state/config",
            "XDG_CACHE_HOME": "/state/cache",
            "TMPDIR": "/tmp",
            "PATH": "/usr/bin:/bin",
            "PYTHONNOUSERSITE": "1",
        },
        start_new_session=True,
    )
    if process.stdout is None:
        pytest.fail("offline runtime cleanup child has no stdout")
    ready = await asyncio.wait_for(process.stdout.readline(), 10)
    if ready.strip() != b"ready":
        pytest.fail("offline SDK runtime did not reach the cleanup barrier")
    await terminate_and_reap(process, 0.05)
    return process.returncode


def test_real_sdk_runtime_process_is_terminable_and_reaped(tmp_path: Path) -> None:
    """The current SDK runtime leaves no accepted process after cleanup."""
    runtime_root = Path(sys.prefix)
    state = tmp_path / "state"
    work = tmp_path / "work"
    state.mkdir()
    work.mkdir()
    worker = tmp_path / "cleanup_worker.py"
    worker.write_text(
        "import time\n"
        "import claude_agent_sdk\n"
        "print('ready',flush=True)\n"
        "time.sleep(60)\n"
    )
    runtime = _runtime(runtime_root, tmp_path)
    command = build_sandbox_command(runtime, worker, state, work)
    returncode = asyncio.run(_run_and_reap(command))
    if returncode is None:
        pytest.fail("offline SDK runtime process was not reaped")
