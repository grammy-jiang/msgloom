"""Verify targeted Microsoft Calendar full acquisition."""

from __future__ import annotations

import asyncio
import json
from urllib.parse import parse_qs, urlsplit

import pytest
from scrapy import Request
from scrapy.http import Response, TextResponse
from scrapy.utils.test import get_crawler

from message_ingest.items.acquisition import RawHttpEvidenceItem
from message_ingest.items.microsoft.outlook.calendar import (
    OutlookCalendarAttachmentContentItem,
    OutlookCalendarAttachmentItem,
    OutlookCalendarEventItem,
    OutlookCalendarEventSurfaceItem,
)
from message_ingest.spiders.microsoft.outlook.calendar.full import (
    OutlookCalendarFullSpider,
)


def _spider(
    *,
    event_ids: str = "event-1",
    calendar_id: str = "",
    page_size: str = "100",
    max_raw_content_bytes: int | None = None,
) -> OutlookCalendarFullSpider:
    crawler = get_crawler(
        OutlookCalendarFullSpider,
        settings_dict={
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_SOURCE_IDENTITY_REQUIRED": False,
            **(
                {"MSGLOOM_MAX_RAW_CONTENT_BYTES": max_raw_content_bytes}
                if max_raw_content_bytes is not None
                else {}
            ),
        },
    )
    spider = OutlookCalendarFullSpider.from_crawler(
        crawler,
        event_ids=event_ids,
        calendar_id=calendar_id,
        page_size=page_size,
    )
    crawler.spider = spider
    return spider


async def _collect_start(spider: OutlookCalendarFullSpider):
    return [value async for value in spider.start()]


def _response(request: Request, payload: dict) -> TextResponse:
    return TextResponse(
        request.url,
        request=request,
        body=json.dumps(payload).encode(),
        encoding="utf-8",
        headers={"Content-Type": "application/json"},
    )


def test_full_start_deduplicates_ids_and_requests_text_body() -> None:
    spider = _spider(event_ids="event-1,event-2,event-1", page_size="25")
    requests = asyncio.run(_collect_start(spider))
    if [request.cb_kwargs["event_id"] for request in requests] != [
        "event-1",
        "event-2",
    ]:
        pytest.fail("Expected one detail request for each unique Calendar target")
    if [urlsplit(request.url).path for request in requests] != [
        "/v1.0/me/events/event-1",
        "/v1.0/me/events/event-2",
    ]:
        pytest.fail("Expected default-calendar event detail paths")
    for request in requests:
        if request.headers.get("Prefer") != (
            b'IdType="ImmutableId", outlook.body-content-type="text"'
        ):
            pytest.fail("Calendar detail Prefer bytes changed")


def test_named_calendar_scopes_detail_and_attachment_paths() -> None:
    spider = _spider(
        event_ids="event/with space",
        calendar_id="calendar/one",
        page_size="7",
    )
    detail = next(
        request
        for request in asyncio.run(_collect_start(spider))
        if request.callback == spider.parse_event_detail
    )
    if urlsplit(detail.url).path != (
        "/v1.0/me/calendars/calendar%2Fone/events/event%2Fwith%20space"
    ):
        pytest.fail(f"Unexpected named-calendar path: {detail.url!r}")

    attachments = spider._attachments_request(
        "event/with space",
        page_number=1,
    )
    if urlsplit(attachments.url).path != (
        "/v1.0/me/calendars/calendar%2Fone/events/event%2Fwith%20space/attachments"
    ):
        pytest.fail(f"Unexpected attachment path: {attachments.url!r}")
    if parse_qs(urlsplit(attachments.url).query).get("$top") != ["7"]:
        pytest.fail("Expected Calendar attachment page size")


def test_event_detail_emits_evidence_event_and_attachment_request() -> None:
    spider = _spider()
    request = spider._event_detail_request("event-1")
    output = list(
        spider.parse_event_detail(
            _response(
                request,
                {
                    "id": "event-1",
                    "changeKey": "v1",
                    "subject": "Planning",
                    "body": {
                        "contentType": "text",
                        "content": "Detailed agenda",
                    },
                    "hasAttachments": True,
                    "start": {
                        "dateTime": "2026-09-28T09:00:00",
                        "timeZone": "UTC",
                    },
                    "end": {
                        "dateTime": "2026-09-28T10:00:00",
                        "timeZone": "UTC",
                    },
                },
            ),
            **request.cb_kwargs,
        )
    )
    if not isinstance(output[0], RawHttpEvidenceItem):
        pytest.fail("Expected raw event detail evidence first")
    event = next(
        value for value in output if isinstance(value, OutlookCalendarEventItem)
    )
    if event.observation_kind != "full":
        pytest.fail("Expected full Calendar event observation kind")
    body = event.raw.get("body")
    if not isinstance(body, dict) or body.get("content") != "Detailed agenda":
        pytest.fail("Expected full Calendar body content")
    surface = next(
        value for value in output if isinstance(value, OutlookCalendarEventSurfaceItem)
    )
    if surface.surface != "detail" or surface.status != "acquired":
        pytest.fail("Expected acquired Calendar detail surface")
    if surface.resource_version != "v1":
        pytest.fail("Expected Calendar detail surface bound to event changeKey")
    attachments = next(value for value in output if isinstance(value, Request))
    if attachments.cb_kwargs["event_id"] != "event-1":
        pytest.fail("Expected event attachment inventory request")
    if attachments.cb_kwargs["resource_version"] != "v1":
        pytest.fail("Expected attachment inventory to retain event changeKey")


