"""Prove atomic OneDrive facts, exact locators, and release eligibility."""

from dataclasses import replace

import pytest
from sqlalchemy import select

from message_ingest.acquisition.handoff import (
    AcquisitionStream,
    FactSpec,
    ReleaseEntrySpec,
    ReleaseGroupSpec,
    ReleaseKind,
    StorageRelation,
)
from message_ingest.catalog import Catalog
from message_ingest.catalog.models.handoff import (
    AcquisitionEffectiveState,
    AcquisitionFact,
)
from message_ingest.catalog.models.microsoft.onedrive import (
    OneDriveContentCapture,
    OneDriveContentRecord,
    OneDriveDeltaResyncObservation,
    OneDriveDriveRecord,
    OneDriveItemRecord,
)
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.catalog.stores.microsoft.onedrive import OneDriveStore
from message_ingest.items.microsoft.onedrive import (
    OneDriveContentItem,
    OneDriveDeltaResyncObservationItem,
    OneDriveDriveItem,
    OneDriveItem,
)
from tests.test_onedrive_resync import _evidence

T0 = "2026-10-01T00:00:00+00:00"
T1 = "2026-10-02T00:00:00+00:00"


@pytest.fixture
def catalog(tmp_path):
    """Open a local isolated catalog."""
    instance = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        yield instance
    finally:
        instance.close()


def metadata(*, evidence="metadata", run="run", at=T0, **raw):
    """Build sanitized local provider data."""
    return OneDriveItem.from_graph(
        {"id": "item", "name": "private-name", "eTag": "v1", **raw},
        observed_at=at,
        evidence_id=evidence,
        run_id=run,
    )


def observation(drive, **kwargs):
    """Build a drive or item fixture with the same provenance."""
    item = metadata(**kwargs)
    if not drive:
        return item
    return OneDriveDriveItem.from_graph(
        item.raw,
        observed_at=item.observed_at,
        evidence_id=item.evidence_id,
        run_id=item.run_id,
    )


def persist(store: OneDriveStore, item):
    """Dispatch a fixture through its public provider persistence operation."""
    if isinstance(item, OneDriveContentItem):
        return store.persist_content(item)
    if isinstance(item, OneDriveDeltaResyncObservationItem):
        return store.persist_resync_observation(item)
    if isinstance(item, OneDriveDriveItem):
        return store.persist_drive(item)
    return store.persist_item(item)


def content(*, evidence="content", run="run", at=T0, digest="a", tag="v1"):
    """Bind one content capture to an explicit metadata version."""
    return OneDriveContentItem(
        item_id="item",
        content_sha256=digest * 64,
        content_bytes=1,
        observed_at=at,
        evidence_id=evidence,
        run_id=run,
        planned_metadata_observed_at=T0,
        planned_metadata_evidence_id="metadata",
        planned_e_tag=tag,
        planned_c_tag=tag,
        response_e_tag=tag,
    )


def facts(catalog, *, run=None):
    """Read immutable facts without current projections."""
    with catalog.Session() as session:
        query = select(AcquisitionFact.payload)
        if run is not None:
            query = query.where(AcquisitionFact.run_id == run)
        return [FactSpec.from_json(payload) for payload in session.scalars(query)]


def one_fact(catalog, run="run"):
    """Require exactly one fact for an operation."""
    rows = facts(catalog, run=run)
    if len(rows) != 1:
        pytest.fail(f"Expected one staged fact for {run}, got {len(rows)}")
    return rows[0]


def release(catalog, fact, *, owner=None, authority=False):
    """Exercise the frozen release core, leaving production publication later."""
    ledger = AcquisitionHandoffStore(catalog)
    group = ReleaseGroupSpec(
        source_id="source",
        stream=AcquisitionStream.ONEDRIVE,
        release_kind=(
            ReleaseKind.AUTHORITY_SCOPE if authority else ReleaseKind.RESOURCE_SET
        ),
        subject_kind="test_scope",
        subject_identity=owner or fact.run_id,
        owner_run_id=owner or fact.run_id,
        released_at=T1,
        coverage_kind="complete",
    )
    entry = ReleaseEntrySpec(
        resource_kind=fact.parent_resource_kind or fact.resource_kind,
        resource_identity=fact.parent_resource_identity or fact.resource_identity,
        facts=((fact.fact_id, "component" if fact.component_kind else "primary"),),
    )
    with catalog.writer_session() as session:
        if authority:
            ledger.release_authority_group_in_session(
                session,
                group,
                (entry,),
                winning_fact_ids=(fact.fact_id,),
            )
        else:
            ledger.release_effective_group_in_session(session, group, (entry,))
    return ledger.list_release_entries("source", AcquisitionStream.ONEDRIVE)


