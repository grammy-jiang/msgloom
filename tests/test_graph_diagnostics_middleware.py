"""
Keep request correlation fresh per attempt and expose it in protocol logs.
"""

from __future__ import annotations

import logging
from uuid import UUID

import pytest
from scrapy.http import Request, Response
from scrapy.utils.misc import build_from_crawler
from scrapy.utils.test import get_crawler

from message_ingest.providers.microsoft_graph.diagnostics import MicrosoftGraphDiagnosticsMiddleware
from message_ingest.spiders.outlook_discover import OutlookDiscoverSpider


def _middleware():
    crawler = get_crawler(OutlookDiscoverSpider)
    crawler.spider = OutlookDiscoverSpider.from_crawler(crawler)
    return build_from_crawler(MicrosoftGraphDiagnosticsMiddleware, crawler)


def test_graph_request_gets_unique_client_request_id_and_debug_log(caplog) -> None:
    middleware = _middleware()
    caplog.set_level(logging.DEBUG, logger="message_ingest.providers.microsoft_graph")
    request = Request(
        "https://graph.microsoft.com/v1.0/me/messages",
        cb_kwargs={"purpose": "message-list"},
    )

    if middleware.process_request(request) is not None:
        pytest.fail("Expected: middleware.process_request(request) is None")

    raw_value = request.headers["client-request-id"]
    if raw_value is None:
        pytest.fail("Expected: raw_value is not None")
    value = raw_value.decode()
    if str(UUID(value)) != value:
        pytest.fail("Expected: str(UUID(value)) == value")
    if request.meta[middleware.client_request_id_meta] != value:
        pytest.fail(
            "Expected: request.meta[middleware.client_request_id_meta] == value"
        )
    if "purpose=message-list" not in caplog.text:
        pytest.fail('Expected: "purpose=message-list" in caplog.text')
    if value not in caplog.text:
        pytest.fail("Expected: value in caplog.text")
    if middleware.stats.get_value("msgloom/graph/request_count") != 1:
        pytest.fail(
            'Expected: middleware.stats.get_value("msgloom/graph/request_count") == 1'
        )
    if (
        middleware.stats.get_value("msgloom/graph/request_purpose_count/message-list")
        != 1
    ):
        pytest.fail(
            'Expected: middleware.stats.get_value("msgloom/graph/request_purpose_count/message-list") == 1'
        )


def test_graph_response_logs_server_request_id(caplog) -> None:
    middleware = _middleware()
    caplog.set_level(logging.DEBUG, logger="message_ingest.providers.microsoft_graph")
    request = Request(
        "https://graph.microsoft.com/v1.0/me/messages",
        cb_kwargs={"purpose": "message-list"},
    )
    middleware.process_request(request)
    response = Response(
        request.url,
        request=request,
        status=200,
        headers={"request-id": "server-request-id"},
    )

    if middleware.process_response(request, response) is not response:
        pytest.fail(
            "Expected: middleware.process_response(request, response) is response"
        )
    if "request_id=server-request-id" not in caplog.text:
        pytest.fail('Expected: "request_id=server-request-id" in caplog.text')
    if middleware.stats.get_value("msgloom/graph/response_count") != 1:
        pytest.fail(
            'Expected: middleware.stats.get_value("msgloom/graph/response_count") == 1'
        )
    if middleware.stats.get_value("msgloom/graph/response_status_count/200") != 1:
        pytest.fail(
            'Expected: middleware.stats.get_value("msgloom/graph/response_status_count/200") == 1'
        )
    if (
        middleware.stats.get_value(
            "msgloom/graph/response_purpose_status_count/message-list/200"
        )
        != 1
    ):
        pytest.fail(
            'Expected: middleware.stats.get_value("msgloom/graph/response_purpose_status_count/message-list/200") == 1'
        )


def test_retry_attempt_receives_new_client_request_id() -> None:
    middleware = _middleware()
    request = Request("https://graph.microsoft.com/v1.0/me/messages")
    middleware.process_request(request)
    first = request.headers["client-request-id"]
    retry = request.copy()
    middleware.process_request(retry)
    if retry.headers["client-request-id"] == first:
        pytest.fail('Expected: retry.headers["client-request-id"] != first')


def test_non_graph_request_is_untouched() -> None:
    middleware = _middleware()
    request = Request("https://example.com/")
    if middleware.process_request(request) is not None:
        pytest.fail("Expected: middleware.process_request(request) is None")
    if "client-request-id" in request.headers:
        pytest.fail('Expected: "client-request-id" not in request.headers')


def test_missing_server_request_id_and_transport_exception_are_counted() -> None:
    middleware = _middleware()
    request = Request(
        "https://graph.microsoft.com/v1.0/me/messages",
        cb_kwargs={"purpose": "message-list"},
    )
    middleware.process_request(request)
    response = Response(request.url, request=request, status=503)
    middleware.process_response(request, response)
    middleware.process_exception(request, RuntimeError("connection reset"))

    if (
        middleware.stats.get_value("msgloom/graph/response_missing_request_id_count")
        != 1
    ):
        pytest.fail(
            'Expected: middleware.stats.get_value("msgloom/graph/response_missing_request_id_count") == 1'
        )
    if middleware.stats.get_value("msgloom/graph/exception_count") != 1:
        pytest.fail(
            'Expected: middleware.stats.get_value("msgloom/graph/exception_count") == 1'
        )
    if (
        middleware.stats.get_value("msgloom/graph/exception_purpose_count/message-list")
        != 1
    ):
        pytest.fail(
            'Expected: middleware.stats.get_value("msgloom/graph/exception_purpose_count/message-list") == 1'
        )
    if (
        middleware.stats.get_value("msgloom/graph/exception_type_count/RuntimeError")
        != 1
    ):
        pytest.fail(
            'Expected: middleware.stats.get_value("msgloom/graph/exception_type_count/RuntimeError") == 1'
        )


def test_cached_graph_response_is_counted_as_replay_not_transport(caplog) -> None:
    middleware = _middleware()
    request = Request(
        "https://graph.microsoft.com/v1.0/me/messages",
        cb_kwargs={"purpose": "message-list"},
    )
    response = Response(
        request.url,
        request=request,
        status=200,
        flags=["cached"],
    )
    caplog.set_level(logging.DEBUG, logger="message_ingest.providers.microsoft_graph")

    returned = middleware.process_response(request, response)

    if returned is not response:
        pytest.fail("Expected: returned is response")
    if middleware.stats.get_value("msgloom/graph/cache_replay_count") != 1:
        pytest.fail(
            'Expected: middleware.stats.get_value("msgloom/graph/cache_replay_count") == 1'
        )
    if (
        middleware.stats.get_value(
            "msgloom/graph/cache_replay_purpose_count/message-list"
        )
        != 1
    ):
        pytest.fail(
            'Expected: middleware.stats.get_value("msgloom/graph/cache_replay_purpose_count/message-list") == 1'
        )
    if middleware.stats.get_value("msgloom/graph/response_count") is not None:
        pytest.fail(
            'Expected: middleware.stats.get_value("msgloom/graph/response_count") is None'
        )
    if "cached response: status=200 purpose=message-list" not in caplog.text:
        pytest.fail(
            'Expected: "cached response: status=200 purpose=message-list" in caplog.text'
        )
    if "client_request_id" in caplog.text:
        pytest.fail("Expected: cached replay log has no client_request_id")
