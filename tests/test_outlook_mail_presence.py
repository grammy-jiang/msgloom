"""Verify Mail folder lifecycle and whole-mailbox presence semantics."""

from __future__ import annotations

from pathlib import Path

import pytest

from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from message_ingest.sync.microsoft.outlook.email.checkpoints import (
    OutlookDeltaCheckpointStore,
)

NOW = "2026-09-28T00:00:00+00:00"


def _catalog(tmp_path: Path) -> Catalog:
    return Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")


def _folder(store: OutlookMailStore, folder_id: str, *, run_id: str) -> None:
    store.upsert_folder(
        folder={
            "id": folder_id,
            "displayName": folder_id,
            "childFolderCount": 0,
            "totalItemCount": 0,
            "unreadItemCount": 0,
            "isHidden": False,
        },
        evidence_id=None,
        observed_at=NOW,
        run_id=run_id,
    )


def _message(store: OutlookMailStore, message_id: str, *, folder_id: str) -> None:
    store.record_message(
        run_id="old-run",
        message={"id": message_id, "parentFolderId": folder_id},
        kind="delta",
        evidence_id=None,
        observed_at=NOW,
    )


def test_complete_folder_snapshot_tombstones_missing_folder_and_drops_cursor(
    tmp_path: Path,
) -> None:
    catalog = _catalog(tmp_path)
    try:
        store = OutlookMailStore(catalog, source_id="source-1")
        checkpoints = OutlookDeltaCheckpointStore(catalog, "source-1")
        for folder_id in ("keep", "removed"):
            _folder(store, folder_id, run_id="baseline")
            checkpoints.write_candidate(
                run_id="baseline",
                folder_id=folder_id,
                delta_link=f"https://graph.test/{folder_id}?$deltatoken=old",
                observed_at=NOW,
            )
        checkpoints.commit("baseline")

        _folder(store, "keep", run_id="current")
        store.write_folder_snapshot_candidate(
            run_id="current", observed_at=NOW, evidence_id=None
        )
        outcome = store.commit_delta_lifecycle(
            "current",
            expected_folder_ids={"keep"},
            reconcile_messages=False,
        )

        if outcome["folders_absent"] != 1:
            pytest.fail("Expected exactly one missing folder tombstone")
        if store.folder_presence(folder_id="keep") is not True:
            pytest.fail("Expected retained folder to remain present")
        if store.folder_presence(folder_id="removed") is not False:
            pytest.fail("Expected missing folder to become absent")
        if checkpoints.get_delta_link("removed") is not None:
            pytest.fail("Expected absent folder's stale message delta cursor removed")
        if checkpoints.get_delta_link("keep") is None:
            pytest.fail("Expected retained folder cursor preserved")
    finally:
        catalog.close()


def test_folder_removal_observation_does_not_imply_global_message_absence(
    tmp_path: Path,
) -> None:
    catalog = _catalog(tmp_path)
    try:
        store = OutlookMailStore(catalog, source_id="source-1")
        _message(store, "m1", folder_id="folder-old")
        store.record_folder_removal(
            run_id="move-run",
            message_id="m1",
            folder_id="folder-old",
            removed_reason="deleted",
            evidence_id=None,
            observed_at=NOW,
        )
        if store.message_presence(message_id="m1") is not True:
            pytest.fail("Per-folder removal must not imply mailbox deletion")
    finally:
        catalog.close()


def test_complete_mailbox_reconciliation_marks_unseen_message_absent_and_filters_planner(
    tmp_path: Path,
) -> None:
    catalog = _catalog(tmp_path)
    try:
        store = OutlookMailStore(catalog, source_id="source-1")
        _message(store, "present", folder_id="inbox")
        _message(store, "gone", folder_id="inbox")
        _folder(store, "inbox", run_id="reconcile-run")
        store.write_folder_snapshot_candidate(
            run_id="reconcile-run", observed_at=NOW, evidence_id=None
        )
        store.record_message_sighting(
            run_id="reconcile-run",
            message_id="present",
            observed_at=NOW,
            evidence_id=None,
        )
        store.write_message_presence_candidate(
            run_id="reconcile-run", observed_at=NOW, evidence_id=None
        )
        store.commit_delta_lifecycle(
            "reconcile-run",
            expected_folder_ids={"inbox"},
            reconcile_messages=True,
        )

        if store.message_presence(message_id="present") is not True:
            pytest.fail("Expected reconciled message to remain present")
        if store.message_presence(message_id="gone") is not False:
            pytest.fail("Expected unseen message to become confirmed absent")
        if store.list_message_ids() != ["present"]:
            pytest.fail("Confirmed-absent messages must be excluded from enrichment")
    finally:
        catalog.close()
