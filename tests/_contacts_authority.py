"""Local fixtures for atomic Contacts authority publication tests."""

import json
from dataclasses import replace
from pathlib import Path

from sqlalchemy import select

from message_ingest.acquisition.handoff import AcquisitionStream, FactSpec
from message_ingest.catalog import Catalog
from message_ingest.catalog.models.handoff import AcquisitionReleaseGroup
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.catalog.stores.microsoft.contacts import ContactsStore
from message_ingest.items.microsoft.contacts import ContactDeltaCheckpointCandidateItem
from tests.test_contacts_catalog import _complete, _contact, _folder


def open_store(path: Path) -> tuple[Catalog, ContactsStore]:
    """Open one isolated local provider catalog."""
    catalog = Catalog(f"sqlite:///{path}")
    return catalog, ContactsStore(catalog, source_id="source")


def stamp(day: int) -> str:
    """Return distinct ordered times without consulting publication order."""
    return f"2026-10-{day:02d}T00:00:00Z"


def snapshot(store, run, day, *, populated=True, complete=True):
    """Stage source-wide traversal with default and custom collections."""
    observed = stamp(day)
    store.begin_snapshot_run(run)
    if populated:
        store.persist_folder(
            _folder("folder", run=run, started=observed, observed=observed)
        )
        for identity, folder, default in (
            ("contact", "folder", False),
            ("default-contact", None, True),
        ):
            store.persist_contact(
                _contact(
                    identity,
                    folder_id=folder,
                    default=default,
                    run=run,
                    started=observed,
                    observed=observed,
                    raw={"companyName": "original"},
                )
            )
    completions: list[tuple[str, str | None, bool]] = [
        ("folder_inventory", None, False)
    ]
    if complete:
        completions.append(("contacts", None, True))
        if populated:
            completions.extend(
                [("child_folders", "folder", False), ("contacts", "folder", False)]
            )
    for kind, folder, default in completions:
        store.persist_completion(
            _complete(
                kind,
                folder_id=folder,
                default=default,
                run=run,
                started=observed,
                observed=observed,
            )
        )


def delta(store, run, day, raws, *, candidate=True):
    """Stage ordered sparse observations and optional terminal cursor."""
    current = store.begin_delta_run(folder_id="folder", run_id=run)
    revision = current.revision if current else None
    for index, raw in enumerate(raws):
        item = _contact(
            str(raw.get("id", "contact")),
            folder_id="folder",
            kind="delta",
            run=run,
            started=stamp(day),
            observed=stamp(day),
            raw=raw,
        )
        store.persist_delta_observation(
            replace(item, evidence_id=f"evidence-{run}-{index}")
        )
    if candidate:
        store.stage_delta_candidate(
            ContactDeltaCheckpointCandidateItem(
                folder_id="folder",
                run_id=run,
                base_revision=revision,
                delta_link="https://graph.example.test/opaque?token=private",
                observed_at=stamp(day),
                evidence_id=f"terminal-{run}",
            )
        )
    return revision


def entries(catalog, run=None):
    """Read committed entries, optionally scoped to their release owner."""
    handoff = AcquisitionHandoffStore(catalog)
    rows = handoff.list_release_entries("source", AcquisitionStream.CONTACTS)
    with catalog.Session() as session:
        groups = {
            row.release_group_id: json.loads(row.payload)
            for row in session.scalars(select(AcquisitionReleaseGroup)).all()
        }
    return [
        (
            json.loads(row["payload"]),
            handoff.load_release_facts(row["release_entry_seq"]),
        )
        for row in rows
        if run is None or groups[row["release_group_id"]]["owner_run_id"] == run
    ]


def primary(catalog, run=None) -> list[FactSpec]:
    """Read resource/context facts without treating transitions as sources."""
    return [
        fact
        for entry, facts in entries(catalog, run)
        for fact in facts
        if entry["entry_kind"] in {"resource", "context"}
        and fact.fact_kind in {"resource_observation", "control_context"}
    ]


def groups(catalog, run):
    """Read immutable group metadata for one owner."""
    with catalog.Session() as session:
        return [
            value
            for row in session.scalars(select(AcquisitionReleaseGroup)).all()
            if (value := json.loads(row.payload))["owner_run_id"] == run
        ]


def database_rows(catalog, tables):
    """Freeze exact table rows to prove transaction-wide rollback."""
    with catalog.engine.connect() as connection:
        return {
            table: connection.exec_driver_sql(
                f"SELECT * FROM {table} ORDER BY 1, 2"
            ).all()
            for table in tables
        }


def reject_release(catalog, table):
    """Fail a real SQLite release insertion after provider mutation starts."""
    with catalog.writer_session() as session:
        session.connection().exec_driver_sql(
            f"CREATE TRIGGER reject_contacts_release BEFORE INSERT ON {table} "
            "BEGIN SELECT RAISE(ABORT, 'injected release failure'); END"
        )
