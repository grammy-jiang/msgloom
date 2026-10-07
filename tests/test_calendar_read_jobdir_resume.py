"""Calendar read-spider JOBDIR scope and serialization tests."""

from __future__ import annotations

import pickle
from pathlib import Path

import pytest
from scrapy.exceptions import CloseSpider
from scrapy.utils.misc import build_from_crawler
from scrapy.utils.request import request_from_dict
from scrapy.utils.test import get_crawler

from message_ingest.extensions.microsoft.outlook.calendar.resume import (
    CalendarFullSpiderState,
    CalendarWindowSpiderState,
)
from message_ingest.spiders.microsoft.outlook.calendar.full import (
    OutlookCalendarFullSpider,
)
from message_ingest.spiders.microsoft.outlook.calendar.window import (
    OutlookCalendarWindowSpider,
)


def _calendar_read_crawler(tmp_path: Path, spider_cls, job_name: str):
    return get_crawler(
        spider_cls,
        settings_dict={
            "JOBDIR": str(tmp_path / job_name),
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'read-catalog.sqlite3'}",
            "MSGLOOM_SOURCE_ID": "calendar-read-source",
            "MSGLOOM_SOURCE_IDENTITY_REQUIRED": False,
            "MSGLOOM_CATALOG_ENABLED": True,
        },
    )


def test_calendar_window_jobdir_restores_same_scope_and_run_id(tmp_path: Path) -> None:
    kwargs = {
        "start_datetime": "2026-09-27T00:00:00+10:00",
        "end_datetime": "2026-10-04T00:00:00+10:00",
        "calendar_id": "calendar-1",
        "page_size": "50",
    }
    crawler1 = _calendar_read_crawler(
        tmp_path, OutlookCalendarWindowSpider, "window-job"
    )
    spider1 = OutlookCalendarWindowSpider.from_crawler(crawler1, **kwargs)
    state1 = build_from_crawler(CalendarWindowSpiderState, crawler1)
    state1.spider_opened(spider1)
    spider1._persist_execution_state()
    run_id = spider1.run_id
    state1.spider_closed(spider1)

    crawler2 = _calendar_read_crawler(
        tmp_path, OutlookCalendarWindowSpider, "window-job"
    )
    spider2 = OutlookCalendarWindowSpider.from_crawler(crawler2, **kwargs)
    state2 = build_from_crawler(CalendarWindowSpiderState, crawler2)
    state2.spider_opened(spider2)

    if spider2.run_id != run_id or spider2._job_resumed is not True:
        pytest.fail("Expected Calendar window JOBDIR run identity to resume")


def test_calendar_window_jobdir_rejects_changed_scope_without_rewriting_state(
    tmp_path: Path,
) -> None:
    crawler1 = _calendar_read_crawler(
        tmp_path, OutlookCalendarWindowSpider, "window-reject-job"
    )
    spider1 = OutlookCalendarWindowSpider.from_crawler(
        crawler1,
        start_datetime="2026-09-27T00:00:00+10:00",
        end_datetime="2026-10-04T00:00:00+10:00",
        calendar_id="calendar-1",
    )
    state1 = build_from_crawler(CalendarWindowSpiderState, crawler1)
    state1.spider_opened(spider1)
    spider1._persist_execution_state()
    state1.spider_closed(spider1)
    state_path = tmp_path / "window-reject-job" / "spider.state"
    saved = state_path.read_bytes()

    crawler2 = _calendar_read_crawler(
        tmp_path, OutlookCalendarWindowSpider, "window-reject-job"
    )
    spider2 = OutlookCalendarWindowSpider.from_crawler(
        crawler2,
        start_datetime="2026-09-28T00:00:00+10:00",
        end_datetime="2026-10-05T00:00:00+10:00",
        calendar_id="calendar-1",
    )
    state2 = build_from_crawler(CalendarWindowSpiderState, crawler2)
    with pytest.raises(CloseSpider):
        state2.spider_opened(spider2)
    state2.spider_closed(spider2)

    if state_path.read_bytes() != saved:
        pytest.fail("Rejected Calendar window scope must leave saved state intact")


