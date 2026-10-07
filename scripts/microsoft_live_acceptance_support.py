"""Support helpers for the bounded Microsoft live-acceptance executable."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.microsoft.outlook.calendar import (
    OutlookCalendarStore,
)
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore

ROOT = Path(__file__).resolve().parents[1]


def _output_dir(value: Path | None) -> Path:
    if value is not None:
        return value.resolve()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return (ROOT / "var" / "live-acceptance" / stamp).resolve()


def _settings(output_dir: Path, source_id: str) -> list[str]:
    return [
        "-s",
        f"MSGLOOM_DATABASE_URL=sqlite:///{output_dir / 'catalog.sqlite3'}",
        "-s",
        f"MSGLOOM_RAW_EVIDENCE_DIR={output_dir / 'raw-evidence'}",
        "-s",
        f"MSGLOOM_SOURCE_ID={source_id}",
        "-s",
        "MSGLOOM_CATALOG_ENABLED=True",
        "-s",
        "MSGLOOM_RAW_EVIDENCE_ENABLED=True",
        "-s",
        "HTTPCACHE_ENABLED=False",
    ]


def _command(*args: str, settings: list[str]) -> list[str]:
    return [sys.executable, "-m", "scrapy", "microsoft", *args, *settings]


def _mail_rule_qualification_command(
    *,
    output_dir: Path,
    source_id: str,
    mailbox: str | None,
    page_size: int,
    message_id: str | None,
    event_message_id: str | None,
) -> tuple[list[str], Path]:
    summary_file = output_dir / "mail-rule-qualification.json"
    command = [
        sys.executable,
        str(ROOT / "scripts" / "microsoft-mail-rule-qualification.py"),
        "--confirm-live",
        "--output-dir",
        str(output_dir),
        "--summary-file",
        str(summary_file),
        "--source-id",
        source_id,
        "--mail-page-size",
        str(page_size),
    ]
    if mailbox:
        command.extend(["--mailbox", mailbox])
    if message_id:
        command.extend(["--message-id", message_id])
    if event_message_id:
        command.extend(["--event-message-id", event_message_id])
    return command, summary_file


def _read_safe_qualification_summary(path: Path) -> dict[str, bool | int | str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        raise RuntimeError(
            "qualification helper produced no valid safe summary"
        ) from None
    if not isinstance(payload, dict):
        raise TypeError("qualification helper summary must be an object")
    allowed = {
        "schema_version",
        "discovery_request_once",
        "discovery_change_key_available",
        "normal_target_selected",
        "event_target_selected",
        "normal_probe_scheduled_once",
        "event_probe_scheduled_once",
        "probe_request_count",
        "target_count",
        "single_probe_per_target",
        "normal_probe_complete",
        "normal_change_key_available",
        "normal_body_available",
        "normal_headers_available",
        "normal_sensitivity_available",
        "normal_message_size_bytes_available",
        "normal_item_class_available",
        "event_probe_complete",
        "event_body_content_type_html",
        "event_logical_body_available",
        "event_html_request_once",
        "event_html_response_html",
        "event_html_projection_complete",
        "mail_scope_only",
        "raw_evidence_count",
        "run_failed",
        "failure_reason_count",
    }
    if set(payload) - allowed:
        raise RuntimeError("qualification helper summary contains unknown fields")
    safe: dict[str, bool | int | str] = {}
    for key, value in payload.items():
        if not isinstance(value, (bool, int, str)):
            raise TypeError("qualification helper summary contains unsafe value")
        safe[key] = value
    return safe


def _qualification_checks_pass(checks: dict[str, bool | int | str]) -> bool:
    required = (
        "discovery_request_once",
        "discovery_change_key_available",
        "normal_target_selected",
        "normal_probe_scheduled_once",
        "single_probe_per_target",
        "normal_probe_complete",
        "normal_change_key_available",
        "normal_body_available",
        "normal_headers_available",
        "normal_sensitivity_available",
        "normal_message_size_bytes_available",
        "normal_item_class_available",
        "mail_scope_only",
    )
    return (
        all(checks.get(key) is True for key in required)
        and int(checks.get("raw_evidence_count", 0) or 0) > 0
        and checks.get("run_failed") is False
        and int(checks.get("failure_reason_count", 0) or 0) == 0
    )


def _event_qualification_passes(checks: dict[str, bool | int | str]) -> bool:
    return all(
        checks.get(key) is True
        for key in (
            "event_target_selected",
            "event_probe_scheduled_once",
            "event_probe_complete",
            "event_logical_body_available",
            "event_html_request_once",
            "event_html_response_html",
            "event_html_projection_complete",
        )
    )


def _database_url(output_dir: Path) -> str:
    return f"sqlite:///{output_dir / 'catalog.sqlite3'}"


def _first_mail_message(output_dir: Path, source_id: str) -> str | None:
    catalog = Catalog(_database_url(output_dir))
    try:
        ids = OutlookMailStore(catalog, source_id=source_id).list_message_ids()
        return ids[0] if ids else None
    finally:
        catalog.close()


def _first_calendar_event(output_dir: Path, source_id: str) -> tuple[str, str] | None:
    catalog = Catalog(_database_url(output_dir))
    try:
        targets = OutlookCalendarStore(
            catalog, source_id=source_id
        ).list_event_targets()
        if not targets:
            return None
        event_id, calendar_id, _version = targets[0]
        return event_id, calendar_id
    finally:
        catalog.close()
