"""Verify source-scoped OneDrive state and evidence-backed checkpoint CAS."""

import importlib
from dataclasses import fields
from typing import Any

import pytest
from sqlalchemy import create_engine, inspect, select

from message_ingest.catalog import Base, Catalog, RawHttpEvidence


@pytest.fixture
def api():
    try:
        return tuple(
            importlib.import_module(path)
            for path in (
                "message_ingest.items.microsoft.onedrive",
                "message_ingest.catalog.models.microsoft.onedrive",
                "message_ingest.catalog.stores.microsoft.onedrive",
            )
        )
    except ModuleNotFoundError as exc:
        pytest.fail(f"OneDrive persistence API is missing: {exc.name}")


@pytest.fixture
def catalog(tmp_path):
    instance = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        yield instance
    finally:
        instance.close()


def _item(items, *, drive=False, observed="2026-09-29T00:00:00Z", **raw):
    cls = items.OneDriveDriveItem if drive else items.OneDriveItem
    return cls.from_graph(
        {"id": "provider-id", **raw},
        observed_at=observed,
        evidence_id="evidence",
        run_id="run",
    )


def _evidence(catalog, *, evidence_id="evidence", source_id="source", run_id="run"):
    catalog.evidence.record(
        RawHttpEvidence(
            evidence_id=evidence_id,
            source_id=source_id,
            run_id=run_id,
            purpose="onedrive.delta",
            observed_at="2026-09-29T00:00:00Z",
            origin="network",
            request_fingerprint="fingerprint",
            request_url="https://graph.microsoft.com/v1.0/me/drive/root/delta",
            request_method="GET",
            request_headers={},
            request_body_sha256="empty",
            request_body_path="empty.bin",
            request_body_bytes=0,
            response_url="https://graph.microsoft.com/v1.0/me/drive/root/delta",
            response_status=200,
            response_headers={},
            response_body_sha256="response",
            response_body_path="response.bin",
            response_body_bytes=2,
            response_flags=[],
            error_type=None,
            error_message=None,
        )
    )


def _candidate(items, *, run_id="run", base_revision=None, **changes):
    values = {
        "delta_link": "https://graph.microsoft.com/v1.0/me/drive/root/delta?token=%2b+",
        "base_revision": base_revision,
        "observed_at": "2026-09-29T00:00:00Z",
        "evidence_id": "evidence",
        "run_id": run_id,
    }
    return items.OneDriveDeltaCheckpointCandidateItem(**(values | changes))


def test_onedrive_schema_is_additive_and_uses_source_scope(api, tmp_path):
    expected = {
        "onedrive_drives": ("source_id",),
        "onedrive_items": ("source_id", "item_id"),
        "onedrive_contents": ("source_id", "item_id"),
        "onedrive_content_captures": ("source_id", "evidence_id"),
        "onedrive_delta_checkpoints": ("source_id",),
        "onedrive_delta_checkpoint_candidates": ("source_id", "run_id"),
        "onedrive_delta_resync_attempts": ("source_id", "run_id", "reset_attempt"),
        "onedrive_delta_resync_observations": ("observation_id",),
    }
    url = f"sqlite:///{tmp_path / 'existing.sqlite3'}"
    engine = create_engine(url)
    try:
        Base.metadata.create_all(
            engine,
            tables=[
                table
                for name, table in Base.metadata.tables.items()
                if name not in expected
            ],
        )
        with engine.begin() as connection:
            connection.exec_driver_sql("CREATE TABLE preserved (value TEXT)")
            connection.exec_driver_sql("INSERT INTO preserved VALUES ('old data')")
        before = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    catalog = Catalog(url)
    try:
        schema = inspect(catalog.engine)
        if set(schema.get_table_names()) - before != set(expected):
            pytest.fail("OneDrive must add only its own tables")
        for table, keys in expected.items():
            if tuple(schema.get_pk_constraint(table)["constrained_columns"]) != keys:
                pytest.fail(f"OneDrive table has wrong identity: {table}")
        with catalog.engine.connect() as connection:
            if connection.exec_driver_sql("SELECT value FROM preserved").scalar() != (
                "old data"
            ):
                pytest.fail("Additive initialization modified existing data")
    finally:
        catalog.close()


