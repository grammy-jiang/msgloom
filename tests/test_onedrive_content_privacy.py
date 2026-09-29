"""Verify framework content log coverage, isolation, and filter cleanup."""

import logging

import pytest
from scrapy import signals
from scrapy.utils.test import get_crawler

from microsoft_graph.extensions.onedrive import OneDriveContentPrivacyExtension
from microsoft_graph.spiders.onedrive import MicrosoftOneDriveSpider
from microsoft_graph.spiders.outlook import OutlookCalendarSpider, OutlookMailSpider
from microsoft_graph.spiders.todo import MicrosoftTodoSpider

SECRET_URL = "https://download.test/SECRET?token=SECRET"
LOGGERS = (
    "scrapy.downloadermiddlewares.redirect",
    "scrapy.dupefilters",
    "scrapy.core.downloader.handlers.http11",
    "scrapy.downloadermiddlewares.httpcompression",
)


@pytest.fixture
def content_privacy():
    crawler = get_crawler(MicrosoftOneDriveSpider)
    spider = MicrosoftOneDriveSpider.from_crawler(crawler, name="content")
    crawler.spider = spider
    extension = OneDriveContentPrivacyExtension.from_crawler(crawler)
    crawler.signals.send_catch_log(signals.spider_opened, spider=spider)
    try:
        yield crawler, spider, extension
    finally:
        crawler.signals.send_catch_log(signals.engine_stopped)
        if any(
            extension._filter in logging.getLogger(name).filters for name in LOGGERS
        ):
            pytest.fail("Content privacy filter leaked beyond crawler lifetime")
        if extension._filter.requests:
            pytest.fail("Content privacy retained requests after engine shutdown")


@pytest.mark.parametrize("logger_name", LOGGERS)
@pytest.mark.parametrize("request_extra", [False, True])
def test_framework_content_filter_redacts_native_records(
    content_privacy, logger_name, request_extra
):
    crawler, spider, _ = content_privacy
    request = spider.content_request("id")
    redirected = request.replace(url=SECRET_URL)
    crawler.signals.send_catch_log(
        signals.request_reached_downloader, request=redirected, spider=spider
    )
    # Native downloader completion precedes compression response middleware.
    crawler.signals.send_catch_log(
        signals.request_left_downloader, request=redirected, spider=spider
    )
    if logger_name.endswith("redirect"):
        message = "Redirecting to %(redirected)s from %(request)s"
        args = {"redirected": redirected, "request": request}
    elif logger_name.endswith("dupefilters"):
        message, args = (
            "Filtered duplicate request: %(request)s",
            {"request": redirected},
        )
    else:
        message, args = f"Cancelling response <200 {SECRET_URL}>", ()
    record = logging.LogRecord(
        logger_name,
        logging.WARNING,
        "",
        0,
        message,
        (args,) if args else (),
        (ValueError, ValueError(SECRET_URL), None),
    )
    if request_extra:
        record.request = redirected
    logging.getLogger(logger_name).filter(record)
    if "SECRET" in record.getMessage() or "SECRET" in str(
        getattr(record, "request", "")
    ):
        pytest.fail("Native content transport logging leaked a private URL")
    if record.exc_info or record.exc_text:
        pytest.fail("Native content transport logging retained private exception text")


@pytest.mark.parametrize("logger_name", LOGGERS)
@pytest.mark.parametrize("other_spider", [False, True])
def test_content_privacy_leaves_unrelated_records_unchanged(
    content_privacy, logger_name, other_spider
):
    crawler, spider, _ = content_privacy
    marked = spider.content_request("id").replace(url=SECRET_URL)
    crawler.signals.send_catch_log(
        signals.request_reached_downloader, request=marked, spider=spider
    )
    request = spider.graph_request("/me/drive")
    message = f"Unrelated diagnostic {request.url}: %(request)s"
    args = {"request": request}
    record = logging.LogRecord(
        logger_name, logging.WARNING, "", 0, message, (args,), None
    )
    if other_spider:
        record.spider = MicrosoftTodoSpider(name="other")
        record.args = {"request": marked}
    original = dict(record.__dict__)
    logging.getLogger(logger_name).filter(record)
    if record.__dict__ != original:
        pytest.fail("OneDrive content privacy changed an unrelated native record")


@pytest.mark.parametrize(
    "spider_class", [MicrosoftTodoSpider, OutlookMailSpider, OutlookCalendarSpider]
)
def test_content_log_coverage_does_not_install_on_other_products(spider_class):
    crawler = get_crawler(spider_class)
    spider = spider_class.from_crawler(crawler, name="other")
    crawler.spider = spider
    extension = OneDriveContentPrivacyExtension.from_crawler(crawler)
    extension.spider_opened(spider)
    if extension._installed:
        pytest.fail("OneDrive-specific log policy must not affect other products")
