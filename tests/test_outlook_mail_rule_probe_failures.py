"""Named Spider request/callback contract for dynamic Mail rule probes."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest
from scrapy.http import Response, TextResponse
from scrapy.spidermiddlewares.httperror import HttpError
from scrapy.utils.test import get_crawler
from twisted.python.failure import Failure

from message_ingest.acquisition.microsoft.outlook.email import (
    MailRuleFact,
    MailRuleProbeStatus,
    MailRuleRequiredData,
    OutlookMailRuleProbeResult,
    mail_rule_observation_from_item,
)
from message_ingest.items.acquisition import RawHttpEvidenceItem
from message_ingest.items.microsoft.outlook.email import OutlookMailItem
from message_ingest.spiders.microsoft.outlook.email.discover import (
    OutlookDiscoverSpider,
)


def _spider() -> OutlookDiscoverSpider:
    crawler = get_crawler(
        OutlookDiscoverSpider,
        settings_dict={"MSGLOOM_SOURCE_IDENTITY_REQUIRED": False},
    )
    spider = OutlookDiscoverSpider.from_crawler(crawler)
    crawler.spider = spider
    return spider


def _observation():
    item = OutlookMailItem.from_graph(
        {
            "id": "message-1",
            "changeKey": "change-1",
            "lastModifiedDateTime": "2026-09-30T03:00:00Z",
            "bodyPreview": "preview",
        },
        source_response_url="https://graph.example.test/messages",
        observed_at="2026-09-30T03:00:01Z",
        observation_kind="delta",
        evidence_id="evidence-source",
        run_id="run-1",
    )
    return mail_rule_observation_from_item(item)


def _response(request, payload: object) -> TextResponse:
    return TextResponse(
        request.url,
        request=request,
        body=json.dumps(payload).encode(),
        encoding="utf-8",
        headers={"Content-Type": "application/json"},
    )


def _query_for(*required: MailRuleRequiredData) -> tuple[Any, dict[str, list[str]]]:
    spider = _spider()
    request = spider.mail_rule_probe_request(
        _observation(),
        frozenset(required),
    )
    return request, parse_qs(urlsplit(request.url).query)


def test_event_message_html_body_uses_logical_body_projection() -> None:
    spider = _spider()
    observation = _observation()
    required = frozenset({MailRuleRequiredData.BODY})
    request = spider.mail_rule_probe_request(observation, required)

    output = list(
        spider.parse_mail_rule_probe(
            _response(
                request,
                {
                    "id": "message-1",
                    "changeKey": "change-1",
                    "body": {
                        "contentType": "html",
                        "content": "<p>Hello <b>Team</b></p><script>secret()</script>",
                    },
                },
            ),
            **request.cb_kwargs,
        )
    )

    result = output[1]
    if not isinstance(result, OutlookMailRuleProbeResult):
        pytest.fail("HTML rule probe did not return internal probe data")
    if result.probe.facts.body != "Hello Team":
        pytest.fail(f"HTML BODY projection changed: {result.probe.facts.body!r}")


def test_partial_probe_keeps_valid_facts_and_marks_only_missing_requested_fact() -> (
    None
):
    spider = _spider()
    observation = _observation()
    required = frozenset({MailRuleRequiredData.BODY, MailRuleRequiredData.HEADERS})
    request = spider.mail_rule_probe_request(observation, required)

    output = list(
        spider.parse_mail_rule_probe(
            _response(
                request,
                {
                    "id": "message-1",
                    "changeKey": "change-1",
                    "body": {"contentType": "text", "content": "body ok"},
                },
            ),
            **request.cb_kwargs,
        )
    )
    result = output[1]
    if not isinstance(result, OutlookMailRuleProbeResult):
        pytest.fail("Partial rule probe did not return internal result")
    if result.probe.status is not MailRuleProbeStatus.PARTIAL:
        pytest.fail("Missing requested headers should make probe PARTIAL")
    if result.probe.facts.body != "body ok":
        pytest.fail("Partial probe discarded valid BODY fact")
    if MailRuleFact.BODY not in result.probe.facts.available_facts:
        pytest.fail("Partial probe lost BODY availability")
    if (
        result.probe.failures != (result.probe.failures[0],)
        or result.probe.failures[0].fact is not MailRuleFact.HEADERS
    ):
        pytest.fail(
            f"Partial probe failure attribution changed: {result.probe.failures!r}"
        )


@pytest.mark.parametrize(
    ("properties", "failed_fact"),
    (
        (
            [
                {"id": "Integer 0x0036", "value": "99"},
                {"id": "Integer 0x0E08", "value": "4096"},
                {"id": "String 0x001A", "value": "IPM.Note"},
            ],
            MailRuleFact.SENSITIVITY,
        ),
        (
            [
                {"id": "Integer 0x0036", "value": "2"},
                {"id": "Integer 0x0E08", "value": "-1"},
                {"id": "String 0x001A", "value": "IPM.Note"},
            ],
            MailRuleFact.MESSAGE_SIZE_BYTES,
        ),
        (
            [
                {"id": "Integer 0x0036", "value": "2"},
                {"id": "Integer 0x0E08", "value": "4096"},
                {"id": "String 0x001A", "value": 123},
            ],
            MailRuleFact.ITEM_CLASS,
        ),
    ),
)
def test_invalid_extended_property_is_partial_not_all_or_nothing(
    properties: list[dict[str, object]],
    failed_fact: MailRuleFact,
) -> None:
    spider = _spider()
    required = frozenset({MailRuleRequiredData.EXTENDED_PROPERTIES})
    request = spider.mail_rule_probe_request(_observation(), required)

    output = list(
        spider.parse_mail_rule_probe(
            _response(
                request,
                {
                    "id": "message-1",
                    "changeKey": "change-1",
                    "singleValueExtendedProperties": properties,
                },
            ),
            **request.cb_kwargs,
        )
    )
    result = output[1]
    if not isinstance(result, OutlookMailRuleProbeResult):
        pytest.fail("Invalid extended property did not return probe result")
    if result.probe.status is not MailRuleProbeStatus.PARTIAL:
        pytest.fail("One invalid extended property should preserve other facts")
    if failed_fact in result.probe.facts.available_facts:
        pytest.fail("Invalid extended property was incorrectly marked available")
    if failed_fact not in {failure.fact for failure in result.probe.failures}:
        pytest.fail("Invalid extended property lost fact-level failure attribution")


def test_duplicate_extended_property_id_is_bounded_partial_failure() -> None:
    spider = _spider()
    required = frozenset({MailRuleRequiredData.EXTENDED_PROPERTIES})
    request = spider.mail_rule_probe_request(_observation(), required)

    output = list(
        spider.parse_mail_rule_probe(
            _response(
                request,
                {
                    "id": "message-1",
                    "changeKey": "change-1",
                    "singleValueExtendedProperties": [
                        {"id": "Integer 0x0036", "value": "2"},
                        {"id": "Integer 0x36", "value": "3"},
                        {"id": "Integer 0x0E08", "value": "4096"},
                        {"id": "String 0x001A", "value": "IPM.Note"},
                    ],
                },
            ),
            **request.cb_kwargs,
        )
    )
    result = output[1]
    if not isinstance(result, OutlookMailRuleProbeResult):
        pytest.fail("Duplicate extended property did not return probe result")
    if result.probe.status is not MailRuleProbeStatus.PARTIAL:
        pytest.fail("Duplicate extended property must be bounded PARTIAL")
    if MailRuleFact.SENSITIVITY in result.probe.facts.available_facts:
        pytest.fail("Duplicate sensitivity values were incorrectly trusted")


@pytest.mark.parametrize(
    "payload",
    [
        {
            "id": "different-message",
            "changeKey": "change-1",
            "body": {"contentType": "text", "content": "complete body"},
        },
        {
            "id": "message-1",
            "body": {"contentType": "text", "content": "complete body"},
        },
        {
            "id": "message-1",
            "changeKey": 123,
            "body": {"contentType": "text", "content": "complete body"},
        },
    ],
)
def test_missing_or_invalid_identity_version_is_failed_probe(payload: object) -> None:
    spider = _spider()
    required = frozenset({MailRuleRequiredData.BODY})
    request = spider.mail_rule_probe_request(_observation(), required)

    output = list(
        spider.parse_mail_rule_probe(
            _response(request, payload),
            **request.cb_kwargs,
        )
    )
    result = output[1]
    if not isinstance(result, OutlookMailRuleProbeResult):
        pytest.fail("Invalid identity/version did not return a probe result")
    if result.probe.status is not MailRuleProbeStatus.FAILED:
        pytest.fail("Invalid identity/version must fail the whole probe")
    if result.probe.facts.available_facts:
        pytest.fail("Invalid identity/version must not retain mixed source facts")


def test_probe_errback_attributes_failure_to_every_requested_group() -> None:
    spider = _spider()
    observation = _observation()
    required = frozenset(
        {
            MailRuleRequiredData.BODY,
            MailRuleRequiredData.HEADERS,
            MailRuleRequiredData.EXTENDED_PROPERTIES,
        }
    )
    request = spider.mail_rule_probe_request(observation, required)
    response = Response(request.url, status=404, request=request)
    failure: Any = Failure(HttpError(response, "private failure text"))
    failure.request = request

    output = list(spider.mail_rule_probe_errback(failure))

    evidence, result = output
    if not isinstance(evidence, RawHttpEvidenceItem):
        pytest.fail("Probe errback must preserve exhausted request evidence")
    if not isinstance(result, OutlookMailRuleProbeResult):
        pytest.fail("Probe errback must return a bounded failed result")
    if result.probe.status is not MailRuleProbeStatus.FAILED:
        pytest.fail("Exhausted rule probe must be FAILED")
    failed = {failure.fact for failure in result.probe.failures}
    expected = {
        MailRuleFact.BODY,
        MailRuleFact.HEADERS,
        MailRuleFact.SENSITIVITY,
        MailRuleFact.MESSAGE_SIZE_BYTES,
        MailRuleFact.ITEM_CLASS,
    }
    if failed != expected:
        pytest.fail(f"Probe request failure attribution changed: {failed!r}")
    if {failure.reason_code for failure in result.probe.failures} != {
        "probe_request_failed"
    }:
        pytest.fail("Probe request failure reason changed")
    if result.probe.facts.available_facts:
        pytest.fail("Exhausted rule probe must not fabricate source facts")
    if spider.run_failed:
        pytest.fail("Expected rule-probe unavailability must not fail crawl directly")
