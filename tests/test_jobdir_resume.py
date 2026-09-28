"""
Exercise native :class:`~scrapy.extensions.spiderstate.SpiderState` persistence
and request callback serialization for clean resume.
"""

from __future__ import annotations

import pickle
from pathlib import Path

import pytest
from scrapy.exceptions import CloseSpider
from scrapy.extensions.spiderstate import SpiderState
from scrapy.utils.misc import build_from_crawler
from scrapy.utils.request import request_from_dict
from scrapy.utils.test import get_crawler

from message_ingest.extensions.calendar_delta_checkpoint import (
    CalendarDeltaSpiderState,
)
from message_ingest.spiders.outlook_calendar_delta import (
    OutlookCalendarDeltaSpider,
)
from message_ingest.spiders.outlook_delta import OutlookDeltaSpider
from message_ingest.spiders.outlook_discover import OutlookDiscoverSpider
from message_ingest.spiders.outlook_full import OutlookFullSpider
from message_ingest.spiders.outlook_mail import OutlookMailSpider


def _crawler(
    tmp_path: Path,
    spider_cls: type[OutlookMailSpider] = OutlookDeltaSpider,
):
    return get_crawler(
        spider_cls,
        settings_dict={
            "JOBDIR": str(tmp_path / "job"),
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_SOURCE_ID": "test-source",
        },
    )


def test_scrapy_spiderstate_persists_delta_execution_state_for_jobdir(
    tmp_path: Path,
) -> None:
    crawler1 = _crawler(tmp_path)
    spider1 = OutlookDeltaSpider.from_crawler(crawler1)
    state1 = build_from_crawler(SpiderState, crawler1)
    state1.spider_opened(spider1)

    spider1._seen_folder_ids = {"folder-one", "folder-two"}
    spider1._started_folder_ids = {"folder-one", "folder-two"}
    spider1._completed_folder_ids = {"folder-one"}
    spider1._folder_inventory_pending = 1
    spider1._delta_start_scheduled = True
    spider1._persist_execution_state()
    run_id = spider1.run_id
    state1.spider_closed(spider1)

    if not (tmp_path / "job" / "spider.state").exists():
        pytest.fail('Expected: (tmp_path / "job" / "spider.state").exists()')

    crawler2 = _crawler(tmp_path)
    spider2 = OutlookDeltaSpider.from_crawler(crawler2)
    state2 = build_from_crawler(SpiderState, crawler2)
    state2.spider_opened(spider2)
    spider2._restore_execution_state()

    if spider2.run_id != run_id:
        pytest.fail("Expected: spider2.run_id == run_id")
    if spider2._seen_folder_ids != {"folder-one", "folder-two"}:
        pytest.fail(
            'Expected: spider2._seen_folder_ids == {"folder-one", "folder-two"}'
        )
    if spider2._started_folder_ids != {"folder-one", "folder-two"}:
        pytest.fail(
            'Expected: spider2._started_folder_ids == {"folder-one", "folder-two"}'
        )
    if spider2._completed_folder_ids != {"folder-one"}:
        pytest.fail('Expected: spider2._completed_folder_ids == {"folder-one"}')
    if spider2._folder_inventory_pending != 1:
        pytest.fail("Expected: spider2._folder_inventory_pending == 1")
    if spider2._delta_start_scheduled is not True:
        pytest.fail("Expected: spider2._delta_start_scheduled is True")


