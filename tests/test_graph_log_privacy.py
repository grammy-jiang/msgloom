"""Exercise framework log formatting and filtering without application state."""

import logging

import pytest
from scrapy import Spider
from scrapy.downloadermiddlewares.httpcache import HttpCacheMiddleware
from scrapy.http import Request, Response
from scrapy.logformatter import LogFormatter
from scrapy.utils.misc import build_from_crawler
from scrapy.utils.test import get_crawler
from twisted.python.failure import Failure

from microsoft_graph.extensions._logfilters import MicrosoftGraphScrapyPrivacyFilter
from microsoft_graph.extensions.privacy import MicrosoftGraphLogPrivacyExtension
from microsoft_graph.logformatter import MicrosoftGraphLogFormatter
from microsoft_graph.request import GRAPH_OPERATION_META_KEY
from microsoft_graph.spiders import MicrosoftGraphSpider

URL = "https://graph.microsoft.com/v1.0/me/messages?$deltatoken=private-cursor"


@pytest.fixture
def crawler():
    crawler = get_crawler(MicrosoftGraphSpider, {"HTTPCACHE_ENABLED": True})
    crawler.spider = MicrosoftGraphSpider.from_crawler(crawler, name="private_graph")
    return crawler


def formatter_calls(spider):
    request = Request(
        URL,
        meta={GRAPH_OPERATION_META_KEY: "contacts"},
        cb_kwargs={"purpose": "private-legacy-purpose"},
    )
    response = Response(URL, request=request)
    exception = RuntimeError("private-exception")
    failure = Failure(exception)
    return {
        "crawled": (request, response, spider),
        "download_error": (failure, request, spider, "private-error-message"),
        "spider_error": (failure, request, response, spider),
        "scraped": ({"payload": "private-item"}, response, spider),
        "dropped": ({"payload": "private-item"}, exception, response, spider),
        "item_error": ({"payload": "private-item"}, exception, response, spider),
    }


def test_formatter_omits_urls_payloads_and_arbitrary_exception_text(crawler):
    formatter = MicrosoftGraphLogFormatter()
    for name, args in formatter_calls(crawler.spider).items():
        result = getattr(formatter, name)(*args)
        rendered = result["msg"] % result["args"]
        if "private-" in rendered or "graph.microsoft.com" in rendered:
            pytest.fail(f"Framework {name} exposed private provider data")
        if name in {"crawled", "download_error", "spider_error"} and (
            "contacts" not in rendered or "GET" not in rendered
        ):
            pytest.fail("Request logs must use neutral Graph operation metadata")


def test_formatter_preserves_native_non_graph_behavior():
    crawler = get_crawler(Spider)
    spider = Spider.from_crawler(crawler, name="public")
    for name, args in formatter_calls(spider).items():
        actual = getattr(MicrosoftGraphLogFormatter(), name)(*args)
        expected = getattr(LogFormatter(), name)(*args)
        if actual != expected:
            pytest.fail(f"Graph formatter changed non-Graph {name} behavior")


@pytest.mark.parametrize("logger", ["scrapy.core.engine", "scrapy.core.scraper"])
def test_filter_sanitizes_request_arguments_extras_and_cached_tracebacks(
    crawler, logger
):
    request = Request(URL, meta={GRAPH_OPERATION_META_KEY: "contacts"})
    record = logging.LogRecord(
        logger,
        logging.ERROR,
        __file__,
        0,
        "Scraper bug processing %(request)s",
        ({"request": request},),
        (RuntimeError, RuntimeError("private-exception"), None),
    )
    record.request = request
    record.item = {"raw": "private-item"}
    record.exc_text = "private-cached-traceback"
    before = crawler.stats.get_stats().copy()
    MicrosoftGraphScrapyPrivacyFilter(crawler).filter(record)
    if "private-" in record.getMessage() or "contacts" not in record.getMessage():
        pytest.fail("Core request summary leaked or lost operation metadata")
    if record.exc_info is not None or record.exc_text is not None:
        pytest.fail("Traceback text must not survive filtering")
    if isinstance(record.__dict__["request"], Request):
        pytest.fail("Structured request extra still contains the provider URL")
    if logger == "scrapy.core.scraper" and record.__dict__["item"] != "dict":
        pytest.fail("Structured item extra must expose only the item type")
    if crawler.stats.get_stats() != before:
        pytest.fail("Framework privacy filtering must have no integrity side effects")


def test_filter_does_not_modify_records_for_another_spider(crawler):
    record = logging.LogRecord(
        "scrapy.core.engine",
        logging.ERROR,
        __file__,
        0,
        "Error while reading start items and requests: public error",
        (),
        (RuntimeError, RuntimeError("public error"), None),
    )
    record.spider = Spider(name="public")
    before = record.__dict__.copy()
    MicrosoftGraphScrapyPrivacyFilter(crawler).filter(record)
    if record.__dict__ != before:
        pytest.fail("A Graph crawler must not redact another spider's record")


def test_framework_extension_filters_native_cache_errors_and_removes_filter(
    crawler, caplog
):
    extension = build_from_crawler(MicrosoftGraphLogPrivacyExtension, crawler)
    cache = build_from_crawler(HttpCacheMiddleware, crawler)

    class UnreadableCache:
        def retrieve_response(self, spider, request):
            raise OSError("private-cache-exception")

    cache.storage = UnreadableCache()
    extension.spider_opened(crawler.spider)
    extension.spider_opened(crawler.spider)
    target = logging.getLogger("scrapy.downloadermiddlewares.httpcache")
    caplog.set_level(logging.WARNING, logger=target.name)
    try:
        if cache.process_request(Request(URL)) is not None:
            pytest.fail("Unreadable cache entry must remain a cache miss")
        if target.filters.count(extension._filter) != 1:
            pytest.fail("Privacy filter must be installed exactly once")
    finally:
        extension.engine_stopped()
    if "private-" in caplog.text or "OSError" not in caplog.text:
        pytest.fail("Native cache failure exposed private provider data")
    if extension._filter in target.filters:
        pytest.fail("Crawler-scoped privacy filter outlived its engine")


def test_framework_extension_leaves_non_graph_spiders_alone():
    crawler = get_crawler(Spider)
    crawler.spider = Spider.from_crawler(crawler, name="public")
    extension = build_from_crawler(MicrosoftGraphLogPrivacyExtension, crawler)
    extension.spider_opened(crawler.spider)
    try:
        if extension._installed:
            pytest.fail("Framework privacy extension must be scoped to Graph spiders")
    finally:
        extension.engine_stopped()
