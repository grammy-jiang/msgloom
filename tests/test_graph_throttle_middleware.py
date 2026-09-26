from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

from scrapy.http import Request, Response
from scrapy.utils.misc import build_from_crawler
from scrapy.utils.test import get_crawler

from msgloom.middlewares import MicrosoftGraphThrottleMiddleware
from msgloom.spiders.outlook_mail import OutlookMailSpider


def _middleware():
    crawler = get_crawler(
        OutlookMailSpider,
        settings_dict={
            "MS_GRAPH_THROTTLE_ENABLED": True,
            "MS_GRAPH_THROTTLE_MAX_RETRIES": 3,
            "MS_GRAPH_THROTTLE_FALLBACK_BASE_SECONDS": 2,
            "MS_GRAPH_THROTTLE_FALLBACK_MAX_SECONDS": 20,
        },
    )
    crawler.spider = OutlookMailSpider.from_crawler(crawler)
    return build_from_crawler(MicrosoftGraphThrottleMiddleware, crawler)


def test_429_honors_retry_after_and_uses_scrapy_retry_request(monkeypatch) -> None:
    middleware = _middleware()
    delays = []

    async def fake_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr("msgloom.middlewares.asyncio.sleep", fake_sleep)
    request = Request("https://graph.microsoft.com/v1.0/me/messages")
    response = Response(request.url, status=429, headers={"Retry-After": "7"}, request=request)
    retry = asyncio.run(middleware.process_response(request, response))

    assert isinstance(retry, Request)
    assert retry.dont_filter is True
    assert retry.meta["retry_times"] == 1
    assert delays == [7.0]
    assert middleware.stats.get_value("msgloom/throttle/count") == 1
    assert middleware.stats.get_value(
        "msgloom/throttle/reason_count/microsoft_graph_429"
    ) == 1
    assert middleware.stats.get_value("msgloom/throttle/wait_seconds_total") == 7


def test_429_without_retry_after_uses_bounded_exponential_backoff(monkeypatch) -> None:
    middleware = _middleware()
    delays = []

    async def fake_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr("msgloom.middlewares.asyncio.sleep", fake_sleep)
    request = Request(
        "https://graph.microsoft.com/v1.0/me/messages",
        meta={"retry_times": 2},
    )
    response = Response(request.url, status=429, request=request)
    retry = asyncio.run(middleware.process_response(request, response))
    assert isinstance(retry, Request)
    assert retry.meta["retry_times"] == 3
    assert delays == [8.0]
    assert middleware.stats.get_value("msgloom/throttle/missing_retry_after_count") == 1


def test_http_date_retry_after_is_supported(monkeypatch) -> None:
    middleware = _middleware()
    delays = []

    async def fake_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr("msgloom.middlewares.asyncio.sleep", fake_sleep)
    retry_at = format_datetime(datetime.now(UTC) + timedelta(seconds=2), usegmt=True)
    request = Request("https://graph.microsoft.com/v1.0/me/messages")
    response = Response(request.url, status=429, headers={"Retry-After": retry_at}, request=request)
    retry = asyncio.run(middleware.process_response(request, response))
    assert isinstance(retry, Request)
    assert 0 <= delays[0] <= 2.5


def test_throttle_max_retries_prevents_second_generic_retry_loop() -> None:
    middleware = _middleware()
    request = Request(
        "https://graph.microsoft.com/v1.0/me/messages",
        meta={"retry_times": 3},
    )
    response = Response(request.url, status=429, request=request)
    returned = asyncio.run(middleware.process_response(request, response))
    assert returned is response
    assert request.meta["dont_retry"] is True
    assert middleware.stats.get_value("msgloom/throttle/max_reached") == 1


def test_non_graph_or_non_429_response_is_untouched() -> None:
    middleware = _middleware()
    request = Request("https://example.com/")
    response = Response(request.url, status=429, request=request)
    assert asyncio.run(middleware.process_response(request, response)) is response
