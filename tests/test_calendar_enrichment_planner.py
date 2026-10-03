"""Verify versioned Outlook Calendar Full-v1 planning."""

from __future__ import annotations

from pathlib import Path

import pytest

from message_ingest.acquisition.microsoft.outlook.calendar.planner import (
    CalendarEnrichmentTarget,
    pending_full_v1_targets,
)
from message_ingest.acquisition.microsoft.outlook.calendar.profile import FULL_V1
from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.microsoft.outlook.calendar import (
    OutlookCalendarStore,
)
from message_ingest.items.microsoft.outlook.calendar import (
    OutlookCalendarAttachmentItem,
    OutlookCalendarEventItem,
)

NOW = "2026-09-28T00:00:00+00:00"


def _store(tmp_path: Path) -> tuple[Catalog, OutlookCalendarStore]:
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    return catalog, OutlookCalendarStore(catalog, source_id="source-1")


def _event(
    store: OutlookCalendarStore,
    event_id: str,
    *,
    run_id: str,
    calendar_id: str = "calendar-1",
) -> None:
    store.persist_event(
        OutlookCalendarEventItem(
            event_id=event_id,
            raw={"id": event_id, "changeKey": f"ck-{event_id}"},
            observed_at=NOW,
            evidence_id=None,
            run_id=run_id,
            calendar_id=calendar_id,
        )
    )


def _surface(
    store: OutlookCalendarStore,
    event_id: str,
    surface: str,
    *,
    status: str = "acquired",
    profile: str | None = FULL_V1,
    resource_version: str | None = None,
) -> None:
    store.set_event_surface(
        run_id="run-1",
        event_id=event_id,
        surface=surface,
        status=status,
        evidence_id=None,
        observed_at=NOW,
        profile_version=profile,
        resource_version=resource_version,
    )


def test_planner_returns_event_and_calendar_for_incomplete_full_profile(
    tmp_path: Path,
) -> None:
    catalog, store = _store(tmp_path)
    try:
        _event(store, "event-1", run_id="run-1", calendar_id="calendar-1")
        if pending_full_v1_targets(store) != (
            CalendarEnrichmentTarget("event-1", "calendar-1", "ck-event-1"),
        ):
            pytest.fail("Expected incomplete Calendar event target with calendar scope")
        _surface(store, "event-1", "detail", resource_version="ck-event-1")
        _surface(store, "event-1", "attachments", resource_version="ck-event-1")
        if pending_full_v1_targets(store):
            pytest.fail("Expected base-complete Calendar event to leave planner")
    finally:
        catalog.close()


def test_planner_scopes_to_collection_runs_and_attachment_surfaces(
    tmp_path: Path,
) -> None:
    catalog, store = _store(tmp_path)
    try:
        _event(store, "event-1", run_id="run-1")
        _event(store, "event-2", run_id="run-2", calendar_id="calendar-2")
        for event_id in ("event-1", "event-2"):
            _surface(store, event_id, "detail", resource_version=f"ck-{event_id}")
            _surface(store, event_id, "attachments", resource_version=f"ck-{event_id}")
        store.persist_attachment_metadata(
            OutlookCalendarAttachmentItem(
                event_id="event-2",
                attachment_id="a2",
                attachment_type="#microsoft.graph.fileAttachment",
                raw={"id": "a2", "@odata.type": "#microsoft.graph.fileAttachment"},
                observed_at=NOW,
                evidence_id=None,
                run_id="run-2",
                calendar_id="calendar-2",
            )
        )

        if pending_full_v1_targets(store, run_ids=("run-1",)):
            pytest.fail(
                "Expected complete run-1 event to remain out of Calendar planner"
            )
        expected = (CalendarEnrichmentTarget("event-2", "calendar-2", "ck-event-2"),)
        if pending_full_v1_targets(store, run_ids=("run-2",)) != expected:
            pytest.fail("Expected missing attachment raw surface for run-2 event")
        _surface(store, "event-2", "attachment_raw:a2", resource_version="ck-event-2")
        if pending_full_v1_targets(store, run_ids=("run-2",)):
            pytest.fail("Expected acquired attachment raw surface to complete event")
    finally:
        catalog.close()


def test_calendar_planner_requires_current_profile_and_valid_limit(
    tmp_path: Path,
) -> None:
    catalog, store = _store(tmp_path)
    try:
        _event(store, "event-1", run_id="run-1")
        _surface(
            store, "event-1", "detail", profile="older", resource_version="ck-event-1"
        )
        _surface(
            store,
            "event-1",
            "attachments",
            profile="older",
            resource_version="ck-event-1",
        )
        if not pending_full_v1_targets(store):
            pytest.fail("Expected older Calendar profile to remain pending")
        with pytest.raises(ValueError, match="limit"):
            pending_full_v1_targets(store, limit=-1)
    finally:
        catalog.close()


def test_same_change_key_current_run_sighting_remains_plannable(tmp_path: Path) -> None:
    catalog, store = _store(tmp_path)
    try:
        _event(store, "event-1", run_id="old-run")
        _event(store, "event-1", run_id="current-run")
        expected = (CalendarEnrichmentTarget("event-1", "calendar-1", "ck-event-1"),)
        if pending_full_v1_targets(store, run_ids=("current-run",)) != expected:
            pytest.fail("Expected unchanged current-window event to remain plannable")
    finally:
        catalog.close()


def test_same_change_key_new_run_still_enters_scoped_backlog(tmp_path: Path) -> None:
    catalog, store = _store(tmp_path)
    try:
        _event(store, "event-1", run_id="old-run")
        # A later collection sees the same semantic version. This must create a
        # run sighting even though it intentionally does not create another
        # semantic CalendarEventObservation.
        _event(store, "event-1", run_id="new-run")

        expected = (CalendarEnrichmentTarget("event-1", "calendar-1", "ck-event-1"),)
        if pending_full_v1_targets(store, run_ids=("new-run",)) != expected:
            pytest.fail("Expected same-version event sighting in current-run planner")
    finally:
        catalog.close()