@pytest.mark.parametrize("drive", [False, True])
def test_metadata_equivalence_recovers_once_and_keeps_exact_evidence(catalog, drive):
    """A retry adopts unreleased state once, with independent run provenance."""
    store = OneDriveStore(catalog, source_id="source")
    persist(store, observation(drive))
    original = one_fact(catalog)
    persist(store, observation(drive, evidence="other", run="retry", at=T1))
    retry = one_fact(catalog, "retry")
    if retry.storage_relation != StorageRelation.CURRENT_EQUIVALENT:
        pytest.fail("Transport provenance fabricated a semantic change")
    if retry.source_state_key != original.source_state_key:
        pytest.fail("Equivalent metadata changed its semantic state key")
    entries = release(catalog, retry)
    if len(entries) != 1:
        pytest.fail("Unreleased equivalent state was not recovered exactly once")
    released = AcquisitionHandoffStore(catalog).load_release_facts(
        entries[0]["release_entry_seq"]
    )
    if released != [original]:
        pytest.fail("Release must bind the original immutable representation")
    persist(store, observation(drive, evidence="metadata", run="cached"))
    cached = one_fact(catalog, "cached")
    if cached.evidence_id != "metadata" or cached.run_id != "cached":
        pytest.fail("Cache evidence ownership replaced logical run provenance")
    # Canonical old evidence can be stale by capture time; it cannot republish.
    if len(release(catalog, cached)) != 1:
        pytest.fail("Released unchanged metadata created repetitive work")
    locator = original.source_version_locator
    if (
        locator is None
        or locator.kind != "evidence"
        or locator.evidence_id != ("metadata")
    ):
        pytest.fail("Metadata locator must pin immutable evidence")
    if "private-name" in repr(original):
        pytest.fail("Provider body leaked into the ledger")


def test_download_url_does_not_change_state_or_leak_into_fact(catalog):
    """Nested preauthenticated URLs are excluded before key derivation."""
    store = OneDriveStore(catalog, source_id="source")
    store.persist_item(
        metadata(
            **{
                "@microsoft.graph.downloadUrl": "https://download.test/secret-one",
                "remoteItem": {
                    "@microsoft.graph.downloadUrl": "secret-two",
                    "id": "remote",
                },
            }
        )
    )
    first = one_fact(catalog)
    store.persist_item(
        metadata(
            run="retry",
            **{
                "@microsoft.graph.downloadUrl": "https://download.test/rotated-secret",
                "remoteItem": {
                    "@microsoft.graph.downloadUrl": "changed",
                    "id": "remote",
                },
            },
        )
    )
    second = one_fact(catalog, "retry")
    if first.source_state_key != second.source_state_key or "secret" in repr(second):
        pytest.fail("Download URL leaked into semantic identity or fact payload")


def test_superseded_metadata_cannot_publish_after_newer_state(catalog):
    """Write-time advancement does not grant delayed publication rights."""
    store = OneDriveStore(catalog, source_id="source")
    store.persist_item(metadata())
    older = one_fact(catalog)
    store.persist_item(metadata(run="new", at=T1, eTag="v2"))
    if release(catalog, older):
        pytest.fail("Superseded metadata became newer primary work")
    store.persist_item(metadata(run="stale", name="different"))
    stale = one_fact(catalog, "stale")
    if stale.storage_relation != StorageRelation.STALE or release(catalog, stale):
        pytest.fail("Stale metadata was not retained solely as audit history")


@pytest.mark.parametrize("change", ["digest", "tag"])
def test_content_state_tracks_bytes_and_version_binding_separately(catalog, change):
    """Metadata remains independent while bytes or version proof advance."""
    store = OneDriveStore(catalog, source_id="source")
    store.persist_item(metadata(run="metadata"))
    primary = one_fact(catalog, "metadata")
    store.persist_content(content())
    first = one_fact(catalog)
    next_item = content(evidence="next", run="next", at=T1)
    next_item = replace(
        next_item,
        **(
            {"content_sha256": "b" * 64}
            if change == "digest"
            else {"planned_e_tag": "v2", "response_e_tag": "v2"}
        ),
    )
    store.persist_content(next_item)
    second = one_fact(catalog, "next")
    if second.storage_relation != StorageRelation.ADVANCED:
        pytest.fail("Content bytes/version binding did not advance component")
    if second.source_state_key == first.source_state_key:
        pytest.fail("Different content state reused a component key")
    if second.effective_key == primary.effective_key:
        pytest.fail("Content and primary metadata share a state slot")
    if second.parent_resource_identity != "item" or not second.component_kind:
        pytest.fail("Content component lost its semantic parent")
    locator = first.source_version_locator
    if (
        locator is None
        or locator.kind != "content_capture"
        or (locator.capture_id != "content" or locator.evidence_id != "content")
    ):
        pytest.fail("Content locator must name its immutable capture association")
    if release(catalog, first):
        pytest.fail("Older content can publish after newer content wins")


