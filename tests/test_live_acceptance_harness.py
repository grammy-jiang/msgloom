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


def test_mail_rule_qualification_dry_run_needs_no_calendar_window(
    tmp_path: Path,
) -> None:
    output = tmp_path / "mail-rule-dry"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dry-run",
            "--mail-rule-qualification",
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
    if "mail-rule-discover" not in result.stdout:
        pytest.fail("Mail-rule qualification did not plan bounded discovery")
    if "mail-rule-probe" not in result.stdout:
        pytest.fail(
            "Mail-rule qualification did not plan the production composite probe"
        )
    if "calendar-" in result.stdout:
        pytest.fail("Mail-rule qualification unexpectedly planned Calendar work")
    if '"overall": "planned"' not in result.stdout:
        pytest.fail("Mail-rule qualification dry-run lost planned summary")
    if output.exists():
        pytest.fail("Mail-rule qualification dry-run must not create local state")


def test_mail_rule_qualification_dry_run_hides_private_message_ids(
    tmp_path: Path,
) -> None:
    output = tmp_path / "mail-rule-private-dry"
    normal_id = "PRIVATE_NORMAL_MESSAGE_ID_1"
    event_id = "PRIVATE_EVENT_MESSAGE_ID_2"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dry-run",
            "--mail-rule-qualification",
            "--mail-rule-message-id",
            normal_id,
            "--mail-rule-event-message-id",
            event_id,
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
    if "mail-rule-event-probe" not in result.stdout:
        pytest.fail("Explicit event-message qualification phase was not planned")
    exposed = result.stdout + result.stderr
    if normal_id in exposed or event_id in exposed:
        pytest.fail("Qualification output exposed private message identifiers")


def test_mail_rule_qualification_helper_allows_omitted_private_ids(
    tmp_path: Path,
) -> None:
    import importlib.util

    helper = ROOT / "scripts" / "microsoft-mail-rule-qualification.py"
    spec = importlib.util.spec_from_file_location(
        "mail_rule_qualification_helper", helper
    )
    if spec is None or spec.loader is None:
        pytest.fail("Could not load Mail rule qualification helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    args = module._parser().parse_args(
        [
            "--confirm-live",
            "--output-dir",
            str(tmp_path / "out"),
            "--summary-file",
            str(tmp_path / "summary.json"),
            "--source-id",
            "test-source",
        ]
    )

    if args.message_id is not None or args.event_message_id is not None:
        pytest.fail("Omitted private qualification IDs must remain optional")
