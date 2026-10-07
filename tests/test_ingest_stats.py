"""
Preserve observable acquisition counters while callbacks stream requests and
items.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from scrapy.http import Request, TextResponse
from scrapy.utils.test import get_crawler

from message_ingest.spiders.microsoft.outlook.email._base import OutlookMailSpider
from message_ingest.spiders.microsoft.outlook.email.discover import (
    OutlookDiscoverSpider,
)
from message_ingest.spiders.microsoft.outlook.email.full import OutlookFullSpider

FIXTURES = Path(__file__).parent / "fixtures" / "microsoft_graph"


def _spider(
    spider_cls: type[OutlookMailSpider] = OutlookDiscoverSpider,
    **kwargs,
) -> OutlookMailSpider:
    crawler = get_crawler(spider_cls)
    return spider_cls.from_crawler(crawler, **kwargs)


async def _collect_start(spider: OutlookMailSpider) -> list[object]:
    return [value async for value in spider.start()]


def _response(filename: str, request: Request | None = None) -> TextResponse:
    if request is None:
        request = Request("https://graph.microsoft.com/v1.0/me/messages")
    return TextResponse(
        url=request.url,
        request=request,
        status=200,
        headers={"Content-Type": "application/json"},
        body=(FIXTURES / filename).read_bytes(),
        encoding="utf-8",
    )


def test_discovery_stats_cover_mode_pages_messages_and_continuation() -> None:
    spider = _spider()
    asyncio.run(_collect_start(spider))
    page1 = _response("list_messages_page_1.json")
    output1 = list(spider.parse(page1, purpose="message-list", page_number=1))
    next_request = output1[-1]
    if not isinstance(next_request, Request):
        pytest.fail("Expected: isinstance(next_request, Request)")
    page2 = _response("list_messages_page_2.json", next_request)
    list(spider.parse(page2, **next_request.cb_kwargs))

    stats = spider.crawler.stats
    if stats.get_value("msgloom/crawl/mode") != "discovery":
        pytest.fail('Expected: stats.get_value("msgloom/crawl/mode") == "discovery"')
    if stats.get_value("msgloom/crawl/discovery/scope") != "mailbox":
        pytest.fail(
            'Expected: stats.get_value("msgloom/crawl/discovery/scope") == "mailbox"'
        )
    if stats.get_value("msgloom/crawl/discovery/page_count") != 2:
        pytest.fail(
            'Expected: stats.get_value("msgloom/crawl/discovery/page_count") == 2'
        )
    if stats.get_value("msgloom/crawl/discovery/message_count") != 2:
        pytest.fail(
            'Expected: stats.get_value("msgloom/crawl/discovery/message_count") == 2'
        )
    if stats.get_value("msgloom/crawl/discovery/continuation_count") != 1:
        pytest.fail(
            'Expected: stats.get_value("msgloom/crawl/discovery/continuation_count") == 1'
        )


def test_full_mode_records_target_message_count() -> None:
    spider = _spider(OutlookFullSpider, message_ids="one,two")
    if not isinstance(spider, OutlookFullSpider):
        pytest.fail("Expected the requested Full spider")
    output = asyncio.run(_collect_start(spider))
    requests = [item for item in output if isinstance(item, Request)]
    if len(requests) != len(output):
        pytest.fail("Initial Full output must contain only selection requests")
    if len(output) != 2:
        pytest.fail("Expected one detail selection request per target")
    if {request.cb_kwargs["message_id"] for request in requests} != {"one", "two"}:
        pytest.fail("Initial requests lost the selected target identities")
    for request in requests:
        if request.cb_kwargs["purpose"] != "message-detail":
            pytest.fail("Component request preceded exact primary selection")
        response = TextResponse(
            request.url,
            request=request,
            encoding="utf-8",
            body=json.dumps({"id": request.cb_kwargs["message_id"]}).encode(),
        )
        children = [
            item
            for item in spider.parse_message_detail(response, **request.cb_kwargs)
            if isinstance(item, Request)
        ]
        if {child.cb_kwargs["purpose"] for child in children} != {
            "message-mime",
            "attachments-list",
        }:
            pytest.fail("Selected detail did not schedule both Full components")
        for child in children:
            if child.cb_kwargs["selection_id"] != request.cb_kwargs["selection_id"]:
                pytest.fail("Full component lost its exact primary selection")
    if spider.crawler.stats.get_value("msgloom/crawl/mode") != "full":
        pytest.fail(
            'Expected: spider.crawler.stats.get_value("msgloom/crawl/mode") == "full"'
        )
    if (
        spider.crawler.stats.get_value("msgloom/crawl/enrichment/target_message_count")
        != 2
    ):
        pytest.fail(
            'Expected: spider.crawler.stats.get_value( "msgloom/crawl/enrichment/target_message_count" ) == 2'
        )