def test_stale_content_cannot_replace_newer_capture_or_effective_fact(catalog):
    """An older download remains history without changing current association."""
    store = OneDriveStore(catalog, source_id="source")
    store.persist_content(content(evidence="new", at=T1))
    winner = one_fact(catalog)
    store.persist_content(content(evidence="old", run="old", digest="b"))
    stale = one_fact(catalog, "old")
    with catalog.Session() as session:
        current = session.get(OneDriveContentRecord, ("source", "item"))
        effective = session.get(AcquisitionEffectiveState, winner.effective_key.digest)
        if current is None or current.latest_evidence_id != "new":
            pytest.fail("Stale content replaced the latest immutable association")
        if effective is None or effective.fact_id != winner.fact_id:
            pytest.fail("Stale content replaced the effective fact")
        if len(session.scalars(select(OneDriveContentCapture)).all()) != 2:
            pytest.fail("Stale content history was discarded")
    if stale.storage_relation != StorageRelation.STALE or release(catalog, stale):
        pytest.fail("Stale content became releasable")


@pytest.mark.parametrize("kind", ["drive", "item", "content", "resync"])
def test_fact_failure_rolls_back_every_provider_stage(catalog, monkeypatch, kind):
    """Fact insertion failure must roll back ORM rows and capture associations."""
    store = OneDriveStore(catalog, source_id="source")
    item = observation(kind == "drive")
    model = OneDriveDriveRecord if kind == "drive" else OneDriveItemRecord
    if kind == "content":
        item, model = content(), OneDriveContentRecord
    if kind == "resync":
        _evidence(catalog, "metadata", "run", T0)
        item = OneDriveDeltaResyncObservationItem.from_graph(
            {"id": "item"},
            observed_at=T0,
            evidence_id="metadata",
            run_id="run",
            reset_attempt=1,
            base_revision=1,
            page_number=1,
            entry_index=0,
        )
        model = OneDriveDeltaResyncObservation

    def fail_fact(*_args, **_kwargs):
        raise OSError("injected fact write failure")

    monkeypatch.setattr(AcquisitionHandoffStore, "_insert_fact", fail_fact)
    with pytest.raises(OSError, match="injected fact"):
        persist(store, item)
    with catalog.Session() as session:
        for table in (
            model,
            OneDriveContentCapture,
            AcquisitionFact,
            AcquisitionEffectiveState,
        ):
            if session.scalars(select(table)).first() is not None:
                pytest.fail(f"Fact failure left committed {table.__name__}")


def test_resync_observation_is_hidden_until_explicit_winning_authority(catalog):
    """Partial 410 enumeration cannot become ordinary effective work."""
    store = OneDriveStore(catalog, source_id="source")
    _evidence(catalog, "page", "run", T0)
    item = OneDriveDeltaResyncObservationItem.from_graph(
        {"id": "item", "eTag": "v1"},
        observed_at=T0,
        evidence_id="page",
        run_id="run",
        reset_attempt=1,
        base_revision=1,
        page_number=2,
        entry_index=3,
    )
    store.persist_resync_observation(item)
    store.persist_resync_observation(item)
    fact = one_fact(catalog)
    if fact.storage_relation != StorageRelation.AUTHORITY_STAGED:
        pytest.fail("Reset observation must remain authority-staged")
    with catalog.Session() as session:
        if session.scalars(select(AcquisitionEffectiveState)).first() is not None:
            pytest.fail("Partial reset changed effective state")
        observation = session.scalars(select(OneDriveDeltaResyncObservation)).one()
        locator = fact.source_version_locator
        if locator is None or locator.observation_id != str(observation.observation_id):
            pytest.fail("Reset fact lost its immutable ordered observation")
    if release(catalog, fact):
        pytest.fail("Reset observation escaped through ordinary completion")
    if len(release(catalog, fact, owner="winner", authority=True)) != 1:
        pytest.fail("Explicit winning authority could not publish staged state")


