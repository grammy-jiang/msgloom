"""Local Calendar fixtures shared by handoff persistence tests."""

from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest
from sqlalchemy import select
from test_calendar_pipeline import _calendar, _crawler, _event, _raw

from message_ingest.acquisition.handoff import (
    FactSpec,
)
from message_ingest.catalog.models.handoff import AcquisitionFact
from message_ingest.catalog.stores.microsoft.outlook.calendar import (
    OutlookCalendarStore,
)
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.microsoft.outlook.calendar import (
    OutlookCalendarAttachmentContentItem,
    OutlookCalendarAttachmentItem,
    OutlookCalendarDeltaObservationItem,
    OutlookCalendarEventSurfaceItem,
    OutlookCalendarSeriesTopologyItem,
)
from message_ingest.pipelines.evidence import RawEvidencePipeline
from message_ingest.pipelines.microsoft.outlook.calendar import OutlookCalendarPipeline

NOW = "2026-09-27T00:00:00+00:00"
LATER = "2026-09-28T00:00:00+00:00"


def _facts(catalog) -> list[FactSpec]:
    with catalog.Session() as session:
        return [
            FactSpec.from_json(row.payload)
            for row in session.scalars(select(AcquisitionFact)).all()
        ]


def _fact(catalog, run: str, component: str | None = None) -> FactSpec:
    rows = [
        fact
        for fact in _facts(catalog)
        if fact.run_id == run and fact.component_kind == component
    ]
    if len(rows) != 1:
        pytest.fail(f"Expected one {run}/{component} fact, got {rows}")
    return rows[0]


@pytest.fixture
def env(tmp_path):
    crawler = _crawler(tmp_path)
    service = CatalogService.from_crawler(crawler)
    yield (
        crawler,
        service.catalog,
        OutlookCalendarStore(service.catalog, source_id="source-1"),
    )
    service.close()


def _capture(crawler, evidence: str, *, at: str = NOW, body: bytes = b"payload"):
    raw = _raw(evidence, observed_at=at)
    raw.run_id = "canonical-capture-run"
    raw.response_body = body
    asyncio.run(RawEvidencePipeline.from_crawler(crawler).process_item(raw))
    return raw


def _item(kind: str, run: str, evidence: str, at: str, value: str):
    if kind == "event":
        return replace(_event(evidence, at, change_key=value), run_id=run)
    if kind == "calendar":
        return replace(_calendar(evidence, at, change_key=value), run_id=run)
    if kind == "attachment":
        return OutlookCalendarAttachmentItem(
            event_id="event-1",
            attachment_id="a1",
            attachment_type="#microsoft.graph.fileAttachment",
            raw={"id": "a1", "name": value},
            observed_at=at,
            evidence_id=evidence,
            run_id=run,
        )
    if kind == "series":
        return OutlookCalendarSeriesTopologyItem(
            series_master_id="event-1",
            calendar_id="default",
            status="acquired",
            raw={
                "id": "event-1",
                "changeKey": value,
                "cancelledOccurrences": [],
                "exceptionOccurrences": [],
            },
            observed_at=at,
            evidence_id=evidence,
            run_id=run,
        )
    if kind == "surface":
        return OutlookCalendarEventSurfaceItem(
            event_id="event-1",
            surface="detail",
            status="acquired",
            observed_at=at,
            evidence_id=evidence,
            run_id=run,
            profile_version="full-v1",
            resource_version=value,
        )
    if kind == "content":
        return OutlookCalendarAttachmentContentItem(
            event_id="event-1",
            attachment_id="a1",
            observed_at=at,
            evidence_id=evidence,
            run_id=run,
        )
    return OutlookCalendarDeltaObservationItem(
        event_id="event-1",
        kind="upsert",
        raw={"id": "event-1", "changeKey": value},
        observed_at=at,
        evidence_id=evidence,
        run_id=run,
        attempt=0,
        page_number=1,
        entry_index=0,
        start_datetime=NOW,
        end_datetime=LATER,
    )


def _persist(crawler, item):
    return asyncio.run(OutlookCalendarPipeline.from_crawler(crawler).process_item(item))


def _seed_content(crawler):
    _capture(crawler, "metadata")
    _persist(crawler, _item("attachment", "metadata-run", "metadata", NOW, "a1"))
