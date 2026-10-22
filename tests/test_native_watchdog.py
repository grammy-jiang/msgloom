"""Prove the native child watchdog returns, reports, and reaps children."""

import os
import signal
import subprocess
import sys
import textwrap
import threading
from pathlib import Path

import pytest
from scrapy.settings import default_settings

from tests.native_watchdog import (
    NATIVE_BARRIER_TIMEOUT,
    NATIVE_COMMAND_TIMEOUT,
    reap_hung_child,
    run_native_command,
)

TESTS = Path(__file__).resolve().parent


def test_barrier_budget_fits_inside_download_and_command_limits():
    """A held fixture response must expire before Scrapy or the watchdog."""
    download = default_settings.DOWNLOAD_TIMEOUT
    if not NATIVE_BARRIER_TIMEOUT < download < NATIVE_COMMAND_TIMEOUT:
        pytest.fail(f"Barrier budget must stay below the {download} s download limit")


def test_finished_child_returns_status_and_text_output(tmp_path):
    """A finished child returns its exit status and text output unchanged."""
    code = (
        "import sys; print('out'); print('err', file=sys.stderr); raise SystemExit(3)"
    )
    result = run_native_command(
        [sys.executable, "-c", code], cwd=tmp_path, env=dict(os.environ)
    )
    if (result.returncode, result.stdout, result.stderr) != (3, "out\n", "err\n"):
        pytest.fail(f"Unexpected child result: {result!r}")


def test_expired_child_is_reaped_before_the_test_fails(tmp_path):
    """An expired child is reaped, and the failure names the watchdog."""
    marker = tmp_path / "pid"
    code = (
        "import os, sys, time; "
        "open(sys.argv[1], 'w').write(str(os.getpid())); time.sleep(600)"
    )
    with pytest.raises(pytest.fail.Exception) as caught:
        run_native_command(
            [sys.executable, "-c", code, str(marker)],
            cwd=tmp_path,
            env=dict(os.environ),
            timeout=1,
        )
    if "exceeded its 1 s watchdog" not in str(caught.value):
        pytest.fail(f"Watchdog failure lacks its budget: {caught.value}")
    if os.name != "posix" or not marker.exists():
        return
    try:
        os.kill(int(marker.read_text()), 0)
    except ProcessLookupError:
        return
    pytest.fail("Expired child survived the watchdog")


def test_registered_child_reports_every_thread_before_it_is_killed(tmp_path):
    """A registered child writes all thread stacks, then dies when killed."""
    code = textwrap.dedent(
        """
        import sys, threading, time
        sys.path.append(sys.argv[1])
        from native_watchdog import install_child_diagnostics
        install_child_diagnostics()
        threading.Thread(target=time.sleep, args=(600,), daemon=True).start()
        print("ready", flush=True)
        time.sleep(600)
        """
    )
    with subprocess.Popen(
        [sys.executable, "-c", code, str(TESTS)],
        cwd=tmp_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as process:
        # Bound the readiness read itself; a child that never starts is
        # killed, so readline() reaches end of file.
        guard = threading.Timer(NATIVE_BARRIER_TIMEOUT, process.kill)
        guard.start()
        try:
            ready = process.stdout.readline() if process.stdout else ""
        finally:
            guard.cancel()
        stderr = reap_hung_child(process)[1]
    if ready != "ready\n":
        pytest.fail(f"Diagnostic child did not start: {stderr}")
    if process.returncode == 0:
        pytest.fail("Hung diagnostic child was not terminated")
    if hasattr(signal, "SIGUSR1") and stderr.count("(most recent call first)") < 2:
        pytest.fail(f"Stack dump did not cover every thread: {stderr}")
