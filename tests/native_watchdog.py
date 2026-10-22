"""
Bound native child commands with one host-calibrated watchdog.

Native tests start real Scrapy or msgloom child processes against local
fixtures. Each child opens its own SQLite catalog or store and commits every
durable step with SQLite's default ``synchronous=FULL`` rollback journal.
One small Outlook Full profile crawl therefore issues about 90 ``fsync``
calls. On an idle Raspberry Pi 5 that crawl is CPU bound and takes about
6 s, of which Spider open to close is below 1 s.

The formal Task 15 host runs four xdist workers against one NVMe device.
Its ``atop`` history for 2026-10-12 to 2026-10-22 records repeated episodes
in which the suites' own write and flush load raises device latency from
below 1 ms to 9-33 ms for 30-330 s. A child that runs during such an episode
keeps making progress, but it can need several minutes; a stack dump of one
shows its writer thread inside the SQLite ``COMMIT`` while the reactor
idles. Every timing failure of the earlier formal attempts overlapped such
an episode, including both native Mail failures on candidate ``2ce2ec0``.

These budgets only bound a hung child or a fixture barrier. They never
assert speed, and callers keep every behavioral assertion. A test whose
subject is timeout handling keeps its own explicit, deliberately short
value instead of these budgets.
"""

from __future__ import annotations

import signal
import subprocess
from pathlib import Path

# Seconds after which one native child command is treated as hung.
NATIVE_COMMAND_TIMEOUT = 300.0
# Seconds a fixture barrier may wait for another component's catalog write.
# This stays below Scrapy's default 180 s DOWNLOAD_TIMEOUT, so a fixture that
# holds a response until a write commits cannot become a download failure.
# It also stays below NATIVE_COMMAND_TIMEOUT, so a missing write reports the
# barrier's own message before the command watchdog fires.
NATIVE_BARRIER_TIMEOUT = 120.0
# Seconds a hung child gets to write its stack dump before it is killed.
DUMP_GRACE_SECONDS = 5.0

_STDERR_TAIL = 12_000
_STDOUT_TAIL = 2_000


def install_child_diagnostics() -> None:
    """
    Let the watchdog request an all-thread stack dump from this child.

    Only test-owned child runners call this. :mod:`faulthandler` writes the
    dump from its C signal handler to stderr, so it works even while every
    Python thread waits in SQLite, a lock, or the reactor. Normal runs never
    receive the signal and print nothing. Platforms without ``SIGUSR1``
    keep the plain kill path.
    """
    if not hasattr(signal, "SIGUSR1"):
        return
    import faulthandler

    faulthandler.register(signal.SIGUSR1, all_threads=True)


def reap_hung_child(process: subprocess.Popen[str]) -> tuple[str, str]:
    """
    Collect a hung child's stack dump and output, then kill and reap it.

    A POSIX child first receives ``SIGUSR1``. A child that called
    :func:`install_child_diagnostics` writes every thread stack and keeps
    running until the grace period ends; any other child exits on the
    signal's default action. The child is always killed and reaped before
    this function returns, so no owned process survives the failing test.
    Earlier timed-out :meth:`~subprocess.Popen.communicate` calls lose no
    output, so the returned text includes everything the child wrote.
    """
    if hasattr(signal, "SIGUSR1"):
        process.send_signal(signal.SIGUSR1)
        try:
            return process.communicate(timeout=DUMP_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            pass
    process.kill()
    return process.communicate()


def run_native_command(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: float = NATIVE_COMMAND_TIMEOUT,
) -> subprocess.CompletedProcess[str]:
    """
    Run one native child and fail with its evidence if it never exits.

    Output is captured as text. A nonzero exit is returned unchanged for
    the caller's own assertion, as with ``subprocess.run(check=False)``.
    When the watchdog expires, :func:`reap_hung_child` records the child's
    stack dump and output, and the test fails with their tails. Long
    ``-c`` runner arguments are abbreviated in the failure message.
    """
    with subprocess.Popen(
        args,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as process:
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            stdout, stderr = reap_hung_child(process)
            # Child runners import this module too; only the test needs pytest.
            import pytest

            shown = [arg if len(arg) <= 200 else arg[:60] + "..." for arg in args]
            pytest.fail(
                f"Native child exceeded its {timeout:g} s watchdog and was "
                f"reaped with exit status {process.returncode}: {shown}\n"
                f"--- stdout tail ---\n{stdout[-_STDOUT_TAIL:]}\n"
                f"--- stderr tail (stack dump last) ---\n"
                f"{stderr[-_STDERR_TAIL:]}"
            )
    return subprocess.CompletedProcess(args, process.returncode, stdout, stderr)
