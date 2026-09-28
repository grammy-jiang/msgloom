"""Shared fixed-window Calendar checkpoint fixtures."""

from pathlib import Path

from message_ingest.calendar_checkpoints import CalendarDeltaCheckpointStore
from message_ingest.catalog import CalendarDeltaObservation

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
    with store.catalog.Session() as session, session.begin():
        session.add(
            CalendarDeltaObservation(
                observation_id=(f"{run_id}-{attempt}-{page_number}-{entry_index}"),
                source_id=store.source_id,
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
