"""Mail authority publication shares the provider transaction."""

import json

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError
from test_outlook_mail_atomic_promotion import (
    SOURCE,
    _catalog,
    _seed_baseline,
    _stage_current,
)

from message_ingest.sync.microsoft.outlook.email.promotion import (
    promote_validated_mail_delta,
)


def test_release_failure_rolls_back_authority(tmp_path):
    catalog = _catalog(tmp_path)
    try:
        store, checkpoints = _seed_baseline(catalog)
        validated = _stage_current(store, checkpoints)
        with catalog.writer_session() as session:
            session.execute(
                text(
                    "CREATE TRIGGER fail_mail_release BEFORE INSERT ON "
                    "acquisition_release_groups BEGIN SELECT "
                    "RAISE(ABORT, 'release fault'); END"
                )
            )
        with pytest.raises(DatabaseError, match="release fault"):
            promote_validated_mail_delta(catalog, source_id=SOURCE, validated=validated)
        if store.message_presence(message_id="gone") is not True:
            pytest.fail("Release failure committed message absence")
        if store.folder_presence(folder_id="removed") is not True:
            pytest.fail("Release failure committed folder absence")
        if "old" not in (checkpoints.get_delta_link("keep") or ""):
            pytest.fail("Release failure advanced the cursor")
    finally:
        catalog.close()


def test_promotion_publishes_scoped_transition_and_is_idempotent(tmp_path):
    catalog = _catalog(tmp_path)
    try:
        store, checkpoints = _seed_baseline(catalog)
        validated = _stage_current(store, checkpoints)
        for _ in range(2):
            promote_validated_mail_delta(catalog, source_id=SOURCE, validated=validated)
        with catalog.Session() as session:
            payloads = (
                session.execute(text("SELECT payload FROM acquisition_release_entries"))
                .scalars()
                .all()
            )
            groups = session.execute(
                text("SELECT count(*) FROM acquisition_release_groups")
            ).scalar_one()
        entries = [json.loads(value) for value in payloads]
        absent = [e for e in entries if e["resource_identity"] == "gone"]
        if groups != 1 or len(absent) != 1:
            pytest.fail("Authority release missing or duplicated")
        if absent[0]["scope_kind"] != "mailbox":
            pytest.fail("Mailbox reconciliation lost its exact scope")
    finally:
        catalog.close()


def test_folder_release_failure_retains_presence_and_message_cursor(tmp_path):
    from message_ingest.sync.microsoft.outlook.email.checkpoints import (
        OutlookFolderDeltaCheckpointStore,
    )

    catalog = _catalog(tmp_path)
    try:
        store, checkpoints = _seed_baseline(catalog)
        folders = OutlookFolderDeltaCheckpointStore(catalog, SOURCE)
        folders.write_candidate(
            run_id="folders",
            delta_link="folder-new",
            observed_at="2026-10-01T00:00:00+00:00",
        )
        store.mark_folder_removed(
            folder_id="keep",
            run_id="folders",
            observed_at="2026-10-01T00:00:00+00:00",
            evidence_id=None,
            reason="deleted",
        )
        if store.folder_presence(folder_id="keep") is not True:
            pytest.fail("Staging a tombstone changed committed presence")
        with catalog.writer_session() as session:
            session.execute(
                text(
                    "CREATE TRIGGER fail_mail_release BEFORE INSERT ON "
                    "acquisition_release_groups BEGIN SELECT "
                    "RAISE(ABORT, 'release fault'); END"
                )
            )
        with pytest.raises(DatabaseError, match="release fault"):
            folders.commit("folders")
        if folders.get_delta_link() is not None:
            pytest.fail("Failed folder release advanced its cursor")
        if store.folder_presence(folder_id="keep") is not True:
            pytest.fail("Failed folder release committed its tombstone")
        if checkpoints.get_delta_link("keep") is None:
            pytest.fail("Failed folder release removed its message cursor")
        with catalog.writer_session() as session:
            session.execute(text("DROP TRIGGER fail_mail_release"))
        folders.commit("folders")
        if store.folder_presence(folder_id="keep") is not False:
            pytest.fail("Successful folder release omitted its tombstone")
        if checkpoints.get_delta_link("keep") is not None:
            pytest.fail("Successful folder release kept its invalid cursor")
        if store.message_presence(message_id="present") is not True:
            pytest.fail("Folder removal fabricated mailbox message deletion")
    finally:
        catalog.close()
