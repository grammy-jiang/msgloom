"""Named Spider request/callback contract for transitional Mail BODY probes."""

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


def test_probe_request_selects_transitional_body_fields_and_text_body() -> None:
    spider = _spider()
    observation = _observation()

    request = spider.mail_rule_probe_request(observation)

    query = parse_qs(urlsplit(request.url).query)
    if query.get("$select") != ["id,changeKey,body,bodyPreview"]:
        pytest.fail(f"Unexpected transitional probe field selection: {query!r}")
    raw_prefer = request.headers.get("Prefer")
    if raw_prefer is None:
        pytest.fail("Rule probe lost its Prefer header")
    prefer = raw_prefer.decode()
    expected = 'IdType="ImmutableId", outlook.body-content-type="text"'
    if prefer != expected:
        pytest.fail(f"Unexpected rule probe Prefer header: {prefer!r}")


def test_probe_request_uses_named_callback_errback_and_disables_cache() -> None:
    spider = _spider()
    observation = _observation()

    request = spider.mail_rule_probe_request(observation)

    if request.callback != spider.parse_mail_rule_probe:
        pytest.fail("Rule probe must use the named Spider callback")
    if request.errback != spider.mail_rule_probe_errback:
        pytest.fail("Rule probe must use the named Spider errback")
    if request.meta.get("dont_cache") is not True:
        pytest.fail("Rule probe must bypass HTTP cache replay")
    if request.cb_kwargs.get("observation") != observation:
        pytest.fail("Rule probe must carry the bounded original observation")


def test_successful_probe_emits_raw_evidence_and_new_fact_container() -> None:
    spider = _spider()
    observation = _observation()
    request = spider.mail_rule_probe_request(observation)
    response = _response(
        request,
        {
            "id": "message-1",
            "changeKey": "change-1",
            "body": {"contentType": "text", "content": "complete body"},
            "bodyPreview": "preview",
        },
    )

    output = list(spider.parse_mail_rule_probe(response, **request.cb_kwargs))

    if len(output) != 2:
        pytest.fail(f"Expected evidence plus internal probe result, got {output!r}")
    evidence, result = output
    if not isinstance(evidence, RawHttpEvidenceItem):
        pytest.fail("Rule probe must preserve ordinary raw HTTP evidence")
    if not isinstance(result, OutlookMailRuleProbeResult):
        pytest.fail("Rule probe callback must emit one internal probe result")
    if result.observation != observation:
        pytest.fail("Probe result lost its original bounded observation")
    if result.probe.status is not MailRuleProbeStatus.COMPLETE:
        pytest.fail("Valid BODY probe must be COMPLETE")
    if result.probe.facts.body != "complete body":
        pytest.fail("Complete body text changed")
    if result.probe.facts.change_key != "change-1":
        pytest.fail("Probe changeKey changed")
    if not {
        MailRuleFact.BODY,
        MailRuleFact.CHANGE_KEY,
        MailRuleFact.BODY_PREVIEW,
    }.issubset(result.probe.facts.available_facts):
        pytest.fail("Complete BODY probe lost fact availability")
    if result.probe.failures:
        pytest.fail("Complete BODY probe unexpectedly retained failures")
    if result.probe.evidence_id != evidence.evidence_id:
        pytest.fail("Probe result must reference the acquired response evidence")


@pytest.mark.parametrize(
    "payload",
    [
        {
            "id": "message-1",
            "changeKey": "change-1",
            "body": {},
        },
        {
            "id": "message-1",
            "body": {"contentType": "text", "content": "complete body"},
        },
        {
            "id": "different-message",
            "changeKey": "change-1",
            "body": {"contentType": "text", "content": "complete body"},
        },
    ],
)
def test_malformed_successful_probe_becomes_failed_fact_result(payload) -> None:
    spider = _spider()
    observation = _observation()
    request = spider.mail_rule_probe_request(observation)

    output = list(
        spider.parse_mail_rule_probe(
            _response(request, payload),
            **request.cb_kwargs,
        )
    )

    if not isinstance(output[0], RawHttpEvidenceItem):
        pytest.fail("Malformed probe response must still preserve source evidence")
    result = output[1]
    if not isinstance(result, OutlookMailRuleProbeResult):
        pytest.fail("Malformed source representation must become a probe result")
    if result.probe.status is not MailRuleProbeStatus.FAILED:
        pytest.fail("Malformed source representation must fail the rule probe")
    if result.probe.facts.available_facts:
        pytest.fail("Failed transitional BODY probe must not retain partial truth")
    if len(result.probe.failures) != 1:
        pytest.fail(
            "Failed transitional BODY probe must expose one bounded fact failure"
        )
    if result.probe.failures[0].fact is not MailRuleFact.BODY:
        pytest.fail("Malformed transitional probe must classify BODY failure")
    if result.probe.failures[0].reason_code != "invalid_probe_payload":
        pytest.fail("Malformed source representation must use bounded reason code")


def test_probe_errback_emits_failure_evidence_and_failed_fact_result() -> None:
    spider = _spider()
    observation = _observation()
    request = spider.mail_rule_probe_request(observation)
    response = Response(request.url, status=404, request=request)
    failure: Any = Failure(HttpError(response, "private failure text"))
    failure.request = request

    output = list(spider.mail_rule_probe_errback(failure))

    if len(output) != 2:
        pytest.fail("Probe errback must emit failure evidence and internal result")
    evidence, result = output
    if not isinstance(evidence, RawHttpEvidenceItem):
        pytest.fail("Probe errback must preserve exhausted request evidence")
    if not isinstance(result, OutlookMailRuleProbeResult):
        pytest.fail("Probe errback must return a bounded internal failed result")
    if result.probe.status is not MailRuleProbeStatus.FAILED:
        pytest.fail("Exhausted rule probe must be represented as FAILED")
    if result.probe.failures[0].reason_code != "probe_request_failed":
        pytest.fail("Exhausted rule probe reason code changed")
    if result.probe.facts.available_facts:
        pytest.fail("Exhausted rule probe must not fabricate source facts")
    if spider.run_failed:
        pytest.fail(
            "Expected rule-probe unavailability must not fail source crawl directly"
        )
