"""Calendar reconstruction consumes producer facts and terminal limitations."""

import asyncio
from pathlib import Path

import pytest
from sqlalchemy import select, text

from message_ingest.acquisition.handoff import FactSpec
from message_ingest.catalog import Catalog
from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.models.handoff import AcquisitionFact
from message_ingest.catalog.stores.microsoft.outlook.calendar import (
    OutlookCalendarStore,
)
from message_ingest.items.microsoft.outlook.calendar import (
    OutlookCalendarEventItem,
    OutlookCalendarSeriesTopologyItem,
)
from msgloom.sources import (
    CollectedSelectionCodec,
    SourceEvidenceError,
    SourceReferenceError,
)
from tests.source_reader.release_nonmail_helpers import (
    SOURCE,
    WHEN,
    publish,
    reader_api,
    save_evidence,
)


def calendar_release(
    saved, *, terminal=False, component_version="v1", proof_version=None
):
    """Use actual Calendar domain writers to obtain immutable exact facts."""
    raw = {
        "id": "event",
        "changeKey": "v1",
        "subject": "Original event",
        "body": {"contentType": "text", "content": "Original body"},
        "start": {"dateTime": "2026-10-01T10:00:00", "timeZone": "UTC"},
        "end": {"dateTime": "2026-10-01T11:00:00", "timeZone": "UTC"},
        "organizer": {"emailAddress": {"address": "owner@example.test"}},
        "attendees": [{"emailAddress": {"address": "guest@example.test"}}],
        "type": "singleInstance",
    }
    if proof_version is not None:
        raw.update(type="occurrence", seriesMasterId="master")
    save_evidence(saved, "event-evidence", {"value": [raw]})
    catalog = Catalog(f"sqlite:///{saved['database']}")
    try:
        store = OutlookCalendarStore(catalog, source_id=SOURCE)
        store.persist_event(
            OutlookCalendarEventItem.from_graph(
                raw,
                observed_at=WHEN,
                evidence_id="event-evidence",
                run_id="current-logical-run",
                calendar_id="calendar",
            )
        )
        if terminal:
            store.set_event_surface(
                event_id="event",
                surface="attachments",
                status="unsupported",
                evidence_id="event-evidence",
                observed_at=WHEN,
                run_id="current-logical-run",
                profile_version="full-v1",
                resource_version=component_version,
            )
        if proof_version is not None:
            master = {
                "id": "master",
                "changeKey": proof_version,
                "type": "seriesMaster",
                "cancelledOccurrences": [],
                "exceptionOccurrences": [],
            }
            save_evidence(saved, "master-evidence", master)
            store.persist_series_topology(
                OutlookCalendarSeriesTopologyItem(
                    series_master_id="master",
                    calendar_id="calendar",
                    status="acquired",
                    raw=master,
                    observed_at=WHEN,
                    evidence_id="master-evidence",
                    run_id="current-logical-run",
                )
            )
        with catalog.Session() as session:
            facts = [
                FactSpec.from_json(row)
                for row in session.scalars(
                    select(AcquisitionFact.payload).where(
                        AcquisitionFact.stream == "outlook_calendar"
                    )
                )
            ]
    finally:
        catalog.close()
    facts.sort(key=lambda fact: fact.component_kind is not None)
    roles = tuple(
        "proof"
        if item.resource_kind == "calendar_series"
        else "component"
        if item.component_kind is not None
        else "primary"
        for item in facts
    )
    return publish(saved, facts, roles=roles)


@pytest.mark.parametrize("proof_version", ["v1", "master-v9"])
def test_calendar_series_proof_keeps_own_resource_version(saved_catalog, proof_version):
    """A master proof must not share its occurrence's change key."""
    seq = calendar_release(saved_catalog, proof_version=proof_version)

    async def check():
        reader = reader_api(saved_catalog)
        try:
            entry = await reader.catalog.get_release_entry(seq)
            if entry is None:
                pytest.fail("Calendar release was not committed")
            facts = await reader.catalog.get_release_facts(entry.reference)
            if tuple(item.role for item in facts) != ("primary", "proof"):
                pytest.fail("Calendar release lost exact fact roles")
            result = await reader.read_entry(entry.reference)
            if result.selection is None:
                pytest.fail("Calendar proof displaced the primary event")
            if result.selection.record.subject != "Original event":
                pytest.fail("Calendar proof replaced the occurrence payload")
            if result.components or result.facts != facts:
                pytest.fail("Calendar proof became material or lost provenance")
            if await reader.read_entry(entry.reference) != result:
                pytest.fail("Calendar proof changed exact replay")
        finally:
            await reader.close()

    asyncio.run(check())


def test_calendar_rejects_mismatched_material_component_version(saved_catalog):
    """Event material still requires the primary event's change key."""
    seq = calendar_release(saved_catalog, terminal=True, component_version="v2")

    async def check():
        reader = reader_api(saved_catalog)
        try:
            entry = await reader.catalog.get_release_entry(seq)
            if entry is None:
                pytest.fail("Calendar release was not committed")
            with pytest.raises(SourceReferenceError, match="component version"):
                await reader.read_entry(entry.reference)
        finally:
            await reader.close()

    asyncio.run(check())


