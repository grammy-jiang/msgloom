"""Mail promotion seals inputs and rolls back every application boundary."""

import json

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError

from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from message_ingest.sync.microsoft.outlook.email.checkpoints import (
    OutlookDeltaCheckpointStore,
    OutlookFolderDeltaCheckpointStore,
)
from tests._mail_provisional import WHEN, capture, prepare, promote
from tests.test_outlook_mail_atomic_promotion import (
    SOURCE,
    _catalog,
    _seed_baseline,
    _stage_current,
)


def state(catalog):
    tables = (
        "messages",
        "message_presence",
        "mail_folders",
        "mail_folder_presence",
        "delta_checkpoints",
        "delta_checkpoint_candidates",
        "mail_delta_absence_generations",
        "mail_projection_owners",
        "acquisition_effective_states",
        "acquisition_release_groups",
        "acquisition_release_entries",
        "mail_authority_decisions",
    )
    with catalog.Session() as session:
        return {
            name: session.execute(text(f"SELECT * FROM {name}")).all()
            for name in tables
        }


@pytest.mark.parametrize(
    "table",
    [
        "messages",
        "acquisition_effective_states",
        "acquisition_release_groups",
        "delta_checkpoints",
    ],
)
def test_failure_at_each_application_boundary_rolls_back_and_reopens(tmp_path, table):
    url = f"sqlite:///{tmp_path / 'catalog.db'}"
    catalog = Catalog(url)
    store = OutlookMailStore(catalog, source_id=SOURCE)
    validated = prepare(store, "winner")
    capture(store, "winner", {"id": "m", "changeKey": "v2", "subject": "winner"})
    before = state(catalog)
    try:
        with catalog.writer_session() as session:
            session.execute(
                text(
                    f"CREATE TRIGGER fail_projection BEFORE INSERT ON {table} "
                    "BEGIN SELECT RAISE(ABORT, 'promotion fault'); END"
                )
            )
        with pytest.raises(DatabaseError, match="promotion fault"):
            promote(store, validated)
        if state(catalog) != before:
            pytest.fail("Projection, pointer, release or cursor escaped rollback")
    finally:
        catalog.close()
    reopened = Catalog(url)
    try:
        if state(reopened) != before:
            pytest.fail("Reopened catalog exposed a partial application")
        with reopened.writer_session() as session:
            session.execute(text("DROP TRIGGER fail_projection"))
        store = OutlookMailStore(reopened, source_id=SOURCE)
        result = promote(store, validated)
        after = state(reopened)
        if promote(store, validated) != result or state(reopened) != after:
            pytest.fail("Exact retry changed an already committed promotion")
    finally:
        reopened.close()


def test_retry_after_independent_observations_cannot_repeat_absence(tmp_path):
    catalog = _catalog(tmp_path)
    try:
        store, checkpoints = _seed_baseline(catalog)
        validated = _stage_current(store, checkpoints)
        result = promote(store, validated)
        checkpoints.write_candidate(
            run_id="new-folder",
            folder_id="removed",
            delta_link="newly-created",
            observed_at=WHEN,
            baseline_identity=checkpoints.get_delta_start("removed")[1],
        )
        checkpoints.commit("new-folder")
        before = state(catalog)
        if promote(store, validated) != result or state(catalog) != before:
            pytest.fail("Retry repeated lifecycle work or deleted a newer cursor")
        with pytest.raises(RuntimeError, match="sealed"):
            capture(store, "current", {"id": "late", "changeKey": "v1"}, scope="keep")
    finally:
        catalog.close()


def test_changed_snapshot_input_fails_sealed_replay(tmp_path):
    catalog = _catalog(tmp_path)
    try:
        store, checkpoints = _seed_baseline(catalog)
        validated = _stage_current(store, checkpoints)
        promote(store, validated)
        store.record_message_sighting(
            run_id="current", message_id="late", observed_at=WHEN, evidence_id=None
        )
        before = state(catalog)
        with pytest.raises(RuntimeError, match="input set changed"):
            promote(store, validated)
        if state(catalog) != before:
            pytest.fail("Changed replay mutated accepted state")
    finally:
        catalog.close()


def test_original_scope_is_not_inferred_from_mutable_parent(tmp_path):
    catalog = _catalog(tmp_path)
    store = OutlookMailStore(catalog, source_id=SOURCE)
    try:
        validated = prepare(store, "winner")
        capture(
            store,
            "winner",
            {"id": "m", "parentFolderId": "moved-to", "changeKey": "v2"},
            scope="inbox",
        )
        promote(store, validated)
        invalid = prepare(store, "invalid")
        capture(store, "invalid", {"id": "m", "changeKey": "v3"}, scope="different")
        with pytest.raises(ValueError, match="outside validated"):
            promote(store, invalid)
    finally:
        catalog.close()


def test_folder_retry_never_repeats_absence_generation(tmp_path):
    catalog = _catalog(tmp_path)
    store = OutlookMailStore(
        catalog, source_id=SOURCE, spider_name="outlook_folder_delta"
    )
    folders = OutlookFolderDeltaCheckpointStore(catalog, SOURCE)
    checkpoints = OutlookDeltaCheckpointStore(catalog, SOURCE)
    try:
        store.mark_folder_removed(
            folder_id="gone",
            run_id="winner",
            observed_at=WHEN,
            evidence_id=None,
            reason="deleted",
        )
        folders.write_candidate(
            run_id="winner",
            delta_link="one",
            observed_at=WHEN,
            baseline_identity=folders.get_delta_start()[1],
        )
        folders.commit("winner")
        checkpoints.write_candidate(
            run_id="new",
            folder_id="gone",
            delta_link="new",
            observed_at=WHEN,
            baseline_identity=checkpoints.get_delta_start("gone")[1],
        )
        checkpoints.commit("new")
        before = state(catalog)
        folders.commit("winner")
        if state(catalog) != before:
            pytest.fail("Folder retry repeated absence generation or invalidation")
        with catalog.Session() as session:
            decision = json.loads(
                session.execute(
                    text("SELECT payload FROM mail_authority_decisions")
                ).scalar_one()
            )
        if len(decision["applied"]) != 2:
            pytest.fail("Decision omitted selected folder context or transition")
    finally:
        catalog.close()
