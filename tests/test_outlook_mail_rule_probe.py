"""Named Spider request/callback contract for dynamic Mail rule probes."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest
from scrapy.http import TextResponse
from scrapy.utils.test import get_crawler

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


def test_metadata_probe_selects_bounded_discovery_fields() -> None:
    request, query = _query_for(MailRuleRequiredData.METADATA)

    selected = query["$select"][0].split(",")
    expected = {
        "id",
        "changeKey",
        "lastModifiedDateTime",
        "subject",
        "from",
        "sender",
        "toRecipients",
        "ccRecipients",
        "bccRecipients",
        "replyTo",
        "receivedDateTime",
        "sentDateTime",
        "createdDateTime",
        "importance",
        "categories",
        "hasAttachments",
        "isRead",
        "isDraft",
        "inferenceClassification",
        "flag",
        "bodyPreview",
    }
    if set(selected) != expected or len(selected) != len(expected):
        pytest.fail(f"Unexpected metadata probe selection: {selected!r}")
    if "$expand" in query:
        pytest.fail("Metadata-only rule probe unexpectedly expands legacy properties")
    if request.headers.get("Prefer") != b'IdType="ImmutableId"':
        pytest.fail(
            "Metadata-only probe added unrelated body representation preference"
        )


def test_body_probe_selects_body_and_text_preference() -> None:
    _request, query = _query_for(MailRuleRequiredData.BODY)
    selected = query["$select"][0].split(",")

    if selected != ["id", "changeKey", "body"]:
        pytest.fail(f"Unexpected BODY probe selection: {selected!r}")
    request, _query = _query_for(MailRuleRequiredData.BODY)
    expected = b'IdType="ImmutableId", outlook.body-content-type="text"'
    if request.headers.get("Prefer") != expected:
        pytest.fail("BODY probe lost the deterministic text preference")


def test_headers_probe_selects_internet_message_headers() -> None:
    _request, query = _query_for(MailRuleRequiredData.HEADERS)

    if query.get("$select") != ["id,changeKey,internetMessageHeaders"]:
        pytest.fail(f"Unexpected HEADERS probe selection: {query!r}")


def test_extended_properties_probe_uses_exact_fixed_ids() -> None:
    _request, query = _query_for(MailRuleRequiredData.EXTENDED_PROPERTIES)

    if query.get("$select") != ["id,changeKey"]:
        pytest.fail(f"Unexpected extended-property select: {query!r}")
    expand = query.get("$expand")
    if expand is None or len(expand) != 1:
        pytest.fail(f"Missing one extended-property expansion: {query!r}")
    if not expand[0].startswith("singleValueExtendedProperties("):
        pytest.fail(
            f"Graph message expansion used the wrong navigation property: {expand!r}"
        )
    for property_id in ("Integer 0x0036", "Integer 0x0E08", "String 0x001A"):
        if property_id not in expand[0]:
            pytest.fail(f"Extended-property expansion lost {property_id!r}")


def test_composite_probe_unions_fields_in_one_request_without_duplicates() -> None:
    request, query = _query_for(
        MailRuleRequiredData.METADATA,
        MailRuleRequiredData.BODY,
        MailRuleRequiredData.HEADERS,
        MailRuleRequiredData.EXTENDED_PROPERTIES,
    )

    selected = query["$select"][0].split(",")
    if selected.count("id") != 1 or selected.count("changeKey") != 1:
        pytest.fail("Composite rule probe duplicated mandatory fields")
    for field in ("body", "internetMessageHeaders", "subject", "toRecipients"):
        if selected.count(field) != 1:
            pytest.fail(f"Composite rule probe lost/duplicated {field!r}")
    if "$expand" not in query:
        pytest.fail("Composite rule probe lost its extended-property expansion")
    if request.meta.get("dont_cache") is not True:
        pytest.fail("Composite rule probe must always bypass HTTP cache")
    if request.meta.get("download_maxsize") != 8 * 1024 * 1024:
        pytest.fail("Composite rule probe lost its 8 MiB response cap")
    required = request.cb_kwargs.get("required_data")
    if required != frozenset(
        {
            MailRuleRequiredData.METADATA,
            MailRuleRequiredData.BODY,
            MailRuleRequiredData.HEADERS,
            MailRuleRequiredData.EXTENDED_PROPERTIES,
        }
    ):
        pytest.fail("Composite rule probe lost its immutable required-data context")


def test_probe_request_rejects_empty_required_data() -> None:
    spider = _spider()
    with pytest.raises(ValueError):
        spider.mail_rule_probe_request(_observation(), frozenset())


def test_probe_request_uses_named_callback_errback_and_bounded_context() -> None:
    spider = _spider()
    observation = _observation()
    required = frozenset({MailRuleRequiredData.BODY, MailRuleRequiredData.HEADERS})

    request = spider.mail_rule_probe_request(observation, required)

    if request.callback != spider.parse_mail_rule_probe:
        pytest.fail("Rule probe must use the named Spider callback")
    if request.errback != spider.mail_rule_probe_errback:
        pytest.fail("Rule probe must use the named Spider errback")
    if request.cb_kwargs.get("observation") != observation:
        pytest.fail("Rule probe must carry the bounded original observation")
    if request.cb_kwargs.get("required_data") != required:
        pytest.fail("Rule probe must carry immutable required-data context")
    if "policy" in request.cb_kwargs or "ruleset_digest" in request.cb_kwargs:
        pytest.fail("Rule probe callback context contains private policy state")


def test_successful_composite_probe_emits_all_requested_facts() -> None:
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
    response = _response(
        request,
        {
            "id": "message-1",
            "changeKey": "change-1",
            "body": {"contentType": "text", "content": "complete body"},
            "internetMessageHeaders": [
                {"name": "X-Test", "value": "one"},
                {"name": "Subject", "value": "private-looking but source data"},
            ],
            "singleValueExtendedProperties": [
                {"id": "Integer 0x36", "value": "2"},
                {"id": "Integer 0xe08", "value": "4096"},
                {"id": "String 0x1a", "value": "IPM.Note"},
            ],
        },
    )

    output = list(spider.parse_mail_rule_probe(response, **request.cb_kwargs))

    evidence, result = output
    if not isinstance(evidence, RawHttpEvidenceItem):
        pytest.fail("Rule probe must preserve ordinary raw HTTP evidence")
    if not isinstance(result, OutlookMailRuleProbeResult):
        pytest.fail("Rule probe callback must emit one internal probe result")
    probe = result.probe
    if probe.status is not MailRuleProbeStatus.COMPLETE or probe.failures:
        pytest.fail(f"Valid composite probe was not COMPLETE: {probe!r}")
    if probe.facts.body != "complete body":
        pytest.fail("Composite probe lost logical BODY")
    if probe.facts.headers != (
        "X-Test: one",
        "Subject: private-looking but source data",
    ):
        pytest.fail("Composite probe did not canonicalize internet headers")
    if probe.facts.sensitivity != "private":
        pytest.fail("Composite probe did not map PidTagSensitivity")
    if probe.facts.message_size_bytes != 4096:
        pytest.fail("Composite probe did not parse PidTagMessageSize")
    if probe.facts.item_class != "IPM.Note":
        pytest.fail("Composite probe did not parse PidTagMessageClass")
    expected = {
        MailRuleFact.CHANGE_KEY,
        MailRuleFact.BODY,
        MailRuleFact.HEADERS,
        MailRuleFact.SENSITIVITY,
        MailRuleFact.MESSAGE_SIZE_BYTES,
        MailRuleFact.ITEM_CLASS,
    }
    if not expected.issubset(probe.facts.available_facts):
        pytest.fail("Composite probe lost requested fact availability")
    if probe.evidence_id != evidence.evidence_id:
        pytest.fail("Composite probe lost its raw-evidence reference")