@pytest.mark.parametrize("drive", [False, True])
def test_provider_projection_keeps_falsey_fields_and_latest_observation(
    api, catalog, drive
):
    items, models, stores = api
    store = stores.OneDriveStore(catalog, source_id="source")
    model = models.OneDriveDriveRecord if drive else models.OneDriveItemRecord
    persist = store.persist_drive if drive else store.persist_item
    raw: dict[str, Any] = {
        "name": "",
        "createdDateTime": "",
        "lastModifiedDateTime": "",
    }
    projection = {"name": "", "created_date_time": "", "last_modified_date_time": ""}
    if drive:
        raw |= {"driveType": "personal", "owner": {}, "quota": {"remaining": 0}}
        projection |= {"drive_type": "personal", "owner": {}, "quota": {"remaining": 0}}
    else:
        raw |= {"size": 0, "file": {}, "parentReference": {"id": "parent"}, "eTag": ""}
        projection |= {
            "size": 0,
            "file": {},
            "parent_reference": {"id": "parent"},
            "e_tag": "",
        }
    item = _item(items, drive=drive, **raw)
    if persist(item) != "created" or persist(item) != "unchanged":
        pytest.fail("Initial and repeated observations must have bounded outcomes")
    stale = _item(items, drive=drive, observed="2026-09-29T09:00:00+10:00")
    if persist(stale) != "stale":
        pytest.fail("Observation ordering must compare timezone-aware instants")
    with catalog.Session() as session:
        record = session.scalars(select(model)).one()
        for name, expected in (
            projection
            | {
                "raw": item.raw,
                "latest_observed_at": item.observed_at,
                "latest_evidence_id": "evidence",
                "latest_run_id": "run",
            }
        ).items():
            if getattr(record, name) != expected:
                pytest.fail(f"Persisted observation changed field {name}")
    changed = _item(items, drive=drive, observed="2026-10-01T00:00:00Z", name="new")
    if persist(changed) != "changed":
        pytest.fail("A later observation must update current state")
    with pytest.raises(ValueError, match="timezone"):
        persist(_item(items, drive=drive, observed="2026-10-01"))


def test_tombstone_preserves_omitted_metadata_and_explicit_falsey_fields(api, catalog):
    items, models, stores = api
    store = stores.OneDriveStore(catalog, source_id="source")
    store.persist_item(
        _item(items, name="report", size=10, file={"mimeType": "text/plain"})
    )
    tombstone = _item(
        items, observed="2026-09-30T00:00:00Z", deleted={}, size=0, eTag=""
    )
    store.persist_item(tombstone)
    with catalog.Session() as session:
        row = session.scalars(select(models.OneDriveItemRecord)).one()
        if (
            not row.is_deleted
            or row.deleted != {}
            or row.name != "report"
            or row.file != {"mimeType": "text/plain"}
            or row.size != 0
            or row.e_tag != ""
            or row.raw != {"id": "provider-id", "deleted": {}, "size": 0, "eTag": ""}
        ):
            pytest.fail("Tombstone lost metadata or ignored an explicit falsey field")
    store.persist_item(_item(items, observed="2026-10-01T00:00:00Z", name="restored"))
    with catalog.Session() as session:
        row = session.scalars(select(models.OneDriveItemRecord)).one()
        if row.is_deleted or row.deleted is not None or row.name != "restored":
            pytest.fail("A later live observation did not restore the drive item")


def test_initial_tombstone_and_other_source_have_independent_state(api, catalog):
    items, models, stores = api
    first = stores.OneDriveStore(catalog, source_id="first")
    second = stores.OneDriveStore(catalog, source_id="second")
    first.persist_item(_item(items, deleted={}))
    second.persist_item(_item(items, name="present"))
    with catalog.Session() as session:
        rows = session.scalars(select(models.OneDriveItemRecord)).all()
        if len(rows) != 2:
            pytest.fail("Different OneDrive source identities collided")
        absent = next(row for row in rows if row.source_id == "first")
        present = next(row for row in rows if row.source_id == "second")
        if absent.name is not None or not absent.is_deleted or present.is_deleted:
            pytest.fail("Initial tombstones must allow missing metadata")


def test_app_projection_removes_download_url_without_mutating_response(api):
    items, _models, _stores = api
    secret = "https://download.example/secret-path?token=secret"
    raw = {
        "id": "item",
        "@microsoft.graph.downloadUrl": secret,
        "remoteItem": {
            "@microsoft.graph.downloadUrl": secret,
            "size": 0,
            "file": {},
            "children": [{"@microsoft.graph.downloadUrl": secret, "name": ""}],
        },
    }
    item = items.OneDriveItem.from_graph(
        raw, observed_at="2026-09-29T00:00:00Z", evidence_id="evidence", run_id="run"
    )
    if secret in repr(item) or item.remote_item != {
        "size": 0,
        "file": {},
        "children": [{"name": ""}],
    }:
        pytest.fail("App metadata must remove nested preauthenticated URLs")
    if raw["@microsoft.graph.downloadUrl"] != secret:
        pytest.fail("Semantic retention policy mutated the raw HTTP source object")
    safe = {"id": "drive", "owner": {"user": {"displayName": ""}}}
    drive = items.OneDriveDriveItem.from_graph(
        safe, observed_at="2026-09-29T00:00:00Z", evidence_id=None, run_id=None
    )
    if drive.raw is not safe or drive.owner is not safe["owner"]:
        pytest.fail("Safe metadata must retain container identity")


