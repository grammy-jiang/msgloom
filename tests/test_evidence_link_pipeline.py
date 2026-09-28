"""Verify provider-independent evidence linking before resource persistence."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
from scrapy.pipelines import ItemPipelineManager
from scrapy.utils.test import get_crawler

import message_ingest.settings as project_settings
from message_ingest.acquisition.contracts import EvidenceLinkedItem
from message_ingest.acquisition.evidence_link import EvidenceLinkPipeline
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.acquisition import RawHttpEvidenceItem
from message_ingest.pipelines.evidence import RawEvidencePipeline


@dataclass(slots=True)
class CalendarEventFixture:
    """Non-Mail resource item satisfying only the acquisition evidence contract."""

    event_id: str
    evidence_id: str | None
    observed_at: str


def _crawler(tmp_path: Path):
    return get_crawler(
        settings_dict={
            "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
            "MSGLOOM_SOURCE_ID": "source-1",
        }
    )


def _raw(
    evidence_id: str,
    *,
    origin: str = "network",
    observed_at: str = "2026-09-27T00:00:00+00:00",
) -> RawHttpEvidenceItem:
    return RawHttpEvidenceItem(
        evidence_id=evidence_id,
        run_id="run-1",
        purpose="calendar.event-list",
        observed_at=observed_at,
        origin=origin,
        request_fingerprint="calendar-fp",
        request_url="https://graph.microsoft.com/v1.0/me/events",
        request_method="GET",
        request_headers={"Accept": ["application/json"]},
        request_body=b"",
        response_url="https://graph.microsoft.com/v1.0/me/events",
        response_status=200,
        response_headers={"Content-Type": ["application/json"]},
        response_body=b'{"value":[]}',
        response_flags=["cached"] if origin == "http_cache" else [],
    )


def test_non_mail_item_satisfies_evidence_contract_and_links(tmp_path: Path) -> None:
    crawler = _crawler(tmp_path)
    raw_pipeline = RawEvidencePipeline.from_crawler(crawler)
    link_pipeline = EvidenceLinkPipeline.from_crawler(crawler)
    raw = _raw("ev-1")
    item = CalendarEventFixture(
        event_id="calendar-event-1",
        evidence_id="ev-1",
        observed_at=raw.observed_at,
    )

    if not isinstance(item, EvidenceLinkedItem):
        pytest.fail("Expected structural EvidenceLinkedItem contract")

    asyncio.run(raw_pipeline.process_item(raw))
    returned = asyncio.run(link_pipeline.process_item(item))

    if returned is not item:
        pytest.fail("Expected EvidenceLinkPipeline to return the same item")
    if item.evidence_id != raw.evidence_id:
        pytest.fail("Expected non-Mail item evidence reference to remain canonical")
    CatalogService.from_crawler(crawler).spider_closed(None, "test-finished")


def test_cache_alias_rewrites_non_mail_item_id_and_timestamp(tmp_path: Path) -> None:
    crawler = _crawler(tmp_path)
    raw_pipeline = RawEvidencePipeline.from_crawler(crawler)
    link_pipeline = EvidenceLinkPipeline.from_crawler(crawler)

    original = _raw(
        "network-evidence",
        observed_at="2026-09-27T00:00:00+00:00",
    )
    asyncio.run(raw_pipeline.process_item(original))

    replay = _raw(
        "cache-provisional",
        origin="http_cache",
        observed_at="2026-09-27T01:00:00+00:00",
    )
    item = CalendarEventFixture(
        event_id="calendar-event-1",
        evidence_id="cache-provisional",
        observed_at=replay.observed_at,
    )
    asyncio.run(raw_pipeline.process_item(replay))
    asyncio.run(link_pipeline.process_item(item))

    if item.evidence_id != original.evidence_id:
        pytest.fail("Expected cache alias to resolve to original evidence ID")
    if item.observed_at != original.observed_at:
        pytest.fail("Expected cache alias to restore original observation time")
    CatalogService.from_crawler(crawler).spider_closed(None, "test-finished")


def test_non_evidence_item_passes_through_without_catalog_lookup(
    tmp_path: Path,
    monkeypatch,
) -> None:
    crawler = _crawler(tmp_path)
    pipeline = EvidenceLinkPipeline.from_crawler(crawler)
    item = {"plain": "item"}

    def unexpected_lookup(*_args, **_kwargs):
        pytest.fail("Expected no catalog lookup for a non-evidence item")

    monkeypatch.setattr(
        pipeline.catalog.evidence,
        "contains",
        unexpected_lookup,
    )
    if asyncio.run(pipeline.process_item(item)) is not item:
        pytest.fail("Expected non-evidence item to pass through unchanged")
    CatalogService.from_crawler(crawler).spider_closed(None, "test-finished")


def test_none_evidence_reference_is_valid_for_terminal_semantics(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path)
    pipeline = EvidenceLinkPipeline.from_crawler(crawler)
    item = CalendarEventFixture(
        event_id="calendar-event-1",
        evidence_id=None,
        observed_at="2026-09-27T00:00:00+00:00",
    )

    if asyncio.run(pipeline.process_item(item)) is not item:
        pytest.fail("Expected item with no evidence reference to pass through")
    if item.evidence_id is not None:
        pytest.fail("Expected: item.evidence_id is None")
    CatalogService.from_crawler(crawler).spider_closed(None, "test-finished")


ROOT = Path(__file__).parents[1]

FEED_RUN = r"""
import sys
from dataclasses import dataclass

