"""Verify Microsoft Calendar inventory discovery."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from scrapy import Request
from scrapy.http import TextResponse
from scrapy.utils.request import request_from_dict
from scrapy.utils.test import get_crawler

from message_ingest.items.acquisition import RawHttpEvidenceItem
from message_ingest.items.microsoft.outlook.calendar import OutlookCalendarItem
from message_ingest.spiders.microsoft.outlook.calendar.discover import (
    OutlookCalendarDiscoverSpider,
)


def _spider() -> OutlookCalendarDiscoverSpider:
    crawler = get_crawler(OutlookCalendarDiscoverSpider)
    return OutlookCalendarDiscoverSpider.from_crawler(crawler)


def _response(spider: OutlookCalendarDiscoverSpider, payload: dict) -> TextResponse:
    request = spider._request(
        f"{spider.graph_root}/me/calendars",
        callback=spider.parse_calendars,
        purpose="calendar-inventory-page",
        cb_kwargs={},
        prefer='IdType="ImmutableId"',
    )
    return TextResponse(
        request.url,
        request=request,
        body=json.dumps(payload).encode(),
        encoding="utf-8",
        headers={"Content-Type": "application/json"},
    )


def test_discover_start_lists_visible_calendars() -> None:
    spider = _spider()
    if spider.crawler.settings.getlist("MS_GRAPH_SCOPES") != ["Calendars.Read"]:
        pytest.fail("Expected Calendar discovery to share Calendars.Read")

    async def first_request() -> Request:
        return await anext(spider.start())

    request = asyncio.run(first_request())
    parsed = urlsplit(request.url)
    if parsed.path != "/v1.0/me/calendars":
        pytest.fail(f"Unexpected Calendar inventory path: {parsed.path}")
    if parse_qs(parsed.query).get("$top") != ["100"]:
        pytest.fail("Expected Calendar inventory page size 100")


def test_discover_emits_inventory_and_opaque_continuation() -> None:
    spider = _spider()
    next_link = "https://graph.microsoft.com/v1.0/me/calendars?$skiptoken=opaque"
    response = _response(
        spider,
        {
            "value": [
                {
                    "id": "calendar-1",
                    "name": "Calendar",
                    "changeKey": "one",
                    "isDefaultCalendar": True,
                },
                {
                    "id": "calendar-2",
                    "name": "Projects",
                    "changeKey": "two",
                    "isDefaultCalendar": False,
                },
            ],
            "@odata.nextLink": next_link,
        },
    )
    output = list(
        spider.parse_calendars(
            response,
            purpose="calendar-inventory-page",
        )
    )
    if not isinstance(output[0], RawHttpEvidenceItem):
        pytest.fail("Expected inventory evidence first")
    calendars = [x for x in output if isinstance(x, OutlookCalendarItem)]
    if [x.calendar_id for x in calendars] != ["calendar-1", "calendar-2"]:
        pytest.fail("Expected visible Calendar inventory")
    continuation = output[-1]
    if not isinstance(continuation, Request) or continuation.url != next_link:
        pytest.fail("Expected opaque inventory continuation")
    restored = request_from_dict(
        continuation.to_dict(spider=spider),
        spider=_spider(),
    )
    if restored.callback is None or restored.callback.__name__ != "parse_calendars":
        pytest.fail("Expected serializable Calendar inventory callback")


def test_discover_does_not_infer_deletion_from_missing_calendar() -> None:
    spider = _spider()
    response = _response(spider, {"value": []})
    output = list(
        spider.parse_calendars(
            response,
            purpose="calendar-inventory-page",
        )
    )
    if len(output) != 1 or not isinstance(output[0], RawHttpEvidenceItem):
        pytest.fail("Expected empty inventory to emit only evidence")
    if (
        spider.crawler.stats.get_value("msgloom/crawl/calendar/inventory_exhausted")
        is not True
    ):
        pytest.fail("Expected inventory traversal completion")


def test_discover_rejects_jobdir(tmp_path: Path) -> None:
    crawler = get_crawler(
        OutlookCalendarDiscoverSpider,
        settings_dict={"JOBDIR": str(tmp_path / "job")},
    )
    with pytest.raises(ValueError, match="does not support JOBDIR"):
        OutlookCalendarDiscoverSpider.from_crawler(crawler)
