"""Verify Calendar persistence through the native item-pipeline stages."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from sqlalchemy import func, select
from scrapy.utils.test import get_crawler

from message_ingest.acquisition.evidence_link import EvidenceLinkPipeline
from message_ingest.catalog import CalendarEventObservation
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items import OutlookCalendarEventItem, RawHttpEvidenceItem
from message_ingest.pipelines.calendar import CalendarPipeline
from message_ingest.pipelines.evidence import RawEvidencePipeline
from message_ingest.spiders.outlook_calendar import OutlookCalendarSpider


def _crawler(tmp_path: Path, *, source_id: str = "source-1"):
    return get_crawler(
        OutlookCalendarSpider,
        settings_dict={
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
            "MSGLOOM_SOURCE_ID": source_id,
            "MSGLOOM_SOURCE_IDENTITY_REQUIRED": False,
        },
    )


def _raw(
    evidence_id: str,
    *,
    origin: str = "network",
    observed_at: str = "2026-09-27T00:00:00+00:00",
) -> RawHttpEvidenceItem:
    return RawHttpEvidenceItem(
        evidence_id=evidence_id,
        run_id="calendar-run",
        purpose="calendar-event-page",
        observed_at=observed_at,
        origin=origin,
        request_fingerprint="c" * 64,
        request_url="https://graph.microsoft.com/v1.0/me/calendar/events",
        request_method="GET",
        request_headers={"Accept": ["application/json"]},
        request_body=b"",
        response_url="https://graph.microsoft.com/v1.0/me/calendar/events",
        response_status=200,
        response_headers={"Content-Type": ["application/json"]},
        response_body=b'{"value":[{"id":"event-1"}]}',
        response_flags=["cached"] if origin == "http_cache" else [],
    )


def _event(
    evidence_id: str,
    observed_at: str,
) -> OutlookCalendarEventItem:
    return OutlookCalendarEventItem(
        event_id="event-1",
        raw={
            "id": "event-1",
            "subject": "Planning",
            "start": {
                "dateTime": "2026-09-27T09:00:00",
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": "2026-09-27T10:00:00",
                "timeZone": "UTC",
            },
            "type": "singleInstance",
        },
        observed_at=observed_at,
        evidence_id=evidence_id,
        run_id="calendar-run",
    )


def test_calendar_pipeline_persists_canonical_event_observation(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path)
    raw_pipeline = RawEvidencePipeline.from_crawler(crawler)
    link_pipeline = EvidenceLinkPipeline.from_crawler(crawler)
    calendar_pipeline = CalendarPipeline.from_crawler(crawler)
    raw = _raw("evidence-original")
    event = _event(raw.evidence_id, raw.observed_at)

    asyncio.run(raw_pipeline.process_item(raw))
    asyncio.run(link_pipeline.process_item(event))
    asyncio.run(calendar_pipeline.process_item(event))

    service = CatalogService.from_crawler(crawler)
    with service.catalog.Session() as session:
        row = session.scalar(select(CalendarEventObservation))
        if row is None:
            pytest.fail("Expected Calendar event observation")
        if row.source_id != "source-1" or row.event_id != "event-1":
            pytest.fail("Expected source-scoped Calendar identity")
        if row.evidence_id != "evidence-original":
            pytest.fail("Expected persisted canonical evidence identity")
        if row.subject != "Planning" or row.event_type != "singleInstance":
            pytest.fail("Expected Calendar semantic projections")
        if row.start != event.raw["start"] or row.end != event.raw["end"]:
            pytest.fail("Expected Graph date/time objects to remain unchanged")
        if row.raw != event.raw:
            pytest.fail("Expected raw event JSON to remain available")
    service.close()


def test_calendar_cache_replay_deduplicates_same_event_observation(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path)
    raw_pipeline = RawEvidencePipeline.from_crawler(crawler)
    link_pipeline = EvidenceLinkPipeline.from_crawler(crawler)
    calendar_pipeline = CalendarPipeline.from_crawler(crawler)

    original = _raw(
        "evidence-original",
        observed_at="2026-09-27T00:00:00+00:00",
    )
    asyncio.run(raw_pipeline.process_item(original))
    first = _event(original.evidence_id, original.observed_at)
    asyncio.run(link_pipeline.process_item(first))
    asyncio.run(calendar_pipeline.process_item(first))

    replay = _raw(
        "evidence-replay",
        origin="http_cache",
        observed_at="2026-09-27T01:00:00+00:00",
    )
    asyncio.run(raw_pipeline.process_item(replay))
    second = _event("evidence-replay", replay.observed_at)
    asyncio.run(link_pipeline.process_item(second))
    asyncio.run(calendar_pipeline.process_item(second))

    if second.evidence_id != original.evidence_id:
        pytest.fail("Expected cache replay to resolve original evidence ID")
    if second.observed_at != original.observed_at:
        pytest.fail("Expected cache replay to restore capture timestamp")

    service = CatalogService.from_crawler(crawler)
    with service.catalog.Session() as session:
        count = session.scalar(
            select(func.count()).select_from(CalendarEventObservation)
        )
        if count != 1:
            pytest.fail(f"Expected one deduplicated Calendar observation, got {count}")
    if crawler.stats.get_value(
        "msgloom/calendar/event_observation_replay_count"
    ) != 1:
        pytest.fail("Expected Calendar replay counter")
    service.close()


def test_calendar_pipeline_passes_other_resource_items_through(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path)
    pipeline = CalendarPipeline.from_crawler(crawler)
    item = {"mail": "or future resource"}

    returned = asyncio.run(pipeline.process_item(item))

    if returned is not item:
        pytest.fail("Expected non-Calendar item to pass through unchanged")
    CatalogService.from_crawler(crawler).close()
