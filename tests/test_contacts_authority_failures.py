"""Prove Contacts provider and release state roll back in one transaction."""

import pytest
from sqlalchemy.exc import IntegrityError

from tests._contacts_authority import (
    database_rows,
    delta,
    open_store,
    reject_release,
    snapshot,
)

TABLES = (
    "contacts",
    "contact_presence",
    "contact_folder_presence",
    "contacts_snapshot_state",
    "contact_promotion_generations",
    "contact_delta_checkpoints",
    "contact_delta_checkpoint_candidates",
    "contact_delta_observations",
    "acquisition_facts",
    "acquisition_effective_states",
    "acquisition_release_groups",
    "acquisition_release_entries",
    "acquisition_release_entry_facts",
)


@pytest.mark.parametrize("mode", ["snapshot", "delta"])
@pytest.mark.parametrize(
    "target",
    [
        "acquisition_facts",
        "acquisition_release_groups",
        "acquisition_release_entries",
        "acquisition_release_entry_facts",
    ],
)
def test_release_failure_rolls_back_provider_authority_and_ledger(
    tmp_path, mode, target
):
    """
    Late publication failure cannot leave cursor, presence, or partial feed.
    """
    catalog, store = open_store(tmp_path / "rollback.db")
    try:
        snapshot(store, "seed", 1)
        store.promote_snapshot("seed")
        if mode == "snapshot":
            snapshot(store, "next", 2, populated=False)
        else:
            delta(
                store,
                "next",
                2,
                [{"jobTitle": "changed"}, {"id": "gone", "@removed": {}}],
            )
        before = database_rows(catalog, TABLES)
        reject_release(catalog, target)
        with pytest.raises(IntegrityError, match="injected release failure"):
            if mode == "snapshot":
                store.promote_snapshot("next")
            else:
                store.promote_delta(
                    folder_id="folder", run_id="next", base_revision=None
                )
        if database_rows(catalog, TABLES) != before:
            pytest.fail("Release failure left provider or handoff mutation committed")
    finally:
        catalog.close()
