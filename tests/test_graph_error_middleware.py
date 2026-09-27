"""
Verify provider retry delays and exhaustion independently of generic transport
retries.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import pytest
from scrapy.http import Request, TextResponse
from scrapy.utils.misc import build_from_crawler
from scrapy.utils.test import get_crawler

from message_ingest.providers.microsoft_graph.errors import MicrosoftGraphErrorMiddleware
from message_ingest.spiders.outlook_discover import OutlookDiscoverSpider


def _middleware():
    crawler = get_crawler(
        OutlookDiscoverSpider,
        settings_dict={
            "MS_GRAPH_ERROR_MIDDLEWARE_ENABLED": True,
            "MS_GRAPH_ERROR_MAX_RETRIES": 3,
            "MS_GRAPH_ERROR_FALLBACK_BASE_SECONDS": 2,
            "MS_GRAPH_ERROR_FALLBACK_MAX_SECONDS": 20,
        },
    )
    crawler.spider = OutlookDiscoverSpider.from_crawler(crawler)
    return build_from_crawler(MicrosoftGraphErrorMiddleware, crawler)


def _response(
    request: Request,
    status: int,
    *,
    code: str | None = None,
    inner_code: str | None = None,
    retry_after: str | None = None,
) -> TextResponse:
    error: dict = {}
    if code is not None:
        error["code"] = code
    if inner_code is not None:
        error["innerError"] = {"code": inner_code}
    body = json.dumps({"error": error}).encode() if error else b""
    headers = {"Content-Type": "application/json"}
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return TextResponse(
        request.url,
        request=request,
        status=status,
        headers=headers,
        body=body,
        encoding="utf-8",
    )


def _request(**meta) -> Request:
    return Request(
        "https://graph.microsoft.com/v1.0/me/messages",
        callback=lambda response, **kwargs: None,
        cb_kwargs={"purpose": "message-list"},
        meta=meta,
    )


def test_429_honors_retry_after_and_uses_scrapy_retry_request(
    monkeypatch, caplog
) -> None:
    middleware = _middleware()
    delays = []

    async def fake_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr("message_ingest.providers.microsoft_graph.errors.asyncio.sleep", fake_sleep)
    caplog.set_level(logging.WARNING, logger="message_ingest.providers.microsoft_graph")
    request = _request()
    response = _response(request, 429, code="TooManyRequests", retry_after="7")
    retry = asyncio.run(middleware.process_response(request, response))

    if not isinstance(retry, Request):
        pytest.fail("Expected: isinstance(retry, Request)")
    if retry.dont_filter is not True:
        pytest.fail("Expected: retry.dont_filter is True")
    if retry.meta[middleware.retry_meta_key] != 1:
        pytest.fail("Expected: retry.meta[middleware.retry_meta_key] == 1")
    if "retry_times" in retry.meta:
        pytest.fail('Expected: "retry_times" not in retry.meta')
    if delays != [7.0]:
        pytest.fail("Expected: delays == [7.0]")
    if middleware.stats.get_value("msgloom/graph_error_retry/count") != 1:
        pytest.fail(
            'Expected: middleware.stats.get_value("msgloom/graph_error_retry/count") == 1'
        )
    if middleware.stats.get_value("msgloom/graph_error/status_count/429") != 1:
        pytest.fail(
            'Expected: middleware.stats.get_value("msgloom/graph_error/status_count/429") == 1'
        )
    if (
        middleware.stats.get_value(
            "msgloom/graph_error/retry_purpose_count/message-list"
        )
        != 1
    ):
        pytest.fail(
            'Expected: middleware.stats.get_value("msgloom/graph_error/retry_purpose_count/message-list") == 1'
        )
    if middleware.stats.get_value("msgloom/graph_error/max_delay_seconds") != 7.0:
        pytest.fail(
            'Expected: middleware.stats.get_value("msgloom/graph_error/max_delay_seconds") == 7.0'
        )
    if "status=429" not in caplog.text:
        pytest.fail('Expected: "status=429" in caplog.text')
    if "purpose=message-list" not in caplog.text:
        pytest.fail('Expected: "purpose=message-list" in caplog.text')


def test_503_uses_graph_backoff_instead_of_immediate_generic_retry(monkeypatch) -> None:
    middleware = _middleware()
    delays = []

    async def fake_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr("message_ingest.providers.microsoft_graph.errors.asyncio.sleep", fake_sleep)
    request = _request(retry_times=1)
    response = _response(request, 503, code="serviceUnavailable", retry_after="5")
    retry = asyncio.run(middleware.process_response(request, response))

    if not isinstance(retry, Request):
        pytest.fail("Expected: isinstance(retry, Request)")
    if retry.meta["retry_times"] != 1:
        pytest.fail('Expected: retry.meta["retry_times"] == 1')
    if retry.meta[middleware.retry_meta_key] != 1:
        pytest.fail("Expected: retry.meta[middleware.retry_meta_key] == 1")
    if retry.headers["Connection"] != b"close":
        pytest.fail('Expected: retry.headers["Connection"] == b"close"')
    if delays != [5.0]:
        pytest.fail("Expected: delays == [5.0]")


def test_509_without_retry_after_uses_exponential_backoff(monkeypatch) -> None:
    middleware = _middleware()
    delays = []

    async def fake_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr("message_ingest.providers.microsoft_graph.errors.asyncio.sleep", fake_sleep)
    request = _request(**{middleware.retry_meta_key: 2})
    response = _response(request, 509, code="BandwidthLimitExceeded")
    retry = asyncio.run(middleware.process_response(request, response))

    if not isinstance(retry, Request):
        pytest.fail("Expected: isinstance(retry, Request)")
    if retry.meta[middleware.retry_meta_key] != 3:
        pytest.fail("Expected: retry.meta[middleware.retry_meta_key] == 3")
    if delays != [8.0]:
        pytest.fail("Expected: delays == [8.0]")


def test_directory_concurrency_violation_409_is_retryable(monkeypatch) -> None:
    middleware = _middleware()
    delays = []

    async def fake_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr("message_ingest.providers.microsoft_graph.errors.asyncio.sleep", fake_sleep)
    request = _request()
    response = _response(
        request,
        409,
        code="Conflict",
        inner_code="Directory_ConcurrencyViolation",
        retry_after="3",
    )
    retry = asyncio.run(middleware.process_response(request, response))

    if not isinstance(retry, Request):
        pytest.fail("Expected: isinstance(retry, Request)")
    if delays != [3.0]:
        pytest.fail("Expected: delays == [3.0]")


def test_other_409_is_left_to_spider_without_retry() -> None:
    middleware = _middleware()
    request = _request()
    response = _response(request, 409, code="Conflict", inner_code="differentConflict")
    if asyncio.run(middleware.process_response(request, response)) is not response:
        pytest.fail(
            "Expected: asyncio.run(middleware.process_response(request, response)) is response"
        )


def test_standard_non_retryable_graph_error_is_left_to_spider() -> None:
    middleware = _middleware()
    request = _request()
    response = _response(request, 400, code="BadRequest")
    if asyncio.run(middleware.process_response(request, response)) is not response:
        pytest.fail(
            "Expected: asyncio.run(middleware.process_response(request, response)) is response"
        )


def test_http_date_retry_after_is_supported(monkeypatch) -> None:
    middleware = _middleware()
    delays = []

    async def fake_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr("message_ingest.providers.microsoft_graph.errors.asyncio.sleep", fake_sleep)
    retry_at = format_datetime(datetime.now(UTC) + timedelta(seconds=2), usegmt=True)
    request = _request()
    response = _response(request, 503, code="serviceUnavailable", retry_after=retry_at)
    retry = asyncio.run(middleware.process_response(request, response))
    if not isinstance(retry, Request):
        pytest.fail("Expected: isinstance(retry, Request)")
    if not 0 <= delays[0] <= 2.5:
        pytest.fail("Expected: 0 <= delays[0] <= 2.5")


def test_retry_limit_prevents_second_generic_retry_loop(caplog) -> None:
    middleware = _middleware()
    caplog.set_level(logging.DEBUG)
    request = _request(retry_times=1, **{middleware.retry_meta_key: 3})
    response = _response(request, 429, code="TooManyRequests")
    returned = asyncio.run(middleware.process_response(request, response))
    if returned is not response:
        pytest.fail("Expected: returned is response")
    if request.meta["dont_retry"] is not True:
        pytest.fail('Expected: request.meta["dont_retry"] is True')
    if request.meta["retry_times"] != 1:
        pytest.fail('Expected: request.meta["retry_times"] == 1')
    if middleware.stats.get_value("msgloom/graph_error_retry/max_reached") != 1:
        pytest.fail(
            'Expected: middleware.stats.get_value("msgloom/graph_error_retry/max_reached") == 1'
        )
    if (
        middleware.stats.get_value(
            "msgloom/graph_error/exhausted_purpose_count/message-list"
        )
        != 1
    ):
        pytest.fail(
            'Expected: middleware.stats.get_value("msgloom/graph_error/exhausted_purpose_count/message-list") == 1'
        )
    if request.url in caplog.text:
        pytest.fail("Expected: request.url not in caplog.text")


def test_explicit_dont_retry_disables_graph_error_retry() -> None:
    middleware = _middleware()
    request = _request(dont_retry=True)
    response = _response(request, 429, code="TooManyRequests")
    returned = asyncio.run(middleware.process_response(request, response))
    if returned is not response:
        pytest.fail("Expected: returned is response")
    if middleware.stats.get_value("msgloom/graph_error_retry/count") is not None:
        pytest.fail(
            'Expected: middleware.stats.get_value("msgloom/graph_error_retry/count") is None'
        )


def test_non_graph_response_is_untouched() -> None:
    middleware = _middleware()
    request = Request("https://example.com/")
    response = TextResponse(request.url, request=request, status=503)
    if asyncio.run(middleware.process_response(request, response)) is not response:
        pytest.fail(
            "Expected: asyncio.run(middleware.process_response(request, response)) is response"
        )


def test_provider_error_code_is_bounded_before_log_and_stat_key(
    monkeypatch,
    caplog,
) -> None:
    middleware = _middleware()
    delays = []

    async def fake_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr("message_ingest.providers.microsoft_graph.errors.asyncio.sleep", fake_sleep)
    caplog.set_level(logging.DEBUG, logger="message_ingest.providers.microsoft_graph.errors")
    request = _request()
    secret_code = "TooManyRequests/secret-provider-value?" + ("x" * 80)
    response = _response(
        request,
        429,
        code=secret_code,
        retry_after="0",
    )

    retry = asyncio.run(middleware.process_response(request, response))

    if not isinstance(retry, Request):
        pytest.fail("Expected: isinstance(retry, Request)")
    if delays != [0.0]:
        pytest.fail("Expected: delays == [0.0]")
    keys = set(middleware.stats.get_stats())
    expected = "msgloom/graph_error_retry/reason_count/microsoft_graph_429_other"
    if expected not in keys:
        pytest.fail("Expected: sanitized Graph retry reason stat")
    if any(secret_code in key for key in keys):
        pytest.fail("Expected: provider error code not present in stat keys")
    if secret_code in caplog.text or "secret-provider-value" in caplog.text:
        pytest.fail("Expected: provider error code not present in logs")


def test_provider_error_code_is_sanitized_in_logs_and_stat_keys(
    monkeypatch,
    caplog,
) -> None:
    middleware = _middleware()
    delays = []

    async def fake_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr("message_ingest.providers.microsoft_graph.errors.asyncio.sleep", fake_sleep)
    caplog.set_level(logging.DEBUG, logger="message_ingest.providers.microsoft_graph.errors")
    request = _request()
    private_code = "TooManyRequests/secret-token?$cursor=private"
    response = _response(
        request,
        429,
        code=private_code,
        retry_after="0",
    )

    retry = asyncio.run(middleware.process_response(request, response))

    if not isinstance(retry, Request):
        pytest.fail("Expected: isinstance(retry, Request)")
    if delays != [0.0]:
        pytest.fail("Expected: delays == [0.0]")
    stats = middleware.stats.get_stats()
    if (
        stats.get("msgloom/graph_error_retry/reason_count/microsoft_graph_429_other")
        != 1
    ):
        pytest.fail("Expected: sanitized Graph retry reason stat ending in _other")
    if any("secret-token" in key or "$cursor" in key for key in stats):
        pytest.fail("Expected: provider error code absent from stat keys")
    if "secret-token" in caplog.text or "$cursor" in caplog.text:
        pytest.fail("Expected: provider error code absent from logs")
    if "code=other" not in caplog.text:
        pytest.fail('Expected: "code=other" in caplog.text')