@pytest.mark.parametrize(
    "spider_cls",
    [
        OutlookDiscoverSpider,
        OutlookDeltaSpider,
        OutlookFullSpider,
    ],
)
def test_outlook_requests_are_serializable_for_scrapy_persistent_scheduler(
    tmp_path: Path,
    spider_cls: type[OutlookMailSpider],
) -> None:
    crawler = _crawler(tmp_path, spider_cls)
    kwargs = {"message_ids": "message-id"} if spider_cls is OutlookFullSpider else {}
    spider = spider_cls.from_crawler(crawler, **kwargs)

    if isinstance(spider, OutlookDiscoverSpider):
        requests = [
            spider._message_list_request(
                "https://graph.microsoft.com/v1.0/me/messages?$top=25",
                page_number=1,
            )
        ]
    elif isinstance(spider, OutlookDeltaSpider):
        requests = [
            spider._folder_list_request(
                "https://graph.microsoft.com/v1.0/me/mailFolders?includeHiddenFolders=true",
                parent_folder_id=None,
                page_number=1,
                purpose="folder-list",
            ),
            spider._message_delta_request(
                "https://graph.microsoft.com/v1.0/me/mailFolders/f/messages/delta?$deltatoken=opaque",
                folder_id="f",
                page_number=2,
            ),
            spider._global_reconciliation_request(),
            spider._reconciliation_message_request("message-id"),
        ]
    else:
        if not isinstance(spider, OutlookFullSpider):
            pytest.fail("Expected: isinstance(spider, OutlookFullSpider)")
        requests = [
            spider._message_detail_request("message-id"),
            spider._message_mime_request("message-id"),
            spider._attachments_request("message-id", page_number=1),
            spider._attachment_raw_request("message-id", "attachment-id"),
            spider._item_attachment_detail_request("message-id", "attachment-id"),
        ]

    for request in requests:
        serialized = request.to_dict(spider=spider)
        restored = request_from_dict(
            pickle.loads(pickle.dumps(serialized, protocol=4)),
            spider=spider,
        )
        if restored.url != request.url:
            pytest.fail("Expected: restored.url == request.url")
        if restored.cb_kwargs != request.cb_kwargs:
            pytest.fail("Expected: restored.cb_kwargs == request.cb_kwargs")
        if restored.meta != request.meta:
            pytest.fail("Expected: restored.meta == request.meta")
        if restored.callback is None:
            pytest.fail("Expected: restored.callback is not None")
        if restored.callback != request.callback:
            pytest.fail("Expected: restored.callback == request.callback")
        if restored.errback is None:
            pytest.fail("Expected: restored.errback is not None")
        if restored.errback != request.errback:
            pytest.fail("Expected: restored.errback == request.errback")


def _calendar_crawler(tmp_path: Path):
    return get_crawler(
        OutlookCalendarDeltaSpider,
        settings_dict={
            "JOBDIR": str(tmp_path / "calendar-job"),
            "MSGLOOM_DATABASE_URL": (
                f"sqlite:///{tmp_path / 'calendar-catalog.sqlite3'}"
            ),
            "MSGLOOM_SOURCE_ID": "calendar-source",
            "MSGLOOM_SOURCE_IDENTITY_REQUIRED": False,
        },
    )


def test_scrapy_spiderstate_persists_calendar_delta_execution_scope(
    tmp_path: Path,
) -> None:
    start = "2026-09-27T00:00:00+10:00"
    end = "2026-10-04T00:00:00+10:00"
    crawler1 = _calendar_crawler(tmp_path)
    spider1 = OutlookCalendarDeltaSpider.from_crawler(
        crawler1,
        start_datetime=start,
        end_datetime=end,
    )
    state1 = build_from_crawler(SpiderState, crawler1)
    state1.spider_opened(spider1)

    spider1.attempt = 1
    spider1.base_revision = 4
    spider1._terminal_delta_seen = True
    spider1._delta_start_scheduled = True
    spider1.mark_run_failed("fixture-failure")
    run_id = spider1.run_id
    state1.spider_closed(spider1)

    crawler2 = _calendar_crawler(tmp_path)
    spider2 = OutlookCalendarDeltaSpider.from_crawler(
        crawler2,
        start_datetime=start,
        end_datetime=end,
    )
    state2 = build_from_crawler(SpiderState, crawler2)
    state2.spider_opened(spider2)
    spider2._restore_execution_state()

    snapshot = spider2.delta_execution_snapshot()
    if snapshot["run_id"] != run_id:
        pytest.fail("Expected Calendar delta run ID to resume")
    if snapshot["attempt"] != 1 or snapshot["base_revision"] != 4:
        pytest.fail("Expected Calendar delta checkpoint CAS facts to resume")
    if snapshot["terminal_delta_seen"] is not True:
        pytest.fail("Expected Calendar terminal execution fact to resume")
    if snapshot["run_failed"] is not True:
        pytest.fail("Expected Calendar failure integrity to resume")
    if "fixture-failure" not in snapshot["failure_reasons"]:
        pytest.fail("Expected Calendar failure reason to resume")


