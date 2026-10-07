"""Verify shared snapshot/delta authority ordering across Contacts stores."""

from concurrent.futures import ThreadPoolExecutor
from typing import Literal

import pytest

from message_ingest.catalog import Catalog
from message_ingest.catalog.models.microsoft.contacts import (
    ContactDeltaCheckpoint,
    ContactPresence,
    ContactRecord,
)
from message_ingest.catalog.stores.microsoft.contacts import ContactsStore
from message_ingest.items.microsoft.contacts import (
    ContactCollectionCompleteItem,
    ContactDeltaCheckpointCandidateItem,
    ContactFolderItem,
    ContactItem,
)


def _folder(run: str, observed: str) -> ContactFolderItem:
    return ContactFolderItem.from_graph(
        {"id": "folder-a", "displayName": ""},
        observed_at=observed,
        evidence_id="evidence-folder",
        run_id=run,
        run_started_at=observed,
    )


def _contact(
    *,
    run: str,
    observed: str,
    company: str,
    kind: str = "snapshot",
) -> ContactItem:
    return ContactItem.from_graph(
        {"id": "target", "displayName": "", "companyName": company},
        folder_id="folder-a",
        is_default_scope=False,
        observation_kind=kind,
        observed_at=observed,
        evidence_id="evidence-contact",
        run_id=run,
        run_started_at=observed,
    )


def _completion(
    kind: Literal["folder_inventory", "child_folders", "contacts"],
    *,
    run: str,
    observed: str,
    folder: bool = False,
    default: bool = False,
) -> ContactCollectionCompleteItem:
    return ContactCollectionCompleteItem(
        collection_kind=kind,
        folder_id="folder-a" if folder else None,
        is_default_scope=default,
        observed_at=observed,
        evidence_id="evidence-complete",
        run_id=run,
        run_started_at=observed,
    )


def _stage_snapshot(store: ContactsStore, *, run: str) -> None:
    observed = "2026-10-01T00:01:00Z"
    store.begin_snapshot_run(run)
    store.persist_folder(_folder(run, observed))
    store.persist_contact(_contact(run=run, observed=observed, company="new"))
    store.persist_completion(
        _completion("folder_inventory", run=run, observed=observed)
    )
    store.persist_completion(
        _completion("contacts", run=run, observed=observed, default=True)
    )
    store.persist_completion(
        _completion("child_folders", run=run, observed=observed, folder=True)
    )
    store.persist_completion(
        _completion("contacts", run=run, observed=observed, folder=True)
    )


def _stage_delta(store: ContactsStore, *, run: str) -> None:
    store.begin_delta_run(folder_id="folder-a", run_id=run)
    observed = "2026-09-30T00:01:00Z"
    for company in ("old-first", "old-last"):
        store.persist_delta_observation(
            _contact(
                run=run,
                observed=observed,
                company=company,
                kind="delta",
            )
        )
    store.stage_delta_candidate(
        ContactDeltaCheckpointCandidateItem(
            folder_id="folder-a",
            delta_link="https://graph.example.test/opaque?$deltatoken=target",
            base_revision=None,
            observed_at="2026-09-30T00:02:00Z",
            evidence_id="evidence-delta",
            run_id=run,
        )
    )


def _seed(store: ContactsStore) -> None:
    store.persist_contact(
        _contact(
            run="seed",
            observed="2026-09-28T00:01:00Z",
            company="seed",
        )
    )


def _current(session):
    identity = {
        "source_id": "contacts-source",
        "scope_key": "folder:folder-a",
        "contact_id": "target",
    }
    return (
        session.get(ContactRecord, identity),
        session.get(ContactPresence, identity),
    )


