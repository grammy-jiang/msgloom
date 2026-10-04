"""Real To Do snapshot and immutable ledger fixtures for Task 9C."""

import json

import pytest
from sqlalchemy import select

from message_ingest.acquisition.handoff import AcquisitionStream, FactSpec
from message_ingest.catalog import Catalog
from message_ingest.catalog.models.handoff import AcquisitionFact
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.sync.microsoft.todo.snapshots import TodoSnapshotStore
from tests.test_todo_sync import _completion, _evidence, _persist_full_snapshot


@pytest.fixture
def catalog(tmp_path):
    """Own one real SQLite catalog for each authority test."""
    value = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    yield value
    value.close()


def snapshot(catalog, run, day, **kwargs):
    """Persist all four families and exact terminal traversal proof."""
    return _persist_full_snapshot(
        catalog,
        source_id="source",
        run_id=run,
        observed_at=f"2026-10-{day:02d}T00:00:00Z",
        **kwargs,
    )


def empty_snapshot(catalog, run, day):
    """Persist a genuinely complete empty source enumeration."""
    timestamp = f"2026-10-{day:02d}T00:00:00Z"
    _evidence(
        catalog,
        evidence_id=f"ev-{run}",
        source_id="source",
        run_id=run,
        observed_at=timestamp,
    )
    store = TodoSnapshotStore(catalog, source_id="source")
    store.record_completion(
        _completion(
            "task_lists",
            run_id=run,
            evidence_id=f"ev-{run}",
            observed_at=timestamp,
        )
    )
    return store


def promote(store, run):
    """Use the production candidate and revision-CAS boundary."""
    base = store.load_revision()
    store.stage_candidate(run, base_revision=base)
    return store.promote_snapshot(run, base_revision=base)


def entries(catalog):
    """Read and validate the public immutable feed."""
    return AcquisitionHandoffStore(catalog).list_release_entries(
        "source",
        AcquisitionStream.TODO,
        limit=1000,
    )


def released_facts(catalog):
    """Resolve exact release members through the production ledger reader."""
    store = AcquisitionHandoffStore(catalog)
    return [
        fact
        for entry in entries(catalog)
        for fact in store.load_release_facts(entry["release_entry_seq"])
    ]


def staged(catalog, run):
    """Inspect immutable provider facts independently of publication."""
    with catalog.Session() as session:
        return [
            FactSpec.from_json(row)
            for row in session.scalars(
                select(AcquisitionFact.payload).where(
                    AcquisitionFact.run_id == run,
                )
            )
        ]


def dump(catalog):
    """Capture every authority and ledger row to detect partial rollback."""
    with catalog.Session() as session:
        tables = (
            session.connection()
            .exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND (name LIKE 'todo_%' OR name LIKE 'acquisition_%')"
            )
            .scalars()
            .all()
        )
        return {
            name: sorted(
                json.dumps(list(row), sort_keys=True, default=str)
                for row in session.connection().exec_driver_sql(
                    f'SELECT * FROM "{name}"'
                )
            )
            for name in tables
        }
