"""Winning observation locators retain exact capture position and ownership."""

import asyncio
from dataclasses import replace

import pytest
from sqlalchemy import select, text

from message_ingest.acquisition.handoff import FactSpec
from message_ingest.catalog import Catalog
from message_ingest.catalog.models.handoff import AcquisitionFact
from message_ingest.catalog.stores.microsoft.onedrive import OneDriveStore
from message_ingest.catalog.stores.microsoft.outlook.calendar import (
    OutlookCalendarStore,
)
from message_ingest.items.microsoft.onedrive import OneDriveDeltaResyncObservationItem
from message_ingest.items.microsoft.outlook.calendar import (
    OutlookCalendarDeltaObservationItem,
)
from msgloom.sources import SourceReaderError
from tests.source_reader.release_nonmail_helpers import (
    SOURCE,
    WHEN,
    publish,
    reader_api,
    save_evidence,
)


@pytest.mark.parametrize("stream", ["outlook_calendar", "onedrive"])
def test_winning_observation_replay_uses_exact_page_position(saved_catalog, stream):
    old = {"id": "resource", "name": "Earlier", "subject": "Earlier", "changeKey": "v1"}
    winner = {
        "id": "resource",
        "name": "Winner",
        "subject": "Winner",
        "changeKey": "v2",
    }
    network = {**winner, "@microsoft.graph.downloadUrl": "synthetic-download-url"}
    save_evidence(
        saved_catalog,
        "ordered",
        {"value": [old, network if stream == "onedrive" else winner]},
    )
    catalog = Catalog(f"sqlite:///{saved_catalog['database']}")
    try:
        if stream == "outlook_calendar":
            store = OutlookCalendarStore(catalog, source_id=SOURCE)
            item = OutlookCalendarDeltaObservationItem(
                event_id="resource",
                kind="upsert",
                raw=winner,
                observed_at=WHEN,
                evidence_id="ordered",
                run_id="original-run",
                attempt=0,
                page_number=1,
                entry_index=1,
                start_datetime="2026-09-01T00:00:00Z",
                end_datetime="2026-10-01T00:00:00Z",
            )
            store.persist_delta_observation(item)
            store.persist_delta_observation(
                replace(item, run_id="current-acquisition-run", attempt=1)
            )
        else:
            with catalog.writer_session() as session:
                session.execute(
                    text(
                        "UPDATE raw_http_evidence SET run_id='current-acquisition-run' "
                        "WHERE evidence_id='ordered'"
                    )
                )
            store = OneDriveStore(catalog, source_id=SOURCE)
            store.persist_resync_observation(
                OneDriveDeltaResyncObservationItem.from_graph(
                    network,
                    observed_at=WHEN,
                    evidence_id="ordered",
                    run_id="current-acquisition-run",
                    reset_attempt=1,
                    base_revision=1,
                    page_number=1,
                    entry_index=1,
                )
            )
        with catalog.Session() as session:
            facts = [
                FactSpec.from_json(p)
                for p in session.scalars(
                    select(AcquisitionFact.payload).where(
                        AcquisitionFact.run_id == "current-acquisition-run"
                    )
                )
            ]
    finally:
        catalog.close()
    seq = publish(saved_catalog, facts, authority=True)

    async def check():
        reader = reader_api(saved_catalog)
        try:
            entry = await reader.catalog.get_release_entry(seq)
            result = await reader.read_entry(entry.reference)
            if result.selection.record.subject != "Winner":
                pytest.fail("Exact winning observation was not reconstructed")
            if "synthetic-download-url" in result.model_dump_json():
                pytest.fail("Sanitized observation exposed a download URL")
            catalog = Catalog(f"sqlite:///{saved_catalog['database']}")
            table = (
                "calendar_delta_observations"
                if stream == "outlook_calendar"
                else "onedrive_delta_resync_observations"
            )
            try:
                with catalog.writer_session() as session:
                    session.execute(text(f"UPDATE {table} SET entry_index=0"))
            finally:
                catalog.close()
            with pytest.raises(SourceReaderError):
                await reader.read_entry(entry.reference)
        finally:
            await reader.close()

    asyncio.run(check())
