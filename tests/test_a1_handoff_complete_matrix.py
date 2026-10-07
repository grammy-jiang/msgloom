"""Validate the static Task 10 executable-candidate inventory."""

import subprocess
import sys
from pathlib import Path

import pytest
from scrapy.spiderloader import SpiderLoader
from scrapy.utils.project import get_project_settings

from tests.handoff_qualification import inventory

MATRIX = inventory.MATRIX

ROOT = Path(__file__).parents[1]
TASK10_ROWS = {
    "mail_discovery",
    "mail_cache_replay",
    "mail_immediate_delta",
    "mail_rules_deferred_full",
    "mail_folder_delta",
    "calendar_discovery_window_resume",
    "calendar_delta",
    "calendar_full_partial_success",
    "todo_discover_sync",
    "contacts_discover_sync_delta",
    "onedrive_discover_delta_reset_content",
    "profile_no_release",
}


def test_machine_matrix_keeps_candidates_collectable_and_status_honest() -> None:
    """Candidate nodes must exist without becoming qualification receipts."""
    scenarios = getattr(inventory, "TASK10_EXECUTABLE_SCENARIOS", None)
    gaps = getattr(inventory, "TASK10_SCENARIO_GAPS", None)
    pending = getattr(inventory, "TASK15_SCENARIOS_PENDING", None)
    if scenarios is None or gaps is None or pending is None:
        pytest.fail("The executable-candidate inventory is missing")
    installed = set(SpiderLoader.from_settings(get_project_settings()).list())
    if installed != set(MATRIX) or len(installed) != 17:
        pytest.fail("Installed spider inventory differs from the exact matrix")
    if set(scenarios) != TASK10_ROWS:
        pytest.fail("Task 10 must retain its exact 12 executable rows")
    if set(gaps) != {"mail_discovery"}:
        pytest.fail("Task 10 lost a known runtime or executable gap")
    if pending != tuple(str(index) for index in range(1, 14)):
        pytest.fail("Task 15 must retain 13 separate pending scenarios")

    nodes = {node for coverage in MATRIX.values() for node in coverage.candidate_tests}
    scenario_nodes = {node for mapped in scenarios.values() for node in mapped}
    if scenario_nodes - nodes:
        pytest.fail("Task 10 scenario mapping cites an unregistered candidate")
    for name, coverage in MATRIX.items():
        if coverage.candidate_tests and coverage.gap:
            pytest.fail(f"{name} has both candidate nodes and a declared gap")
        if not coverage.candidate_tests and not coverage.gap:
            pytest.fail(f"{name} lacks a candidate node or an explicit gap")
        if coverage.pending and coverage.tests:
            pytest.fail(f"{name} is both accepted and pending")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
            *sorted(nodes),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode:
        pytest.fail(
            "Candidate node collection failed:\n" + result.stdout + result.stderr
        )
    collected = {
        line.strip() for line in result.stdout.splitlines() if line.startswith("tests/")
    }
    if collected != nodes:
        pytest.fail("Candidate selectors do not resolve to exact pytest node IDs")
