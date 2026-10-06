"""Verify Mail discovery scope release through real callbacks and stores."""

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
from message_ingest.acquisition.handoff import AcquisitionStream
from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.models.handoff import AcquisitionReleaseGroup
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.extensions.catalog import CatalogService
from message_ingest.extensions.handoff import HandoffReleaseExtension
from message_ingest.pipelines.evidence import RawEvidencePipeline
from message_ingest.pipelines.microsoft.outlook.email import OutlookMailPipeline
from message_ingest.spiders.microsoft.outlook.email.discover import (
    OutlookDiscoverSpider,
)


@pytest.fixture
def mail_case(tmp_path):
    crawler = Crawler(
        OutlookDiscoverSpider,
        Settings(
            {
                "MSGLOOM_CATALOG_ENABLED": True,
                "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
                "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.db'}",
                "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
                "MSGLOOM_TARGET_MAILBOX": "shared@example.test",
            }
        ),
    )
    crawler.settings.set("MSGLOOM_SOURCE_ID", "source", priority="cmdline")
    crawler.stats = MemoryStatsCollector(crawler)
    crawler.request_fingerprinter = RequestFingerprinter(crawler)
    spider = OutlookDiscoverSpider.from_crawler(crawler, folder="inbox", max_pages="1")
    crawler.spider = spider
    spider.run_id = "run"
    service = CatalogService.from_crawler(crawler)
    yield crawler, spider, service
    service.close()


def extension(crawler):
    try:
        return HandoffReleaseExtension.from_crawler(crawler)
    except NotConfigured:
        pytest.fail("Mail discovery has no natural-idle release support")


def parse_page(case, *, next_link=False, cached=False):
    crawler, spider, _ = case
    payload = {"value": [{"id": "one", "subject": "A message"}]}
    if next_link:
        payload["@odata.nextLink"] = "https://graph.microsoft.com/v1.0/me/messages?p=2"
    request = spider._message_list_request(
        "https://graph.microsoft.com/v1.0/users/shared%40example.test/mailFolders/inbox/messages",
        page_number=1,
    )
    response = TextResponse(
        request.url,
        request=request,
        body=json.dumps(payload).encode(),
        encoding="utf-8",
        flags=["cached"] if cached else [],
    )
    pipelines = (
        RawEvidencePipeline.from_crawler(crawler),
        EvidenceLinkPipeline.from_crawler(crawler),
        OutlookMailPipeline.from_crawler(crawler),
    )

    async def persist():
        for item in spider.parse(response):
            if isinstance(item, Request):
                continue
            for pipeline in pipelines:
                item = await pipeline.process_item(item)

    asyncio.run(persist())


def releases(case):
    return AcquisitionHandoffStore(case[2].catalog).list_release_entries(
        "source", AcquisitionStream.OUTLOOK_MAIL
    )


@pytest.mark.parametrize("truncated", [False, True])
def test_mail_discovery_releases_exact_scope_once(mail_case, truncated):
    crawler, spider, service = mail_case
    parse_page(mail_case, next_link=truncated)
    extension(crawler).spider_idle(spider)
    extension(crawler).spider_idle(spider)
    entries = releases(mail_case)
    if len(entries) != 2 or {
        json.loads(row["payload"])["entry_kind"] for row in entries
    } != {"resource", "component"}:
        pytest.fail("Completed Mail discovery did not release its positive message")
    with service.catalog.Session() as session:
        groups = session.scalars(select(AcquisitionReleaseGroup.payload)).all()
    if len(groups) != 1:
        pytest.fail("Mail discovery did not publish one idempotent group")
    group = json.loads(groups[0])
    if group["coverage_kind"] != ("truncated" if truncated else "complete"):
        pytest.fail("Mail discovery lost explicit truncation coverage")
    scope = json.loads(group["scope_identity"])
    if scope["mailbox"] != "shared@example.test" or scope["folder"] != "inbox":
        pytest.fail("Mail discovery lost its exact configured scope")
    if scope["max_pages"] != 1 or scope["page_size"] != 25:
        pytest.fail("Mail discovery lost configured traversal policy")
    if not scope["policy_digest"] or scope["policy_enabled"] is not False:
        pytest.fail("Mail discovery lost effective acquisition policy")
    if group["release_kind"] != "resource_set" or group["authority_revision"]:
        pytest.fail("Positive discovery acquired absence authority")


@pytest.mark.parametrize(
    "damage", ["unfinished", "callback", "item", "scope", "evidence"]
)
def test_mail_discovery_rejects_incomplete_or_failed_scope(mail_case, damage):
    crawler, spider, service = mail_case
    if damage == "unfinished":
        spider.max_pages = 0
    parse_page(mail_case, next_link=damage == "unfinished")
    release = extension(crawler)
    if damage == "callback":
        release.spider_error()
    elif damage == "item":
        release.item_error(object())
    elif damage == "scope":
        spider.folder = "other"
    elif damage == "evidence":
        with service.catalog.writer_session() as writer:
            row = writer.scalar(select(RawHttpEvidence))
            row.response_status = 500
    release.spider_idle(spider)
    if releases(mail_case):
        pytest.fail("Invalid Mail traversal released positive data")


def test_mail_cache_completion_retains_original_capture(mail_case):
    crawler, spider, service = mail_case
    parse_page(mail_case)
    spider.run_id = "replay"
    parse_page(mail_case, cached=True)
    extension(crawler).spider_idle(spider)
    if len(releases(mail_case)) != 2:
        pytest.fail("Cached Mail completion did not recover unreleased state")
    with service.catalog.Session() as session:
        evidence = session.scalars(select(RawHttpEvidence)).all()
        group = json.loads(session.scalar(select(AcquisitionReleaseGroup.payload)))
    if len(evidence) != 1 or evidence[0].run_id != "run":
        pytest.fail("Cache replay changed canonical capture ownership")
    if group["owner_run_id"] != "replay":
        pytest.fail("Mail discovery release lost its logical run")
