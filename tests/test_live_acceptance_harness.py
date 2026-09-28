"""Verify the live acceptance harness safety gate and dry-run plan."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "microsoft-live-acceptance.py"
START = "2026-09-27T00:00:00+10:00"
END = "2026-10-04T00:00:00+10:00"


def test_live_harness_requires_explicit_confirmation(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--calendar-start",
            START,
            "--calendar-end",
            END,
            "--output-dir",
            str(tmp_path / "live"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        pytest.fail("Live harness must not run without --confirm-live")
    if "requires --confirm-live" not in result.stderr:
        pytest.fail("Expected explicit live-execution safety diagnostic")


def test_live_harness_dry_run_is_network_free_and_privacy_safe(tmp_path: Path) -> None:
    output = tmp_path / "dry"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dry-run",
            "--calendar-start",
            START,
            "--calendar-end",
            END,
            "--output-dir",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(result.stderr)
    if '"overall": "planned"' not in result.stdout:
        pytest.fail("Expected dry-run acceptance summary")
    if output.exists():
        pytest.fail("Dry-run must not create local acceptance state")


def test_live_harness_dry_run_can_plan_shared_target_without_disclosing_locator(
    tmp_path: Path,
) -> None:
    output = tmp_path / "shared-dry"
    locator = "00000000-0000-0000-0000-000000000123"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dry-run",
            "--mailbox",
            locator,
            "--calendar-start",
            START,
            "--calendar-end",
            END,
            "--output-dir",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(result.stderr)
    if '"delegated_target": true' not in result.stdout:
        pytest.fail("Expected shared-target acceptance plan marker")
    if locator in result.stdout or locator in result.stderr:
        pytest.fail("Acceptance output must not disclose mailbox locator")