def test_attachment_page_keeps_content_in_evidence_only_and_follows_nextlink() -> None:
    spider = _spider(page_size="1")
    request = spider._attachments_request("event-1", page_number=1)
    next_link = (
        "https://graph.microsoft.com/v1.0/me/events/event-1/attachments?"
        "$skiptoken=opaque%2Fnext"
    )
    output = list(
        spider.parse_attachments(
            _response(
                request,
                {
                    "value": [
                        {
                            "@odata.type": "#microsoft.graph.fileAttachment",
                            "id": "attachment-1",
                            "name": "agenda.txt",
                            "contentType": "text/plain",
                            "size": 12,
                            "isInline": False,
                            "contentBytes": "SGVsbG8=",
                        }
                    ],
                    "@odata.nextLink": next_link,
                },
            ),
            **request.cb_kwargs,
        )
    )
    if not isinstance(output[0], RawHttpEvidenceItem):
        pytest.fail("Expected attachment page evidence first")
    attachment = next(
        value for value in output if isinstance(value, OutlookCalendarAttachmentItem)
    )
    if attachment.content_bytes_present is not True:
        pytest.fail("Expected attachment content-presence marker")
    if "contentBytes" in attachment.raw:
        pytest.fail("Expected contentBytes to remain only in raw HTTP evidence")
    requests = [value for value in output if isinstance(value, Request)]
    raw_request = next(value for value in requests if value.url.endswith("/$value"))
    if raw_request.cb_kwargs["attachment_id"] != "attachment-1":
        pytest.fail("Expected raw file-attachment request")
    continuation = next(value for value in requests if value.url == next_link)
    if continuation.meta.get("verbatim_url") is not True:
        pytest.fail("Expected attachment continuation to remain opaque")


def test_raw_attachment_content_emits_link_item() -> None:
    spider = _spider()
    request = spider._attachment_raw_request(
        "event-1",
        "attachment-1",
    )
    response = Response(
        request.url,
        request=request,
        body=b"attachment bytes",
        headers={"Content-Type": "application/octet-stream"},
    )
    output = list(
        spider.parse_attachment_content(
            response,
            **request.cb_kwargs,
        )
    )
    if not isinstance(output[0], RawHttpEvidenceItem):
        pytest.fail("Expected raw Calendar attachment evidence first")
    content = output[1]
    if not isinstance(content, OutlookCalendarAttachmentContentItem):
        pytest.fail("Expected Calendar attachment content link item")
    if content.event_id != "event-1" or content.attachment_id != "attachment-1":
        pytest.fail("Expected attachment content identity")


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"event_ids": " , "}, "event ID"),
        ({"event_ids": "event-1", "page_size": "0"}, "page_size"),
        (
            {"event_ids": "event-1", "calendar_id": " calendar "},
            "calendar_id",
        ),
    ],
)
def test_full_validates_arguments(kwargs: dict[str, str], match: str) -> None:
    with pytest.raises(ValueError, match=match):
        OutlookCalendarFullSpider(**kwargs)


def test_expanded_item_keeps_nested_bytes_in_evidence_only() -> None:
    spider = _spider()
    request = spider._item_attachment_detail_request("event-1", "item-1")
    payload = {
        "id": "item-1",
        "@odata.type": "#microsoft.graph.itemAttachment",
        "item": {
            "subject": "Embedded message",
            "attachments": [{"name": "nested.txt", "contentBytes": "SGVsbG8="}],
        },
    }
    output = list(
        spider.parse_attachment_detail(_response(request, payload), **request.cb_kwargs)
    )
    evidence, metadata, surface = output
    if not isinstance(evidence, RawHttpEvidenceItem):
        pytest.fail("Expected raw evidence first")
    if json.loads(evidence.response_body) != payload:
        pytest.fail("Expected exact expanded item evidence")
    if not isinstance(metadata, OutlookCalendarAttachmentItem):
        pytest.fail("Expected expanded item metadata")
    if "contentBytes" in json.dumps(metadata.raw):
        pytest.fail("Nested attachment bytes belong only in raw evidence")
    if metadata.raw["item"]["subject"] != "Embedded message":
        pytest.fail("Expected expanded item semantics to remain available")
    if not isinstance(surface, OutlookCalendarEventSurfaceItem):
        pytest.fail("Expected item attachment detail surface")
    if surface.surface != "item_attachment_detail:item-1":
        pytest.fail("Expected item attachment detail surface key")


