"""Verify Contacts snapshot and sparse delta facts under provider ownership."""

import json
from dataclasses import asdict, replace

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from message_ingest.acquisition.handoff import AcquisitionStream, StorageRelation
from message_ingest.catalog import Catalog
from message_ingest.catalog.models.handoff import (
    AcquisitionEffectiveState,
    AcquisitionFact,
)
from message_ingest.catalog.models.microsoft.contacts import (
    ContactDeltaObservation,
    ContactFolderRecord,
    ContactFolderSighting,
    ContactRecord,
    ContactSighting,
)
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.catalog.stores.microsoft.contacts import ContactsStore
from message_ingest.items.microsoft.contacts import (
    ContactDeltaCheckpointCandidateItem,
    ContactFolderItem,
    ContactItem,
)
from tests._todo_contacts_handoff import facts, publish, reject_facts
from tests.test_contacts_catalog import _complete, _contact, _folder


@pytest.fixture
def catalog(tmp_path):
    """Provide an isolated local catalog, with no provider traffic."""
    value = Catalog(f"sqlite:///{tmp_path / 'contacts.sqlite3'}")
    yield value
    value.close()


def snapshot(store: ContactsStore, run: str, day: int) -> None:
    """Stage one complete folder/default/custom snapshot without promotion."""
    observed = f"2026-10-0{day}T00:00:00Z"
    store.begin_snapshot_run(run)
    store.persist_folder(
        _folder("folder", run=run, started=observed, observed=observed)
    )
    store.persist_contact(
        _contact(
            "contact",
            folder_id="folder",
            run=run,
            started=observed,
            observed=observed,
            raw={"companyName": "original"},
        )
    )
    store.persist_contact(
        _contact(
            "default-contact",
            default=True,
            run=run,
            started=observed,
            observed=observed,
        )
    )
    for kind, folder_id, default in (
        ("folder_inventory", None, False),
        ("contacts", None, True),
        ("contacts", "folder", False),
        ("child_folders", "folder", False),
    ):
        store.persist_completion(
            _complete(
                kind,
                run=run,
                started=observed,
                observed=observed,
                folder_id=folder_id,
                default=default,
            )
        )


def persist_snapshot(store: ContactsStore, item: ContactFolderItem | ContactItem):
    """Select the provider operation by the concrete local fixture type."""
    if isinstance(item, ContactFolderItem):
        return store.persist_folder(item)
    return store.persist_contact(item)


@pytest.mark.parametrize("folder", [False, True])
def test_snapshot_stages_exact_current_equivalent_and_stale_facts(catalog, folder):
    """Snapshot sightings cannot stand in for exact versioned source facts."""
    store = ContactsStore(catalog, source_id="source")
    item = _folder("id") if folder else _contact("id", default=True)
    persist_snapshot(store, item)
    persist_snapshot(store, item)
    first = facts(catalog, "run")
    if len(first) != 1 or first[0].storage_relation != StorageRelation.ADVANCED:
        pytest.fail("Exact repeated persistence must stage one advanced fact")
    persist_snapshot(
        store, replace(item, run_id="retry", observed_at="2026-10-01T00:00:00Z")
    )
    second = facts(catalog, "retry")[0]
    if (
        second.storage_relation != StorageRelation.CURRENT_EQUIVALENT
        or second.revalidated_fact_id != first[0].fact_id
    ):
        pytest.fail("Equivalent snapshot must pin the original advanced fact")
    persist_snapshot(store, replace(item, run_id="stale"))
    if facts(catalog, "stale")[0].storage_relation != StorageRelation.STALE:
        pytest.fail("Older snapshot fact must remain stale")
    if (
        second.source_version_locator is None
        or second.source_version_locator.evidence_id != item.evidence_id
    ):
        pytest.fail("Snapshot locator must reference exact evidence, not current row")


