"""Verify Contacts snapshot presence and staged custom-folder delta state."""

import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, select
from test_catalog_model_package_layout import (
    MAIL_BINDING_TABLE_NAMES,
    PRE_MAIL_BINDING_TABLE_NAMES,
)

from message_ingest.catalog import Base, Catalog
from message_ingest.catalog.models.microsoft.contacts import (
    ContactDeltaCheckpoint,
    ContactPresence,
    ContactRecord,
    ContactsSnapshotState,
)
from message_ingest.catalog.stores.microsoft.contacts import ContactsStore
from message_ingest.items.microsoft.contacts import (
    ContactCollectionCompleteItem,
    ContactDeltaCheckpointCandidateItem,
    ContactFolderItem,
    ContactItem,
)


def test_contacts_schema_is_additive_and_preserves_existing_data(tmp_path):
    """Add Contacts and Mail bindings while preserving pre-Mail history."""
    url = f"sqlite:///{tmp_path / 'existing.sqlite3'}"
    expected = {
        "contact_folders",
        "contact_folder_presence",
        "contact_folder_sightings",
        "contacts",
        "contact_presence",
        "contact_sightings",
        "contact_collection_completions",
        "contacts_snapshot_state",
        "contact_delta_observations",
        "contact_delta_checkpoint_candidates",
        "contact_delta_checkpoints",
        "contact_promotion_bases",
        "contact_promotion_generations",
    }
    engine = create_engine(url)
    try:
        Base.metadata.create_all(
            engine,
            tables=[
                Base.metadata.tables[name]
                for name in sorted(PRE_MAIL_BINDING_TABLE_NAMES - set(expected))
            ],
        )
        with engine.begin() as connection:
            connection.exec_driver_sql("CREATE TABLE preserved (value TEXT)")
            connection.exec_driver_sql("INSERT INTO preserved VALUES ('old data')")
            connection.exec_driver_sql(
                "CREATE INDEX preserved_value ON preserved(value)"
            )
            before_schema = {
                name: sql
                for name, sql in connection.exec_driver_sql(
                    "SELECT name, sql FROM sqlite_master"
                )
            }
        before = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    catalog = Catalog(url)
    try:
        schema = inspect(catalog.engine)
        if (
            set(schema.get_table_names()) - before
            != expected | MAIL_BINDING_TABLE_NAMES
        ):
            pytest.fail("Contacts schema initialization was not additive")
        with catalog.engine.connect() as connection:
            after_schema = {
                name: sql
                for name, sql in connection.exec_driver_sql(
                    "SELECT name, sql FROM sqlite_master"
                )
            }
            if not before_schema.items() <= after_schema.items():
                pytest.fail(
                    "Additive initialization changed existing schema or indexes"
                )
            if (
                connection.exec_driver_sql("SELECT value FROM preserved").scalar()
                != "old data"
            ):
                pytest.fail("Contacts schema initialization changed existing data")
    finally:
        catalog.close()


