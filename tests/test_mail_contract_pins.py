"""Full callbacks retain exact pins before semantic pipeline completion."""

import asyncio
import json

import pytest
from scrapy.http import Request, TextResponse
from scrapy.utils.request import request_from_dict
from test_outlook_mail_full_enrichment import _spider

from message_ingest.catalog.stores.microsoft.outlook._email_handoff import (
    primary_projection,
    semantic_digest,
)
from message_ingest.items.microsoft.outlook.email import (
    OutlookMailDetailItem,
    OutlookMessageSurfaceItem,
)


def test_detail_selects_parent_for_native_serializable_component_requests():
    """Select once from exact detail bytes, before any pipeline ordering."""
    spider = _spider(message_ids="m1")

    async def initial_requests():
        return [request async for request in spider.start()]

    initial = asyncio.run(initial_requests())
    if len(initial) != 1:
        pytest.fail("Expected one primary selection request")
    request = initial[0]
    if not isinstance(request, Request):
        pytest.fail("Expected a native Request for primary selection")
    if request.cb_kwargs["purpose"] != "message-detail":
        pytest.fail("Components were scheduled without an exact selected primary")
    payload = {"id": "m1", "changeKey": "v1"}
    response = TextResponse(
        request.url,
        request=request,
        body=json.dumps(payload).encode(),
        encoding="utf-8",
    )
    output = list(spider.parse_message_detail(response, **request.cb_kwargs))
    children = [item for item in output if isinstance(item, Request)]
    if {r.cb_kwargs["purpose"] for r in children} != {
        "message-mime",
        "attachments-list",
    }:
        pytest.fail("Selected primary did not schedule the Full obligations")
    expected = semantic_digest(primary_projection(payload))
    for child in children:
        restored = request_from_dict(child.to_dict(spider=spider), spider=spider)
        if restored.cb_kwargs.get("resource_version") != expected:
            pytest.fail("Native request serialization lost the exact parent pin")
        if not restored.cb_kwargs.get("primary_observed_at"):
            pytest.fail("Missing parent freshness provenance")
    if not any(isinstance(item, OutlookMailDetailItem) for item in output):
        pytest.fail("Primary detail persistence disappeared")


def test_binary_and_empty_inventory_keep_selected_parent():
    """Non-JSON MIME and empty inventories cannot infer their parent."""
    spider = _spider(message_ids="m1")
    pin = {
        "resource_version": "selected",
        "primary_observed_at": "2026-10-03T00:00:00+00:00",
    }
    for purpose, body in [
        ("message-mime", b"binary"),
        ("attachments-list", b'{"value":[]}'),
    ]:
        request = Request(
            "https://example.test/fixture",
            cb_kwargs={"purpose": purpose, "message_id": "m1", **pin},
        )
        response = TextResponse(
            request.url,
            request=request,
            body=body,
            encoding="utf-8",
        )
        if purpose == "message-mime":
            outputs = spider.parse_raw_evidence(response, **request.cb_kwargs)
        else:
            outputs = spider.parse_attachments(
                response,
                page_number=1,
                **request.cb_kwargs,
            )
        for item in outputs:
            if (
                isinstance(item, OutlookMessageSurfaceItem)
                and getattr(item, "resource_version", None) != "selected"
            ):
                pytest.fail("Full surface discarded the explicit parent")


@pytest.mark.parametrize("code", [401, 403, 404, 410, 405])
def test_empty_terminal_http_response_retains_request_pin(code):
    """Local HTTP decisions keep exact parent even without response bytes."""
    from scrapy.spidermiddlewares.httperror import HttpError
    from twisted.python.failure import Failure

    spider = _spider(message_ids="m1")
    request = spider._message_mime_request(
        "m1",
        resource_version="selected",
        primary_observed_at="2026-10-03T00:00:00+00:00",
    )
    response = TextResponse(request.url, request=request, status=code, body=b"")
    failure = Failure(HttpError(response))
    failure.request = request  # type: ignore[attr-defined]
    outputs = list(spider.errback(failure))
    surfaces = [item for item in outputs if isinstance(item, OutlookMessageSurfaceItem)]
    if len(surfaces) != 1 or surfaces[0].resource_version != "selected":
        pytest.fail("Empty error response lost request-selected parent")


def test_native_size_cancellation_retains_request_pin():
    """Download limits remain terminal under the same exact selected parent."""
    from scrapy.exceptions import DownloadCancelledError
    from twisted.python.failure import Failure

    spider = _spider(message_ids="m1")
    request = spider._attachment_raw_request(
        "m1",
        "a1",
        resource_version="selected",
        primary_observed_at="2026-10-03T00:00:00+00:00",
    )
    failure = Failure(DownloadCancelledError())
    failure.request = request  # type: ignore[attr-defined]
    outputs = list(spider.errback(failure))
    surfaces = [item for item in outputs if isinstance(item, OutlookMessageSurfaceItem)]
    if len(surfaces) != 1:
        pytest.fail("Missing terminal size-limit surface")
    if (surfaces[0].status, surfaces[0].resource_version) != (
        "omitted_size_limit",
        "selected",
    ):
        pytest.fail("Size cancellation lost exact binding or outcome")