from scrapy import Request, Spider
from scrapy.crawler import CrawlerProcess

import message_ingest.settings as project_settings
from message_ingest.items.acquisition import RawHttpEvidenceItem


@dataclass(slots=True)
class CalendarEvent:
    event_id: str
    evidence_id: str | None
    observed_at: str


def raw(evidence_id, *, origin="network", observed_at="2026-09-27T00:00:00+00:00"):
    return RawHttpEvidenceItem(
        evidence_id=evidence_id,
        run_id="feed-run",
        purpose="calendar.event-list",
        observed_at=observed_at,
        origin=origin,
        request_fingerprint="feed-fingerprint",
        request_url="https://graph.microsoft.com/v1.0/me/events",
        request_method="GET",
        request_headers={"Accept": ["application/json"]},
        request_body=b"",
        response_url="https://graph.microsoft.com/v1.0/me/events",
        response_status=200,
        response_headers={"Content-Type": ["application/json"]},
        response_body=b'{"value":[]}',
        response_flags=["cached"] if origin == "http_cache" else [],
    )


class ProbeSpider(Spider):
    name = "evidence_link_feed_probe"

    async def start(self):
        yield Request(
            "data:text/plain,probe",
            callback=self.parse_probe,
            dont_filter=True,
        )

    def parse_probe(self, response):
        yield raw(
            "original",
            observed_at="2026-09-27T00:00:00+00:00",
        )
        yield raw(
            "replay",
            origin="http_cache",
            observed_at="2026-09-27T01:00:00+00:00",
        )
        yield CalendarEvent(
            "event-1",
            "replay",
            "2026-09-27T01:00:00+00:00",
        )
        yield {"plain": "item"}
        yield CalendarEvent(
            "broken",
            "missing",
            "2026-09-27T01:00:00+00:00",
        )


feed_path, database_url, raw_dir = sys.argv[1:4]
process = CrawlerProcess(
    {
        "ITEM_PIPELINES": project_settings.ITEM_PIPELINES,
        "MSGLOOM_CATALOG_ENABLED": True,
        "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
        "MSGLOOM_DATABASE_URL": database_url,
        "MSGLOOM_RAW_EVIDENCE_DIR": raw_dir,
        "MSGLOOM_SOURCE_ID": "feed-source",
        "CONCURRENT_ITEMS": 1,
        "LOG_ENABLED": False,
        "TELNETCONSOLE_ENABLED": False,
        "REMOTE_CONTROL_ENABLED": False,
        "FEEDS": {
            feed_path: {
                "format": "jsonlines",
                "item_classes": [CalendarEvent, dict],
            }
        },
    }
)
process.crawl(ProbeSpider)
process.start()
"""


def test_feed_export_sees_only_successful_canonicalized_items(
    tmp_path: Path,
) -> None:
    feed_path = tmp_path / "feed.jsonl"
    database_url = f"sqlite:///{tmp_path / 'catalog.sqlite3'}"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            FEED_RUN,
            str(feed_path),
            database_url,
            str(tmp_path / "raw"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(result.stdout + result.stderr)

    rows = [
        json.loads(line) for line in feed_path.read_text().splitlines() if line.strip()
    ]
    if rows != [
        {
            "event_id": "event-1",
            "evidence_id": "original",
            "observed_at": "2026-09-27T00:00:00+00:00",
        },
        {"plain": "item"},
    ]:
        pytest.fail(f"Unexpected exported acquisition items: {rows!r}")


def test_catalog_disabled_skips_all_persistence_stages() -> None:
    crawler = get_crawler(
        settings_dict={
            "ITEM_PIPELINES": project_settings.ITEM_PIPELINES,
            "MSGLOOM_CATALOG_ENABLED": False,
            "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
        }
    )
    manager = ItemPipelineManager.from_crawler(crawler)

    if manager.middlewares:
        pytest.fail("Expected all catalog-backed pipelines to be disabled")
    if hasattr(crawler, "_msgloom_catalog_service"):
        pytest.fail("Expected disabled pipelines not to create CatalogService")
