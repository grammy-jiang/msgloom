"""Verify privacy at the native Scrapy HTTP-cache logging boundary."""

from __future__ import annotations

import logging

import pytest
from scrapy.downloadermiddlewares.httpcache import HttpCacheMiddleware
from scrapy.http import Request
from scrapy.utils.misc import build_from_crawler
from scrapy.utils.test import get_crawler

from message_ingest.extensions.microsoft_graph.privacy import (
    MicrosoftGraphLogPrivacyExtension,
)
from message_ingest.spiders.microsoft.outlook.email.discover import (
    OutlookDiscoverSpider,
)


def test_native_http_cache_read_failure_redacts_graph_request_and_exception(
    caplog,
) -> None:
    crawler = get_crawler(
        OutlookDiscoverSpider,
        settings_dict={"HTTPCACHE_ENABLED": True},
    )
    spider = OutlookDiscoverSpider.from_crawler(crawler)
    crawler.spider = spider
    privacy = build_from_crawler(MicrosoftGraphLogPrivacyExtension, crawler)
    privacy.spider_opened(spider)
    cache = build_from_crawler(HttpCacheMiddleware, crawler)

    class UnreadableCache:
        @staticmethod
        def retrieve_response(_spider, _request):
            raise OSError("private-cache-exception")

    cache.storage = UnreadableCache()
    request = Request(
        "https://graph.microsoft.com/v1.0/me/messages?$skiptoken=private-cache-cursor"
    )
    caplog.set_level(
        logging.WARNING,
        logger="scrapy.downloadermiddlewares.httpcache",
    )
    try:
        returned = cache.process_request(request)
    finally:
        privacy.engine_stopped()

    if returned is not None:
        pytest.fail("Expected cache read failure to continue as a cache miss")
    if "OSError" not in caplog.text:
        pytest.fail("Expected bounded cache error type in log")
    if "private-cache-cursor" in caplog.text:
        pytest.fail("Expected Graph continuation cursor not to enter cache log")
    if "private-cache-exception" in caplog.text:
        pytest.fail("Expected cache exception text not to enter cache log")