def test_calendar_full_jobdir_restores_scope_and_rejects_changed_targets(
    tmp_path: Path,
) -> None:
    kwargs = {
        "event_ids": ["event-1", "event-2"],
        "calendar_id": "calendar-1",
        "page_size": "25",
        "operation": "enrich",
        "profile": "outlook-calendar-full-v1",
    }
    crawler1 = _calendar_read_crawler(tmp_path, OutlookCalendarFullSpider, "full-job")
    spider1 = OutlookCalendarFullSpider.from_crawler(crawler1, **kwargs)
    state1 = build_from_crawler(CalendarFullSpiderState, crawler1)
    state1.spider_opened(spider1)
    spider1._persist_execution_state()
    run_id = spider1.run_id
    state1.spider_closed(spider1)
    state_path = tmp_path / "full-job" / "spider.state"
    saved = state_path.read_bytes()

    crawler2 = _calendar_read_crawler(tmp_path, OutlookCalendarFullSpider, "full-job")
    spider2 = OutlookCalendarFullSpider.from_crawler(crawler2, **kwargs)
    state2 = build_from_crawler(CalendarFullSpiderState, crawler2)
    state2.spider_opened(spider2)
    if spider2.run_id != run_id or spider2._job_resumed is not True:
        pytest.fail("Expected Calendar full JOBDIR run identity to resume")

    crawler3 = _calendar_read_crawler(tmp_path, OutlookCalendarFullSpider, "full-job")
    spider3 = OutlookCalendarFullSpider.from_crawler(
        crawler3,
        **{**kwargs, "event_ids": ["event-1", "event-3"]},
    )
    state3 = build_from_crawler(CalendarFullSpiderState, crawler3)
    with pytest.raises(CloseSpider):
        state3.spider_opened(spider3)
    state3.spider_closed(spider3)
    if state_path.read_bytes() != saved:
        pytest.fail("Rejected Calendar full scope must leave saved state intact")


def test_calendar_window_and_full_requests_serialize_for_jobdir(tmp_path: Path) -> None:
    window_crawler = _calendar_read_crawler(
        tmp_path, OutlookCalendarWindowSpider, "serialize-window-job"
    )
    window = OutlookCalendarWindowSpider.from_crawler(
        window_crawler,
        start_datetime="2026-09-27T00:00:00+10:00",
        end_datetime="2026-10-04T00:00:00+10:00",
        calendar_id="calendar-1",
    )
    window_request = window._request(
        "https://graph.microsoft.com/v1.0/me/calendars/calendar-1/calendarView?$skiptoken=opaque",
        callback=window.parse_events,
        purpose="calendar-window-page",
        cb_kwargs={"calendar_id": "calendar-1"},
        verbatim_url=True,
        prefer='IdType="ImmutableId"',
    )

    full_crawler = _calendar_read_crawler(
        tmp_path, OutlookCalendarFullSpider, "serialize-full-job"
    )
    full = OutlookCalendarFullSpider.from_crawler(
        full_crawler,
        event_ids=["event-1"],
        calendar_id="calendar-1",
    )
    requests = [
        window_request,
        full._event_detail_request("event-1", resource_version="v1"),
        full._attachments_request("event-1", page_number=1, resource_version="v1"),
        full._attachment_raw_request("event-1", "attachment-1", resource_version="v1"),
        full._item_attachment_detail_request(
            "event-1", "attachment-1", resource_version="v1"
        ),
        full._series_master_request("series-1"),
    ]
    for request in requests:
        spider = window if request is window_request else full
        restored = request_from_dict(
            pickle.loads(pickle.dumps(request.to_dict(spider=spider), protocol=4)),
            spider=spider,
        )
        if restored.url != request.url:
            pytest.fail(
                "Expected Calendar read request URL to survive JOBDIR serialization"
            )
        if restored.cb_kwargs != request.cb_kwargs:
            pytest.fail(
                "Expected Calendar read callback kwargs to survive serialization"
            )
        if restored.callback != request.callback or restored.errback != request.errback:
            pytest.fail("Expected Calendar read callbacks to survive serialization")
