"""Verify bounded Microsoft Calendar window acquisition."""

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

from message_ingest.items import OutlookCalendarEventItem, RawHttpEvidenceItem
from message_ingest.spiders.microsoft.outlook.calendar.window import (
    OutlookCalendarWindowSpider,
)

START = "2026-09-27T00:00:00+10:00"
END = "2026-10-04T00:00:00+10:00"


def _spider(
    *,
    calendar_id: str = "",
    page_size: str = "100",
    settings: dict | None = None,
) -> OutlookCalendarWindowSpider:
    crawler = get_crawler(
        OutlookCalendarWindowSpider,
        settings_dict=settings or {},
    )
    return OutlookCalendarWindowSpider.from_crawler(
        crawler,
        start_datetime=START,
        end_datetime=END,
        calendar_id=calendar_id,
        page_size=page_size,
    )


def _response(
    spider: OutlookCalendarWindowSpider,
    payload: dict,
    *,
    calendar_id: str = "default",
) -> TextResponse:
    request = spider._request(
        f"{spider.graph_root}/me/calendar/calendarView",
        callback=spider.parse_events,
        purpose="calendar-window-page",
        cb_kwargs={"calendar_id": calendar_id},
        prefer='IdType="ImmutableId"',
    )
    return TextResponse(
        request.url,
        request=request,
        body=json.dumps(payload).encode(),
        encoding="utf-8",
        headers={"Content-Type": "application/json"},
    )


def test_window_spider_owns_scope_and_resource_pipeline() -> None:
    spider = _spider()
    settings = spider.crawler.settings
    if settings.getlist("MS_GRAPH_SCOPES") != ["Calendars.Read"]:
        pytest.fail("Expected Calendar window to share Calendars.Read")
    if settings.getbool("MSGLOOM_DELTA_CHECKPOINT_ENABLED"):
        pytest.fail("Expected Mail delta checkpoint disabled")
    expected = {
        "message_ingest.pipelines.evidence.RawEvidencePipeline": 200,
        "message_ingest.acquisition.evidence_link.EvidenceLinkPipeline": 250,
        "message_ingest.pipelines.calendar.CalendarPipeline": 300,
    }
    if settings.getdict("ITEM_PIPELINES") != expected:
        pytest.fail("Expected Calendar-specific native pipeline chain")


def test_window_start_request_uses_calendar_view_and_explicit_range() -> None:
    spider = _spider()

    async def first_request() -> Request:
        return await anext(spider.start())

    request = asyncio.run(first_request())
    parsed = urlsplit(request.url)
    query = parse_qs(parsed.query)
    if parsed.path != "/v1.0/me/calendar/calendarView":
        pytest.fail(f"Unexpected Calendar endpoint: {parsed.path}")
    if query.get("startDateTime") != [START] or query.get("endDateTime") != [END]:
        pytest.fail(f"Unexpected Calendar window: {query!r}")
    if query.get("$top") != ["100"]:
        pytest.fail("Expected Calendar page size 100")
    if "$select" in query:
        pytest.fail("Expected calendarView to retain provider event properties")
    if request.headers.get("Prefer") != b'IdType="ImmutableId"':
        pytest.fail("Expected immutable Outlook IDs")


def test_window_can_target_a_specific_calendar() -> None:
    spider = _spider(calendar_id="calendar / one")

    async def first_request() -> Request:
        return await anext(spider.start())

    request = asyncio.run(first_request())
    if urlsplit(request.url).path != (
        "/v1.0/me/calendars/calendar%20%2F%20one/calendarView"
    ):
        pytest.fail(f"Unexpected specific-calendar path: {request.url}")
    if request.cb_kwargs.get("calendar_id") != "calendar / one":
        pytest.fail("Expected declared calendar provenance in callback kwargs")


