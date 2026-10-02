#!/usr/bin/env python3
"""Run one private read-only Outlook Mail rule-probe qualification crawl."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from scripts.microsoft_mail_rule_qualification_spider import (
    MailRuleQualificationSpider,
)
from scripts.microsoft_mail_rule_qualification_spider import (
    _event_html_projection as _project_event_html,
)


def _event_html_projection(payload: object) -> tuple[bool, bool]:
    """Preserve the qualification helper entrypoint used by acceptance tests."""

    return _project_event_html(payload)


def _bounded_private_id(value: str) -> str:
    if not value or value != value.strip() or len(value) > 4096:
        raise argparse.ArgumentTypeError("private message ID is invalid")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Private read-only Outlook Mail rule-probe qualification."
    )
    parser.add_argument("--confirm-live", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--summary-file", type=Path, required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--mailbox", default="")
    parser.add_argument("--mail-page-size", type=int, default=10)
    parser.add_argument("--message-id", type=_bounded_private_id, default=None)
    parser.add_argument("--event-message-id", type=_bounded_private_id, default=None)
    return parser


def _summary(crawler, *, expected_scope: str) -> dict[str, bool | int | str]:
    stats = crawler.stats
    normal_complete = bool(
        stats.get_value("qualification/normal_probe_complete", False)
    )
    event_complete = bool(stats.get_value("qualification/event_probe_complete", False))
    target_count = int(stats.get_value("qualification/target_count", 0) or 0)
    request_count = int(stats.get_value("qualification/probe_request_count", 0) or 0)
    scopes = tuple(crawler.settings.getlist("MS_GRAPH_SCOPES"))
    spider = crawler.spider
    run_failed = bool(getattr(spider, "run_failed", False))
    failure_reasons = getattr(spider, "failure_reasons", frozenset())
    return {
        "schema_version": 1,
        "discovery_request_once": (
            stats.get_value("qualification/discovery_request_count", 0) == 1
        ),
        "discovery_change_key_available": bool(
            stats.get_value("qualification/discovery_change_key_available", False)
        ),
        "normal_target_selected": bool(
            stats.get_value("qualification/normal_target_selected", False)
        ),
        "event_target_selected": bool(
            stats.get_value("qualification/event_target_selected", False)
        ),
        "normal_probe_scheduled_once": (
            stats.get_value("qualification/normal_probe_scheduled_count", 0) == 1
        ),
        "event_probe_scheduled_once": (
            stats.get_value("qualification/event_probe_scheduled_count", 0) == 1
        ),
        "probe_request_count": request_count,
        "target_count": target_count,
        "single_probe_per_target": request_count == target_count and target_count > 0,
        "normal_probe_complete": normal_complete,
        "normal_change_key_available": bool(
            stats.get_value("qualification/normal_change_key_available", False)
        ),
        "normal_body_available": bool(
            stats.get_value("qualification/normal_body_available", False)
        ),
        "normal_headers_available": bool(
            stats.get_value("qualification/normal_headers_available", False)
        ),
        "normal_sensitivity_available": bool(
            stats.get_value("qualification/normal_sensitivity_available", False)
        ),
        "normal_message_size_bytes_available": bool(
            stats.get_value(
                "qualification/normal_message_size_bytes_available",
                False,
            )
        ),
        "normal_item_class_available": bool(
            stats.get_value("qualification/normal_item_class_available", False)
        ),
        "event_probe_complete": event_complete,
        "event_body_content_type_html": bool(
            stats.get_value("qualification/event_body_content_type_html", False)
        ),
        "event_logical_body_available": bool(
            stats.get_value("qualification/event_body_available", False)
        ),
        "event_html_request_once": (
            stats.get_value("qualification/event_html_request_count", 0) == 1
        ),
        "event_html_response_html": bool(
            stats.get_value("qualification/event_html_response_html", False)
        ),
        "event_html_projection_complete": bool(
            stats.get_value(
                "qualification/event_html_projection_complete",
                False,
            )
        ),
        "mail_scope_only": scopes == (expected_scope,),
        "raw_evidence_count": int(
            stats.get_value("msgloom/evidence/response_persisted_count", 0) or 0
        ),
        "run_failed": run_failed,
        "failure_reason_count": (
            len(failure_reasons)
            if isinstance(failure_reasons, (set, frozenset, tuple, list))
            else 0
        ),
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.confirm_live:
        raise SystemExit("qualification requires --confirm-live")
    if not 1 <= args.mail_page_size <= 1000:
        raise SystemExit("--mail-page-size must be between 1 and 1000")
    if args.mailbox and (
        args.mailbox != args.mailbox.strip() or len(args.mailbox) > 4096
    ):
        raise SystemExit("--mailbox is invalid")

    output_dir = args.output_dir.resolve()
    summary_file = args.summary_file.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_file.parent.mkdir(parents=True, exist_ok=True)

    settings = get_project_settings()
    overrides = {
        "MSGLOOM_DATABASE_URL": f"sqlite:///{output_dir / 'catalog.sqlite3'}",
        "MSGLOOM_RAW_EVIDENCE_DIR": str(output_dir / "raw-evidence"),
        "MSGLOOM_SOURCE_ID": args.source_id,
        "MSGLOOM_CATALOG_ENABLED": True,
        "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
        "MSGLOOM_SOURCE_IDENTITY_REQUIRED": False,
        "MSGLOOM_CRAWL_STATUS_ENABLED": False,
        "MSGLOOM_TARGET_MAILBOX": args.mailbox,
        "HTTPCACHE_ENABLED": False,
        "LOG_ENABLED": False,
    }
    for key, value in overrides.items():
        settings.set(key, value, priority="cmdline")

    process = CrawlerProcess(settings, install_root_handler=False)
    crawler = process.create_crawler(MailRuleQualificationSpider)
    expected_scope = "Mail.Read.Shared" if args.mailbox else "Mail.Read"
    process.crawl(
        crawler,
        qualification_message_id=args.message_id or "",
        qualification_event_message_id=args.event_message_id or "",
        qualification_page_size=str(args.mail_page_size),
    )
    process.start()

    payload = _summary(crawler, expected_scope=expected_scope)
    summary_file.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.chmod(summary_file, 0o600)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
