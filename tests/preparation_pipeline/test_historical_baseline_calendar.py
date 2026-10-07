"""Calendar baseline admits exact observations without manual adapter changes."""

import asyncio

import pytest
from sqlalchemy import select

from message_ingest.catalog import Catalog
from message_ingest.catalog.models.microsoft.outlook.calendar import (
    CalendarEventObservation,
)
from message_ingest.catalog.stores.microsoft.outlook.calendar import (
    OutlookCalendarStore,
)
from message_ingest.items.microsoft.outlook.calendar import OutlookCalendarEventItem
from msgloom.contracts import VersionRef
from msgloom.preparation_pipeline.historical_baseline import HistoricalBaselineService
from msgloom.sources import SourceReferenceError
from msgloom.sources._catalog import encode_parts
from tests.preparation_intake_helpers import payload, run, setup
from tests.source_reader.release_nonmail_helpers import SOURCE, WHEN, save_evidence
from tests.source_reader.test_calendar_release_reader import calendar_release


def save_current(saved, *, preledger=False):
    """Advance the mutable event while preserving the old observation."""
    raw = {"id": "event", "changeKey": "v2", "subject": "Current event"}
    save_evidence(saved, "current-calendar", {"value": [raw]})
    catalog = Catalog(f"sqlite:///{saved['database']}")
    try:
        if preledger:
            with catalog.writer_session() as session:
                session.add(
                    CalendarEventObservation(
                        observation_id="preledger-observation",
                        source_id=SOURCE,
                        event_id="event",
                        evidence_id="current-calendar",
                        observed_at=WHEN,
                        raw=raw,
                    )
                )
        else:
            OutlookCalendarStore(catalog, source_id=SOURCE).persist_event(
                OutlookCalendarEventItem.from_graph(
                    raw,
                    observed_at=WHEN,
                    evidence_id="current-calendar",
                    run_id="next-run",
                    calendar_id="calendar",
                )
            )
        with catalog.Session() as session:
            return {
                row.evidence_id: VersionRef(
                    "outlook_calendar",
                    encode_parts(SOURCE, "event"),
                    row.observation_id,
                )
                for row in session.scalars(select(CalendarEventObservation))
            }
    finally:
        catalog.close()


@pytest.mark.parametrize("released_ref", [False, True])
def test_calendar_baseline_freezes_historical_and_current(
    saved_catalog, tmp_path, released_ref
):
    """Catch manual-reader rejection and mutable-current substitution."""
    sequence = calendar_release(saved_catalog)
    versions = save_current(saved_catalog)

    async def check():
        reader, persistence, scope, _ = await setup(
            saved_catalog, tmp_path, stream="outlook_calendar"
        )
        try:
            old = versions["event-evidence"]
            if released_ref:
                entry = await reader.catalog.get_release_entry(sequence)
                released = await reader.read_entry(entry)
                old = released.selection.record.source
            approved = (old, versions["current-calendar"])
            with pytest.raises(SourceReferenceError):
                await reader.read_selection(old)
            result = await run(
                HistoricalBaselineService(persistence, reader),
                scope,
                sources=approved,
                approval_id="calendar-approved",
            )
            workset = await payload(persistence, result)
            if workset.baseline_sources != approved or workset.entries:
                pytest.fail("Calendar baseline changed its explicit selection")
            if workset.cutoff.last_release_entry_seq != sequence:
                pytest.fail("Calendar baseline changed the captured release anchor")
            records = []
            for ref in workset.selection_refs:
                selection = await payload(
                    persistence, await persistence.get_result(ref.result_id)
                )
                records.append(selection.record)
            if [record.subject for record in records] != [
                "Original event",
                "Current event",
            ]:
                pytest.fail("Calendar baseline substituted mutable current evidence")
            if tuple(record.source for record in records) != approved:
                pytest.fail("Calendar baseline lost exact requested identities")
            if (
                await reader.catalog.max_release_entry_seq(SOURCE, "outlook_calendar")
                != sequence
            ):
                pytest.fail("Calendar baseline fabricated release chronology")
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())


def test_calendar_baseline_accepts_preledger_genesis(saved_catalog, tmp_path):
    """An exact saved observation needs no fabricated prior release."""
    versions = save_current(saved_catalog, preledger=True)

    async def check():
        reader, persistence, scope, _ = await setup(
            saved_catalog, tmp_path, stream="outlook_calendar"
        )
        try:
            result = await run(
                HistoricalBaselineService(persistence, reader),
                scope,
                sources=(versions["current-calendar"],),
                approval_id="genesis",
            )
            workset = await payload(persistence, result)
            if workset.cutoff.last_release_entry_seq or workset.entries:
                pytest.fail("Calendar genesis fabricated a release")
            if len(await persistence.list_preparation_intake_worksets(scope)) != 1:
                pytest.fail("Calendar genesis is not discoverable")
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())