def test_content_state_has_no_second_body_or_transport_url(api, catalog):
    items, models, stores = api
    item = items.OneDriveContentItem(
        item_id="provider-id",
        content_sha256="digest",
        content_bytes=0,
        observed_at="2026-09-29T00:00:00Z",
        evidence_id="evidence",
        run_id="run",
    )
    store = stores.OneDriveStore(catalog, source_id="source")
    if store.persist_content(item) != "created":
        pytest.fail("Explicit capture must create semantic content state")
    allowed = {
        "item_id",
        "content_sha256",
        "content_bytes",
        "observed_at",
        "evidence_id",
        "run_id",
        "planned_metadata_observed_at",
        "planned_metadata_evidence_id",
        "planned_e_tag",
        "planned_c_tag",
        "response_e_tag",
    }
    if {field.name for field in fields(item)} != allowed:
        pytest.fail("Content items must contain only digest/size and provenance")
    with catalog.Session() as session:
        row = session.scalars(select(models.OneDriveContentRecord)).one()
        if row.content_sha256 != "digest" or row.content_bytes != 0:
            pytest.fail("Semantic content record lost the digest or empty byte count")
        if any(
            "body" in column.name or "url" in column.name
            for column in row.__table__.columns
        ):
            pytest.fail("Content body or transport URL leaked into semantic state")
        capture = session.scalars(select(models.OneDriveContentCapture)).one()
        if capture.evidence_id != "evidence" or capture.content_sha256 != "digest":
            pytest.fail("Append-only content capture lost its evidence association")
        if any(
            "body" in column.name or "url" in column.name
            for column in capture.__table__.columns
        ):
            pytest.fail("Content capture association must not duplicate bytes or URLs")


def test_candidate_is_not_resume_point_and_promotion_compares_revision(api, catalog):
    items, _models, stores = api
    store = stores.OneDriveStore(catalog, source_id="source")
    _evidence(catalog)
    candidate = _candidate(items)
    store.persist_candidate(candidate)
    if store.load_checkpoint() is not None:
        pytest.fail("An unpromoted terminal candidate must not be a resume point")
    first = store.promote_checkpoint(run_id="run", base_revision=None)
    if first.revision != 1 or first.delta_link != candidate.delta_link:
        pytest.fail("First promotion changed the opaque cursor")
    _evidence(catalog, evidence_id="ev2", run_id="run2")
    _evidence(catalog, evidence_id="ev3", run_id="run3")
    store.persist_candidate(
        _candidate(
            items,
            run_id="run2",
            base_revision=1,
            evidence_id="ev2",
            delta_link="opaque-second",
        )
    )
    store.persist_candidate(
        _candidate(
            items,
            run_id="run3",
            base_revision=1,
            evidence_id="ev3",
            delta_link="opaque-third",
        )
    )
    second = store.promote_checkpoint(run_id="run2", base_revision=1)
    if second.revision != 2 or second.delta_link != "opaque-second":
        pytest.fail("A clean second run did not advance its starting revision")
    with pytest.raises(ValueError, match="revision"):
        store.promote_checkpoint(run_id="run3", base_revision=1)
    if store.load_checkpoint().delta_link != "opaque-second":
        pytest.fail("A stale run replaced the committed cursor")


@pytest.mark.parametrize("mismatch", ["missing", "source", "run"])
def test_candidate_requires_committed_evidence_for_its_source_and_run(
    api, catalog, mismatch
):
    items, _models, stores = api
    store = stores.OneDriveStore(catalog, source_id="source")
    if mismatch != "missing":
        _evidence(
            catalog,
            source_id="other" if mismatch == "source" else "source",
            run_id="other" if mismatch == "run" else "run",
        )
    with pytest.raises(ValueError, match="evidence"):
        store.persist_candidate(_candidate(items))
    if store.load_checkpoint() is not None:
        pytest.fail("Invalid candidate evidence advanced the checkpoint")


@pytest.mark.parametrize(
    "changes",
    [
        {"run_id": None},
        {"evidence_id": None},
        {"base_revision": 0},
        {"base_revision": True},
        {"delta_link": ""},
    ],
)
def test_candidate_rejects_invalid_terminal_context(api, catalog, changes):
    items, _models, stores = api
    _evidence(catalog)
    store = stores.OneDriveStore(catalog, source_id="source")
    with pytest.raises(ValueError):
        store.persist_candidate(_candidate(items, **changes))