def test_snapshot_promotion_wins_shared_generation_over_older_delta(tmp_path):
    url = f"sqlite:///{tmp_path / 'overlap.sqlite3'}"
    first_catalog = Catalog(url)
    second_catalog = Catalog(url)
    try:
        delta_store = ContactsStore(first_catalog, source_id="contacts-source")
        snapshot_store = ContactsStore(second_catalog, source_id="contacts-source")
        _seed(delta_store)
        _stage_delta(delta_store, run="delta-old")
        _stage_snapshot(snapshot_store, run="snapshot-new")
        snapshot_store.promote_snapshot("snapshot-new")
        with pytest.raises(RuntimeError, match="generation is stale"):
            delta_store.promote_delta(
                folder_id="folder-a", run_id="delta-old", base_revision=None
            )
        with first_catalog.Session() as session:
            row, presence = _current(session)
            checkpoint = session.get(
                ContactDeltaCheckpoint,
                {"source_id": "contacts-source", "folder_id": "folder-a"},
            )
            if (
                row is None
                or row.company_name != "new"
                or row.latest_observed_at != "2026-10-01T00:01:00Z"
            ):
                pytest.fail("Rejected older delta replaced newer snapshot metadata")
            if presence is None or presence.latest_run_id != "snapshot-new":
                pytest.fail("Rejected older delta changed snapshot presence")
            if checkpoint is not None:
                pytest.fail("Rejected older delta advanced its cursor")
    finally:
        second_catalog.close()
        first_catalog.close()


def test_delta_promotion_wins_without_overwriting_newer_saved_state(tmp_path):
    url = f"sqlite:///{tmp_path / 'reverse-overlap.sqlite3'}"
    first_catalog = Catalog(url)
    second_catalog = Catalog(url)
    try:
        delta_store = ContactsStore(first_catalog, source_id="contacts-source")
        snapshot_store = ContactsStore(second_catalog, source_id="contacts-source")
        _seed(delta_store)
        _stage_delta(delta_store, run="delta-old")
        _stage_snapshot(snapshot_store, run="snapshot-new")
        checkpoint = delta_store.promote_delta(
            folder_id="folder-a", run_id="delta-old", base_revision=None
        )
        if checkpoint.revision != 1:
            pytest.fail("Winning delta did not advance its cursor")
        with pytest.raises(RuntimeError, match="generation is stale"):
            snapshot_store.promote_snapshot("snapshot-new")
        with first_catalog.Session() as session:
            row, presence = _current(session)
            committed = session.get(
                ContactDeltaCheckpoint,
                {"source_id": "contacts-source", "folder_id": "folder-a"},
            )
            if (
                row is None
                or row.company_name != "new"
                or row.latest_observed_at != "2026-10-01T00:01:00Z"
            ):
                pytest.fail("Older delta overwrote a newer saved observation")
            if presence is not None:
                pytest.fail("Stale delta or rejected snapshot changed presence")
            if committed is None or committed.run_id != "delta-old":
                pytest.fail("Snapshot conflict changed the winning delta cursor")
    finally:
        second_catalog.close()
        first_catalog.close()


def test_ordered_delta_chain_is_last_wins_at_equal_observation_time(tmp_path):
    catalog = Catalog(f"sqlite:///{tmp_path / 'chain.sqlite3'}")
    try:
        store = ContactsStore(catalog, source_id="contacts-source")
        _seed(store)
        _stage_delta(store, run="delta-chain")
        store.promote_delta(
            folder_id="folder-a", run_id="delta-chain", base_revision=None
        )
        with catalog.Session() as session:
            row, _presence = _current(session)
            if row is None or row.company_name != "old-last":
                pytest.fail("Ordered delta chain did not preserve last-wins semantics")
    finally:
        catalog.close()


def test_two_catalog_promotions_serialize_and_one_generation_wins(tmp_path):
    url = f"sqlite:///{tmp_path / 'concurrent.sqlite3'}"
    first_catalog = Catalog(url)
    second_catalog = Catalog(url)
    try:
        first = ContactsStore(first_catalog, source_id="contacts-source")
        second = ContactsStore(second_catalog, source_id="contacts-source")
        _stage_delta(first, run="delta-first")
        _stage_delta(second, run="delta-second")

        def promote(store: ContactsStore, run: str) -> str:
            try:
                store.promote_delta(
                    folder_id="folder-a", run_id=run, base_revision=None
                )
            except RuntimeError:
                return "stale"
            return "committed"

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(promote, first, "delta-first"),
                executor.submit(promote, second, "delta-second"),
            ]
            values = sorted(future.result(timeout=10) for future in futures)
        if values != ["committed", "stale"]:
            pytest.fail(f"Cross-Catalog promotion CAS was not serialized: {values!r}")
        with first_catalog.Session() as session:
            checkpoint = session.get(
                ContactDeltaCheckpoint,
                {"source_id": "contacts-source", "folder_id": "folder-a"},
            )
            if checkpoint is None or checkpoint.revision != 1:
                pytest.fail("Concurrent promotions advanced more than one cursor")
    finally:
        second_catalog.close()
        first_catalog.close()
