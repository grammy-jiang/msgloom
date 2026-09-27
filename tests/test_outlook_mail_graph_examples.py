"""
Parse checked-in Graph examples and retain links between evidence and semantic
items.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from scrapy.http import Request, TextResponse
from scrapy.utils.test import get_crawler

from message_ingest.items import OutlookMailItem
from message_ingest.spiders.outlook_discover import OutlookDiscoverSpider

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


def _spider(**kwargs) -> OutlookDiscoverSpider:
    crawler = get_crawler(OutlookDiscoverSpider)
    return OutlookDiscoverSpider.from_crawler(crawler, **kwargs)


async def _collect_start(spider: OutlookDiscoverSpider) -> list[object]:
    return [value async for value in spider.start()]


def test_default_start_targets_entire_mailbox_and_has_no_page_limit() -> None:
    spider = _spider()
    output = asyncio.run(_collect_start(spider))

    if spider.folder != "":
        pytest.fail('Expected: spider.folder == ""')
    if spider.max_pages != 0:
        pytest.fail("Expected: spider.max_pages == 0")
    request = output[0]
    if not isinstance(request, Request):
        pytest.fail("Expected: isinstance(request, Request)")
    parsed = urlsplit(request.url)
    if parsed.path != "/v1.0/me/messages":
        pytest.fail('Expected: parsed.path == "/v1.0/me/messages"')
    query = parse_qs(parsed.query)
    if query["$top"] != ["25"]:
        pytest.fail('Expected: query["$top"] == ["25"]')
    if "$select" not in query:
        pytest.fail('Expected: "$select" in query')
    if request.cb_kwargs != {"purpose": "message-list", "page_number": 1}:
        pytest.fail(
            'Expected: request.cb_kwargs == {"purpose": "message-list", "page_number": 1}'
        )
    if "message_id" in request.meta:
        pytest.fail('Expected: "message_id" not in request.meta')
    if "page_number" in request.meta:
        pytest.fail('Expected: "page_number" not in request.meta')


def test_explicit_folder_scope_is_supported_without_changing_default() -> None:
    spider = _spider(folder="archive")
    request = asyncio.run(_collect_start(spider))[0]
    if not isinstance(request, Request):
        pytest.fail("Expected: isinstance(request, Request)")
    if urlsplit(request.url).path != "/v1.0/me/mailFolders/archive/messages":
        pytest.fail(
            'Expected: urlsplit(request.url).path == "/v1.0/me/mailFolders/archive/messages"'
        )


def test_documented_message_shape_maps_and_preserves_full_graph_object() -> None:
    spider = _spider()
    response = _response("list_messages_page_1.json")
    payload = json.loads(response.body)

    output = list(spider.parse(response, purpose="message-list", page_number=1))

    message = next(value for value in output if isinstance(value, OutlookMailItem))
    if message.message_id != "immutable-message-001":
        pytest.fail('Expected: message.message_id == "immutable-message-001"')
    if message.subject != "Daily service report":
        pytest.fail('Expected: message.subject == "Daily service report"')
    if message.sender_address != "monitor@example.test":
        pytest.fail('Expected: message.sender_address == "monitor@example.test"')
    if message.importance != "normal":
        pytest.fail('Expected: message.importance == "normal"')
    if message.inference_classification != "focused":
        pytest.fail('Expected: message.inference_classification == "focused"')
    if message.raw != payload["value"][0]:
        pytest.fail('Expected: message.raw == payload["value"][0]')
    if message.raw["toRecipients"][0]["emailAddress"]["address"] != "user@example.test":
        pytest.fail(
            'Expected: message.raw["toRecipients"][0]["emailAddress"]["address"] == "user@example.test"'
        )
    if message.raw["flag"]["flagStatus"] != "notFlagged":
        pytest.fail('Expected: message.raw["flag"]["flagStatus"] == "notFlagged"')
    if message.raw["categories"] != ["Project Alpha"]:
        pytest.fail('Expected: message.raw["categories"] == ["Project Alpha"]')
    if message.observation_kind != "discovery":
        pytest.fail('Expected: message.observation_kind == "discovery"')


def test_pagination_follows_nextlink_page_after_page_until_graph_stops() -> None:
    spider = _spider()
    page1 = _response("list_messages_page_1.json")
    payload1 = json.loads(page1.body)

    page1_output = list(spider.parse(page1, purpose="message-list", page_number=1))
    next_request = page1_output[-1]
    if not isinstance(next_request, Request):
        pytest.fail("Expected: isinstance(next_request, Request)")
    if next_request.url != payload1["@odata.nextLink"]:
        pytest.fail('Expected: next_request.url == payload1["@odata.nextLink"]')
    if next_request.cb_kwargs["page_number"] != 2:
        pytest.fail('Expected: next_request.cb_kwargs["page_number"] == 2')
    if next_request.meta["verbatim_url"] is not True:
        pytest.fail('Expected: next_request.meta["verbatim_url"] is True')

    page2 = _response("list_messages_page_2.json", request=next_request)
    page2_output = list(spider.parse(page2, **next_request.cb_kwargs))
    page2_message = next(
        value for value in page2_output if isinstance(value, OutlookMailItem)
    )
    if page2_message.message_id != "immutable-message-002":
        pytest.fail('Expected: page2_message.message_id == "immutable-message-002"')
    if any(isinstance(value, Request) for value in page2_output):
        pytest.fail(
            "Expected: not any(isinstance(value, Request) for value in page2_output)"
        )


def test_optional_max_pages_is_only_an_explicit_development_limit() -> None:
    spider = _spider(max_pages="1")
    output = list(
        spider.parse(
            _response("list_messages_page_1.json"),
            purpose="message-list",
            page_number=1,
        )
    )
    if any(isinstance(value, Request) for value in output):
        pytest.fail("Expected: not any(isinstance(value, Request) for value in output)")
    if spider.crawler.stats.get_value("msgloom/crawl/discovery/truncated_count") != 1:
        pytest.fail(
            'Expected: spider.crawler.stats.get_value("msgloom/crawl/discovery/truncated_count") == 1'
        )
