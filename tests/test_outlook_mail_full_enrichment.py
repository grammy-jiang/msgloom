"""
Verify targeted full acquisition, representation headers, and attachment
output.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from scrapy.http import Request, TextResponse
from scrapy.utils.test import get_crawler

from message_ingest.items import (
    OutlookAttachmentItem,
    OutlookMailDetailItem,
    OutlookMessageSurfaceItem,
)
from message_ingest.spiders.outlook_full import OutlookFullSpider

FIXTURES = Path(__file__).parent / "fixtures" / "microsoft_graph"


def _spider(**kwargs) -> OutlookFullSpider:
    crawler = get_crawler(OutlookFullSpider)
    return OutlookFullSpider.from_crawler(crawler, **kwargs)


async def _collect_start(spider: OutlookFullSpider) -> list[Request]:
    requests = []
    async for value in spider.start():
        if not isinstance(value, Request):
            pytest.fail("Expected: isinstance(value, Request)")
        requests.append(value)
    return requests


def _response(
    request: Request, filename: str, content_type: str = "application/json"
) -> TextResponse:
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
    if len(output) != 6:
        pytest.fail("Expected: len(output) == 6")
    purposes = [request.cb_kwargs["purpose"] for request in output]
    if purposes.count("message-detail") != 2:
        pytest.fail('Expected: purposes.count("message-detail") == 2')
    if purposes.count("message-mime") != 2:
        pytest.fail('Expected: purposes.count("message-mime") == 2')
    if purposes.count("attachments-list") != 2:
        pytest.fail('Expected: purposes.count("attachments-list") == 2')
    if not all("message_id" not in request.meta for request in output):
        pytest.fail(
            'Expected: all("message_id" not in request.meta for request in output)'
        )


def test_message_detail_requests_non_default_fields_and_emits_detail_item() -> None:
    spider = _spider(message_ids="immutable-message-002")
    detail_request = next(
        request
        for request in asyncio.run(_collect_start(spider))
        if request.cb_kwargs["purpose"] == "message-detail"
    )
    selected = set(
        parse_qs(urlsplit(detail_request.url).query)["$select"][0].split(",")
    )
    if {"body", "uniqueBody", "internetMessageHeaders", "changeKey"} > selected:
        pytest.fail(
            'Expected: {"body", "uniqueBody", "internetMessageHeaders", "changeKey"} <= selected'
        )

    output = list(
        spider.parse_message_detail(
            _response(detail_request, "message_detail.json"), **detail_request.cb_kwargs
        )
    )
    detail = next(value for value in output if isinstance(value, OutlookMailDetailItem))
    if detail.raw["internetMessageHeaders"][2]["name"] != "X-Example-Trace":
        pytest.fail(
            'Expected: detail.raw["internetMessageHeaders"][2]["name"] == "X-Example-Trace"'
        )


def test_attachment_list_schedules_supported_followups_and_completeness_surface() -> (
    None
):
    spider = _spider(message_ids="immutable-message-002")
    request = next(
        request
        for request in asyncio.run(_collect_start(spider))
        if request.cb_kwargs["purpose"] == "attachments-list"
    )
    output = list(
        spider.parse_attachments(
            _response(request, "message_attachments.json"), **request.cb_kwargs
        )
    )

    attachment_items = [
        value for value in output if isinstance(value, OutlookAttachmentItem)
    ]
    requests = [value for value in output if isinstance(value, Request)]
    surfaces = [
        value for value in output if isinstance(value, OutlookMessageSurfaceItem)
    ]
    if len(attachment_items) != 3:
        pytest.fail("Expected: len(attachment_items) == 3")
    if {surface.surface for surface in surfaces} != {
        "attachments",
        "attachment_raw:attachment-reference-001",
    }:
        pytest.fail(
            'Expected: {surface.surface for surface in surfaces} == { "attachments", "attachment_raw:attachment-reference-001", }'
        )
    reference_surface = next(
        surface
        for surface in surfaces
        if surface.surface == "attachment_raw:attachment-reference-001"
    )
    if reference_surface.status != "unsupported":
        pytest.fail('Expected: reference_surface.status == "unsupported"')

    raw_requests = [r for r in requests if r.cb_kwargs["purpose"] == "attachment-raw"]
    if {r.cb_kwargs["attachment_id"] for r in raw_requests} != {
        "attachment-file-001",
        "attachment-item-001",
    }:
        pytest.fail(
            'Expected: {r.cb_kwargs["attachment_id"] for r in raw_requests} == { "attachment-file-001", "attachment-item-001", }'
        )
    if any(
        r.cb_kwargs.get("attachment_id") == "attachment-reference-001"
        and r.cb_kwargs["purpose"] == "attachment-raw"
        for r in requests
    ):
        pytest.fail(
            'Expected: not any( r.cb_kwargs.get("attachment_id") == "attachment-reference-001" and r.cb_kwargs["purpose"] == "attachment-raw" for r in requests )'
        )


def test_item_attachment_detail_emits_metadata_and_surface() -> None:
    spider = _spider(message_ids="immutable-message-002")
    request = spider._item_attachment_detail_request(
        "immutable-message-002", "attachment-item-001"
    )
    output = list(
        spider.parse_attachment_detail(
            _response(request, "item_attachment_detail.json"),
            **request.cb_kwargs,
        )
    )
    attachment = next(
        value for value in output if isinstance(value, OutlookAttachmentItem)
    )
    surface = next(
        value for value in output if isinstance(value, OutlookMessageSurfaceItem)
    )
    if attachment.raw["item"]["attachments"][0]["name"] != "nested.pdf":
        pytest.fail(
            'Expected: attachment.raw["item"]["attachments"][0]["name"] == "nested.pdf"'
        )
    if surface.surface != "item_attachment_detail:attachment-item-001":
        pytest.fail(
            'Expected: surface.surface == "item_attachment_detail:attachment-item-001"'
        )


def test_mime_callback_emits_raw_http_evidence_then_semantic_surface() -> None:
    spider = _spider(message_ids="immutable-message-002")
    request = spider._message_mime_request("immutable-message-002")
    response = _response(request, "message_mime.eml", "message/rfc822")
    output = list(spider.parse_raw_evidence(response, **request.cb_kwargs))
    surface = next(
        value for value in output if isinstance(value, OutlookMessageSurfaceItem)
    )
    if surface.surface != "mime":
        pytest.fail('Expected: surface.surface == "mime"')
