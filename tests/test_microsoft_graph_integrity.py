"""Verify Graph-wide integrity tracking outside Outlook-specific lifecycle code."""

from __future__ import annotations

import pytest
from scrapy import Spider, signals
from scrapy.utils.misc import build_from_crawler
from scrapy.utils.test import get_crawler
from twisted.python.failure import Failure

from message_ingest.providers.microsoft_graph.integrity import (
    MicrosoftGraphIntegrityExtension,
)
from message_ingest.providers.microsoft_graph.spider import MicrosoftGraphSpider


class FixtureGraphSpider(MicrosoftGraphSpider):
    """Minimal Graph resource used to exercise provider lifecycle signals."""

    name = "graph_integrity_fixture"

    async def start(self):
        """Yield nothing while keeping Scrapy's async start contract."""
        if False:
            yield None


class NonGraphSpider(Spider):
    """Control fixture that must remain outside Graph integrity tracking."""

    name = "non_graph_integrity_fixture"


def _graph():
    crawler = get_crawler(FixtureGraphSpider)
    spider = FixtureGraphSpider.from_crawler(crawler)
    crawler.spider = spider
    extension = build_from_crawler(MicrosoftGraphIntegrityExtension, crawler)
    return crawler, spider, extension


@pytest.mark.parametrize(
    ("signal_name", "reason"),
    [
        ("spider_error", "spider_error"),
        ("item_error", "item_error"),
        ("item_dropped", "item_dropped"),
    ],
)
def test_graph_failure_signals_mark_logical_run_failed(
    signal_name: str,
    reason: str,
) -> None:
    crawler, spider, _extension = _graph()

    crawler.signals.send_catch_log(
        signal=getattr(signals, signal_name),
        spider=spider,
        failure=Failure(RuntimeError("private failure")),
        response=None,
        item=object(),
        exception=RuntimeError("private drop"),
    )

    if spider.run_failed is not True:
        pytest.fail("Expected: spider.run_failed is True")
    if reason not in spider.failure_reasons:
        pytest.fail("Expected provider failure reason in spider.failure_reasons")
    key = f"msgloom/crawl/integrity_failure_reason_count/{reason}"
    if crawler.stats.get_value(key) != 1:
        pytest.fail("Expected exactly one integrity failure counter increment")


def test_integrity_reason_is_idempotent_across_duplicate_observers() -> None:
    crawler, spider, extension = _graph()

    extension.item_error(spider=spider)
    extension.item_error(spider=spider)

    if spider.failure_reasons != frozenset({"item_error"}):
        pytest.fail('Expected: spider.failure_reasons == frozenset({"item_error"})')
    if (
        crawler.stats.get_value(
            "msgloom/crawl/integrity_failure_reason_count/item_error"
        )
        != 1
    ):
        pytest.fail("Expected duplicate integrity observations to remain idempotent")


def test_non_graph_spider_is_ignored() -> None:
    crawler = get_crawler(NonGraphSpider)
    spider = NonGraphSpider.from_crawler(crawler)
    crawler.spider = spider
    extension = build_from_crawler(MicrosoftGraphIntegrityExtension, crawler)

    extension.spider_error(spider=spider)

    if crawler.stats.get_value(
        "msgloom/crawl/integrity_failure_reason_count/spider_error"
    ) is not None:
        pytest.fail("Expected non-Graph spider to be ignored")
