"""Verify OneDrive-specific log coverage and filter cleanup."""

import logging

import pytest
from scrapy import Request
from scrapy.utils.test import get_crawler

from message_ingest.extensions.microsoft.onedrive.privacy import (
    OneDriveContentPrivacyExtension,
)
from message_ingest.spiders.microsoft.onedrive.content import (
    MicrosoftOneDriveContentSpider,
)
from message_ingest.spiders.microsoft.todo.discover import MicrosoftTodoDiscoverSpider


@pytest.mark.parametrize(
    "logger_name,message,args",
    [
        (
            "scrapy.downloadermiddlewares.redirect",
            "Redirecting to %(redirected)s from %(request)s",
            {
                "redirected": Request("https://download.test/SECRET?token=SECRET"),
                "request": Request(
                    "https://graph.microsoft.com/v1.0/me/drive/items/id/content"
                ),
            },
        ),
        (
            "scrapy.core.downloader.handlers.http11",
            "Cancelling https://download.test/SECRET",
            (),
        ),
    ],
)
def test_content_log_filter_redacts_native_redirect_and_size_messages(
    logger_name, message, args
):
    crawler = get_crawler(MicrosoftOneDriveContentSpider)
    instance = MicrosoftOneDriveContentSpider.from_crawler(crawler, item_ids='["id"]')
    crawler.spider = instance
    extension = OneDriveContentPrivacyExtension.from_crawler(crawler)
    target = logging.getLogger(logger_name)
    extension.spider_opened(instance)
    try:
        record = logging.LogRecord(
            logger_name, logging.WARNING, "", 0, message, args, None
        )
        target.filter(record)
        if "SECRET" in record.getMessage():
            pytest.fail("Native content transport logging leaked a private URL")
    finally:
        extension.engine_stopped()
    if extension._filter in target.filters:
        pytest.fail("Content privacy filter leaked beyond crawler lifetime")


def test_content_log_coverage_does_not_install_on_other_products():
    crawler = get_crawler(MicrosoftTodoDiscoverSpider)
    instance = MicrosoftTodoDiscoverSpider.from_crawler(crawler)
    crawler.spider = instance
    extension = OneDriveContentPrivacyExtension.from_crawler(crawler)
    extension.spider_opened(instance)
    if extension._installed:
        pytest.fail("OneDrive-specific log policy must not affect To Do")
