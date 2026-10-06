"""Reject stale authority without changing its cursor or publishing absence."""

import json

import pytest
from sqlalchemy import text
from test_outlook_mail_atomic_promotion import (
    SOURCE,
    _catalog,
    _folder,
    _seed_baseline,
    _stage_current,
)

from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from message_ingest.sync.microsoft.outlook.email.checkpoints import (
    OutlookFolderDeltaCheckpointStore,
)
from message_ingest.sync.microsoft.outlook.email.promotion import (
    promote_validated_mail_delta,
)


@pytest.mark.parametrize("replay", [False, True], ids=["delayed", "a-b-a"])
def test_older_empty_folder_candidate_cannot_rewind_authority(tmp_path, replay):
    catalog = _catalog(tmp_path)
    try:
        folders = OutlookFolderDeltaCheckpointStore(catalog, SOURCE)
        folders.write_candidate(
            run_id="a", delta_link="cursor-a", observed_at="2026-10-01T00:00:00+00:00"
        )
        if replay:
            folders.commit("a")
        folders.write_candidate(
            run_id="b", delta_link="cursor-b", observed_at="2026-10-02T00:00:00+00:00"
        )
        folders.commit("b")
        with catalog.Session() as session:
            before = session.execute(
                text("SELECT * FROM folder_delta_checkpoints")
            ).all()
            groups_before = session.execute(
                text("SELECT * FROM acquisition_release_groups")
            ).all()
        with pytest.raises(RuntimeError, match="displaced"):
            folders.commit("a")
        with catalog.Session() as session:
            after = session.execute(
                text("SELECT * FROM folder_delta_checkpoints")
            ).all()
            groups_after = session.execute(
                text("SELECT * FROM acquisition_release_groups")
            ).all()
        if after != before or folders.get_delta_link() != "cursor-b":
            pytest.fail("Older authority rewound the winning folder cursor")
        if groups_after != groups_before:
            pytest.fail("Displaced authority changed durable release groups")
    finally:
        catalog.close()


def test_inventory_absence_cannot_displace_newer_staged_folder_presence(tmp_path):
    catalog = _catalog(tmp_path)
    try:
        store, checkpoints = _seed_baseline(catalog)
        validated = _stage_current(store, checkpoints)
        newer = OutlookMailStore(
            catalog, source_id=SOURCE, spider_name="outlook_folder_delta"
        )
        _folder(newer, "removed", run_id="newer", when="2026-10-03T00:00:00+00:00")
        outcome = promote_validated_mail_delta(
            catalog, source_id=SOURCE, validated=validated
        )
        if store.folder_presence(folder_id="removed") is not True:
            pytest.fail("Old inventory displaced newer accepted folder metadata")
        if checkpoints.get_delta_link("removed") is None:
            pytest.fail("Old inventory deleted the protected folder cursor")
        if outcome["folders_absent"] != 0:
            pytest.fail("Skipped inventory absence counted as winning state")
        with catalog.Session() as session:
            entries = [
                json.loads(payload)
                for payload in session.scalars(
                    text("SELECT payload FROM acquisition_release_entries")
                )
            ]
        if any(entry["resource_identity"] == "removed" for entry in entries):
            pytest.fail("Old inventory published a false folder absence")
    finally:
        catalog.close()
