"""Prove the native child watchdog returns, reports, and reaps children."""

import os
import signal
import subprocess
import sys
import textwrap
import threading
from io import StringIO
from pathlib import Path
from typing import cast

import pytest
from scrapy.settings import default_settings

from tests import native_watchdog
from tests.native_watchdog import (
    DUMP_GRACE_SECONDS,
    NATIVE_BARRIER_TIMEOUT,
    NATIVE_COMMAND_TIMEOUT,
    _kill_and_reap,
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


@pytest.mark.parametrize("error_type", [OSError, KeyboardInterrupt])
def test_communication_exception_kills_and_reaps_owned_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error_type: type[BaseException]
) -> None:
    """A non-timeout exception must not enter an unbounded Popen.__exit__."""
    observed: list[subprocess.Popen[str]] = []

    class FaultyCommunicationPopen(subprocess.Popen[str]):
        def communicate(
            self, input: str | None = None, timeout: float | None = None
        ) -> tuple[str, str]:
            observed.append(self)
            if len(observed) == 1:
                raise error_type("synthetic read failure")
            return super().communicate(input=input, timeout=timeout)

    monkeypatch.setattr(native_watchdog.subprocess, "Popen", FaultyCommunicationPopen)
    with pytest.raises(error_type, match="synthetic read failure"):
        run_native_command(
            [sys.executable, "-c", "import time; time.sleep(600)"],
            cwd=tmp_path,
            env=dict(os.environ),
        )
    if len(observed) != 2:
        pytest.fail(f"Expected bounded cleanup after the error: {len(observed)}")
    child = observed[0]
    if child.poll() is None or child.returncode == 0:
        pytest.fail("Abnormal communication left the native child running")
    if any(
        stream is not None and not stream.closed
        for stream in (child.stdout, child.stderr)
    ):
        pytest.fail("Native child capture streams were not closed")


def test_killed_child_output_drain_and_reap_have_deadlines() -> None:
    """Inherited output pipes must not allow the post-kill path to hang."""

    class UndrainableChild:
        def __init__(self) -> None:
            self.args = ["synthetic-native-child"]
            self.returncode: int | None = None
            self.stdout = StringIO()
            self.stderr = StringIO()
            self.drain_timeout: float | None = None
            self.wait_timeout: float | None = None

        def poll(self) -> int | None:
            return self.returncode

        def kill(self) -> None:
            self.returncode = -9

        def communicate(self, *, timeout: float) -> tuple[str, str]:
            self.drain_timeout = timeout
            raise subprocess.TimeoutExpired(self.args, timeout)

        def wait(self, *, timeout: float) -> int:
            self.wait_timeout = timeout
            return -9

    fake = UndrainableChild()
    with pytest.raises(subprocess.TimeoutExpired):
        _kill_and_reap(cast("subprocess.Popen[str]", fake))
    if (
        fake.returncode != -9
        or fake.drain_timeout != DUMP_GRACE_SECONDS
        or fake.wait_timeout != DUMP_GRACE_SECONDS
        or not fake.stdout.closed
        or not fake.stderr.closed
    ):
        pytest.fail("Post-kill drain or reap was unbounded or left pipes open")


def test_blocked_descendant_pipe_preserves_watchdog_output_and_reaps() -> None:
    """A bounded drain timeout still reports captured stdout and stacks."""

    class DescendantHeldPipe:
        def __init__(self) -> None:
            self.args = ["synthetic-native-child"]
            self.returncode: int | None = None
            self.stdout = StringIO()
            self.stderr = StringIO()
            self.budgets: list[float] = []
            self.reaped = False

        def poll(self) -> int | None:
            return self.returncode

        def send_signal(self, _signum: int) -> None:
            """Pretend to request a stack dump from the hung child."""

        def kill(self) -> None:
            self.returncode = -9

        def communicate(self, *, timeout: float) -> tuple[str, str]:
            self.budgets.append(timeout)
            raise subprocess.TimeoutExpired(
                self.args, timeout, output=b"early stdout\n", stderr=b"stack dump\n"
            )

        def wait(self, *, timeout: float) -> int:
            if timeout != DUMP_GRACE_SECONDS:
                pytest.fail("Native child reap is not time-limited")
            self.reaped = True
            return -9

    fake = DescendantHeldPipe()
    stdout, stderr = reap_hung_child(cast("subprocess.Popen[str]", fake))
    if stdout != "early stdout\n" or not stderr.startswith("stack dump\n"):
        pytest.fail("Watchdog lost partial stdout or stderr during cleanup")
    if "Native capture drain timed out" not in stderr:
        pytest.fail("Watchdog hid the inherited-pipe drain timeout")
    if (
        not fake.reaped
        or fake.returncode != -9
        or not fake.budgets
        or any(budget != DUMP_GRACE_SECONDS for budget in fake.budgets)
        or not fake.stdout.closed
        or not fake.stderr.closed
    ):
        pytest.fail("Watchdog output preservation bypassed bounded reaping")