def test_fresh_process_catalog_registers_contacts_without_store_import(tmp_path):
    url = f"sqlite:///{tmp_path / 'fresh.sqlite3'}"
    code = f"""
from sqlalchemy import inspect
from message_ingest.catalog import Catalog
catalog = Catalog({url!r})
try:
    names = sorted(name for name in inspect(catalog.engine).get_table_names()
                   if name.startswith("contact"))
    print(chr(10).join(names))
finally:
    catalog.close()
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        pytest.fail(result.stderr)
    expected = {
        "contact_collection_completions",
        "contact_delta_checkpoint_candidates",
        "contact_delta_checkpoints",
        "contact_delta_observations",
        "contact_folder_presence",
        "contact_folder_sightings",
        "contact_folders",
        "contact_presence",
        "contact_promotion_bases",
        "contact_promotion_generations",
        "contact_sightings",
        "contacts",
        "contacts_snapshot_state",
    }
    if set(result.stdout.splitlines()) != expected:
        pytest.fail(f"Fresh Catalog missed Contacts tables: {result.stdout!r}")


def _folder(
    folder_id,
    *,
    run="run",
    started="2026-09-29T00:00:00Z",
    observed="2026-09-29T00:01:00Z",
):
    return ContactFolderItem.from_graph(
        {"id": folder_id, "displayName": ""},
        observed_at=observed,
        evidence_id="evidence-folder",
        run_id=run,
        run_started_at=started,
    )


def _contact(
    contact_id,
    *,
    folder_id=None,
    default=False,
    kind="snapshot",
    run="run",
    started="2026-09-29T00:00:00Z",
    observed="2026-09-29T00:02:00Z",
    raw=None,
):
    return ContactItem.from_graph(
        {"id": contact_id, "displayName": "", **(raw or {})},
        folder_id=folder_id,
        is_default_scope=default,
        observation_kind=kind,
        observed_at=observed,
        evidence_id="evidence-contact",
        run_id=run,
        run_started_at=started,
    )


def _complete(
    kind,
    *,
    folder_id=None,
    default=False,
    run="run",
    started="2026-09-29T00:00:00Z",
    observed="2026-09-29T00:03:00Z",
):
    return ContactCollectionCompleteItem(
        collection_kind=kind,
        folder_id=folder_id,
        is_default_scope=default,
        observed_at=observed,
        evidence_id="evidence-complete",
        run_id=run,
        run_started_at=started,
    )


def _store(tmp_path, source="contacts-source"):
    catalog = Catalog(f"sqlite:///{tmp_path / (source + '.sqlite3')}")
    return catalog, ContactsStore(catalog, source_id=source)


def _stage_complete_snapshot(store, *, run="run", started="2026-09-29T00:00:00Z"):
    store.begin_snapshot_run(run)
    store.persist_folder(_folder("folder-a", run=run, started=started))
    store.persist_contact(_contact("default-a", default=True, run=run, started=started))
    store.persist_contact(
        _contact("custom-a", folder_id="folder-a", run=run, started=started)
    )
    store.persist_completion(_complete("folder_inventory", run=run, started=started))
    store.persist_completion(
        _complete("contacts", default=True, run=run, started=started)
    )
    store.persist_completion(
        _complete("child_folders", folder_id="folder-a", run=run, started=started)
    )
    store.persist_completion(
        _complete("contacts", folder_id="folder-a", run=run, started=started)
    )


def test_snapshot_promotion_is_atomic_authoritative_and_preserves_history(tmp_path):
    catalog, store = _store(tmp_path)
    try:
        _stage_complete_snapshot(store)
        result = store.promote_snapshot("run")
        if result != {
            "folders_present": 1,
            "folders_absent": 0,
            "contacts_present": 2,
            "contacts_absent": 0,
        }:
            pytest.fail(f"Unexpected first promotion: {result!r}")
        with catalog.Session() as session:
            rows = session.scalars(select(ContactPresence)).all()
            if len(rows) != 2 or not all(row.is_present for row in rows):
                pytest.fail("Complete snapshot did not publish contact presence")
        newer = "2026-09-30T00:00:00Z"
        store.begin_snapshot_run("run-2")
        store.persist_completion(
            _complete("folder_inventory", run="run-2", started=newer)
        )
        store.persist_completion(
            _complete("contacts", default=True, run="run-2", started=newer)
        )
        # No custom folders were sighted, so no custom collection completion is required.
        result = store.promote_snapshot("run-2")
        if result["folders_absent"] != 1 or result["contacts_absent"] != 2:
            pytest.fail("Complete empty snapshot did not mark prior state absent")
        with catalog.Session() as session:
            if len(session.scalars(select(ContactRecord)).all()) != 2:
                pytest.fail("Snapshot absence deleted historical provider data")
            if any(
                row.is_present for row in session.scalars(select(ContactPresence)).all()
            ):
                pytest.fail("Absent contacts remained authoritative-present")
    finally:
        catalog.close()


def test_incomplete_or_stale_snapshot_cannot_change_authoritative_presence(tmp_path):
    catalog, store = _store(tmp_path)
    try:
        _stage_complete_snapshot(store, run="new", started="2026-09-30T00:00:00Z")
        store.promote_snapshot("new")
        store.begin_snapshot_run("old")
        store.persist_folder(
            _folder("folder-a", run="old", started="2026-09-29T00:00:00Z")
        )
        store.persist_completion(
            _complete("folder_inventory", run="old", started="2026-09-29T00:00:00Z")
        )
        store.persist_completion(
            _complete(
                "contacts", default=True, run="old", started="2026-09-29T00:00:00Z"
            )
        )
        with pytest.raises(RuntimeError, match="incomplete"):
            store.promote_snapshot("old")
        _stage_complete_snapshot(
            store, run="old-complete", started="2026-09-29T00:00:00Z"
        )
        with pytest.raises(RuntimeError, match="stale"):
            store.promote_snapshot("old-complete")
        with catalog.Session() as session:
            state = session.get(ContactsSnapshotState, "contacts-source")
            if state is None or state.latest_run_id != "new":
                pytest.fail("Rejected snapshot changed committed run state")
    finally:
        catalog.close()


def test_equal_contact_observation_does_not_replace_conflicting_provider_state(
    tmp_path,
):
    catalog, store = _store(tmp_path)
    try:
        first = _contact("same", default=True, raw={"companyName": "first"})
        second = _contact("same", default=True, raw={"companyName": "second"})
        if store.persist_contact(first) != "created":
            pytest.fail("Initial contact was not created")
        if store.persist_contact(second) != "stale":
            pytest.fail("Equal-time conflicting contact must be rejected")
        with catalog.Session() as session:
            if session.scalars(select(ContactRecord)).one().company_name != "first":
                pytest.fail("Equal observation replaced current contact state")
    finally:
        catalog.close()


def test_custom_folder_delta_stages_changes_and_promotes_cursor_atomically(tmp_path):
    catalog, store = _store(tmp_path)
    try:
        store.persist_contact(
            _contact("contact", folder_id="folder-a", raw={"companyName": "old"})
        )
        store.begin_delta_run(folder_id="folder-a", run_id="delta-run")
        update = _contact(
            "contact",
            folder_id="folder-a",
            kind="delta",
            run="delta-run",
            started="2026-09-30T00:00:00Z",
            observed="2026-09-30T00:01:00Z",
            raw={"companyName": "new"},
        )
        removed = _contact(
            "gone",
            folder_id="folder-a",
            kind="delta",
            run="delta-run",
            started="2026-09-30T00:00:00Z",
            observed="2026-09-30T00:02:00Z",
            raw={"@removed": {"reason": "deleted"}},
        )
        store.persist_delta_observation(update)
        store.persist_delta_observation(removed)
        store.stage_delta_candidate(
            ContactDeltaCheckpointCandidateItem(
                folder_id="folder-a",
                delta_link="https://graph.example.test/opaque?$deltatoken=secret",
                base_revision=None,
                observed_at="2026-09-30T00:03:00Z",
                evidence_id="evidence-delta",
                run_id="delta-run",
            )
        )
        with catalog.Session() as session:
            if (
                session.scalars(select(ContactRecord).filter_by(contact_id="contact"))
                .one()
                .company_name
                != "old"
            ):
                pytest.fail("Uncommitted delta changed authoritative contact state")
        checkpoint = store.promote_delta(
            folder_id="folder-a", run_id="delta-run", base_revision=None
        )
        if checkpoint.revision != 1 or checkpoint.delta_link.find("deltatoken") < 0:
            pytest.fail("Delta cursor was not promoted")
        with catalog.Session() as session:
            row = session.scalars(
                select(ContactRecord).filter_by(contact_id="contact")
            ).one()
            if row.company_name != "new" or row.display_name != "":
                pytest.fail(
                    "Sparse delta update did not merge with preserved provider data"
                )
            gone = session.get(
                ContactPresence,
                {
                    "source_id": "contacts-source",
                    "scope_key": "folder:folder-a",
                    "contact_id": "gone",
                },
            )
            if gone is None or gone.is_present or gone.removed_reason != "deleted":
                pytest.fail("Delta tombstone was not applied on checkpoint promotion")
            if (
                session.get(
                    ContactDeltaCheckpoint,
                    {"source_id": "contacts-source", "folder_id": "folder-a"},
                )
                is None
            ):
                pytest.fail("Delta checkpoint missing after atomic promotion")
    finally:
        catalog.close()


def test_sources_are_isolated(tmp_path):
    catalog = Catalog(f"sqlite:///{tmp_path / 'shared.sqlite3'}")
    try:
        first = ContactsStore(catalog, source_id="first")
        second = ContactsStore(catalog, source_id="second")
        first.persist_contact(_contact("same", default=True))
        second.persist_contact(_contact("same", default=True))
        with catalog.Session() as session:
            if len(session.scalars(select(ContactRecord)).all()) != 2:
                pytest.fail("Contacts from separate logical sources collided")
    finally:
        catalog.close()
