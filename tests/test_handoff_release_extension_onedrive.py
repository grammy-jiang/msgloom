"""Prove OneDrive completion through awaited evidence and provider writes."""

import asyncio
import json
from typing import Any, cast

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
from message_ingest.items.microsoft.onedrive import OneDriveItem
from message_ingest.pipelines.evidence import RawEvidencePipeline
from message_ingest.pipelines.microsoft.onedrive import OneDrivePipeline
from message_ingest.spiders.microsoft.onedrive.content import (
    MicrosoftOneDriveContentSpider,
)
from message_ingest.spiders.microsoft.onedrive.discover import (
    MicrosoftOneDriveDiscoverSpider,
)


@pytest.fixture(params=["discover", "content"])
def case(tmp_path, request):
    cls = (
        MicrosoftOneDriveContentSpider
        if request.param == "content"
        else MicrosoftOneDriveDiscoverSpider
    )
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
    spider = cls.from_crawler(
        crawler,
        **({"item_ids": '["one", "two"]'} if request.param == "content" else {}),
    )
    crawler.spider = spider
    spider.run_id = "run"
    service = CatalogService.from_crawler(crawler)
    yield crawler, spider, service
    service.close()


def extension(case):
    try:
        return HandoffReleaseExtension.from_crawler(case[0])
    except NotConfigured:
        pytest.fail("OneDrive has no native-idle release support")


def persist(case, output):
    pipelines = [
        RawEvidencePipeline.from_crawler(case[0]),
        EvidenceLinkPipeline.from_crawler(case[0]),
        OneDrivePipeline.from_crawler(case[0]),
    ]

    async def write():
        for item in output:
            if isinstance(item, Request):
                continue
            for pipeline in pipelines:
                item = await pipeline.process_item(item)

    asyncio.run(write())


def response(spider, callback, payload, purpose, **kwargs):
    request = spider._request(
        "/me/drive", callback=callback, purpose=purpose, cb_kwargs=kwargs
    )
    return TextResponse(
        request.url,
        request=request,
        body=json.dumps(payload).encode(),
        encoding="utf-8",
        headers={"ETag": '"v1"'},
    )


def acquire(case, *, complete=True, linked=True):
    _, spider, _ = case
    if spider.name.endswith("discover"):
        drive = response(spider, spider.parse_drive, {"id": "drive"}, "onedrive-drive")
        persist(
            case, spider.parse_drive(drive, **cast(Request, drive.request).cb_kwargs)
        )
        payload: dict[str, Any] = {"value": [{"id": "one", "eTag": '"v1"'}]}
        if not complete:
            payload["@odata.nextLink"] = "https://graph.microsoft.com/v1.0/next"
        page = response(
            spider, spider.parse_children, payload, "onedrive-root-children-page"
        )
        persist(
            case, spider.parse_children(page, **cast(Request, page.request).cb_kwargs)
        )
        return
    metadata = response(
        spider,
        spider.parse_content,
        {"id": "one", "eTag": '"v1"'},
        "onedrive-root-children-page",
    )
    evidence = spider._raw_http_evidence_item(metadata, "onedrive-root-children-page")
    persist(
        case,
        [
            evidence,
            OneDriveItem.from_graph(
                metadata.json(),
                observed_at=evidence.observed_at,
                evidence_id=evidence.evidence_id,
                run_id=spider.run_id,
            ),
        ],
    )
    page = response(
        spider,
        spider.parse_content,
        {"bytes": "payload"},
        "onedrive-content",
        item_id="one",
        planned_metadata_observed_at=evidence.observed_at,
        planned_metadata_evidence_id=evidence.evidence_id,
        planned_e_tag='"v1"' if linked else '"wrong"',
        planned_c_tag=None,
    )
    persist(case, spider.parse_content(page, **cast(Request, page.request).cb_kwargs))


def groups(case):
    with case[2].catalog.Session() as session:
        return [
            json.loads(row)
            for row in session.scalars(select(AcquisitionReleaseGroup.payload)).all()
        ]


def test_completed_subject_releases_once(case):
    ext = extension(case)
    acquire(case)
    ext.spider_idle(case[1])
    first = groups(case)
    expected = "content_capture" if case[1].name.endswith("content") else "resource_set"
    if len(first) != 1 or first[0]["release_kind"] != expected:
        pytest.fail("Completed OneDrive subject did not publish the expected group")
    ext.spider_idle(case[1])
    if groups(case) != first:
        pytest.fail("Repeated idle changed immutable release")


def test_incomplete_subject_cannot_release(case):
    ext = extension(case)
    acquire(case, complete=False, linked=False)
    ext.spider_idle(case[1])
    if groups(case):
        pytest.fail("Incomplete inventory or unlinked content was released")


def test_invalid_canonical_evidence_cannot_release(case):
    ext = extension(case)
    acquire(case)
    with case[2].catalog.writer_session() as writer:
        for row in writer.scalars(select(RawHttpEvidence)):
            row.response_status = 503
    ext.spider_idle(case[1])
    if groups(case):
        pytest.fail("Invalid canonical evidence authorized release")


def test_target_failure_blocks_only_owned_content(case):
    ext = extension(case)
    acquire(case)
    ext.item_error(type("FailedItem", (), {"item_id": "two"})())
    case[1].mark_run_failed("item_error")
    ext.spider_idle(case[1])
    expected = 1 if case[1].name.endswith("content") else 0
    if len(groups(case)) != expected:
        pytest.fail("Target failure lost independent content or released inventory")


def test_callback_failure_blocks_completed_target(case):
    ext = extension(case)
    acquire(case)
    request = Request(
        "https://graph.microsoft.com/v1.0/me", cb_kwargs={"item_id": "one"}
    )
    ext.spider_error(TextResponse(request.url, request=request))
    case[1].mark_run_failed("spider_error")
    ext.spider_idle(case[1])
    if groups(case):
        pytest.fail("Callback failure released its target")


def test_changed_target_scope_cannot_release(case):
    ext = extension(case)
    acquire(case)
    if case[1].name.endswith("discover"):
        case[1].page_size += 1
    else:
        case[1].item_ids = ("other",)
    ext.spider_idle(case[1])
    if groups(case):
        pytest.fail("Completion crossed its bound source target scope")


def test_equivalent_retry_recovers_unreleased_subject(case):
    acquire(case)
    case[1].run_id = "retry"
    acquire(case)
    ext = extension(case)
    ext.spider_idle(case[1])
    if len(groups(case)) != 1 or groups(case)[0]["owner_run_id"] != "retry":
        pytest.fail("Logical retry did not recover canonical persisted state")
