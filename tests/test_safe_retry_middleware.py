"""Keep Scrapy generic retries native while preventing URL leakage."""

from __future__ import annotations

import logging

import pytest
from scrapy.http import Request, Response
from scrapy.utils.misc import build_from_crawler
from scrapy.utils.test import get_crawler

from message_ingest.providers.microsoft_graph.errors import PrivacySafeRetryMiddleware
from message_ingest.spiders.microsoft.outlook.email.discover import (
    OutlookDiscoverSpider,
)

SECRET_URL = (
    "https://graph.microsoft.com/v1.0/me/messages/delta?$deltatoken=secret-cursor"
)


def _middleware(
    retry_times: int,
    *,
    give_up_log_level: str = "ERROR",
) -> PrivacySafeRetryMiddleware:
    crawler = get_crawler(
        OutlookDiscoverSpider,
        settings_dict={
            "RETRY_ENABLED": True,
            "RETRY_TIMES": retry_times,
            "RETRY_GIVE_UP_LOG_LEVEL": give_up_log_level,
        },
    )
    crawler.spider = OutlookDiscoverSpider.from_crawler(crawler)
    return build_from_crawler(PrivacySafeRetryMiddleware, crawler)


def _request() -> Request:
    return Request(
        SECRET_URL,
        callback=lambda response, **kwargs: None,
        cb_kwargs={"purpose": "message-delta"},
    )


def test_generic_retry_schedule_keeps_native_stats_without_url_log(caplog) -> None:
    middleware = _middleware(1)
    request = _request()
    response = Response(request.url, request=request, status=500)
    caplog.set_level(
        logging.DEBUG, logger="message_ingest.providers.microsoft_graph.errors"
    )

    retry = middleware.process_response(request, response)

    if not isinstance(retry, Request):
        pytest.fail("Expected: isinstance(retry, Request)")
    if middleware.crawler.stats.get_value("retry/count") != 1:
        pytest.fail('Expected: middleware.crawler.stats.get_value("retry/count") == 1')
    if "purpose=message-delta" not in caplog.text:
        pytest.fail('Expected: "purpose=message-delta" in caplog.text')
    if "reason=http_500" not in caplog.text:
        pytest.fail('Expected: "reason=http_500" in caplog.text')
    if "secret-cursor" in caplog.text or SECRET_URL in caplog.text:
        pytest.fail("Expected: secret Graph URL not in caplog.text")


def test_generic_retry_exhaustion_logs_safe_reason_only(caplog) -> None:
    middleware = _middleware(0)
    request = _request()
    response = Response(request.url, request=request, status=500)
    caplog.set_level(
        logging.DEBUG, logger="message_ingest.providers.microsoft_graph.errors"
    )

    returned = middleware.process_response(request, response)

    if returned is not response:
        pytest.fail("Expected: returned is response")
    if middleware.crawler.stats.get_value("retry/max_reached") != 1:
        pytest.fail(
            'Expected: middleware.crawler.stats.get_value("retry/max_reached") == 1'
        )
    if "Scrapy retry limit reached" not in caplog.text:
        pytest.fail('Expected: "Scrapy retry limit reached" in caplog.text')
    if "reason=http_500" not in caplog.text:
        pytest.fail('Expected: "reason=http_500" in caplog.text')
    if "secret-cursor" in caplog.text or SECRET_URL in caplog.text:
        pytest.fail("Expected: secret Graph URL not in caplog.text")


def test_generic_retry_exception_text_is_not_logged(caplog) -> None:
    middleware = _middleware(0)
    request = _request()
    caplog.set_level(
        logging.DEBUG, logger="message_ingest.providers.microsoft_graph.errors"
    )

    retry = middleware._retry(
        request,
        RuntimeError("private failure text with secret-cursor"),
    )

    if retry is not None:
        pytest.fail("Expected: retry is None")
    if "reason=RuntimeError" not in caplog.text:
        pytest.fail('Expected: "reason=RuntimeError" in caplog.text')
    if "private failure text" in caplog.text or "secret-cursor" in caplog.text:
        pytest.fail("Expected: arbitrary exception text not in caplog.text")


def test_generic_retry_honors_configured_give_up_log_level(caplog) -> None:
    middleware = _middleware(0, give_up_log_level="WARNING")
    request = _request()
    response = Response(request.url, request=request, status=500)
    caplog.set_level(
        logging.DEBUG, logger="message_ingest.providers.microsoft_graph.errors"
    )

    middleware.process_response(request, response)

    records = [
        record
        for record in caplog.records
        if record.name == "message_ingest.providers.microsoft_graph.errors"
        and "Scrapy retry limit reached" in record.getMessage()
    ]
    if len(records) != 1:
        pytest.fail("Expected: len(records) == 1")
    if records[0].levelno != logging.WARNING:
        pytest.fail("Expected: records[0].levelno == logging.WARNING")


def test_generic_retry_honors_request_give_up_log_level_override(caplog) -> None:
    middleware = _middleware(0, give_up_log_level="ERROR")
    request = _request()
    request.meta["give_up_log_level"] = "INFO"
    response = Response(request.url, request=request, status=500)
    caplog.set_level(
        logging.DEBUG, logger="message_ingest.providers.microsoft_graph.errors"
    )

    middleware.process_response(request, response)

    records = [
        record
        for record in caplog.records
        if record.name == "message_ingest.providers.microsoft_graph.errors"
        and "Scrapy retry limit reached" in record.getMessage()
    ]
    if len(records) != 1:
        pytest.fail("Expected: len(records) == 1")
    if records[0].levelno != logging.INFO:
        pytest.fail("Expected: records[0].levelno == logging.INFO")


def test_generic_retry_none_give_up_override_falls_back_to_setting(
    caplog,
) -> None:
    middleware = _middleware(0, give_up_log_level="WARNING")
    request = _request()
    request.meta["give_up_log_level"] = None
    response = Response(request.url, request=request, status=500)
    caplog.set_level(
        logging.DEBUG, logger="message_ingest.providers.microsoft_graph.errors"
    )

    returned = middleware.process_response(request, response)

    if returned is not response:
        pytest.fail("Expected: returned is response")
    records = [
        record
        for record in caplog.records
        if record.name == "message_ingest.providers.microsoft_graph.errors"
        and "Scrapy retry limit reached" in record.getMessage()
    ]
    if len(records) != 1:
        pytest.fail("Expected: len(records) == 1")
    if records[0].levelno != logging.WARNING:
        pytest.fail("Expected: records[0].levelno == logging.WARNING")
