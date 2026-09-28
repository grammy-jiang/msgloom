"""Verify recurring-series topology persistence and planner freshness."""

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
    OutlookCalendarEventItem,
    OutlookCalendarSeriesTopologyItem,
)

NOW = "2026-09-28T00:00:00+00:00"
LATER = "2026-09-28T01:00:00+00:00"


def _store(tmp_path: Path) -> tuple[Catalog, OutlookCalendarStore]:
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    return catalog, OutlookCalendarStore(catalog, source_id="source-1")


def _recurring_event(store: OutlookCalendarStore, *, observed_at: str = NOW) -> None:
    store.persist_event(
        OutlookCalendarEventItem(
            event_id="occurrence-1",
            raw={
                "id": "occurrence-1",
                "changeKey": "occ-v1",
                "type": "occurrence",
                "seriesMasterId": "series-1",
            },
            observed_at=observed_at,
            evidence_id=None,
            run_id="run-1",
            calendar_id="calendar-1",
        )
    )


def _base_surfaces(store: OutlookCalendarStore, *, observed_at: str = NOW) -> None:
    for surface in ("detail", "attachments"):
        store.set_event_surface(
            event_id="occurrence-1",
            surface=surface,
            status="acquired",
            evidence_id=None,
            observed_at=observed_at,
            profile_version=FULL_V1,
            resource_version="occ-v1",
        )


def _topology(
    store: OutlookCalendarStore,
    *,
    observed_at: str,
    status: str = "acquired",
) -> None:
    raw = None
    if status == "acquired":
        raw = {
            "id": "series-1",
            "changeKey": "master-v1",
            "cancelledOccurrences": ["oid-1"],
            "exceptionOccurrences": [{"id": "exception-1"}],
        }
    store.persist_series_topology(
        OutlookCalendarSeriesTopologyItem(
            series_master_id="series-1",
            calendar_id="calendar-1",
            status=status,
            raw=raw,
            observed_at=observed_at,
            evidence_id=None,
            run_id="run-1",
        )
    )


def test_recurring_event_remains_pending_until_topology_covers_latest_sighting(
    tmp_path: Path,
) -> None:
    catalog, store = _store(tmp_path)
    try:
        _recurring_event(store)
        _base_surfaces(store)
        expected = (CalendarEnrichmentTarget("occurrence-1", "calendar-1", "occ-v1"),)
        if pending_full_v1_targets(store) != expected:
            pytest.fail("Expected recurring event without topology to remain pending")

        _topology(store, observed_at=NOW)
        if pending_full_v1_targets(store):
            pytest.fail("Expected fresh series topology to complete recurring target")

        _recurring_event(store, observed_at=LATER)
        if pending_full_v1_targets(store) != expected:
            pytest.fail("New window sighting must make older topology stale")
    finally:
        catalog.close()


def test_terminal_series_topology_outcome_converges_planner(tmp_path: Path) -> None:
    catalog, store = _store(tmp_path)
    try:
        _recurring_event(store)
        _base_surfaces(store)
        _topology(store, observed_at=NOW, status="unavailable")
        if pending_full_v1_targets(store):
            pytest.fail("Terminal unavailable topology should not retry forever")
    finally:
        catalog.close()
