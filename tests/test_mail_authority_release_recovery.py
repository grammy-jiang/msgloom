"""
Mail releases recover exact unreleased state and isolate source ownership.
"""

import json

import pytest
from sqlalchemy import text
from test_outlook_mail_atomic_promotion import SOURCE, _catalog

from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from message_ingest.sync.microsoft.outlook.email.checkpoints import (
    OutlookFolderDeltaCheckpointStore,
)


def _folder(store, run, when, name="Folder"):
    store.upsert_folder(
        folder={"id": "f", "displayName": name},
        evidence_id=None,
        observed_at=when,
        run_id=run,
    )


def _commit(catalog, source, run):
    checkpoints = OutlookFolderDeltaCheckpointStore(catalog, source)
    checkpoints.write_candidate(
        run_id=run, delta_link=run, observed_at="2026-10-01T00:00:00+00:00"
    )
    checkpoints.commit(run)


def _entries(catalog):
    with catalog.Session() as session:
        return [
            json.loads(value)
            for value in session.scalars(
                text("SELECT payload FROM acquisition_release_entries")
            )
        ]


def test_unreleased_equivalent_recovers_once_and_source_isolated(tmp_path):
    catalog = _catalog(tmp_path)
    try:
        store = OutlookMailStore(catalog, source_id=SOURCE)
        other = OutlookMailStore(catalog, source_id="other")
        _folder(store, "unreleased", "2026-10-01T00:00:00+00:00")
        _folder(other, "recovery", "2026-10-01T00:00:00+00:00")
        _folder(store, "recovery", "2026-10-02T00:00:00+00:00")
        _commit(catalog, SOURCE, "recovery")
        if len(_entries(catalog)) != 1:
            pytest.fail("Exact unreleased folder state did not recover")
        _folder(store, "unchanged", "2026-10-03T00:00:00+00:00")
        _commit(catalog, SOURCE, "unchanged")
        if len(_entries(catalog)) != 1:
            pytest.fail("Released unchanged state generated repeated work")
        with catalog.Session() as session:
            sources = list(
                session.scalars(
                    text("SELECT DISTINCT source_id FROM acquisition_release_groups")
                )
            )
        if sources != [SOURCE]:
            pytest.fail("One source released another source's facts")
    finally:
        catalog.close()


def test_displaced_pending_folder_tombstone_does_not_remove_newer_folder(tmp_path):
    catalog = _catalog(tmp_path)
    try:
        store = OutlookMailStore(catalog, source_id=SOURCE)
        _folder(store, "baseline", "2026-10-01T00:00:00+00:00")
        store.mark_folder_removed(
            folder_id="f",
            run_id="old",
            observed_at="2026-10-02T00:00:00+00:00",
            evidence_id=None,
            reason="deleted",
        )
        _folder(store, "newer", "2026-10-03T00:00:00+00:00")
        _commit(catalog, SOURCE, "old")
        if store.folder_presence(folder_id="f") is not True or _entries(catalog):
            pytest.fail("Displaced tombstone became an authority impact")
    finally:
        catalog.close()


def test_newer_staged_positive_folder_displaces_older_tombstone(tmp_path):
    catalog = _catalog(tmp_path)
    try:
        store = OutlookMailStore(catalog, source_id=SOURCE)
        _folder(store, "baseline", "2026-10-01T00:00:00+00:00")
        store.mark_folder_removed(
            folder_id="f",
            run_id="old",
            observed_at="2026-10-02T00:00:00+00:00",
            evidence_id=None,
            reason="deleted",
        )
        newer = OutlookMailStore(
            catalog, source_id=SOURCE, spider_name="outlook_folder_delta"
        )
        _folder(newer, "newer", "2026-10-03T00:00:00+00:00", name="Renamed")
        _commit(catalog, SOURCE, "old")
        if store.folder_presence(folder_id="f") is not True or _entries(catalog):
            pytest.fail("Older authority displaced a newer accepted observation")
    finally:
        catalog.close()


def test_authority_winner_does_not_group_displaced_current_fact(tmp_path):
    catalog = _catalog(tmp_path)
    try:
        store = OutlookMailStore(catalog, source_id=SOURCE)
        _folder(store, "same-run", "2026-10-01T00:00:00+00:00")
        store.mark_folder_removed(
            folder_id="f",
            run_id="same-run",
            observed_at="2026-10-02T00:00:00+00:00",
            evidence_id=None,
            reason="deleted",
        )
        _commit(catalog, SOURCE, "same-run")
        entries = _entries(catalog)
        if {entry["entry_kind"] for entry in entries} != {"context", "transition"}:
            pytest.fail("Displaced current context suppressed the winning context")
    finally:
        catalog.close()
