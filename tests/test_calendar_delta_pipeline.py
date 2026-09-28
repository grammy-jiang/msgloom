"""Verify Calendar delta persistence and checkpoint staging."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from scrapy.utils.test import get_crawler
from sqlalchemy import select

from message_ingest.acquisition.evidence_link import EvidenceLinkPipeline
from message_ingest.catalog import CalendarDeltaObservation, CalendarEventRecord
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.acquisition import RawHttpEvidenceItem
from message_ingest.items.microsoft.outlook.calendar import (
    OutlookCalendarDeltaCheckpointCandidateItem,
    OutlookCalendarDeltaObservationItem,
    OutlookCalendarEventItem,
)
from message_ingest.pipelines.evidence import RawEvidencePipeline
from message_ingest.pipelines.microsoft.outlook.calendar import OutlookCalendarPipeline
from message_ingest.spiders.microsoft.outlook.calendar.delta import (
    OutlookCalendarDeltaSpider,
)
from message_ingest.sync.microsoft.outlook.calendar.checkpoints import (
    CalendarDeltaCheckpointStore,
)

START = "2026-09-27T00:00:00+10:00"
END = "2026-10-04T00:00:00+10:00"


def _crawler(tmp_path: Path):
    return get_crawler(
        OutlookCalendarDeltaSpider,
        settings_dict={
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
            "MSGLOOM_SOURCE_ID": "source-1",
            "MSGLOOM_SOURCE_IDENTITY_REQUIRED": False,
        },
    )


def _raw(evidence_id: str, observed_at: str) -> RawHttpEvidenceItem:
    return RawHttpEvidenceItem(
        evidence_id=evidence_id,
        run_id="run-1",
        purpose="calendar-delta-page",
        observed_at=observed_at,
        origin="network",
        request_fingerprint=(evidence_id[0] if evidence_id else "a") * 64,
        request_url="https://graph.microsoft.com/v1.0/me/calendarView/delta",
        request_method="GET",
        request_headers={"Accept": ["application/json"]},
        request_body=b"",
        response_url="https://graph.microsoft.com/v1.0/me/calendarView/delta",
        response_status=200,
        response_headers={"Content-Type": ["application/json"]},
        response_body=b'{"value":[]}',
        response_flags=[],
    )


def _persist(crawler, raw: RawHttpEvidenceItem, item) -> None:
    raw_pipeline = RawEvidencePipeline.from_crawler(crawler)
    link_pipeline = EvidenceLinkPipeline.from_crawler(crawler)
    calendar_pipeline = OutlookCalendarPipeline.from_crawler(crawler)
    asyncio.run(raw_pipeline.process_item(raw))
    asyncio.run(link_pipeline.process_item(item))
    asyncio.run(calendar_pipeline.process_item(item))


def test_delta_observation_is_scoped_and_replay_safe(tmp_path: Path) -> None:
    crawler = _crawler(tmp_path)
    raw = _raw("delta-evidence-1", "2026-09-27T00:00:00+00:00")
    item = OutlookCalendarDeltaObservationItem(
        event_id="event-1",
        kind="removed",
        raw={"id": "event-1", "@removed": {"reason": "deleted"}},
        observed_at=raw.observed_at,
        evidence_id=raw.evidence_id,
        run_id="run-1",
        attempt=0,
        page_number=1,
        entry_index=0,
        start_datetime=START,
        end_datetime=END,
        removed_reason="deleted",
    )
    _persist(crawler, raw, item)

    pipeline = OutlookCalendarPipeline.from_crawler(crawler)
    asyncio.run(pipeline.process_item(item))

    service = CatalogService.from_crawler(crawler)
    with service.catalog.Session() as session:
        rows = session.scalars(select(CalendarDeltaObservation)).all()
        if len(rows) != 1:
            pytest.fail(f"Expected one replay-safe delta observation, got {len(rows)}")
        row = rows[0]
        if (
            row.event_id != "event-1"
            or row.kind != "removed"
            or row.removed_reason != "deleted"
            or row.start_datetime != START
            or row.end_datetime != END
        ):
            pytest.fail(f"Unexpected persisted Calendar delta row: {row!r}")
    if crawler.stats.get_value("msgloom/calendar/delta_observation_replay_count") != 1:
        pytest.fail("Expected Calendar delta replay counter")
    service.close()


def test_delta_candidate_is_durable_but_not_committed_by_pipeline(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path)
    raw = _raw("candidate-evidence", "2026-09-27T00:00:00+00:00")
    candidate = OutlookCalendarDeltaCheckpointCandidateItem(
        run_id="run-1",
        attempt=0,
        base_revision=None,
        delta_link="https://graph.microsoft.com/v1.0/me/calendarView/delta?$deltatoken=one",
        observed_at=raw.observed_at,
        evidence_id=raw.evidence_id,
        start_datetime=START,
        end_datetime=END,
    )
    _persist(crawler, raw, candidate)

    store = CalendarDeltaCheckpointStore.from_crawler(
        crawler,
        start_datetime=START,
        end_datetime=END,
    )
    pending = store.load_candidate(run_id="run-1", attempt=0)
    if pending is None or not pending.delta_link.endswith("=one"):
        pytest.fail("Expected durable Calendar delta candidate")
    if store.get_checkpoint() is not None:
        pytest.fail("Pipeline must not promote Calendar delta checkpoint")
    CatalogService.from_crawler(crawler).close()


def test_scoped_removal_does_not_claim_global_event_deletion(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path)
    initial_raw = _raw("event-evidence", "2026-09-27T00:00:00+00:00")
    event = OutlookCalendarEventItem(
        event_id="event-1",
        raw={
            "id": "event-1",
            "changeKey": "v1",
            "subject": "Moves outside window later",
            "start": {"dateTime": "2026-09-28T09:00:00", "timeZone": "UTC"},
            "end": {"dateTime": "2026-09-28T10:00:00", "timeZone": "UTC"},
            "type": "singleInstance",
        },
        observed_at=initial_raw.observed_at,
        evidence_id=initial_raw.evidence_id,
        run_id="run-1",
        observation_kind="delta",
    )
    _persist(crawler, initial_raw, event)

    removed_raw = _raw("removed-evidence", "2026-09-28T00:00:00+00:00")
    removed = OutlookCalendarDeltaObservationItem(
        event_id="event-1",
        kind="removed",
        raw={"id": "event-1", "@removed": {"reason": "deleted"}},
        observed_at=removed_raw.observed_at,
        evidence_id=removed_raw.evidence_id,
        run_id="run-2",
        attempt=0,
        page_number=1,
        entry_index=0,
        start_datetime=START,
        end_datetime=END,
        removed_reason="deleted",
    )
    _persist(crawler, removed_raw, removed)

    service = CatalogService.from_crawler(crawler)
    with service.catalog.Session() as session:
        current = session.scalar(select(CalendarEventRecord))
        if current is None or current.is_removed is not False:
            pytest.fail("Scoped Calendar delta removal must not imply global deletion")
    service.close()
