"""Measure FIFO rejection after a finite interpreter readiness barrier."""

import selectors
import subprocess
import sys
from pathlib import Path

import pytest


def run_fifo_probe(code: str, path: Path) -> str:
    """Own startup and cleanup while bounding only the ready file operation."""
    process = subprocess.Popen(
        [sys.executable, "-c", code, str(path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        if process.stdout is None:
            pytest.fail("FIFO probe has no readiness pipe")
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            if not selector.select(timeout=30.0):
                pytest.fail("FIFO probe did not reach its startup barrier")
        ready = process.stdout.readline()
        if ready != "READY\n":
            pytest.fail(f"FIFO probe failed before its file operation: {ready!r}")
        try:
            output, _ = process.communicate(input="proceed\n", timeout=3.0)
        except subprocess.TimeoutExpired:
            pytest.fail("ready FIFO operation blocked past its finite budget")
        if process.returncode != 0:
            pytest.fail(f"FIFO probe failed after readiness: {output!r}")
        return ready + output
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate()
