from __future__ import annotations

import asyncio
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from scrapy.http import Request, TextResponse
from scrapy.utils.test import get_crawler

from msgloom.items import OutlookMailItem
from msgloom.spiders.outlook_mail import OutlookMailSpider


FIXTURES = Path(__file__).parent / "fixtures" / "microsoft_graph"


def _response(filename: str, request: Request | None = None) -> TextResponse:
    body = (FIXTURES / filename).read_bytes()
    if request is None:
        request = Request("https://graph.microsoft.com/v1.0/me/messages")
    return TextResponse(
        url=request.url,
        request=request,
        status=200,
        headers={"Content-Type": "application/json"},
        body=body,
        encoding="utf-8",
    )


def _spider(**kwargs) -> OutlookMailSpider:
    crawler = get_crawler(OutlookMailSpider)
    return OutlookMailSpider.from_crawler(crawler, **kwargs)


async def _collect_start(spider: OutlookMailSpider) -> list[object]:
    return [value async for value in spider.start()]


def test_default_start_targets_entire_mailbox_and_has_no_page_limit() -> None:
    spider = _spider()
    output = asyncio.run(_collect_start(spider))

    assert spider.folder == ""
    assert spider.max_pages == 0
    request = output[0]
    assert isinstance(request, Request)
    parsed = urlsplit(request.url)
    assert parsed.path == "/v1.0/me/messages"
    query = parse_qs(parsed.query)
    assert query["$top"] == ["25"]
    assert "$select" in query
    assert request.cb_kwargs == {"purpose": "message-list", "page_number": 1}
    assert "message_id" not in request.meta
    assert "page_number" not in request.meta


def test_explicit_folder_scope_is_supported_without_changing_default() -> None:
    spider = _spider(folder="archive")
    request = asyncio.run(_collect_start(spider))[0]
    assert isinstance(request, Request)
    assert urlsplit(request.url).path == "/v1.0/me/mailFolders/archive/messages"


def test_documented_message_shape_maps_and_preserves_full_graph_object() -> None:
    spider = _spider()
    response = _response("list_messages_page_1.json")
    payload = json.loads(response.body)

    output = list(spider.parse(response, purpose="message-list", page_number=1))

    message = output[0]
    assert isinstance(message, OutlookMailItem)
    assert message.message_id == "immutable-message-001"
    assert message.subject == "Daily service report"
    assert message.sender_address == "monitor@example.test"
    assert message.importance == "normal"
    assert message.inference_classification == "focused"
    assert message.raw == payload["value"][0]
    assert message.raw["toRecipients"][0]["emailAddress"]["address"] == "user@example.test"
    assert message.raw["flag"]["flagStatus"] == "notFlagged"
    assert message.raw["categories"] == ["Project Alpha"]
    assert message.observation_kind == "discovery"


def test_pagination_follows_nextlink_page_after_page_until_graph_stops() -> None:
    spider = _spider()
    page1 = _response("list_messages_page_1.json")
    payload1 = json.loads(page1.body)

    page1_output = list(spider.parse(page1, purpose="message-list", page_number=1))
    next_request = page1_output[-1]
    assert isinstance(next_request, Request)
    assert next_request.url == payload1["@odata.nextLink"]
    assert next_request.cb_kwargs["page_number"] == 2
    assert next_request.meta["verbatim_url"] is True

    page2 = _response("list_messages_page_2.json", request=next_request)
    page2_output = list(spider.parse(page2, **next_request.cb_kwargs))
    assert isinstance(page2_output[0], OutlookMailItem)
    assert page2_output[0].message_id == "immutable-message-002"
    assert not any(isinstance(value, Request) for value in page2_output)


def test_optional_max_pages_is_only_an_explicit_development_limit() -> None:
    spider = _spider(max_pages="1")
    output = list(
        spider.parse(
            _response("list_messages_page_1.json"),
            purpose="message-list",
            page_number=1,
        )
    )
    assert not any(isinstance(value, Request) for value in output)
    assert spider.crawler.stats.get_value("msgloom/crawl/discovery/truncated_count") == 1
