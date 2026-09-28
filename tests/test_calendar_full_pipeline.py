"""Verify rich Calendar event and attachment persistence."""

from pathlib import Path

import pytest
from sqlalchemy import func, select
from test_calendar_pipeline import _crawler, _event, _process, _raw

from message_ingest.catalog import (
    CalendarEventAttachmentRecord,
    CalendarEventObservation,
    CalendarEventRecord,
    Catalog,
)
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items import (
    OutlookCalendarAttachmentContentItem,
    OutlookCalendarAttachmentItem,
)
from message_ingest.pipelines.calendar_attachments import CalendarAttachmentStore


def test_same_change_key_merges_richer_detail_without_later_downgrade(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path)
    basic_raw = _raw("basic-evidence")
    basic = _event(basic_raw.evidence_id, basic_raw.observed_at)
    _process(crawler, basic_raw, basic)

    detail_raw = _raw(
        "detail-evidence",
        observed_at="2026-09-27T01:00:00+00:00",
    )
    detail = _event(detail_raw.evidence_id, detail_raw.observed_at)
    detail.observation_kind = "full"
    detail.raw["body"] = {
        "contentType": "text",
        "content": "Detailed agenda",
    }
    detail.raw["organizer"] = {"emailAddress": {"address": "owner@example.test"}}
    _process(crawler, detail_raw, detail)

    later_basic_raw = _raw(
        "later-basic-evidence",
        observed_at="2026-09-27T02:00:00+00:00",
    )
    later_basic = _event(
        later_basic_raw.evidence_id,
        later_basic_raw.observed_at,
    )
    _process(crawler, later_basic_raw, later_basic)

    service = CatalogService.from_crawler(crawler)
    with service.catalog.Session() as session:
        current = session.scalar(select(CalendarEventRecord))
        if current is None:
            pytest.fail("Expected current Calendar event state")
        body = current.raw.get("body")
        if not isinstance(body, dict):
            pytest.fail("Expected rich Calendar body to survive basic refresh")
        if body.get("content") != "Detailed agenda":
            pytest.fail("Expected rich Calendar body content")
        if "organizer" not in current.raw:
            pytest.fail("Expected rich Calendar organizer to survive")
        count = session.scalar(
            select(func.count()).select_from(CalendarEventObservation)
        )
        if count != 1:
            pytest.fail("Expected one semantic version for one unchanged changeKey")
    service.close()


def test_calendar_attachment_metadata_avoids_content_bytes_duplication(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path)
    raw = _raw(
        "attachment-evidence",
        observed_at="2026-09-27T01:00:00+00:00",
    )
    item = OutlookCalendarAttachmentItem(
        event_id="event-1",
        attachment_id="attachment-1",
        attachment_type="#microsoft.graph.fileAttachment",
        raw={
            "@odata.type": "#microsoft.graph.fileAttachment",
            "id": "attachment-1",
            "name": "agenda.txt",
            "contentType": "text/plain",
            "size": 12,
            "isInline": False,
        },
        observed_at=raw.observed_at,
        evidence_id=raw.evidence_id,
        run_id="calendar-run",
        calendar_id="default",
        content_bytes_present=True,
    )
    _process(crawler, raw, item)

    service = CatalogService.from_crawler(crawler)
    with service.catalog.Session() as session:
        record = session.scalar(select(CalendarEventAttachmentRecord))
        if record is None:
            pytest.fail("Expected Calendar attachment record")
        if record.name != "agenda.txt" or record.content_type != "text/plain":
            pytest.fail("Expected Calendar attachment projections")
        if record.content_bytes_present is not True:
            pytest.fail("Expected Calendar attachment content marker")
        if record.content_status != "pending":
            pytest.fail("Expected raw attachment content still pending")
        if "contentBytes" in record.raw:
            pytest.fail("Expected semantic attachment row without contentBytes")
        if record.latest_evidence_id != "attachment-evidence":
            pytest.fail("Expected attachment linked to raw HTTP evidence")

    content_raw = _raw(
        "attachment-content-evidence",
        observed_at="2026-09-27T01:01:00+00:00",
    )
    content = OutlookCalendarAttachmentContentItem(
        event_id="event-1",
        attachment_id="attachment-1",
        observed_at=content_raw.observed_at,
        evidence_id=content_raw.evidence_id,
        run_id="calendar-run",
    )
    _process(crawler, content_raw, content)
    with service.catalog.Session() as session:
        record = session.scalar(select(CalendarEventAttachmentRecord))
        if record is None or record.content_status != "acquired":
            pytest.fail("Expected Calendar attachment content acquisition")
        if record.content_evidence_id != "attachment-content-evidence":
            pytest.fail("Expected raw attachment content evidence link")
    service.close()


@pytest.mark.parametrize(
    ("source_id", "calendar_id", "expected"),
    [
        ("source-1", "default", "calendar-1"),
        ("source-2", "default", "default"),
        ("source-1", "named-calendar", "named-calendar"),
    ],
)
def test_attachment_calendar_resolution_stays_within_source(
    tmp_path: Path,
    source_id: str,
    calendar_id: str,
    expected: str,
) -> None:
    catalog = Catalog(f"sqlite:///{tmp_path / 'attachments.sqlite3'}")
    try:
        with catalog.Session() as session, session.begin():
            session.add(
                CalendarEventRecord(
                    source_id="source-1",
                    event_id="event-1",
                    calendar_id="calendar-1",
                    latest_observed_at="2026-09-27T00:00:00+00:00",
                    raw={},
                )
            )
        store = CalendarAttachmentStore(catalog, source_id=source_id)
        store.persist_metadata(
            OutlookCalendarAttachmentItem(
                event_id="event-1",
                attachment_id="attachment-1",
                attachment_type="#microsoft.graph.itemAttachment",
                raw={},
                observed_at="2026-09-27T00:00:00+00:00",
                evidence_id=None,
                run_id="run-1",
                calendar_id=calendar_id,
            )
        )
        with catalog.Session() as session:
            row = session.scalar(select(CalendarEventAttachmentRecord))
            if row is None or row.calendar_id != expected:
                pytest.fail("Attachment calendar resolution crossed its scope")
    finally:
        catalog.close()
