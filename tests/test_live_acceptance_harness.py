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


def _load_live_acceptance_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "microsoft_live_acceptance_for_test",
        SCRIPT,
    )
    if spec is None or spec.loader is None:
        pytest.fail("Could not load Microsoft live acceptance module")
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_event_qualification_accepts_text_production_probe_with_separate_html_proof() -> (
    None
):
    module = _load_live_acceptance_module()
    checks = {
        "event_target_selected": True,
        "event_probe_scheduled_once": True,
        "event_probe_complete": True,
        "event_body_content_type_html": False,
        "event_logical_body_available": True,
        "event_html_request_once": True,
        "event_html_response_html": True,
        "event_html_projection_complete": True,
    }

    if not module._event_qualification_passes(checks):
        pytest.fail(
            "Event qualification must accept a production text response when a "
            "separate no-preference GET proves the HTML projection path"
        )


def test_event_html_qualification_payload_requires_real_html_and_logical_projection() -> (
    None
):
    import importlib.util

    helper = ROOT / "scripts" / "microsoft-mail-rule-qualification.py"
    spec = importlib.util.spec_from_file_location(
        "mail_rule_html_qualification_helper", helper
    )
    if spec is None or spec.loader is None:
        pytest.fail("Could not load Mail rule qualification helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    html, projected = module._event_html_projection(
        {
            "body": {
                "contentType": "html",
                "content": "<p>visible</p><table><tr><td>cell</td></tr></table>",
            }
        }
    )
    if html is not True or projected is not True:
        pytest.fail("Qualification-only HTML payload did not prove logical projection")

    text_html, text_projected = module._event_html_projection(
        {"body": {"contentType": "text", "content": "visible"}}
    )
    if text_html is not False or text_projected is not False:
        pytest.fail("Text response must not masquerade as the HTML fallback proof")
