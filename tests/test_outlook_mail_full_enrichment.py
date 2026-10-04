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

from message_ingest.items.microsoft.outlook.email import (
    OutlookAttachmentItem,
    OutlookMailDetailItem,
    OutlookMessageSurfaceItem,
)
from message_ingest.spiders.microsoft.outlook.email.full import OutlookFullSpider

FIXTURES = Path(__file__).parent / "fixtures" / "microsoft_graph"


def _spider(*, max_raw_content_bytes: int | None = None, **kwargs) -> OutlookFullSpider:
    settings = {}
    if max_raw_content_bytes is not None:
        settings["MSGLOOM_MAX_RAW_CONTENT_BYTES"] = max_raw_content_bytes
    crawler = get_crawler(OutlookFullSpider, settings_dict=settings)
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
    if any(getattr(surface, "run_id", None) != spider.run_id for surface in surfaces):
        pytest.fail("Attachment surface producer lost current logical run")
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
    if getattr(surface, "run_id", None) != spider.run_id:
        pytest.fail("Surface producer lost current logical run")
    if surface.surface != "mime":
        pytest.fail('Expected: surface.surface == "mime"')


def test_attachment_inventory_requests_metadata_only_and_caps_response() -> None:
    spider = _spider(
        message_ids="immutable-message-002",
        max_raw_content_bytes=1024,
    )
    request = spider._attachments_request(
        "immutable-message-002",
        page_number=1,
    )
    selected = set(parse_qs(urlsplit(request.url).query)["$select"][0].split(","))
    if "contentBytes" in selected:
        pytest.fail("Attachment inventory must never request contentBytes")
    if {"id", "name", "contentType", "size", "isInline"} > selected:
        pytest.fail("Expected attachment planning metadata in $select")
    if request.meta.get("download_maxsize") != 1024:
        pytest.fail("Expected native Scrapy maxsize on attachment inventory")


def test_known_oversized_item_attachment_is_terminal_without_followup_requests() -> (
    None
):
    spider = _spider(message_ids="m1", max_raw_content_bytes=100)
    request = spider._attachments_request("m1", page_number=1)
    response = TextResponse(
        request.url,
        request=request,
        body=(
            b'{"value":[{"@odata.type":"#microsoft.graph.itemAttachment",'
            b'"id":"large-item","name":"large.eml","size":101,"isInline":false}]}'
        ),
        encoding="utf-8",
        headers={"Content-Type": "application/json"},
    )
    output = list(spider.parse_attachments(response, **request.cb_kwargs))
    if any(isinstance(value, Request) for value in output):
        pytest.fail("Known oversized attachment must not schedule content requests")
    surfaces = {
        value.surface: value.status
        for value in output
        if isinstance(value, OutlookMessageSurfaceItem)
    }
    if surfaces.get("attachment_raw:large-item") != "omitted_size_limit":
        pytest.fail("Expected oversized raw attachment terminal omission")
    if surfaces.get("item_attachment_detail:large-item") != "omitted_size_limit":
        pytest.fail("Expected oversized expanded item terminal omission")
    if surfaces.get("attachments") != "acquired":
        pytest.fail("Attachment inventory itself should remain acquired")


def test_mail_raw_requests_use_configured_native_scrapy_maxsize() -> None:
    spider = _spider(message_ids="m1", max_raw_content_bytes=4096)
    for request in (
        spider._message_mime_request("m1"),
        spider._attachment_raw_request("m1", "a1"),
        spider._item_attachment_detail_request("m1", "a1"),
    ):
        if request.meta.get("download_maxsize") != 4096:
            pytest.fail("Expected configured Scrapy download_maxsize on raw content")


def test_rule_authoritative_refresh_disables_cache_for_every_full_request() -> None:
    spider = _spider(
        message_ids="immutable-message-002",
        operation="refresh",
        _authoritative_rule_refresh=True,
    )

    base = asyncio.run(_collect_start(spider))
    if not base or not all(request.meta.get("dont_cache") is True for request in base):
        pytest.fail("Authoritative Full base requests did not bypass HTTP cache")

    attachments = spider._attachments_request(
        "immutable-message-002",
        page_number=2,
        url="https://graph.example.test/next",
        verbatim_url=True,
    )
    raw = spider._attachment_raw_request("immutable-message-002", "a1")
    item = spider._item_attachment_detail_request("immutable-message-002", "a1")
    for request in (attachments, raw, item):
        if request.meta.get("dont_cache") is not True:
            pytest.fail("Authoritative Full child request did not bypass HTTP cache")


def test_explicit_full_refresh_preserves_existing_cache_behavior() -> None:
    spider = _spider(message_ids="immutable-message-002", operation="refresh")

    requests = asyncio.run(_collect_start(spider))

    if any(request.meta.get("dont_cache") is True for request in requests):
        pytest.fail("Ordinary operator Full unexpectedly became authoritative no-cache")


def test_authoritative_rule_refresh_rejects_enrich_operation() -> None:
    with pytest.raises(ValueError, match="authoritative rule refresh requires refresh"):
        _spider(
            message_ids="immutable-message-002",
            operation="enrich",
            _authoritative_rule_refresh=True,
        )