@pytest.mark.parametrize("folder", [False, True])
@pytest.mark.parametrize("existing", [False, True])
def test_snapshot_fact_failure_rolls_back_state_and_sightings(
    catalog, folder, existing
):
    """Fact-write failure must roll back each snapshot domain transaction."""
    store = ContactsStore(catalog, source_id="source")
    item = _folder("id") if folder else _contact("id", default=True)
    model = ContactFolderRecord if folder else ContactRecord
    sighting = ContactFolderSighting if folder else ContactSighting
    if existing:
        persist_snapshot(store, item)
    reject_facts(catalog)
    newer = replace(
        item,
        run_id="new",
        observed_at="2026-10-02T00:00:00Z",
        raw={"id": "id", "displayName": "changed"},
    )
    with pytest.raises(IntegrityError, match="injected fact failure"):
        persist_snapshot(store, newer)
    with catalog.Session() as session:
        row = session.scalars(select(model)).one_or_none()
        if (row is None) != (not existing) or row is not None and row.raw != item.raw:
            pytest.fail("Fact failure left a changed snapshot projection")
        if len(session.scalars(select(sighting)).all()) != int(existing):
            pytest.fail("Fact failure left a new snapshot sighting")
        if len(session.scalars(select(AcquisitionFact)).all()) != int(existing):
            pytest.fail("Failed snapshot write left a ledger fact")


def test_snapshot_retry_adopts_unreleased_state_without_repeating_work(catalog):
    """A later full unchanged snapshot adopts an unreleased advancement once."""
    store = ContactsStore(catalog, source_id="source")
    original_ids: set[str] = set()
    for day, run in enumerate(("failed", "retry", "unchanged"), 1):
        snapshot(store, run, day)
        rows = facts(catalog, run)
        if len(rows) != 3:
            pytest.fail("Snapshot must stage folder and both scoped contacts")
        if run == "failed":
            original_ids = {row.fact_id for row in rows}
            continue
        store.promote_snapshot(run)
        entries = publish(catalog, run, AcquisitionStream.CONTACTS, rows)
        if len(entries) != 3:
            pytest.fail("Unchanged snapshot duplicated work or failed recovery")
        released = {
            fact.fact_id
            for entry in entries
            for fact in AcquisitionHandoffStore(catalog).load_release_facts(
                entry["release_entry_seq"]
            )
        }
        if released != original_ids:
            pytest.fail("Retry fabricated a new immutable source version")


def stage_delta(store: ContactsStore, run: str, *, day: int = 3) -> None:
    """Stage sparse provider input and its opaque terminal cursor locally."""
    observed = f"2026-10-0{day}T00:00:00Z"
    store.begin_delta_run(folder_id="folder", run_id=run)
    store.persist_delta_observation(
        _contact(
            "contact",
            folder_id="folder",
            kind="delta",
            run=run,
            observed=observed,
            raw={"jobTitle": "new title"},
        )
    )
    store.stage_delta_candidate(
        ContactDeltaCheckpointCandidateItem(
            folder_id="folder",
            delta_link="https://graph.example.test/opaque?$deltatoken=secret",
            base_revision=None,
            observed_at=observed,
            evidence_id="delta-proof",
            run_id=run,
        )
    )


def test_sparse_delta_stays_authority_staged_and_never_uses_merged_record(catalog):
    """A sparse delta's immutable locator must not advertise a merged contact."""
    store = ContactsStore(catalog, source_id="source")
    snapshot(store, "seed", 1)
    store.promote_snapshot("seed")
    stage_delta(store, "delta")
    row = facts(catalog, "delta")[0]
    if (
        row.storage_relation != StorageRelation.AUTHORITY_STAGED
        or row.provider_order != 1
    ):
        pytest.fail("Sparse delta must retain authority staging and provider order")
    if (
        row.scope_identity != "folder:folder"
        or row.spider_name != "microsoft_contacts_delta"
    ):
        pytest.fail("Delta lost exact folder or acquisition provenance")
    locator = row.source_version_locator
    if locator is None or locator.kind != "observation" or not locator.observation_id:
        pytest.fail("Sparse delta must point to its ordered immutable observation")
    serialized = json.dumps(asdict(row))
    if any(
        value in serialized
        for value in ("new title", "original", "deltatoken", "secret")
    ):
        pytest.fail("Provider content or opaque cursor leaked into ledger")
    if publish(catalog, "early", AcquisitionStream.CONTACTS, [row]):
        pytest.fail("Sparse delta leaked before winning authority promotion")
    store.promote_delta(folder_id="folder", run_id="delta", base_revision=None)
    with catalog.Session() as session:
        merged = session.get(ContactRecord, ("source", "folder:folder", "contact"))
        observation = session.scalars(select(ContactDeltaObservation)).one()
        if (
            merged is None
            or merged.company_name != "original"
            or merged.job_title != "new title"
        ):
            pytest.fail("Existing ordered sparse merge was changed")
        if "companyName" in observation.raw:
            pytest.fail("Immutable delta observation was replaced with merged state")
    if facts(catalog, "delta")[0] != row:
        pytest.fail("Promotion mutated the historical provider fact")
    # Automatic release of winning delta state belongs to Task 9.
    if AcquisitionHandoffStore(catalog).list_release_entries(
        "source", AcquisitionStream.CONTACTS
    ):
        pytest.fail("Task 4 unexpectedly installed authority publication")


