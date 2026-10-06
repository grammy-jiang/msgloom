"""Reject lost candidate proof and ambiguous authority observations."""

import pytest
from sqlalchemy import text
from test_outlook_mail_atomic_promotion import (
    SOURCE,
    _catalog,
    _seed_baseline,
    _stage_current,
)

from message_ingest.acquisition.handoff import AcquisitionFactKind as Kind
from message_ingest.catalog.stores.microsoft.outlook._email_handoff import (
    MailFactWriter,
)
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from message_ingest.sync.microsoft.outlook.email.checkpoints import (
    OutlookFolderDeltaCheckpointStore,
)
from message_ingest.sync.microsoft.outlook.email.promotion import (
    promote_validated_mail_delta,
)


def test_candidate_set_rechecked_before_lifecycle_mutation(tmp_path):
    catalog = _catalog(tmp_path)
    try:
        store, checkpoints = _seed_baseline(catalog)
        validated = _stage_current(store, checkpoints)
        checkpoints.write_candidate(
            run_id="current",
            folder_id="removed",
            delta_link="unexpected",
            observed_at="2026-10-01T00:00:00+00:00",
        )
        with pytest.raises(ValueError, match="candidate"):
            promote_validated_mail_delta(catalog, source_id=SOURCE, validated=validated)
        if store.folder_presence(folder_id="removed") is not True:
            pytest.fail("Invalid candidates changed authority")
    finally:
        catalog.close()


def test_equal_time_competing_states_fail_closed(tmp_path):
    catalog = _catalog(tmp_path)
    try:
        folders = OutlookFolderDeltaCheckpointStore(catalog, SOURCE)
        folders.write_candidate(
            run_id="r", delta_link="new", observed_at="2026-10-01T00:00:00+00:00"
        )
        writer = MailFactWriter(catalog, SOURCE, "outlook_folder_delta")
        with catalog.writer_session() as session:
            for state in (False, True):
                writer.stage(
                    session,
                    run_id="r",
                    resource_id="f",
                    resource_kind="mail_folder",
                    kind=Kind.CONTROL_CONTEXT,
                    state={"is_present": state},
                    evidence_id=None,
                    observed_at="2026-10-01T00:00:00+00:00",
                    authority=True,
                )
        with pytest.raises(ValueError, match="Ambiguous"):
            folders.commit("r")
        if folders.get_delta_link() is not None:
            pytest.fail("Ambiguous state advanced folder cursor")
    finally:
        catalog.close()


def test_positive_folder_delta_stages_presence_until_commit(tmp_path):
    catalog = _catalog(tmp_path)
    try:
        store = OutlookMailStore(
            catalog, source_id=SOURCE, spider_name="outlook_folder_delta"
        )
        store.upsert_folder(
            folder={"id": "new", "displayName": "New"},
            evidence_id=None,
            run_id="r",
            observed_at="2026-10-01T00:00:00+00:00",
        )
        if store.folder_presence(folder_id="new") is not None:
            pytest.fail("Positive delta presence escaped authority gate")
        folders = OutlookFolderDeltaCheckpointStore(catalog, SOURCE)
        folders.write_candidate(
            run_id="r", delta_link="new", observed_at="2026-10-01T00:00:00+00:00"
        )
        folders.commit("r")
        if store.folder_presence(folder_id="new") is not True:
            pytest.fail("Winning positive delta did not establish presence")
    finally:
        catalog.close()


def test_many_equivalent_facts_make_one_bounded_impact(tmp_path):
    catalog = _catalog(tmp_path)
    try:
        store, checkpoints = _seed_baseline(catalog)
        validated = _stage_current(store, checkpoints)
        writer = MailFactWriter(catalog, SOURCE, "outlook_delta")
        with catalog.writer_session() as session:
            for order in range(130):
                writer.stage(
                    session,
                    run_id="current",
                    resource_id="new-message",
                    state={"id": "new-message"},
                    evidence_id=None,
                    observed_at=f"2026-10-01T00:00:{order % 60:02d}.{order:06d}+00:00",
                )
        promote_validated_mail_delta(catalog, source_id=SOURCE, validated=validated)
        with catalog.Session() as session:
            count = session.execute(
                text(
                    "SELECT count(*) FROM acquisition_release_entries WHERE json_extract(payload, '$.resource_identity') = 'new-message'"
                )
            ).scalar_one()
        if count != 1:
            pytest.fail("Equivalent run facts did not produce one impact")
    finally:
        catalog.close()


def test_newer_folder_presence_survives_old_inventory(tmp_path):
    from test_outlook_mail_atomic_promotion import _folder

    catalog = _catalog(tmp_path)
    try:
        store, checkpoints = _seed_baseline(catalog)
        validated = _stage_current(store, checkpoints)
        _folder(store, "removed", run_id="newer", when="2026-10-03T00:00:00+00:00")
        promote_validated_mail_delta(catalog, source_id=SOURCE, validated=validated)
        if store.folder_presence(folder_id="removed") is not True:
            pytest.fail("Old inventory displaced newer folder presence")
        if checkpoints.get_delta_link("removed") is None:
            pytest.fail("Skipped old absence deleted a newer folder cursor")
    finally:
        catalog.close()