def test_calendar_series_proof_requires_saved_evidence(saved_catalog):
    """Excluding proof from material checks must not bypass its evidence."""
    seq = calendar_release(saved_catalog, proof_version="master-v9")
    catalog = Catalog(f"sqlite:///{saved_catalog['database']}")
    try:
        with catalog.Session() as session:
            proof = session.get(RawHttpEvidence, "master-evidence")
            if proof is None:
                pytest.fail("Calendar proof evidence was not persisted")
            Path(proof.response_body_path).unlink()
    finally:
        catalog.close()

    async def check():
        reader = reader_api(saved_catalog)
        try:
            entry = await reader.catalog.get_release_entry(seq)
            if entry is None:
                pytest.fail("Calendar release was not committed")
            with pytest.raises(SourceEvidenceError):
                await reader.read_entry(entry.reference)
        finally:
            await reader.close()

    asyncio.run(check())


@pytest.mark.parametrize("terminal", [False, True])
def test_calendar_exact_observation_and_terminal_component(saved_catalog, terminal):
    seq = calendar_release(saved_catalog, terminal=terminal)

    async def check():
        reader = reader_api(saved_catalog)
        try:
            entry = await reader.catalog.get_release_entry(seq)
            before = await reader.read_entry(entry.reference)
            record = before.selection.record
            if record.source_type.value != "outlook_calendar":
                pytest.fail("Calendar lost explicit source category")
            if (
                record.subject != "Original event"
                or record.body.content != "Original body"
            ):
                pytest.fail("Calendar exact provider fields lost")
            if record.author.identity != "owner@example.test":
                pytest.fail("Calendar organizer lost")
            if len(record.recipients) != 1:
                pytest.fail("Calendar attendees lost")
            if terminal and not any(
                "unsupported" in item.code for item in record.limitations
            ):
                pytest.fail("Terminal Calendar component limitation disappeared")
            if before.facts[0].run_id != "current-logical-run":
                pytest.fail("Capture owner replaced logical acquisition provenance")
            codec = CollectedSelectionCodec()
            if codec.decode(codec.encode(before.selection)) != before.selection:
                pytest.fail("Calendar selection cannot roundtrip")
            catalog = Catalog(f"sqlite:///{saved_catalog['database']}")
            try:
                with catalog.writer_session() as session:
                    session.execute(
                        text("UPDATE calendar_events SET subject='future', raw='{}'")
                    )
                    session.execute(
                        text(
                            "UPDATE calendar_event_surfaces SET status='acquired', "
                            "resource_version='v2'"
                        )
                    )
            finally:
                catalog.close()
            if await reader.read_entry(entry.reference) != before:
                pytest.fail("Future Calendar projection altered immutable replay")
        finally:
            await reader.close()

    asyncio.run(check())


def test_terminal_component_codec_retains_profile_and_status(saved_catalog):
    """Frozen component replay must retain local terminal outcome semantics."""
    from dataclasses import replace

    from message_ingest.acquisition.handoff import AcquisitionFactKind
    from tests.source_reader.release_nonmail_helpers import fact

    seqs = []
    for profile in ("outlook-calendar-full-v1", "future-fixture-profile"):
        item = replace(
            fact(
                "outlook_calendar",
                "calendar_event_surface",
                "event",
                "ev-contact",
                component_kind="attachments",
            ),
            fact_kind=AcquisitionFactKind.COMPONENT_OBSERVATION,
            parent_resource_kind="calendar_event",
            parent_resource_identity="event",
            transition_reason=(
                '{"profile_version":"' + profile + '","status":"unsupported"}'
            ),
            source_state_key=("a" if profile.endswith("v1") else "b") * 64,
        )
        seqs.append(
            publish(saved_catalog, [item], roles=("component",), entry_kind="component")
        )

    async def check():
        reader = reader_api(saved_catalog)
        try:
            refs = []
            for seq, profile in zip(
                seqs,
                ("outlook-calendar-full-v1", "future-fixture-profile"),
                strict=True,
            ):
                entry = await reader.catalog.get_release_entry(seq)
                result = await reader.read_entry(entry.reference)
                selected = result.components[0]
                codec = CollectedSelectionCodec()
                decoded = codec.decode(codec.encode(selected))
                fields = {item.name: item.value for item in decoded.record.metadata}
                if (
                    fields.get("profile_version") != profile
                    or fields.get("status") != "unsupported"
                ):
                    pytest.fail("Component replay lost immutable terminal semantics")
                refs.append(decoded.source)
            if refs[0] == refs[1]:
                pytest.fail("Different terminal profiles aliased one component version")
        finally:
            await reader.close()

    asyncio.run(check())