def test_calendar_delta_jobdir_rejects_different_window(
    tmp_path: Path,
) -> None:
    crawler1 = _calendar_crawler(tmp_path)
    spider1 = OutlookCalendarDeltaSpider.from_crawler(
        crawler1,
        start_datetime="2026-09-27T00:00:00+10:00",
        end_datetime="2026-10-04T00:00:00+10:00",
    )
    state1 = build_from_crawler(SpiderState, crawler1)
    state1.spider_opened(spider1)
    spider1._delta_start_scheduled = True
    spider1._persist_execution_state()
    state1.spider_closed(spider1)

    crawler2 = _calendar_crawler(tmp_path)
    spider2 = OutlookCalendarDeltaSpider.from_crawler(
        crawler2,
        start_datetime="2026-09-28T00:00:00+10:00",
        end_datetime="2026-10-05T00:00:00+10:00",
    )
    state2 = build_from_crawler(SpiderState, crawler2)
    state2.spider_opened(spider2)
    with pytest.raises(ValueError, match="different fixed window"):
        spider2._restore_execution_state()


def test_calendar_delta_requests_serialize_for_persistent_scheduler(
    tmp_path: Path,
) -> None:
    crawler = _calendar_crawler(tmp_path)
    spider = OutlookCalendarDeltaSpider.from_crawler(
        crawler,
        start_datetime="2026-09-27T00:00:00+10:00",
        end_datetime="2026-10-04T00:00:00+10:00",
    )
    requests = [
        spider._initial_delta_request(reset_count=0),
        spider._delta_request(
            "https://graph.microsoft.com/v1.0/me/calendarView/delta?$skiptoken=opaque",
            page_number=2,
            from_checkpoint=False,
            reset_count=0,
        ),
    ]

    for request in requests:
        serialized = request.to_dict(spider=spider)
        restored = request_from_dict(
            pickle.loads(pickle.dumps(serialized, protocol=4)),
            spider=spider,
        )
        if restored.url != request.url:
            pytest.fail("Expected Calendar delta URL to survive serialization")
        if restored.cb_kwargs != request.cb_kwargs:
            pytest.fail(
                "Expected Calendar delta callback state to survive serialization"
            )
        if restored.meta != request.meta:
            pytest.fail("Expected Calendar delta meta to survive serialization")
        if restored.callback != request.callback:
            pytest.fail("Expected Calendar delta callback to survive serialization")
        if restored.errback != request.errback:
            pytest.fail("Expected Calendar delta errback to survive serialization")


def test_calendar_state_validates_during_open_and_preserves_rejected_job(
    tmp_path: Path,
) -> None:
    crawler1 = _calendar_crawler(tmp_path)
    spider1 = OutlookCalendarDeltaSpider.from_crawler(
        crawler1,
        start_datetime="2026-09-27T00:00:00+10:00",
        end_datetime="2026-10-04T00:00:00+10:00",
    )
    state1 = build_from_crawler(CalendarDeltaSpiderState, crawler1)
    state1.spider_opened(spider1)
    spider1._delta_start_scheduled = True
    spider1._persist_execution_state()
    state1.spider_closed(spider1)
    saved = (tmp_path / "calendar-job" / "spider.state").read_bytes()

    crawler2 = _calendar_crawler(tmp_path)
    spider2 = OutlookCalendarDeltaSpider.from_crawler(
        crawler2,
        start_datetime="2026-09-28T00:00:00+10:00",
        end_datetime="2026-10-05T00:00:00+10:00",
    )
    state2 = build_from_crawler(CalendarDeltaSpiderState, crawler2)
    with pytest.raises(CloseSpider):
        state2.spider_opened(spider2)
    state2.spider_closed(spider2)
    if not spider2.run_failed:
        pytest.fail("Rejected Calendar scope must report failure")
    if (tmp_path / "calendar-job" / "spider.state").read_bytes() != saved:
        pytest.fail("Rejected startup must leave execution state intact")