def test_content_cache_revalidation_preserves_original_capture(catalog):
    """Canonical evidence belongs to the first capture, not the retry run."""
    store = OneDriveStore(catalog, source_id="source")
    store.persist_content(content())
    original = one_fact(catalog)
    store.persist_content(content(run="retry"))
    retry = one_fact(catalog, "retry")
    if retry.storage_relation != StorageRelation.CURRENT_EQUIVALENT:
        pytest.fail("Same capture must revalidate the existing content fact")
    if retry.source_version_locator != original.source_version_locator:
        pytest.fail("Logical run changed the immutable content locator")
    with catalog.Session() as session:
        capture = session.get(OneDriveContentCapture, ("source", "content"))
        if capture is None or capture.run_id != "run":
            pytest.fail("Retry rewrote the original capture provenance")
    if len(release(catalog, retry)) != 1:
        pytest.fail("Equivalent capture could not recover unreleased content")


def test_already_released_equivalent_metadata_creates_no_second_entry(catalog):
    """A fresh identical network observation is not new downstream work."""
    store = OneDriveStore(catalog, source_id="source")
    store.persist_item(metadata())
    if len(release(catalog, one_fact(catalog))) != 1:
        pytest.fail("Initial state was not released")
    store.persist_item(metadata(run="retry", evidence="new-evidence", at=T1))
    retry = one_fact(catalog, "retry")
    if retry.storage_relation != StorageRelation.CURRENT_EQUIVALENT:
        pytest.fail("Unchanged network metadata must be current-equivalent")
    if len(release(catalog, retry)) != 1:
        pytest.fail("Unchanged released state created a duplicate entry")


@pytest.mark.parametrize("kind", ["drive", "item", "content"])
def test_fact_failure_restores_previous_state_and_association(
    catalog, monkeypatch, kind
):
    """Even flushed ORM advances must roll back with a failed fact insert."""
    store = OneDriveStore(catalog, source_id="source")
    before_item = content() if kind == "content" else observation(kind == "drive")
    persist(store, before_item)
    after_item = (
        content(evidence="next", run="next", at=T1, digest="b")
        if kind == "content"
        else observation(
            kind == "drive",
            run="next",
            evidence="next",
            at=T1,
            name="changed",
        )
    )
    tables = (
        OneDriveDriveRecord,
        OneDriveItemRecord,
        OneDriveContentRecord,
        OneDriveContentCapture,
        AcquisitionFact,
        AcquisitionEffectiveState,
    )
    with catalog.Session() as session:
        before = [session.execute(select(model.__table__)).all() for model in tables]

    def fail_fact(_store, writer, _spec):
        writer.flush()
        raise OSError("injected fact failure after flush")

    monkeypatch.setattr(AcquisitionHandoffStore, "_insert_fact", fail_fact)
    with pytest.raises(OSError, match="after flush"):
        persist(store, after_item)
    with catalog.Session() as session:
        after = [session.execute(select(model.__table__)).all() for model in tables]
    if before != after:
        pytest.fail("Fact failure committed a state/capture/index advancement")


def test_metadata_locator_disambiguates_versions_in_same_evidence(catalog):
    """Repeated provider IDs in one page still have distinct exact locators."""
    store = OneDriveStore(catalog, source_id="source")
    store.persist_item(metadata())
    first = one_fact(catalog)
    store.persist_item(metadata(run="second", eTag="v2"))
    second = one_fact(catalog, "second")
    if first.source_version_locator == second.source_version_locator:
        pytest.fail("Distinct provider versions share an ambiguous exact locator")


def test_unchanged_preledger_metadata_does_not_invent_bootstrap_work(catalog):
    """Only genuine post-ledger advancement admits existing historical rows."""
    item = metadata()
    with catalog.writer_session() as session:
        session.add(
            OneDriveItemRecord(
                source_id="source",
                item_id="item",
                name=item.name,
                e_tag=item.e_tag,
                raw=item.raw,
                is_deleted=False,
                latest_observed_at=T0,
                latest_evidence_id="metadata",
                latest_run_id="historical",
            )
        )
    OneDriveStore(catalog, source_id="source").persist_item(metadata(at=T1))
    fact = one_fact(catalog)
    if fact.storage_relation != StorageRelation.CURRENT_EQUIVALENT:
        pytest.fail("Historical unchanged state was falsely advanced")
    if release(catalog, fact):
        pytest.fail("Unchanged pre-ledger data fabricated incremental work")
