"""Verify exact Calendar traversal proof and durable window completion."""

import asyncio
import json

import pytest
from scrapy import Request
from scrapy.crawler import Crawler
from scrapy.exceptions import NotConfigured
from scrapy.http import TextResponse
from scrapy.settings import Settings
from scrapy.statscollectors import MemoryStatsCollector
from scrapy.utils.request import RequestFingerprinter
from sqlalchemy import select

from message_ingest.acquisition.evidence_link import EvidenceLinkPipeline
from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.models.handoff import AcquisitionReleaseGroup
from message_ingest.extensions.catalog import CatalogService
from message_ingest.extensions.handoff import HandoffReleaseExtension
from message_ingest.pipelines.evidence import RawEvidencePipeline
from message_ingest.pipelines.microsoft.outlook.calendar import OutlookCalendarPipeline
from message_ingest.spiders.microsoft.outlook.calendar.discover import (
    OutlookCalendarDiscoverSpider,
)
from message_ingest.spiders.microsoft.outlook.calendar.window import (
    OutlookCalendarWindowSpider,
)


@pytest.fixture(params=["discover", "window"])
def case(tmp_path, request):
    window = request.param == "window"
    cls = OutlookCalendarWindowSpider if window else OutlookCalendarDiscoverSpider
    crawler = Crawler(
        cls,
        Settings(
            {
                "MSGLOOM_CATALOG_ENABLED": True,
                "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
                "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.db'}",
                "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
            }
        ),
    )
    crawler.settings.set("MSGLOOM_SOURCE_ID", "source", priority="cmdline")
    crawler.stats = MemoryStatsCollector(crawler)
    crawler.request_fingerprinter = RequestFingerprinter(crawler)
    args = (
        {
            "start_datetime": "2026-09-27T00:00:00Z",
            "end_datetime": "2026-10-04T00:00:00Z",
        }
        if window
        else {}
    )
    spider = cls.from_crawler(crawler, **args)
    crawler.spider = spider
    spider.run_id = "run"
    service = CatalogService.from_crawler(crawler)
    yield crawler, spider, service
    service.close()


def extension(crawler):
    try:
        return HandoffReleaseExtension.from_crawler(crawler)
    except NotConfigured:
        pytest.fail("Calendar traversal has no native-idle release support")


def parse_page(case, *, unfinished=False, cached=False, label="one"):
    crawler, spider, _ = case
    window = spider.name == "outlook_calendar_window"
    callback = spider.parse_events if window else spider.parse_calendars
    purpose = "calendar-window-page" if window else "calendar-inventory-page"
    kwargs = {"calendar_id": "default"} if window else {}
    request = spider._request(
        "https://graph.microsoft.com/v1.0/me/calendars",
        callback=callback,
        purpose=purpose,
        cb_kwargs=kwargs,
    )
    payload = {
        "value": [{"id": "one", "changeKey": label, "subject": label, "name": label}]
    }
    if unfinished:
        payload["@odata.nextLink"] = request.url + "?page=2"
    response = TextResponse(
        request.url,
        request=request,
        body=json.dumps(payload).encode(),
        encoding="utf-8",
        flags=["cached"] if cached else [],
    )
    pipelines = [
        RawEvidencePipeline.from_crawler(crawler),
        EvidenceLinkPipeline.from_crawler(crawler),
        OutlookCalendarPipeline.from_crawler(crawler),
    ]

    async def persist():
        for item in callback(response, **request.cb_kwargs):
            if isinstance(item, Request):
                continue
            for pipeline in pipelines:
                item = await pipeline.process_item(item)

    asyncio.run(persist())


def groups(case):
    with case[2].catalog.Session() as session:
        return [
            json.loads(row)
            for row in session.scalars(select(AcquisitionReleaseGroup.payload)).all()
        ]


