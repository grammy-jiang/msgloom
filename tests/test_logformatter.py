"""
Keep useful acquisition identifiers in logs without exposing private message
payloads.
"""

from __future__ import annotations

import pytest
from scrapy import Spider

from message_ingest.items.acquisition import RawHttpEvidenceItem
from message_ingest.items.microsoft.outlook.calendar import (
    OutlookCalendarDeltaCheckpointCandidateItem,
    OutlookCalendarEventItem,
)
from message_ingest.items.microsoft.outlook.email import OutlookMailItem
from message_ingest.observability.formatter import MessageIngestLogFormatter
from message_ingest.observability.item_summary import summarize_item


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

    summary = summarize_item(item)

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

    summary = summarize_item(item)

    if summary != "OutlookMailItem(message_id='m1')":
        pytest.fail("Expected: summary == \"OutlookMailItem(message_id='m1')\"")
    if "Secret" in summary:
        pytest.fail('Expected: "Secret" not in summary')


def test_calendar_log_summary_does_not_include_raw_event_payload() -> None:
    item = OutlookCalendarEventItem(
        event_id="event-1",
        raw={"subject": "Secret calendar subject", "body": "Secret body"},
        observed_at="2026-09-28T00:00:00+00:00",
        evidence_id="ev1",
        run_id="run1",
        calendar_id="calendar-1",
    )

    summary = summarize_item(item)

    if summary != (
        "OutlookCalendarEventItem(event_id='event-1', calendar_id='calendar-1')"
    ):
        pytest.fail(f"Unexpected Calendar event summary: {summary!r}")
    if "Secret" in summary:
        pytest.fail("Expected Calendar event payload not to enter logs")


def test_calendar_delta_candidate_summary_omits_delta_link_and_window() -> None:
    item = OutlookCalendarDeltaCheckpointCandidateItem(
        run_id="run1",
        attempt=2,
        base_revision=1,
        delta_link="https://graph.microsoft.com/v1.0/me/calendarView/delta?$deltatoken=secret",
        observed_at="2026-09-28T00:00:00+00:00",
        evidence_id="ev1",
        start_datetime="2026-01-01T00:00:00+00:00",
        end_datetime="2027-01-01T00:00:00+00:00",
    )

    summary = summarize_item(item)

    if summary != (
        "OutlookCalendarDeltaCheckpointCandidateItem("
        "attempt=2, calendar_scope='default')"
    ):
        pytest.fail(f"Unexpected Calendar delta summary: {summary!r}")
    if "secret" in summary or "2026-01-01" in summary:
        pytest.fail("Expected Calendar delta cursor/window not to enter logs")


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
    if "Crawled acquisition response" not in rendered:
        pytest.fail("Expected provider-neutral acquisition response log")
    if "Crawled Graph response" in rendered:
        pytest.fail("Expected global formatter not to hard-code Microsoft Graph")
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
    if "Error downloading acquisition request" not in rendered:
        pytest.fail("Expected provider-neutral acquisition request log")
    if "Error downloading Graph request" in rendered:
        pytest.fail("Expected global formatter not to hard-code Microsoft Graph")
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
