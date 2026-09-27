"""Verify the minimal Microsoft Calendar spider boundary."""

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
from message_ingest.spiders.outlook_calendar import OutlookCalendarSpider


def _spider(settings: dict | None = None) -> OutlookCalendarSpider:
    crawler = get_crawler(
        OutlookCalendarSpider,
        settings_dict=settings or {},
    )
    return OutlookCalendarSpider.from_crawler(crawler)


def _response(
    spider: OutlookCalendarSpider,
    payload: dict,
) -> TextResponse:
    request = spider._request(
        f"{spider.graph_root}/me/calendar/events",
        callback=spider.parse_events,
        purpose="calendar-event-page",
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


def test_calendar_spider_owns_scope_and_resource_pipeline() -> None:
    spider = _spider()
    settings = spider.crawler.settings

    if settings.getlist("MS_GRAPH_SCOPES") != ["Calendars.ReadBasic"]:
        pytest.fail("Expected Calendar resource to own Calendars.ReadBasic")
    if settings.getbool("MSGLOOM_DELTA_CHECKPOINT_ENABLED"):
        pytest.fail("Expected Mail delta checkpoint extension disabled")
    if settings.getbool("MSGLOOM_CRAWL_STATUS_ENABLED"):
        pytest.fail("Expected Mail crawl status extension disabled")
    expected = {
        "message_ingest.pipelines.evidence.RawEvidencePipeline": 200,
        "message_ingest.acquisition.evidence_link.EvidenceLinkPipeline": 250,
        "message_ingest.pipelines.calendar.CalendarPipeline": 300,
    }
    if settings.getdict("ITEM_PIPELINES") != expected:
        pytest.fail("Expected Calendar-specific native pipeline chain")


def test_calendar_start_request_uses_native_graph_request() -> None:
    spider = _spider()

    async def first_request() -> Request:
        return await anext(spider.start())

    request = asyncio.run(first_request())
    parsed = urlsplit(request.url)
    query = parse_qs(parsed.query)

    if parsed.path != "/v1.0/me/calendar/events":
        pytest.fail(f"Unexpected Calendar endpoint: {parsed.path}")
    if query.get("$select") != ["id,subject,start,end,type"]:
        pytest.fail("Expected bounded Calendar field selection")
    if query.get("$top") != ["50"]:
        pytest.fail("Expected Calendar page size of 50")
    if request.headers.get("Prefer") != b'IdType="ImmutableId"':
        pytest.fail("Expected Calendar to request immutable Outlook IDs")
    if request.callback != spider.parse_events or request.errback != spider.errback:
        pytest.fail("Expected provider-native callback and errback wiring")


def test_calendar_page_emits_evidence_events_then_opaque_continuation() -> None:
    spider = _spider()
    next_link = (
        "https://graph.microsoft.com/v1.0/me/calendar/events?"
        "$skiptoken=opaque%2Ftoken"
    )
    response = _response(
        spider,
        {
            "value": [
                {
                    "id": "event-1",
                    "subject": "One",
                    "start": {"dateTime": "2026-09-27T09:00:00", "timeZone": "UTC"},
                    "end": {"dateTime": "2026-09-27T10:00:00", "timeZone": "UTC"},
                    "type": "singleInstance",
                },
                {
                    "id": "event-2",
                    "subject": "Series",
                    "start": {"dateTime": "2026-09-28T09:00:00", "timeZone": "UTC"},
                    "end": {"dateTime": "2026-09-28T10:00:00", "timeZone": "UTC"},
                    "type": "seriesMaster",
                },
            ],
            "@odata.nextLink": next_link,
        },
    )

    output = list(
        spider.parse_events(
            response,
            purpose="calendar-event-page",
        )
    )

    if not isinstance(output[0], RawHttpEvidenceItem):
        pytest.fail("Expected raw evidence before Calendar semantic items")
    events = [value for value in output if isinstance(value, OutlookCalendarEventItem)]
    if [event.event_id for event in events] != ["event-1", "event-2"]:
        pytest.fail("Expected two Calendar events in provider order")
    continuation = output[-1]
    if not isinstance(continuation, Request):
        pytest.fail("Expected final output to be the continuation Request")
    if continuation.url != next_link:
        pytest.fail("Expected Graph continuation URL to remain opaque")
    if continuation.cb_kwargs != {"purpose": "calendar-event-page"}:
        pytest.fail("Expected serializable Calendar callback context")


def test_calendar_empty_final_page_marks_pagination_exhausted() -> None:
    spider = _spider()
    response = _response(spider, {"value": []})

    output = list(
        spider.parse_events(
            response,
            purpose="calendar-event-page",
        )
    )

    if len(output) != 1 or not isinstance(output[0], RawHttpEvidenceItem):
        pytest.fail("Expected final empty page to retain its raw evidence")
    if spider.crawler.stats.get_value(
        "msgloom/crawl/calendar/pagination_exhausted"
    ) is not True:
        pytest.fail("Expected Calendar pagination exhaustion fact")


def test_calendar_malformed_event_fails_after_evidence() -> None:
    spider = _spider()
    response = _response(spider, {"value": [{"subject": "missing id"}]})
    output = spider.parse_events(
        response,
        purpose="calendar-event-page",
    )

    first = next(output)
    if not isinstance(first, RawHttpEvidenceItem):
        pytest.fail("Expected evidence before semantic validation")
    with pytest.raises(ValueError, match="non-empty id"):
        next(output)


def test_calendar_continuation_round_trips_through_scrapy_serialization() -> None:
    spider = _spider()
    next_link = (
        "https://graph.microsoft.com/v1.0/me/calendar/events?"
        "$skiptoken=opaque"
    )
    response = _response(
        spider,
        {"value": [], "@odata.nextLink": next_link},
    )
    continuation = list(
        spider.parse_events(
            response,
            purpose="calendar-event-page",
        )
    )[-1]
    if not isinstance(continuation, Request):
        pytest.fail("Expected Calendar continuation Request")

    wire = continuation.to_dict(spider=spider)
    restored = request_from_dict(wire, spider=_spider())

    if restored.callback is None or restored.callback.__name__ != "parse_events":
        pytest.fail("Expected named Calendar callback to survive serialization")
    if restored.errback is None or restored.errback.__name__ != "errback":
        pytest.fail("Expected inherited Graph errback to survive serialization")
    if restored.cb_kwargs != continuation.cb_kwargs:
        pytest.fail("Expected Calendar callback kwargs to survive serialization")


def test_calendar_rejects_jobdir_until_resume_is_defined(tmp_path: Path) -> None:
    crawler = get_crawler(
        OutlookCalendarSpider,
        settings_dict={"JOBDIR": str(tmp_path / "job")},
    )
    with pytest.raises(ValueError, match="does not support JOBDIR"):
        OutlookCalendarSpider.from_crawler(crawler)
