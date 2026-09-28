"""Verify Calendar persistence through native item-pipeline stages."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from scrapy.utils.test import get_crawler
from sqlalchemy import func, select

from message_ingest.acquisition.evidence_link import EvidenceLinkPipeline
from message_ingest.catalog import (
    CalendarEventObservation,
    CalendarEventRecord,
    CalendarRecord,
)
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.acquisition import RawHttpEvidenceItem
from message_ingest.items.microsoft.outlook.calendar import (
    OutlookCalendarEventItem,
    OutlookCalendarItem,
)
from message_ingest.pipelines.evidence import RawEvidencePipeline
from message_ingest.pipelines.microsoft.outlook.calendar import OutlookCalendarPipeline
from message_ingest.spiders.microsoft.outlook.calendar.window import (
    OutlookCalendarWindowSpider,
)


def _crawler(tmp_path: Path, *, source_id: str = "source-1"):
    return get_crawler(
        OutlookCalendarWindowSpider,
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
        purpose="calendar-window-page",
        observed_at=observed_at,
        origin=origin,
        request_fingerprint="c" * 64,
        request_url="https://graph.microsoft.com/v1.0/me/calendar/calendarView",
        request_method="GET",
        request_headers={"Accept": ["application/json"]},
        request_body=b"",
        response_url="https://graph.microsoft.com/v1.0/me/calendar/calendarView",
        response_status=200,
        response_headers={"Content-Type": ["application/json"]},
        response_body=b'{"value":[{"id":"event-1"}]}',
        response_flags=["cached"] if origin == "http_cache" else [],
    )


def _calendar(
    evidence_id: str,
    observed_at: str,
    *,
    change_key: str = "calendar-v1",
) -> OutlookCalendarItem:
    return OutlookCalendarItem(
        calendar_id="calendar-1",
        raw={
            "id": "calendar-1",
            "name": "Work",
            "changeKey": change_key,
            "isDefaultCalendar": True,
            "canEdit": True,
            "canShare": False,
            "canViewPrivateItems": True,
        },
        observed_at=observed_at,
        evidence_id=evidence_id,
        run_id="calendar-run",
    )


def _event(
    evidence_id: str,
    observed_at: str,
    *,
    change_key: str = "event-v1",
    subject: str = "Planning",
) -> OutlookCalendarEventItem:
    return OutlookCalendarEventItem(
        event_id="event-1",
        raw={
            "id": "event-1",
            "changeKey": change_key,
            "subject": subject,
            "start": {
                "dateTime": "2026-09-27T09:00:00",
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": "2026-09-27T10:00:00",
                "timeZone": "UTC",
            },
            "type": "occurrence",
            "seriesMasterId": "series-1",
            "isAllDay": False,
            "isCancelled": False,
        },
        observed_at=observed_at,
        evidence_id=evidence_id,
        run_id="calendar-run",
        calendar_id="default",
        observation_kind="window",
    )


def _process(
    crawler,
    raw: RawHttpEvidenceItem,
    item,
) -> None:
    raw_pipeline = RawEvidencePipeline.from_crawler(crawler)
    link_pipeline = EvidenceLinkPipeline.from_crawler(crawler)
    calendar_pipeline = OutlookCalendarPipeline.from_crawler(crawler)
    asyncio.run(raw_pipeline.process_item(raw))
    asyncio.run(link_pipeline.process_item(item))
    asyncio.run(calendar_pipeline.process_item(item))


def test_calendar_inventory_upserts_latest_record(tmp_path: Path) -> None:
    crawler = _crawler(tmp_path)
    first_raw = _raw("calendar-evidence-1")
    _process(
        crawler,
        first_raw,
        _calendar(first_raw.evidence_id, first_raw.observed_at),
    )
    second_raw = _raw(
        "calendar-evidence-2",
        observed_at="2026-09-27T01:00:00+00:00",
    )
    changed = _calendar(
        second_raw.evidence_id,
        second_raw.observed_at,
        change_key="calendar-v2",
    )
    changed.raw["name"] = "Projects"
    _process(crawler, second_raw, changed)

    service = CatalogService.from_crawler(crawler)
    with service.catalog.Session() as session:
        row = session.scalar(select(CalendarRecord))
        if row is None:
            pytest.fail("Expected Calendar inventory record")
        if row.calendar_id != "calendar-1" or row.name != "Projects":
            pytest.fail("Expected latest Calendar metadata")
        if row.change_key != "calendar-v2":
            pytest.fail("Expected latest Calendar changeKey")
        if row.latest_evidence_id != "calendar-evidence-2":
            pytest.fail("Expected latest Calendar evidence")
    if crawler.stats.get_value("msgloom/calendar/calendar_changed_count") != 1:
        pytest.fail("Expected Calendar metadata change counter")
    service.close()


def test_event_first_observation_populates_current_state(tmp_path: Path) -> None:
    crawler = _crawler(tmp_path)
    raw = _raw("event-evidence-1")
    event = _event(raw.evidence_id, raw.observed_at)
    _process(crawler, raw, event)

    service = CatalogService.from_crawler(crawler)
    with service.catalog.Session() as session:
        current = session.scalar(select(CalendarEventRecord))
        observation = session.scalar(select(CalendarEventObservation))
        if current is None or observation is None:
            pytest.fail("Expected current Calendar event and observation")
        if current.change_key != "event-v1" or current.subject != "Planning":
            pytest.fail("Expected Calendar current-state projections")
        if current.series_master_id != "series-1":
            pytest.fail("Expected recurring-series relationship")
        if current.is_all_day is not False or current.is_cancelled is not False:
            pytest.fail("Expected Calendar boolean projections")
        if observation.evidence_id != "event-evidence-1":
            pytest.fail("Expected observation linked to canonical evidence")
    service.close()


def test_same_change_key_updates_capture_without_new_semantic_version(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path)
    first_raw = _raw("event-evidence-1")
    _process(
        crawler,
        first_raw,
        _event(first_raw.evidence_id, first_raw.observed_at),
    )
    second_raw = _raw(
        "event-evidence-2",
        observed_at="2026-09-27T01:00:00+00:00",
    )
    _process(
        crawler,
        second_raw,
        _event(second_raw.evidence_id, second_raw.observed_at),
    )

    service = CatalogService.from_crawler(crawler)
    with service.catalog.Session() as session:
        count = session.scalar(
            select(func.count()).select_from(CalendarEventObservation)
        )
        current = session.scalar(select(CalendarEventRecord))
        if count != 1:
            pytest.fail(f"Expected one semantic version, got {count}")
        if current is None or current.latest_evidence_id != "event-evidence-2":
            pytest.fail("Expected current state to retain latest capture")
    if crawler.stats.get_value("msgloom/calendar/event_unchanged_count") != 1:
        pytest.fail("Expected unchanged semantic-version counter")
    service.close()


def test_changed_change_key_appends_new_semantic_version(tmp_path: Path) -> None:
    crawler = _crawler(tmp_path)
    first_raw = _raw("event-evidence-1")
    _process(
        crawler,
        first_raw,
        _event(first_raw.evidence_id, first_raw.observed_at),
    )
    second_raw = _raw(
        "event-evidence-2",
        observed_at="2026-09-27T01:00:00+00:00",
    )
    _process(
        crawler,
        second_raw,
        _event(
            second_raw.evidence_id,
            second_raw.observed_at,
            change_key="event-v2",
            subject="Planning moved",
        ),
    )

    service = CatalogService.from_crawler(crawler)
    with service.catalog.Session() as session:
        count = session.scalar(
            select(func.count()).select_from(CalendarEventObservation)
        )
        current = session.scalar(select(CalendarEventRecord))
        if count != 2:
            pytest.fail(f"Expected two semantic versions, got {count}")
        if current is None or current.change_key != "event-v2":
            pytest.fail("Expected changed Calendar current state")
        if current.subject != "Planning moved":
            pytest.fail("Expected changed Calendar subject")
    service.close()


def test_cache_replay_does_not_duplicate_event_observation(tmp_path: Path) -> None:
    crawler = _crawler(tmp_path)
    original = _raw("evidence-original")
    _process(
        crawler,
        original,
        _event(original.evidence_id, original.observed_at),
    )
    replay = _raw(
        "evidence-replay",
        origin="http_cache",
        observed_at="2026-09-27T01:00:00+00:00",
    )
    second = _event("evidence-replay", replay.observed_at)
    _process(crawler, replay, second)
    if second.evidence_id != "evidence-original":
        pytest.fail("Expected cache replay to resolve original evidence")

    service = CatalogService.from_crawler(crawler)
    with service.catalog.Session() as session:
        count = session.scalar(
            select(func.count()).select_from(CalendarEventObservation)
        )
        if count != 1:
            pytest.fail(f"Expected one replay-deduplicated version, got {count}")
    if crawler.stats.get_value("msgloom/calendar/event_replay_count") != 1:
        pytest.fail("Expected Calendar replay counter")
    service.close()


def test_calendar_pipeline_passes_other_resource_items_through(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path)
    pipeline = OutlookCalendarPipeline.from_crawler(crawler)
    item = {"mail": "or future resource"}
    returned = asyncio.run(pipeline.process_item(item))
    if returned is not item:
        pytest.fail("Expected non-Calendar item to pass through unchanged")
    CatalogService.from_crawler(crawler).close()


def test_older_canonical_capture_cannot_roll_current_event_state_back(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path)

    first = _raw(
        "capture-a",
        observed_at="2026-09-27T01:00:00+00:00",
    )
    _process(crawler, first, _event(first.evidence_id, first.observed_at))

    same = _raw(
        "capture-b",
        observed_at="2026-09-27T02:00:00+00:00",
    )
    _process(crawler, same, _event(same.evidence_id, same.observed_at))

    changed = _raw(
        "capture-c",
        observed_at="2026-09-27T03:00:00+00:00",
    )
    _process(
        crawler,
        changed,
        _event(
            changed.evidence_id,
            changed.observed_at,
            change_key="event-v2",
            subject="Current version",
        ),
    )

    replay = _raw(
        "capture-replay",
        origin="http_cache",
        observed_at=same.observed_at,
    )
    replay.request_fingerprint = same.request_fingerprint
    replay.response_body = same.response_body
    old = _event(
        replay.evidence_id,
        replay.observed_at,
        change_key="event-v1",
        subject="Old version",
    )
    _process(crawler, replay, old)

    service = CatalogService.from_crawler(crawler)
    with service.catalog.Session() as session:
        current = session.scalar(select(CalendarEventRecord))
        count = session.scalar(
            select(func.count()).select_from(CalendarEventObservation)
        )
        if current is None:
            pytest.fail("Expected Calendar current state")
        if current.change_key != "event-v2" or current.subject != "Current version":
            pytest.fail("Expected older cache capture not to roll current state back")
        if current.latest_evidence_id != "capture-c":
            pytest.fail("Expected latest evidence to remain the newest capture")
        if count != 2:
            pytest.fail(f"Expected two semantic versions, got {count}")
    stale = crawler.stats.get_value("msgloom/calendar/event_stale_count", 0)
    replayed = crawler.stats.get_value("msgloom/calendar/event_replay_count", 0)
    if stale + replayed != 1:
        pytest.fail("Expected old canonical capture to be classified stale or replay")
    service.close()


def test_default_window_event_resolves_discovered_default_calendar_id(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path)
    calendar_raw = _raw("calendar-evidence")
    _process(
        crawler,
        calendar_raw,
        _calendar(calendar_raw.evidence_id, calendar_raw.observed_at),
    )
    event_raw = _raw(
        "event-evidence",
        observed_at="2026-09-27T01:00:00+00:00",
    )
    _process(
        crawler,
        event_raw,
        _event(event_raw.evidence_id, event_raw.observed_at),
    )

    service = CatalogService.from_crawler(crawler)
    with service.catalog.Session() as session:
        current = session.scalar(select(CalendarEventRecord))
        if current is None or current.calendar_id != "calendar-1":
            pytest.fail(
                "Expected default window event to join discovered default calendar"
            )
    service.close()
