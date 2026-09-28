"""Verify neutral transport policy with native Scrapy requests and stats."""

import asyncio
import json

import pytest
from scrapy import Spider
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.http import Request, TextResponse
from scrapy.utils.test import get_crawler

from microsoft_graph.scrapy.middlewares.diagnostics import (
    MicrosoftGraphDiagnosticsMiddleware,
)
from microsoft_graph.scrapy.middlewares.errors import MicrosoftGraphErrorMiddleware
from microsoft_graph.scrapy.request import GRAPH_OPERATION_META_KEY


def middleware(settings=None):
    crawler = get_crawler(
        settings_dict={
            "MS_GRAPH_ERROR_MIDDLEWARE_ENABLED": True,
            "MS_GRAPH_ERROR_MAX_RETRIES": 1,
            **(settings or {}),
        }
    )
    crawler.spider = Spider.from_crawler(crawler, name="transport")
    return MicrosoftGraphErrorMiddleware.from_crawler(crawler)


def response(request, status=429):
    return TextResponse(
        request.url,
        request=request,
        status=status,
        encoding="utf-8",
        headers={"Retry-After": "0"},
        body=json.dumps(
            {"error": {"innererror": {"code": "Directory_ConcurrencyViolation"}}}
        ).encode(),
    )


def test_retry_default_policy_and_configurable_509():
    request = Request("https://graph.microsoft.com/v1.0/me")
    original = response(request, 509)
    if asyncio.run(middleware().process_response(request, original)) is not original:
        pytest.fail("509 must be an explicit consumer policy")
    configured = middleware({"MS_GRAPH_ERROR_RETRY_HTTP_CODES": [509]})
    if not isinstance(
        asyncio.run(configured.process_response(request, original)), Request
    ):
        pytest.fail("Consumer must be able to add 509")


def test_neutral_operation_stats_and_retry_exhaustion():
    component = middleware({"MS_GRAPH_STATS_PREFIX": "consumer"})
    request = Request(
        "https://graph.microsoft.com/v1.0/me",
        meta={
            GRAPH_OPERATION_META_KEY: "object",
            "retry_times": 2,
        },
        cb_kwargs={"purpose": "legacy"},
    )
    retry = asyncio.run(component.process_response(request, response(request)))
    if not isinstance(retry, Request) or retry.meta["retry_times"] != 2:
        pytest.fail("Native generic retry count must survive Graph retries")
    stats = component.stats.get_stats()
    if stats.get("consumer/graph_error/retry_purpose_count/object") != 1:
        pytest.fail("Operation metadata must override legacy purpose")
    failed = response(retry)
    returned = asyncio.run(component.process_response(retry, failed))
    generic = RetryMiddleware.from_crawler(component.crawler)
    if returned is not failed or generic.process_response(retry, failed) is not failed:
        pytest.fail("Exhausted Graph retry must not start another generic budget")


def test_diagnostics_supports_custom_host_and_neutral_metadata():
    component = middleware({"MS_GRAPH_SERVICE_ROOT": "https://graph.example/v1.0"})
    diagnostics = MicrosoftGraphDiagnosticsMiddleware.from_crawler(component.crawler)
    request = Request(
        "https://graph.example/v1.0/me",
        meta={
            GRAPH_OPERATION_META_KEY: "read",
        },
    )
    diagnostics.process_request(request)
    first = request.headers.get("client-request-id")
    diagnostics.process_request(request)
    diagnostics.process_response(request, response(request, 200))
    diagnostics.process_exception(request, TimeoutError())
    if not first or first == request.headers.get("client-request-id"):
        pytest.fail("Every transport attempt needs a new correlation ID")
    stats = component.stats.get_stats()
    if stats.get("microsoft_graph/graph/request_purpose_count/read") != 2:
        pytest.fail("Framework diagnostics must use neutral stats")
    if stats.get("microsoft_graph/graph/exception_type_count/TimeoutError") != 1:
        pytest.fail("Transport failures must be counted")
