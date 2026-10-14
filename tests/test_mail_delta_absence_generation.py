"""A folder tombstone invalidates absent Mail delta starts from earlier runs."""

from pathlib import Path

import pytest

from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from message_ingest.sync.microsoft.outlook.email.checkpoints import (
    OutlookDeltaCheckpointStore,
    OutlookFolderDeltaCheckpointStore,
)


def test_predelete_absent_baseline_never_resurrects_removed_folder_cursor(
    tmp_path: Path,
) -> None:
    """A(X absent), B(commit Y), folder tombstone, delayed A(Z) is stale."""
    catalog = Catalog(f"sqlite:///{tmp_path / 'tombstone.db'}")
    try:
        source = "source"
        folder = "inbox"
        mail = OutlookMailStore(catalog, source_id=source)
        store = OutlookDeltaCheckpointStore(catalog, source)
        t0 = "2026-10-14T00:00:00+00:00"
        t1 = "2026-10-14T00:00:01+00:00"
        t2 = "2026-10-14T00:00:02+00:00"
        t3 = "2026-10-14T00:00:03+00:00"
        mail.upsert_folder(
            folder={"id": folder, "displayName": "Inbox"},
            observed_at=t0,
            run_id="inventory",
            evidence_id=None,
        )
        _, a_baseline = store.get_delta_start(folder)
        _, b_baseline = store.get_delta_start(folder)
        if a_baseline != b_baseline:
            pytest.fail("Fixture must start two runs from the same absent cursor")
        store.write_candidate(
            baseline_identity=b_baseline,
            run_id="B",
            folder_id=folder,
            delta_link="Y",
            observed_at=t1,
        )
        store.commit("B")
        mail.mark_folder_removed(
            folder_id=folder,
            run_id="delete",
            observed_at=t2,
            evidence_id=None,
            reason="deleted",
        )
        folder_store = OutlookFolderDeltaCheckpointStore(catalog, source)
        folder_store.write_candidate(
            run_id="delete",
            delta_link="folder-current",
            observed_at=t2,
        )
        folder_store.commit("delete")
        if store.get_delta_link(folder) is not None:
            pytest.fail("Committed folder removal did not invalidate cursor Y")
        _, post_delete_baseline = store.get_delta_start(folder)
        if a_baseline == post_delete_baseline:
            pytest.fail("Folder tombstone reused the previous absent generation")
        # A's Graph response predates the folder removal despite arriving last.
        store.write_candidate(
            baseline_identity=a_baseline,
            run_id="A",
            folder_id=folder,
            delta_link="Z-from-pre-delete",
            observed_at=t3,
        )
        with pytest.raises(RuntimeError, match="displaced"):
            store.commit("A")
        if store.get_delta_link(folder) is not None:
            pytest.fail("Stale A resurrected deleted Mail folder cursor")
        # A new crawl may start safely from the new absent generation.
        store.write_candidate(
            baseline_identity=post_delete_baseline,
            run_id="C",
            folder_id=folder,
            delta_link="C-new",
            observed_at="2026-10-14T00:00:04+00:00",
        )
        store.commit("C")
        if store.get_delta_link(folder) != "C-new":
            pytest.fail("Latest absent generation blocked legitimate new cursor")
    finally:
        catalog.close()
