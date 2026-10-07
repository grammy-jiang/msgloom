"""Exercise Full release through native signals and real catalog fixtures."""

import importlib.util

import pytest
from _full_completion_fixtures import seed_target
from scrapy import signals
from scrapy.crawler import Crawler
from scrapy.settings import Settings
from scrapy.statscollectors import MemoryStatsCollector

from message_ingest.acquisition.handoff import AcquisitionStream
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.extensions.catalog import CatalogService
from message_ingest.spiders.microsoft.outlook.calendar.full import (
    OutlookCalendarFullSpider,
)
from message_ingest.spiders.microsoft.outlook.email.full import OutlookFullSpider


@pytest.fixture(params=["mail", "calendar"])
def release_case(request, tmp_path):
    """Use production Spider identities, signals, catalog, and profile proof."""
    name = "message_ingest.extensions.handoff"
    if importlib.util.find_spec(name) is None:
        pytest.skip("Full natural-idle release extension is not implemented")
    from message_ingest.extensions.handoff import HandoffReleaseExtension

    family = request.param
    cls = OutlookFullSpider if family == "mail" else OutlookCalendarFullSpider
    crawler = Crawler(
        cls,
        Settings(
            {
                "MSGLOOM_CATALOG_ENABLED": True,
                "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
                "MSGLOOM_SOURCE_ID": "source",
                "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.db'}",
            }
        ),
    )
    crawler.stats = MemoryStatsCollector(crawler)
    kwargs = {"message_ids" if family == "mail" else "event_ids": "one,two"}
    spider = cls.from_crawler(crawler, **kwargs)
    spider.run_id = "run"
    crawler.spider = spider
    service = CatalogService.from_crawler(crawler)
    extension = HandoffReleaseExtension.from_crawler(crawler)
    seed_target(service.catalog, family)
    stream = (
        AcquisitionStream.OUTLOOK_MAIL
        if family == "mail"
        else AcquisitionStream.OUTLOOK_CALENDAR
    )
    yield crawler, spider, service, extension, stream
    service.close()


def entries(case):
    return AcquisitionHandoffStore(case[2].catalog).list_release_entries(
        "source", case[4]
    )


def test_closed_signal_never_publishes(release_case):
    crawler, spider, *_ = release_case
    crawler.signals.send_catch_log(
        signal=signals.spider_closed, spider=spider, reason="finished"
    )
    if entries(release_case):
        pytest.fail("Closing published without native idle")


def test_idle_releases_only_complete_target_once(release_case):
    crawler, spider, *_ = release_case
    spider.mark_run_failed("request_failure:second-target")
    for _ in range(2):
        crawler.signals.send_catch_log(signal=signals.spider_idle, spider=spider)
    rows = entries(release_case)
    if len(rows) != 1 or '"resource_identity":"one"' not in rows[0]["payload"]:
        pytest.fail(f"Expected exactly one independently complete target: {rows}")


def test_unknown_item_error_blocks_publication(release_case):
    crawler, spider, *_ = release_case
    crawler.signals.send_catch_log(
        signal=signals.item_error, spider=spider, item=object()
    )
    crawler.signals.send_catch_log(signal=signals.spider_idle, spider=spider)
    if entries(release_case):
        pytest.fail("Unattributed item failure allowed publication")


def test_busy_writer_blocks_publication(release_case):
    import asyncio

    crawler, spider, service, *_ = release_case
    asyncio.run(service.write_lock.acquire())
    try:
        crawler.signals.send_catch_log(signal=signals.spider_idle, spider=spider)
        if entries(release_case):
            pytest.fail("Busy writer allowed publication")
    finally:
        service.write_lock.release()


def test_full_idle_extension_exists():
    if importlib.util.find_spec("message_ingest.extensions.handoff") is None:
        pytest.fail("Full natural-idle release extension is not implemented")
