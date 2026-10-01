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
            "singleValueLegacyExtendedProperties": [
                {"id": "Integer 0x0036", "value": "2"},
                {"id": "Integer 0x0E08", "value": "4096"},
                {"id": "String 0x001A", "value": "IPM.Note"},
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
                    "singleValueLegacyExtendedProperties": properties,
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
                    "singleValueLegacyExtendedProperties": [
                        {"id": "Integer 0x0036", "value": "2"},
                        {"id": "Integer 0x0036", "value": "3"},
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