def test_delta_fact_failure_rolls_back_observation_and_ordinal(catalog):
    """A failed fact insert may not leave an untracked ordered observation."""
    store = ContactsStore(catalog, source_id="source")
    reject_facts(catalog)
    with pytest.raises(IntegrityError, match="injected fact failure"):
        stage_delta(store, "delta")
    with catalog.Session() as session:
        if session.scalar(select(ContactDeltaObservation)) is not None:
            pytest.fail("Fact failure left an ordered provider observation")
        if (
            session.scalar(select(AcquisitionFact)) is not None
            or session.scalar(select(AcquisitionEffectiveState)) is not None
        ):
            pytest.fail("Fact failure left partial handoff state")


def test_stale_generation_never_promotes_sparse_facts(catalog):
    """An older generation's durable delta staging cannot gain authority."""
    store = ContactsStore(catalog, source_id="source")
    stage_delta(store, "loser", day=1)
    row = facts(catalog, "loser")[0]
    snapshot(store, "winner", 2)
    store.promote_snapshot("winner")
    with pytest.raises(RuntimeError, match="generation is stale"):
        store.promote_delta(folder_id="folder", run_id="loser", base_revision=None)
    if publish(catalog, "loser-release", AcquisitionStream.CONTACTS, [row]):
        pytest.fail("Stale generation published a contact resource")
    if store.load_delta_checkpoint("folder") is not None:
        pytest.fail("Stale generation advanced its checkpoint")


def test_delta_duplicate_contact_entries_keep_distinct_ordered_locators(catalog):
    """Repeated IDs within a delta page must retain separate ordered facts."""
    store = ContactsStore(catalog, source_id="source")
    for raw in (
        {"jobTitle": "first"},
        {"@removed": {"reason": "deleted"}},
        {"jobTitle": "last"},
    ):
        store.persist_delta_observation(
            _contact("same", folder_id="folder", kind="delta", run="delta", raw=raw)
        )
    rows = facts(catalog, "delta")
    if sorted(
        row.provider_order if row.provider_order is not None else -1 for row in rows
    ) != [1, 2, 3]:
        pytest.fail("Delta order was lost or duplicate IDs were collapsed")
    if (
        len(
            {
                row.source_version_locator.observation_id
                for row in rows
                if row.source_version_locator
            }
        )
        != 3
    ):
        pytest.fail("Sparse observations share an ambiguous immutable locator")
    with catalog.Session() as session:
        if session.scalar(select(AcquisitionEffectiveState)) is not None:
            pytest.fail("Staging changed effective state before promotion")


def test_moved_folder_invalidates_its_previous_parent_fact(catalog):
    """A metadata parent change must supersede the same folder's old state."""
    store = ContactsStore(catalog, source_id="source")
    first = replace(_folder("folder"), raw={"id": "folder", "parentFolderId": "old"})
    store.persist_folder(first)
    old = facts(catalog, "run")
    store.persist_folder(
        replace(
            first,
            run_id="moved",
            observed_at="2026-10-02T00:00:00Z",
            raw={"id": "folder", "parentFolderId": "new"},
        )
    )
    if publish(catalog, "delayed-old-parent", AcquisitionStream.CONTACTS, old):
        pytest.fail("Moved folder retained a publishable stale parent state")
