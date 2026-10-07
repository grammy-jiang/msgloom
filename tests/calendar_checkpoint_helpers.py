"""Shared fixed-window Calendar checkpoint fixtures."""

import json
from pathlib import Path

from calendar_handoff_helpers import _capture
from sqlalchemy.engine import make_url
from test_calendar_pipeline import _crawler

from message_ingest.catalog.stores.microsoft.outlook.calendar import (
    OutlookCalendarStore,
)
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.microsoft.outlook.calendar import (
    OutlookCalendarDeltaObservationItem,
)
from message_ingest.sync.microsoft.outlook.calendar.checkpoints import (
    CalendarDeltaCheckpointStore,
)

START = "2026-10-01T00:00:00+00:00"
END = "2026-11-01T00:00:00+00:00"


def _url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'catalog.sqlite3'}"


def _store(
    tmp_path: Path,
    *,
    source_id: str = "source-1",
    start: str = START,
    end: str = END,
) -> CalendarDeltaCheckpointStore:
    return CalendarDeltaCheckpointStore(
        _url(tmp_path),
        source_id=source_id,
        start_datetime=start,
        end_datetime=end,
    )


def _candidate(
    store: CalendarDeltaCheckpointStore,
    *,
    run_id: str,
    attempt: int,
    base_revision: int | None,
    delta_link: str,
    evidence_id: str,
) -> None:
    store.write_candidate(
        run_id=run_id,
        attempt=attempt,
        base_revision=base_revision,
        delta_link=delta_link,
        evidence_id=evidence_id,
        observed_at="2026-10-02T00:00:00+00:00",
    )


def _observation(
    store: CalendarDeltaCheckpointStore,
    *,
    run_id: str,
    attempt: int,
    event_id: str,
    kind: str,
    page_number: int,
    entry_index: int,
    evidence_id: str,
    raw: dict[str, object],
    removed_reason: str | None = None,
) -> None:
    # These authority fixtures must use the ledger-aware writer too.
    database = make_url(store.catalog.database_url).database
    if database is None:
        raise ValueError("Calendar test requires a file catalog")
    crawler = _crawler(Path(database).parent, source_id=store.source_id)
    try:
        _capture(
            crawler,
            evidence_id,
            at="2026-10-02T00:00:00+00:00",
            body=json.dumps({"value": [raw]}).encode(),
        )
    finally:
        CatalogService.from_crawler(crawler).close()
    OutlookCalendarStore(
        store.catalog, source_id=store.source_id
    ).persist_delta_observation(
        OutlookCalendarDeltaObservationItem(
            calendar_scope=store.calendar_scope,
            start_datetime=store.start_datetime,
            end_datetime=store.end_datetime,
            run_id=run_id,
            attempt=attempt,
            page_number=page_number,
            entry_index=entry_index,
            event_id=event_id,
            kind=kind,
            removed_reason=removed_reason,
            evidence_id=evidence_id,
            observed_at="2026-10-02T00:00:00+00:00",
            raw=raw,
        )
    )
