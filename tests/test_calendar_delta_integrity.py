"""Verify Calendar delta idle-time checkpoint safety."""

from __future__ import annotations

from pathlib import Path

import pytest
from scrapy.exceptions import CloseSpider
from scrapy.utils.test import get_crawler

from message_ingest.calendar_checkpoints import CalendarDeltaCheckpointStore
from message_ingest.extensions.calendar_delta_checkpoint import (
    CalendarDeltaCheckpointExtension,
)
from message_ingest.extensions.catalog import CatalogService
from message_ingest.spiders.outlook_calendar_delta import OutlookCalendarDeltaSpider

START = "2026-09-27T00:00:00+10:00"
END = "2026-10-04T00:00:00+10:00"


def _setup(tmp_path: Path):
    crawler = get_crawler(
        OutlookCalendarDeltaSpider,
        settings_dict={
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_SOURCE_ID": "source-1",
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_SOURCE_IDENTITY_REQUIRED": False,
        },
    )
    spider = OutlookCalendarDeltaSpider.from_crawler(
        crawler,
        start_datetime=START,
        end_datetime=END,
    )
    crawler.spider = spider
    extension = CalendarDeltaCheckpointExtension.from_crawler(crawler)
    store = CalendarDeltaCheckpointStore.from_crawler(
        crawler,
        start_datetime=START,
        end_datetime=END,
    )
    return crawler, spider, extension, store


def _candidate(spider, store) -> None:
    store.write_candidate(
        run_id=spider.run_id,
        attempt=spider.attempt,
        base_revision=spider.base_revision,
        delta_link="https://graph.microsoft.com/v1.0/me/calendarView/delta?$deltatoken=done",
        evidence_id="evidence-1",
        observed_at="2026-09-27T00:00:00+00:00",
    )


def test_successful_idle_promotes_exact_candidate(tmp_path: Path) -> None:
    crawler, spider, extension, store = _setup(tmp_path)
    spider._terminal_delta_seen = True
    _candidate(spider, store)

    extension.spider_idle(spider)

    state = store.get_checkpoint()
    if state is None or state.revision != 1:
        pytest.fail("Expected Calendar delta checkpoint revision one")
    if crawler.stats.get_value("msgloom/calendar/checkpoint/outcome") != "committed":
        pytest.fail("Expected committed Calendar checkpoint outcome")
    CatalogService.from_crawler(crawler).close()


def test_missing_candidate_blocks_promotion(tmp_path: Path) -> None:
    crawler, spider, extension, store = _setup(tmp_path)
    spider._terminal_delta_seen = True

    with pytest.raises(CloseSpider) as excinfo:
        extension.spider_idle(spider)

    if excinfo.value.reason != "calendar_delta_incomplete":
        pytest.fail(f"Unexpected close reason: {excinfo.value.reason}")
    if store.get_checkpoint() is not None:
        pytest.fail("Expected no Calendar checkpoint after incomplete round")
    if not spider.run_failed:
        pytest.fail("Expected incomplete Calendar delta round to fail integrity")
    CatalogService.from_crawler(crawler).close()


def test_item_error_blocks_candidate_promotion(tmp_path: Path) -> None:
    crawler, spider, extension, store = _setup(tmp_path)
    spider._terminal_delta_seen = True
    _candidate(spider, store)
    extension.item_error(spider)

    with pytest.raises(CloseSpider):
        extension.spider_idle(spider)

    if store.get_checkpoint() is not None:
        pytest.fail("Expected item error to block Calendar checkpoint promotion")
    CatalogService.from_crawler(crawler).close()
