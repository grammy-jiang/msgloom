"""Private Outlook Mail RuleEngine live-qualification spider support."""

from __future__ import annotations

from typing import Any

from scrapy.http import TextResponse

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
