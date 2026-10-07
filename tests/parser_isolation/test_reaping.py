"""Distinguish an exited process from a fully reaped process."""

import os
import select
import subprocess
import sys

import pytest

from msgloom.preparation.isolation.runner import _wait_pidfds


def test_pidfd_readability_does_not_finish_reaping() -> None:
    """An owned zombie remains pending until its parent consumes the status."""
    process = subprocess.Popen([sys.executable, "-c", "pass"])
    pidfd = os.pidfd_open(process.pid)
    try:
        poller = select.poll()
        poller.register(pidfd, select.POLLIN)
        if not poller.poll(10_000):
            pytest.fail("Synthetic child did not reach the exit barrier")
        if _wait_pidfds([pidfd], 0.05):
            pytest.fail("Cleanup accepted an exited but unreaped child")
        process.wait(timeout=5)
        if not _wait_pidfds([pidfd], 0.5):
            pytest.fail("Cleanup did not accept the fully reaped child")
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
        os.close(pidfd)