def test_calendar_completed_scope_releases_once(case):
    crawler, spider, _ = case
    parse_page(case)
    extension(crawler).spider_idle(spider)
    extension(crawler).spider_idle(spider)
    rows = groups(case)
    if len(rows) != 1:
        pytest.fail("Calendar terminal traversal must release one group")
    group = rows[0]
    scope = json.loads(group["scope_identity"])
    if scope["mailbox"] != "me" or group["owner_run_id"] != "run":
        pytest.fail("Calendar release lost exact mailbox or logical run")
    if group["authority_revision"] or group["coverage_kind"] != "complete":
        pytest.fail("Calendar positive traversal gained absence authority")
    if spider.name.endswith("window") and (
        scope["start_datetime"] != spider.start_datetime
        or scope["end_datetime"] != spider.end_datetime
        or scope["calendar_id"] != "default"
    ):
        pytest.fail("Calendar window release lost its exact scope")


@pytest.mark.parametrize(
    "damage", ["unfinished", "callback", "item", "scope", "evidence"]
)
def test_calendar_failed_or_incomplete_scope_does_not_release(case, damage):
    crawler, spider, service = case
    parse_page(case, unfinished=damage == "unfinished")
    release = extension(crawler)
    if damage == "callback":
        release.spider_error()
    elif damage == "item":
        release.item_error(object())
    elif damage == "scope":
        spider.page_size += 1
    elif damage == "evidence":
        with service.catalog.writer_session() as writer:
            writer.scalar(select(RawHttpEvidence)).response_status = 500
    release.spider_idle(spider)
    if groups(case):
        pytest.fail("Invalid Calendar traversal released a group")


def test_calendar_cached_terminal_keeps_canonical_capture(case):
    crawler, spider, service = case
    parse_page(case)
    spider.run_id = "replay"
    parse_page(case, cached=True)
    extension(crawler).spider_idle(spider)
    if len(groups(case)) != 1 or groups(case)[0]["owner_run_id"] != "replay":
        pytest.fail("Cached terminal evidence did not release current logical run")
    with service.catalog.Session() as session:
        captures = session.scalars(select(RawHttpEvidence)).all()
    if len(captures) != 1 or captures[0].run_id != "run":
        pytest.fail("Cache replay replaced canonical evidence ownership")


def test_window_resume_retains_only_primitive_terminal_proof(case):
    crawler, spider, _ = case
    if spider.name != "outlook_calendar_window":
        return
    parse_page(case)
    # JSON round-trip excludes raw items, callback objects, and payload bytes.
    restored = json.loads(json.dumps(spider.state))
    spider.handoff_completion = None
    spider.state = restored
    spider.run_id = "new-attempt"
    spider._restore_execution_state()
    extension(crawler).spider_idle(spider)
    if len(groups(case)) != 1 or groups(case)[0]["owner_run_id"] != "run":
        pytest.fail("Window terminal proof did not survive durable state restore")


@pytest.mark.parametrize("changed", ["mailbox", "source"])
def test_window_resume_rejects_changed_target_binding(case, changed):
    crawler, spider, _ = case
    if spider.name != "outlook_calendar_window":
        return
    spider._persist_execution_state()
    if changed == "mailbox":
        crawler.settings.set(
            "MSGLOOM_TARGET_MAILBOX", "other@example.test", priority="cmdline"
        )
    else:
        crawler.settings.set("MSGLOOM_SOURCE_ID", "other-source", priority="cmdline")
    with pytest.raises(ValueError, match="different window scope"):
        spider._restore_execution_state()


def test_calendar_completed_replay_ignores_later_state_changes(case):
    crawler, spider, _ = case
    parse_page(case)
    extension(crawler).spider_idle(spider)
    original = groups(case)
    proof = spider.handoff_completion
    spider.run_id = "later"
    parse_page(case, label="changed")
    spider.run_id = "run"
    spider.handoff_completion = proof
    extension(crawler).spider_idle(spider)
    if groups(case) != original or spider.run_failed:
        pytest.fail("Completed Calendar replay must retain immutable publication")
