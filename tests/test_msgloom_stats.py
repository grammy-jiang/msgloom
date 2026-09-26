from __future__ import annotations

import asyncio
from pathlib import Path

from scrapy.http import Request, TextResponse
from scrapy.utils.test import get_crawler

from msgloom.spiders.outlook_mail import OutlookMailSpider


FIXTURES = Path(__file__).parent / "fixtures" / "microsoft_graph"


def _spider(**kwargs) -> OutlookMailSpider:
    crawler = get_crawler(OutlookMailSpider)
    return OutlookMailSpider.from_crawler(crawler, **kwargs)


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
    assert isinstance(next_request, Request)
    page2 = _response("list_messages_page_2.json", next_request)
    list(spider.parse(page2, **next_request.cb_kwargs))

    stats = spider.crawler.stats
    assert stats.get_value("msgloom/crawl/mode") == "discovery"
    assert stats.get_value("msgloom/crawl/discovery/scope") == "mailbox"
    assert stats.get_value("msgloom/crawl/discovery/page_count") == 2
    assert stats.get_value("msgloom/crawl/discovery/message_count") == 2
    assert stats.get_value("msgloom/crawl/discovery/continuation_count") == 1


def test_full_mode_records_target_message_count() -> None:
    spider = _spider(message_ids="one,two")
    output = asyncio.run(_collect_start(spider))
    assert len(output) == 6
    assert spider.crawler.stats.get_value("msgloom/crawl/mode") == "full"
    assert spider.crawler.stats.get_value(
        "msgloom/crawl/enrichment/target_message_count"
    ) == 2
