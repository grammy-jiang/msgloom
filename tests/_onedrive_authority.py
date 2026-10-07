"""Build local OneDrive authority fixtures without network or credentials."""

import json

import pytest
from sqlalchemy import select

from message_ingest.acquisition.handoff import AcquisitionStream, FactSpec
from message_ingest.catalog import Catalog
from message_ingest.catalog.models.handoff import (
    AcquisitionEffectiveState,
    AcquisitionFact,
    AcquisitionReleaseEntry,
    AcquisitionReleaseEntryFact,
    AcquisitionReleaseGroup,
)
from message_ingest.catalog.models.microsoft.onedrive import (
    OneDriveDeltaCheckpoint,
    OneDriveItemRecord,
)
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.catalog.stores.microsoft.onedrive import OneDriveStore
from message_ingest.items.microsoft.onedrive import (
    OneDriveDeltaResyncAttemptItem,
    OneDriveDeltaResyncObservationItem,
    OneDriveItem,
)
from tests.test_onedrive_resync import _candidate, _evidence

T0 = "2026-10-01T00:00:00+00:00"
T1 = "2026-10-01T01:00:00+00:00"
T2 = "2026-10-01T02:00:00+00:00"
T3 = "2026-10-01T03:00:00+00:00"


@pytest.fixture
def catalog(tmp_path):
    """Close each isolated database after testing."""
    instance = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        yield instance
    finally:
        instance.close()


def store(catalog):
    """Use the real provider store for every fixture write."""
    return OneDriveStore(
        catalog, source_id="source", spider_name="microsoft_onedrive_delta"
    )


def item(catalog, run, identity="item", *, at=T0, tag="A", raw=None):
    """Persist one exact metadata capture with committed evidence."""
    evidence = f"{run}-{identity}-{tag}"
    _evidence(catalog, evidence, run, at)
    value = OneDriveItem.from_graph(
        raw or {"id": identity, "name": "private-name", "eTag": tag},
        observed_at=at,
        evidence_id=evidence,
        run_id=run,
    )
    store(catalog).persist_item(value)
    return value


def candidate(catalog, run, base, *, at=T3):
    """Stage a terminal candidate without granting release authority."""
    evidence = f"{run}-terminal"
    _evidence(catalog, evidence, run, at)
    store(catalog).persist_candidate(
        _candidate(run, base, evidence, at, f"opaque-private-cursor-{run}")
    )


def promote(catalog, run, base, *, reset=None):
    """Invoke the public checkpoint owner, including its CAS decision."""
    return store(catalog).promote_checkpoint(
        run_id=run, base_revision=base, reset_attempt=reset
    )


def base(catalog):
    """Commit a base cursor with no resource effects."""
    candidate(catalog, "base", None, at=T0)
    promote(catalog, "base", None)


def start_reset(catalog, run="reset", *, base_revision=1):
    """Persist the existing one-reset attempt contract."""
    evidence = f"{run}-trigger"
    _evidence(catalog, evidence, run, T1)
    store(catalog).persist_resync_attempt(
        OneDriveDeltaResyncAttemptItem(
            reset_attempt=1,
            base_revision=base_revision,
            started_at=T1,
            trigger_evidence_id=evidence,
            run_id=run,
        )
    )


def sighting(catalog, raw, *, run="reset", base_revision=1, page=1, index=0, at=T2):
    """Stage exact page/entry ordering, including repeated resource IDs."""
    evidence = f"{run}-page-{page}-{index}"
    _evidence(catalog, evidence, run, at)
    store(catalog).persist_resync_observation(
        OneDriveDeltaResyncObservationItem.from_graph(
            raw,
            observed_at=at,
            evidence_id=evidence,
            run_id=run,
            reset_attempt=1,
            base_revision=base_revision,
            page_number=page,
            entry_index=index,
        )
    )


def groups(catalog):
    """Return immutable authority metadata."""
    with catalog.Session() as session:
        return [
            json.loads(payload)
            for payload in session.scalars(select(AcquisitionReleaseGroup.payload))
        ]


def released(catalog):
    """Read public immutable entries and their exact fact associations."""
    ledger = AcquisitionHandoffStore(catalog)
    return [
        (
            json.loads(row["payload"]),
            ledger.load_release_facts(row["release_entry_seq"]),
        )
        for row in ledger.list_release_entries("source", AcquisitionStream.ONEDRIVE)
    ]


def primary(catalog):
    """Separate primary observations from scoped transition entries."""
    return [
        fact
        for entry, facts in released(catalog)
        if entry["entry_kind"] == "resource"
        for fact in facts
    ]


def transitions(catalog):
    """Read exact scoped authority facts."""
    return [
        fact
        for entry, facts in released(catalog)
        if entry["entry_kind"] == "transition"
        for fact in facts
    ]


def run_facts(catalog, run):
    """Read durable staging independently of provider current rows."""
    with catalog.Session() as session:
        return [
            FactSpec.from_json(payload)
            for payload in session.scalars(
                select(AcquisitionFact.payload).where(AcquisitionFact.run_id == run)
            )
        ]


def snapshot(catalog):
    """Freeze all rows that promotion must restore after publication failure."""
    tables = (
        OneDriveDeltaCheckpoint,
        OneDriveItemRecord,
        AcquisitionFact,
        AcquisitionEffectiveState,
        AcquisitionReleaseGroup,
        AcquisitionReleaseEntry,
        AcquisitionReleaseEntryFact,
    )
    with catalog.Session() as session:
        return [session.execute(select(model.__table__)).all() for model in tables]