def test_recurring_event_detail_requests_expanded_series_master_topology() -> None:
    spider = _spider()
    request = spider._event_detail_request("occurrence-1")
    output = list(
        spider.parse_event_detail(
            _response(
                request,
                {
                    "id": "occurrence-1",
                    "changeKey": "occ-v1",
                    "type": "occurrence",
                    "seriesMasterId": "series-1",
                    "subject": "Recurring",
                },
            ),
            **request.cb_kwargs,
        )
    )
    topology = next(
        value
        for value in output
        if isinstance(value, Request)
        and value.cb_kwargs.get("purpose") == "calendar-series-master"
    )
    if urlsplit(topology.url).path != "/v1.0/me/events/series-1":
        pytest.fail(f"Unexpected series-master path: {topology.url!r}")
    if topology.url != (
        "https://graph.microsoft.com/v1.0/me/events/series-1?"
        "%24select=id%2CchangeKey%2Ctype%2Csubject%2Cstart%2Cend%2C"
        "occurrenceId%2CexceptionOccurrences%2CcancelledOccurrences&"
        "%24expand=exceptionOccurrences"
    ):
        pytest.fail("Full-v1 series selection or query order changed")
    query = parse_qs(urlsplit(topology.url).query)
    if query.get("$expand") != ["exceptionOccurrences"]:
        pytest.fail("Expected expanded exceptionOccurrences")
    selected = query.get("$select", [""])[0]
    for field in ("exceptionOccurrences", "cancelledOccurrences", "occurrenceId"):
        if field not in selected:
            pytest.fail(f"Expected {field} in series-master select")


def test_series_master_callback_emits_shared_topology_item() -> None:
    from message_ingest.items.microsoft.outlook.calendar import (
        OutlookCalendarSeriesTopologyItem,
    )

    spider = _spider(calendar_id="calendar-1")
    request = spider._series_master_request("series-1")
    payload = {
        "id": "series-1",
        "changeKey": "master-v2",
        "type": "seriesMaster",
        "cancelledOccurrences": ["occurrence-id-1"],
        "exceptionOccurrences": [
            {
                "id": "exception-1",
                "occurrenceId": "occurrence-id-2",
                "subject": "Moved occurrence",
            }
        ],
    }
    output = list(
        spider.parse_series_master(
            _response(request, payload),
            **request.cb_kwargs,
        )
    )
    topology = next(
        value
        for value in output
        if isinstance(value, OutlookCalendarSeriesTopologyItem)
    )
    if topology.series_master_id != "series-1" or topology.status != "acquired":
        pytest.fail("Expected acquired shared series topology")
    if topology.calendar_id != "calendar-1":
        pytest.fail("Expected containing calendar scope on series topology")
    if topology.raw != payload:
        pytest.fail("Expected exact expanded series master payload")


def test_calendar_attachment_inventory_requests_metadata_only_and_caps_response() -> (
    None
):
    spider = _spider(max_raw_content_bytes=2048)
    request = spider._attachments_request("event-1", page_number=1)
    query = parse_qs(urlsplit(request.url).query)
    selected = set(query["$select"][0].split(","))
    if "contentBytes" in selected:
        pytest.fail("Calendar attachment inventory must not request contentBytes")
    if request.meta.get("download_maxsize") != 2048:
        pytest.fail("Expected native maxsize on Calendar attachment inventory")


def test_calendar_known_oversized_item_attachment_is_terminal_without_requests() -> (
    None
):
    spider = _spider(max_raw_content_bytes=100)
    request = spider._attachments_request(
        "event-1", page_number=1, resource_version="v1"
    )
    output = list(
        spider.parse_attachments(
            _response(
                request,
                {
                    "value": [
                        {
                            "@odata.type": "#microsoft.graph.itemAttachment",
                            "id": "large-item",
                            "name": "large.eml",
                            "size": 101,
                            "isInline": False,
                        }
                    ]
                },
            ),
            **request.cb_kwargs,
        )
    )
    if any(isinstance(value, Request) for value in output):
        pytest.fail("Known oversized Calendar attachment must not schedule content")
    surfaces = {
        value.surface: value.status
        for value in output
        if isinstance(value, OutlookCalendarEventSurfaceItem)
    }
    if surfaces.get("attachment_raw:large-item") != "omitted_size_limit":
        pytest.fail("Expected Calendar raw attachment size omission")
    if surfaces.get("item_attachment_detail:large-item") != "omitted_size_limit":
        pytest.fail("Expected Calendar item-detail size omission")
    if surfaces.get("attachments") != "acquired":
        pytest.fail("Calendar attachment inventory should remain acquired")
