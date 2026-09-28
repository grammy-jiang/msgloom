"""
Keep useful acquisition identifiers in logs without exposing private message
payloads.
"""

from __future__ import annotations

import pytest
from scrapy import Spider

from message_ingest.items.acquisition import RawHttpEvidenceItem
from message_ingest.items.microsoft.outlook.email import OutlookMailItem
from message_ingest.logformatter import MessageIngestLogFormatter


def test_raw_evidence_log_summary_does_not_include_bodies_or_headers() -> None:
    item = RawHttpEvidenceItem(
        evidence_id="ev1",
        run_id="run1",
        purpose="message-list",
        observed_at="2026-09-26T00:00:00+00:00",
        origin="network",
        request_fingerprint="fp",
        request_url="https://graph.microsoft.com/v1.0/me/messages?secret=query",
        request_method="GET",
        request_headers={"Secret": ["do-not-log"]},
        request_body=b"secret-request-body",
        response_url="https://graph.microsoft.com/v1.0/me/messages?secret=query",
        response_status=200,
        response_headers={"Secret": ["do-not-log"]},
        response_body=b"secret-response-body",
        response_flags=[],
    )

    summary = MessageIngestLogFormatter._summary(item)

    if "message-list" not in summary:
        pytest.fail('Expected: "message-list" in summary')
    if "ev1" not in summary:
        pytest.fail('Expected: "ev1" in summary')
    if "secret" in summary:
        pytest.fail('Expected: "secret" not in summary')
    if "do-not-log" in summary:
        pytest.fail('Expected: "do-not-log" not in summary')


def test_mail_log_summary_does_not_include_subject_or_body_preview() -> None:
    item = OutlookMailItem(
        message_id="m1",
        subject="Secret subject",
        sender_address="sender@example.com",
        from_address="sender@example.com",
        received_date_time=None,
        internet_message_id=None,
        conversation_id=None,
        parent_folder_id=None,
        importance=None,
        inference_classification=None,
        is_read=None,
        has_attachments=None,
        body_preview="Secret body preview",
        raw={"id": "m1", "subject": "Secret subject"},
        source_response_url="https://graph.microsoft.com/v1.0/me/messages",
        observed_at="2026-09-26T00:00:00+00:00",
        observation_kind="discovery",
        evidence_id="ev1",
        run_id="run1",
    )

    summary = MessageIngestLogFormatter._summary(item)

    if summary != "OutlookMailItem(message_id='m1')":
        pytest.fail("Expected: summary == \"OutlookMailItem(message_id='m1')\"")
    if "Secret" in summary:
        pytest.fail('Expected: "Secret" not in summary')


def test_crawled_log_does_not_include_full_graph_url() -> None:
    from scrapy.http import Request, Response

    formatter = MessageIngestLogFormatter()
    request = Request(
        "https://graph.microsoft.com/v1.0/me/messages/delta?$deltatoken=secret-token",
        cb_kwargs={"purpose": "message-delta"},
    )
    response = Response(request.url, request=request, status=200)

    result = formatter.crawled(request, response, spider=Spider(name="test"))
    rendered = result["msg"] % result["args"]

    if "message-delta" not in rendered:
        pytest.fail('Expected: "message-delta" in rendered')
    if "secret-token" in rendered:
        pytest.fail('Expected: "secret-token" not in rendered')
    if "graph.microsoft.com" in rendered:
        pytest.fail('Expected: "graph.microsoft.com" not in rendered')


def test_download_error_log_omits_exception_text_and_url() -> None:
    from scrapy.http import Request
    from scrapy.utils.test import get_crawler
    from twisted.python.failure import Failure

    from message_ingest.spiders.microsoft.outlook.email.discover import (
        OutlookDiscoverSpider,
    )

    crawler = get_crawler(OutlookDiscoverSpider)
    spider = OutlookDiscoverSpider.from_crawler(crawler)
    request = Request(
        "https://graph.microsoft.com/v1.0/me/messages/delta?$deltatoken=secret-token",
        cb_kwargs={"purpose": "message-delta"},
    )
    failure = Failure(
        RuntimeError(
            "private transport failure at "
            "https://graph.microsoft.com/v1.0/me/messages?secret=1"
        )
    )

    result = MessageIngestLogFormatter().download_error(
        failure,
        request,
        spider,
        errmsg="private transport failure with secret-token",
    )
    rendered = result["msg"] % result["args"]

    if "RuntimeError" not in rendered:
        pytest.fail('Expected: "RuntimeError" in rendered')
    if "message-delta" not in rendered:
        pytest.fail('Expected: "message-delta" in rendered')
    if "secret-token" in rendered or "private transport failure" in rendered:
        pytest.fail("Expected: exception text and URL token not in rendered")


def test_dropped_log_omits_exception_message() -> None:
    from scrapy.utils.test import get_crawler

    from message_ingest.spiders.microsoft.outlook.email.discover import (
        OutlookDiscoverSpider,
    )

    crawler = get_crawler(OutlookDiscoverSpider)
    spider = OutlookDiscoverSpider.from_crawler(crawler)
    exception = RuntimeError("private dropped-item text")

    result = MessageIngestLogFormatter().dropped(
        object(),
        exception,
        response=None,
        spider=spider,
    )
    rendered = result["msg"] % result["args"]

    if "RuntimeError" not in rendered:
        pytest.fail('Expected: "RuntimeError" in rendered')
    if "private dropped-item text" in rendered:
        pytest.fail("Expected: exception message not in rendered")