def test_window_emits_occurrences_exceptions_and_opaque_continuation() -> None:
    spider = _spider()
    next_link = (
        "https://graph.microsoft.com/v1.0/me/calendar/calendarView?"
        "$skiptoken=opaque%2Ftoken"
    )
    response = _response(
        spider,
        {
            "value": [
                {
                    "id": "occurrence-1",
                    "changeKey": "v1",
                    "subject": "Recurring occurrence",
                    "type": "occurrence",
                    "seriesMasterId": "series-1",
                    "isAllDay": False,
                    "isCancelled": False,
                    "start": {"dateTime": "2026-09-28T09:00:00", "timeZone": "UTC"},
                    "end": {"dateTime": "2026-09-28T10:00:00", "timeZone": "UTC"},
                },
                {
                    "id": "exception-1",
                    "changeKey": "v2",
                    "subject": "Moved occurrence",
                    "type": "exception",
                    "seriesMasterId": "series-1",
                    "isAllDay": False,
                    "isCancelled": False,
                    "start": {"dateTime": "2026-09-29T11:00:00", "timeZone": "UTC"},
                    "end": {"dateTime": "2026-09-29T12:00:00", "timeZone": "UTC"},
                },
            ],
            "@odata.nextLink": next_link,
        },
    )
    output = list(
        spider.parse_events(
            response,
            calendar_id="default",
            purpose="calendar-window-page",
        )
    )
    if not isinstance(output[0], RawHttpEvidenceItem):
        pytest.fail("Expected raw evidence before Calendar event items")
    events = [x for x in output if isinstance(x, OutlookCalendarEventItem)]
    if [x.raw["type"] for x in events] != ["occurrence", "exception"]:
        pytest.fail("Expected recurrence-expanded Calendar event types")
    if any(x.calendar_id != "default" for x in events):
        pytest.fail("Expected calendar provenance on every event")
    continuation = output[-1]
    if not isinstance(continuation, Request) or continuation.url != next_link:
        pytest.fail("Expected opaque Calendar continuation request")


def test_window_final_page_marks_pagination_exhausted() -> None:
    spider = _spider()
    response = _response(spider, {"value": []})
    output = list(
        spider.parse_events(
            response,
            calendar_id="default",
            purpose="calendar-window-page",
        )
    )
    if len(output) != 1 or not isinstance(output[0], RawHttpEvidenceItem):
        pytest.fail("Expected final empty page evidence")
    if (
        spider.crawler.stats.get_value("msgloom/crawl/calendar/pagination_exhausted")
        is not True
    ):
        pytest.fail("Expected Calendar window traversal completion")


def test_window_continuation_round_trips_scrapy_serialization() -> None:
    spider = _spider()
    next_link = (
        "https://graph.microsoft.com/v1.0/me/calendar/calendarView?$skiptoken=opaque"
    )
    response = _response(
        spider,
        {"value": [], "@odata.nextLink": next_link},
    )
    continuation = list(
        spider.parse_events(
            response,
            calendar_id="default",
            purpose="calendar-window-page",
        )
    )[-1]
    if not isinstance(continuation, Request):
        pytest.fail("Expected Calendar continuation Request")
    restored = request_from_dict(
        continuation.to_dict(spider=spider),
        spider=_spider(),
    )
    if restored.callback is None or restored.callback.__name__ != "parse_events":
        pytest.fail("Expected named Calendar callback after serialization")
    if restored.cb_kwargs != continuation.cb_kwargs:
        pytest.fail("Expected Calendar callback kwargs after serialization")


@pytest.mark.parametrize(
    ("start", "end", "match"),
    [
        ("", END, "start_datetime"),
        ("2026-09-27T00:00:00", END, "offset"),
        (END, START, "earlier"),
        (START, START, "earlier"),
    ],
)
def test_window_rejects_invalid_scope(start: str, end: str, match: str) -> None:
    crawler = get_crawler(OutlookCalendarWindowSpider)
    with pytest.raises(ValueError, match=match):
        OutlookCalendarWindowSpider.from_crawler(
            crawler,
            start_datetime=start,
            end_datetime=end,
        )


def test_window_rejects_jobdir(tmp_path: Path) -> None:
    crawler = get_crawler(
        OutlookCalendarWindowSpider,
        settings_dict={"JOBDIR": str(tmp_path / "job")},
    )
    with pytest.raises(ValueError, match="does not support JOBDIR"):
        OutlookCalendarWindowSpider.from_crawler(
            crawler,
            start_datetime=START,
            end_datetime=END,
        )
