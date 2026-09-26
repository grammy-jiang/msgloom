from __future__ import annotations

import asyncio
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from scrapy.http import Request, TextResponse
from scrapy.utils.test import get_crawler

from msgloom.items import (
    OutlookAttachmentItem,
    OutlookMailDetailItem,
    OutlookMessageSurfaceItem,
)
from msgloom.spiders.outlook_mail import OutlookMailSpider


FIXTURES = Path(__file__).parent / "fixtures" / "microsoft_graph"


def _spider(**kwargs) -> OutlookMailSpider:
    crawler = get_crawler(OutlookMailSpider)
    return OutlookMailSpider.from_crawler(crawler, **kwargs)


async def _collect_start(spider: OutlookMailSpider) -> list[object]:
    return [value async for value in spider.start()]


def _response(request: Request, filename: str, content_type: str = "application/json") -> TextResponse:
    return TextResponse(
        url=request.url,
        request=request,
        status=200,
        headers={"Content-Type": content_type},
        body=(FIXTURES / filename).read_bytes(),
        encoding="utf-8",
    )


def test_selected_message_ids_start_three_full_enrichment_surfaces_each() -> None:
    spider = _spider(message_ids="id-one,id-two")
    output = asyncio.run(_collect_start(spider))
    assert len(output) == 6
    purposes = [request.cb_kwargs["purpose"] for request in output]
    assert purposes.count("message-detail") == 2
    assert purposes.count("message-mime") == 2
    assert purposes.count("attachments-list") == 2
    assert all("message_id" not in request.meta for request in output)


def test_message_detail_requests_non_default_fields_and_emits_detail_item() -> None:
    spider = _spider(message_ids="immutable-message-002")
    detail_request = next(
        request
        for request in asyncio.run(_collect_start(spider))
        if request.cb_kwargs["purpose"] == "message-detail"
    )
    selected = set(parse_qs(urlsplit(detail_request.url).query)["$select"][0].split(","))
    assert {"body", "uniqueBody", "internetMessageHeaders", "changeKey"} <= selected

    output = list(spider.parse_message_detail(_response(detail_request, "message_detail.json"), **detail_request.cb_kwargs))
    assert len(output) == 1
    assert isinstance(output[0], OutlookMailDetailItem)
    assert output[0].raw["internetMessageHeaders"][2]["name"] == "X-Example-Trace"


def test_attachment_list_schedules_supported_followups_and_completeness_surface() -> None:
    spider = _spider(message_ids="immutable-message-002")
    request = next(
        request
        for request in asyncio.run(_collect_start(spider))
        if request.cb_kwargs["purpose"] == "attachments-list"
    )
    output = list(spider.parse_attachments(_response(request, "message_attachments.json"), **request.cb_kwargs))

    attachment_items = [value for value in output if isinstance(value, OutlookAttachmentItem)]
    requests = [value for value in output if isinstance(value, Request)]
    surfaces = [value for value in output if isinstance(value, OutlookMessageSurfaceItem)]
    assert len(attachment_items) == 3
    assert len(surfaces) == 1
    assert surfaces[0].surface == "attachments"

    raw_requests = [r for r in requests if r.cb_kwargs["purpose"] == "attachment-raw"]
    assert {r.cb_kwargs["attachment_id"] for r in raw_requests} == {
        "attachment-file-001",
        "attachment-item-001",
    }
    assert not any(
        r.cb_kwargs.get("attachment_id") == "attachment-reference-001"
        and r.cb_kwargs["purpose"] == "attachment-raw"
        for r in requests
    )


def test_item_attachment_detail_emits_metadata_and_surface() -> None:
    spider = _spider()
    request = spider._item_attachment_detail_request(
        "immutable-message-002", "attachment-item-001"
    )
    output = list(
        spider.parse_attachment_detail(
            _response(request, "item_attachment_detail.json"),
            **request.cb_kwargs,
        )
    )
    assert isinstance(output[0], OutlookAttachmentItem)
    assert isinstance(output[1], OutlookMessageSurfaceItem)
    assert output[0].raw["item"]["attachments"][0]["name"] == "nested.pdf"


def test_mime_callback_only_emits_semantic_surface_raw_bytes_are_not_spider_items() -> None:
    spider = _spider()
    request = spider._message_mime_request("immutable-message-002")
    response = _response(request, "message_mime.eml", "message/rfc822")
    output = list(spider.parse_raw_evidence(response, **request.cb_kwargs))
    assert len(output) == 1
    assert isinstance(output[0], OutlookMessageSurfaceItem)
    assert output[0].surface == "mime"
