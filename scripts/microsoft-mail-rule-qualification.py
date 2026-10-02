#!/usr/bin/env python3
"""Run one private read-only Outlook Mail rule-probe qualification crawl."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scrapy.crawler import CrawlerProcess
from scrapy.http import TextResponse
from scrapy.utils.project import get_project_settings

from message_ingest.acquisition.microsoft.outlook.email import (
    MailRuleFact,
    MailRuleFacts,
    MailRuleObservation,
    MailRuleProbeStatus,
    MailRuleRequiredData,
    OutlookMailRuleProbeResult,
    mail_rule_observation_from_item,
    parse_mail_rule_policy,
)
from message_ingest.acquisition.microsoft.outlook.email.rule_body import (
    MailBodyUnavailable,
    logical_mail_body,
)
from message_ingest.acquisition.microsoft.outlook.email.rule_probe import (
    MAIL_RULE_PROBE_MAX_BYTES,
)
from message_ingest.spiders.microsoft.outlook.email.discover import (
    OutlookDiscoverSpider,
)
from microsoft_graph.protocol import GraphCollectionPage

_REQUIRED_DATA = frozenset(
    {
        MailRuleRequiredData.METADATA,
        MailRuleRequiredData.BODY,
        MailRuleRequiredData.HEADERS,
        MailRuleRequiredData.EXTENDED_PROPERTIES,
    }
)
_SAFE_FACTS = (
    MailRuleFact.CHANGE_KEY,
    MailRuleFact.BODY,
    MailRuleFact.HEADERS,
    MailRuleFact.SENSITIVITY,
    MailRuleFact.MESSAGE_SIZE_BYTES,
    MailRuleFact.ITEM_CLASS,
)


class MailRuleQualificationSpider(OutlookDiscoverSpider):
    """Discover a bounded sample, then issue one production probe per target."""

    name = "outlook_mail_rule_qualification"

    def __init__(
        self,
        *args,
        qualification_message_id: str = "",
        qualification_event_message_id: str = "",
        qualification_page_size: str = "10",
        **kwargs,
    ) -> None:
        super().__init__(
            *args,
            folder="",
            page_size=qualification_page_size,
            max_pages="1",
            _mail_rule_policy=parse_mail_rule_policy(None),
            **kwargs,
        )
        self._explicit_message_id = qualification_message_id
        self._explicit_event_id = qualification_event_message_id
        self._kinds_by_message_id: dict[str, set[str]] = {}

    async def start(self):
        """Issue exactly one bounded discovery page through production helpers."""

        self.crawler.stats.set_value("qualification/discovery_request_count", 1)
        path = self.messages_path(
            fields=self.discovery_fields,
            order_by="receivedDateTime desc",
            page_size=self.page_size,
        )
        yield self._message_list_request(f"{self.graph_root}{path}", page_number=1)

    def parse(
        self,
        response: TextResponse,
        *,
        purpose: str = "message-list",
        page_number: int = 1,
    ):
        """Select private targets without yielding semantic Mail Items."""

        del page_number
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        page = GraphCollectionPage.from_payload(
            response.json(),
            missing_value_empty=True,
            empty_links_absent=True,
            validate_links=False,
        )
        messages = page.values
        valid = [
            message
            for message in messages
            if isinstance(message.get("id"), str)
            and isinstance(message.get("changeKey"), str)
        ]
        self.crawler.stats.set_value(
            "qualification/discovery_change_key_available",
            bool(valid),
        )

        by_id = {
            message["id"]: message
            for message in valid
            if isinstance(message.get("id"), str)
        }
        normal_id = self._explicit_message_id or _first_normal_message_id(valid)
        event_id = self._explicit_event_id or _first_event_message_id(valid)
        self.crawler.stats.set_value(
            "qualification/normal_target_selected",
            bool(normal_id),
        )
        self.crawler.stats.set_value(
            "qualification/event_target_selected",
            bool(event_id),
        )

        targets: dict[str, set[str]] = {}
        if normal_id:
            targets.setdefault(normal_id, set()).add("normal")
        if event_id:
            targets.setdefault(event_id, set()).add("event")
        self._kinds_by_message_id = targets
        self.crawler.stats.set_value(
            "qualification/target_count",
            len(targets),
        )

        for message_id, kinds in targets.items():
            raw = by_id.get(message_id)
            observation = (
                mail_rule_observation_from_item(
                    self._message_item(
                        raw,
                        response.url,
                        evidence.observed_at,
                        observation_kind="qualification",
                        evidence_id=evidence.evidence_id,
                    )
                )
                if raw is not None
                else MailRuleObservation(
                    message_id=message_id,
                    run_id=self.run_id,
                    evidence_id=None,
                    observation_kind="qualification",
                    facts=MailRuleFacts(),
                )
            )
            for kind in kinds:
                self.crawler.stats.inc_value(
                    f"qualification/{kind}_probe_scheduled_count"
                )
            self.crawler.stats.inc_value("qualification/probe_request_count")
            yield self.mail_rule_probe_request(observation, _REQUIRED_DATA)
            if "event" in kinds:
                yield self._event_html_qualification_request(message_id)

    def _event_html_qualification_request(self, message_id: str):
        """Read one eventMessage without body-format preference for qualification."""

        self.crawler.stats.inc_value("qualification/event_html_request_count")
        return self.graph_request(
            self.message_path(
                message_id,
                fields=("id", "changeKey", "body"),
            ),
            callback=self.parse_event_html_qualification,
            errback=self.errback,
            operation="mail-rule-event-html-qualification",
            cb_kwargs={
                "purpose": "mail-rule-event-html-qualification",
                "message_id": message_id,
            },
            prefer=self.graph_prefer,
            dont_cache=True,
            download_maxsize=MAIL_RULE_PROBE_MAX_BYTES,
        )

    def parse_event_html_qualification(
        self,
        response: TextResponse,
        *,
        purpose: str,
        message_id: str,
    ):
        """Prove documented HTML eventMessage representation separately."""

        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        html = projected = False
        try:
            payload = response.json()
            if isinstance(payload, dict) and payload.get("id") == message_id:
                html, projected = _event_html_projection(payload)
        except (TypeError, ValueError):
            pass
        self.crawler.stats.set_value(
            "qualification/event_html_response_html",
            html,
        )
        self.crawler.stats.set_value(
            "qualification/event_html_projection_complete",
            projected,
        )

    def parse_mail_rule_probe(
        self,
        response: TextResponse,
        *,
        purpose: str,
        observation: MailRuleObservation,
        required_data: frozenset[MailRuleRequiredData],
    ):
        """Reuse production parser and retain only safe qualification stats."""

        content_type = _body_content_type(response)
        for output in super().parse_mail_rule_probe(
            response,
            purpose=purpose,
            observation=observation,
            required_data=required_data,
        ):
            if isinstance(output, OutlookMailRuleProbeResult):
                self._record_probe_result(
                    observation.message_id,
                    output,
                    content_type=content_type,
                )
                continue
            yield output

    def mail_rule_probe_errback(self, failure):
        """Reuse production failure conversion without leaking private context."""

        request = self._failure_request(failure)
        observation = request.cb_kwargs.get("observation")
        for output in super().mail_rule_probe_errback(failure):
            if isinstance(output, OutlookMailRuleProbeResult) and isinstance(
                observation, MailRuleObservation
            ):
                self._record_probe_result(
                    observation.message_id,
                    output,
                    content_type=None,
                )
                continue
            yield output

    def _record_probe_result(
        self,
        message_id: str,
        result: OutlookMailRuleProbeResult,
        *,
        content_type: str | None,
    ) -> None:
        kinds = self._kinds_by_message_id.get(message_id, ())
        for kind in kinds:
            prefix = f"qualification/{kind}"
            self.crawler.stats.set_value(
                f"{prefix}_probe_status",
                result.probe.status.value,
            )
            self.crawler.stats.set_value(
                f"{prefix}_probe_complete",
                result.probe.status is MailRuleProbeStatus.COMPLETE,
            )
            for fact in _SAFE_FACTS:
                self.crawler.stats.set_value(
                    f"{prefix}_{fact.value}_available",
                    fact in result.probe.facts.available_facts,
                )
            if kind == "event":
                self.crawler.stats.set_value(
                    "qualification/event_body_content_type_html",
                    content_type == "html",
                )


def _first_normal_message_id(messages: list[dict[str, Any]]) -> str:
    for message in messages:
        if not _is_event_message(message):
            value = message.get("id")
            if isinstance(value, str):
                return value
    return ""


def _first_event_message_id(messages: list[dict[str, Any]]) -> str:
    for message in messages:
        if _is_event_message(message):
            value = message.get("id")
            if isinstance(value, str):
                return value
    return ""


def _is_event_message(message: dict[str, Any]) -> bool:
    graph_type = message.get("@odata.type")
    return isinstance(graph_type, str) and "eventmessage" in graph_type.casefold()


def _body_content_type(response: TextResponse) -> str | None:
    try:
        payload = response.json()
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    body = payload.get("body")
    if not isinstance(body, dict):
        return None
    content_type = body.get("contentType")
    return content_type.casefold() if isinstance(content_type, str) else None


def _event_html_projection(payload: object) -> tuple[bool, bool]:
    """Return whether a provider payload proves the HTML logical-body path."""

    if not isinstance(payload, dict):
        return False, False
    body = payload.get("body")
    if not isinstance(body, dict):
        return False, False
    content_type = body.get("contentType")
    if not isinstance(content_type, str) or content_type.casefold() != "html":
        return False, False
    try:
        logical_mail_body(body)
    except MailBodyUnavailable:
        return True, False
    return True, True


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
