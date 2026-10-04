"""
Verify exact Contacts authority releases and bounded reader compatibility.
"""

import asyncio
import json

import pytest
from sqlalchemy import select

from message_ingest.catalog.models.microsoft.contacts import (
    ContactDeltaObservation,
    ContactRecord,
)
from msgloom.sources import HandoffCatalog, SourceReaderLimits
from tests._contacts_authority import (
    delta,
    entries,
    groups,
    open_store,
    primary,
    snapshot,
)
from tests._todo_contacts_handoff import facts


@pytest.fixture
def owned(tmp_path):
    """Provide one disposable authority owner."""
    catalog, store = open_store(tmp_path / "contacts.db")
    yield catalog, store
    catalog.close()


def test_snapshot_publishes_exact_sources_and_scoped_presence(owned):
    """
    Missing in-transaction source or presence publication loses authority.
    """
    catalog, store = owned
    snapshot(store, "first", 1)
    before = {fact.fact_id for fact in facts(catalog, "first")}
    store.promote_snapshot("first")
    if {fact.fact_id for fact in primary(catalog)} != before:
        pytest.fail("Snapshot did not publish its exact three source facts")
    transitions = [
        fact
        for entry, rows in entries(catalog)
        if entry["entry_kind"] == "transition"
        for fact in rows
    ]
    if {
        (
            fact.resource_kind,
            fact.resource_identity,
            fact.scope_identity,
            fact.transition_reason,
        )
        for fact in transitions
    } != {
        ("contact_folder", "folder", "root", "present"),
        ("contact", "contact", "folder:folder", "present"),
        ("contact", "default-contact", "default", "present"),
    }:
        pytest.fail("Snapshot presence lost exact resource/scope identities")
    group = groups(catalog, "first")
    if len(group) != 1 or group[0]["authority_revision"] != "1":
        pytest.fail("Snapshot release does not bind winning shared generation")


def test_snapshot_retry_recovers_once_and_unchanged_round_has_zero_entries(owned):
    """Equivalent retry must recover a failed run without snapshot churn."""
    catalog, store = owned
    snapshot(store, "failed", 1)
    original = {fact.fact_id for fact in facts(catalog, "failed")}
    snapshot(store, "retry", 2)
    store.promote_snapshot("retry")
    if {fact.fact_id for fact in primary(catalog, "retry")} != original:
        pytest.fail("Equivalent snapshot failed exact unreleased recovery")
    snapshot(store, "unchanged", 3)
    store.promote_snapshot("unchanged")
    store.promote_snapshot("unchanged")
    if entries(catalog, "unchanged") or len(groups(catalog, "unchanged")) != 1:
        pytest.fail("Unchanged round churned or duplicate promotion changed group")


def test_snapshot_absence_is_scoped_and_incomplete_round_cannot_publish(owned):
    """
    Partial traversal must not claim absence or advance release authority.
    """
    catalog, store = owned
    snapshot(store, "seed", 1)
    store.promote_snapshot("seed")
    snapshot(store, "incomplete", 2, populated=False, complete=False)
    with pytest.raises(RuntimeError, match="incomplete"):
        store.promote_snapshot("incomplete")
    if groups(catalog, "incomplete"):
        pytest.fail("Incomplete snapshot published an authority group")
    snapshot(store, "empty", 3, populated=False)
    store.promote_snapshot("empty")
    if primary(catalog, "empty"):
        pytest.fail("Absence fabricated a primary provider representation")
    absent = [
        (fact.resource_identity, fact.scope_identity, fact.transition_reason)
        for entry, rows in entries(catalog, "empty")
        for fact in rows
    ]
    if set(absent) != {
        ("folder", "root", "not_in_complete_inventory"),
        ("contact", "folder:folder", "not_in_complete_snapshot"),
        ("default-contact", "default", "not_in_complete_snapshot"),
    }:
        pytest.fail("Absence escaped its exact authoritative collection")
    snapshot(store, "still-empty", 4, populated=False)
    store.promote_snapshot("still-empty")
    if entries(catalog, "still-empty"):
        pytest.fail("Repeated absence created duplicate downstream work")


def test_sparse_delta_releases_only_final_applied_observation(owned):
    """
    Releasing an intermediate ordinal or merged record changes replay truth.
    """
    catalog, store = owned
    snapshot(store, "seed", 1)
    store.promote_snapshot("seed")
    delta(
        store,
        "change",
        2,
        [
            {"jobTitle": "first"},
            {"@removed": {"reason": "deleted"}},
            {"jobTitle": "last"},
        ],
    )
    staged = facts(catalog, "change")
    winner = next(fact for fact in staged if fact.provider_order == 3)
    if entries(catalog, "change"):
        pytest.fail("Delta observations leaked before checkpoint promotion")
    store.promote_delta(folder_id="folder", run_id="change", base_revision=None)
    if [fact.fact_id for fact in primary(catalog, "change")] != [winner.fact_id]:
        pytest.fail("Delta failed to release exact final winning sparse observation")
    if facts(catalog, "change")[:3] != staged:
        pytest.fail("Promotion rewrote immutable staged delta provenance")
    with catalog.Session() as session:
        current = session.get(ContactRecord, ("source", "folder:folder", "contact"))
        exact = session.scalars(
            select(ContactDeltaObservation).filter_by(run_id="change", ordinal=3)
        ).one()
        if current is None or current.company_name != "original":
            pytest.fail("Promotion broke existing sparse current-state merge")
        if "companyName" in exact.raw:
            pytest.fail("Sparse replay locator points to mutable merged state")
    if len(groups(catalog, "change")) != 1:
        pytest.fail("Winning delta did not publish one atomic authority group")
    serialized = json.dumps(groups(catalog, "change"))
    if any(value in serialized for value in ("private", "jobTitle", "delta_link")):
        pytest.fail("Provider payload or cursor leaked into release metadata")


def test_delta_tombstone_is_transition_with_exact_winning_proof(owned):
    """A sparse tombstone cannot become a primary contact representation."""
    catalog, store = owned
    snapshot(store, "seed", 1)
    store.promote_snapshot("seed")
    delta(
        store,
        "remove",
        2,
        [{"jobTitle": "intermediate"}, {"@removed": {"reason": "deleted"}}],
    )
    tombstone = next(
        fact for fact in facts(catalog, "remove") if fact.provider_order == 2
    )
    store.promote_delta(folder_id="folder", run_id="remove", base_revision=None)
    released = entries(catalog, "remove")
    if len(released) != 1 or released[0][0]["entry_kind"] != "transition":
        pytest.fail("Final removal did not produce exactly one scoped transition")
    entry, rows = released[0]
    if (tombstone.fact_id, "proof") not in [tuple(pair) for pair in entry["facts"]]:
        pytest.fail("Removal lost its exact winning sparse tombstone proof")
    transition = next(fact for fact in rows if fact.component_kind == "presence")
    if (transition.scope_identity, transition.transition_reason) != (
        "folder:folder",
        "delta_removed",
    ):
        pytest.fail("Tombstone escaped scope or copied an arbitrary provider reason")


def test_stale_sparse_delta_advances_only_its_winning_checkpoint(owned):
    """
    An applied generation must not make individually skipped input primary.
    """
    catalog, store = owned
    delta(store, "old-delta", 1, [{"jobTitle": "stale"}])
    snapshot(store, "new-snapshot", 2)
    store.promote_delta(folder_id="folder", run_id="old-delta", base_revision=None)
    if entries(catalog, "old-delta") or len(groups(catalog, "old-delta")) != 1:
        pytest.fail("Skipped stale delta became a primary or presence entry")
    with pytest.raises(RuntimeError, match="generation is stale"):
        store.promote_snapshot("new-snapshot")
    if groups(catalog, "new-snapshot"):
        pytest.fail("Losing snapshot generation published authority")


def test_snapshot_winner_blocks_losing_delta_release(owned):
    """Shared generation fences snapshot and delta publication together."""
    catalog, store = owned
    delta(store, "old-delta", 1, [{"jobTitle": "stale"}])
    snapshot(store, "winner", 2)
    store.promote_snapshot("winner")
    with pytest.raises(RuntimeError, match="generation is stale"):
        store.promote_delta(folder_id="folder", run_id="old-delta", base_revision=None)
    if groups(catalog, "old-delta") or len(groups(catalog, "winner")) != 1:
        pytest.fail("Snapshot/delta no longer share publication ownership")


def test_delta_requires_terminal_candidate_and_repeated_state_has_no_churn(owned):
    """Partial delta cannot publish; exact repeated state is released once."""
    catalog, store = owned
    delta(store, "partial", 1, [{"jobTitle": "A"}], candidate=False)
    with pytest.raises(RuntimeError, match="candidate is missing"):
        store.promote_delta(folder_id="folder", run_id="partial", base_revision=None)
    if groups(catalog, "partial"):
        pytest.fail("Partial delta published authority or absence")
    for day, run in ((2, "first"), (3, "same")):
        revision = delta(store, run, day, [{"jobTitle": "A"}])
        store.promote_delta(folder_id="folder", run_id=run, base_revision=revision)
    if len(primary(catalog, "first")) != 1 or entries(catalog, "same"):
        pytest.fail("Repeated winning sparse state churned or first release lost")


def test_five_alternating_delta_states_keep_exact_readable_locators(tmp_path):
    """A/B/A/B/A must remain five distinct immutable feed applications."""
    path = tmp_path / "alternating.db"
    catalog, store = open_store(path)
    try:
        expected = []
        for day, state in enumerate(("A", "B", "A", "B", "A"), 1):
            run = f"delta-{day}"
            revision = delta(store, run, day, [{"jobTitle": state}])
            staged = facts(catalog, run)[0]
            expected.append(staged.fact_id)
            store.promote_delta(folder_id="folder", run_id=run, base_revision=revision)
        if [fact.fact_id for fact in primary(catalog)] != expected:
            pytest.fail("Alternating applications reused or lost immutable facts")

        async def read():
            reader = HandoffCatalog(path, SourceReaderLimits(max_list_results=2))
            try:
                maximum = await reader.max_release_entry_seq("source", "contacts")
                after = 0
                observed = []
                while after < maximum:
                    page = await reader.list_release_entries(
                        "source",
                        "contacts",
                        after_seq=after,
                        through_seq=maximum,
                        limit=2,
                    )
                    if not page.entries:
                        pytest.fail("Reader lost committed entries inside cutoff")
                    for entry in page.entries:
                        rows = await reader.get_release_facts(entry)
                        observed.extend(
                            fact.fact_id for fact in rows if fact.role == "primary"
                        )
                        if not await reader.verify_entry_anchor(
                            entry.release_entry_seq, entry.entry_digest
                        ):
                            pytest.fail("Reader rejected committed anchor")
                    after = page.entries[-1].release_entry_seq
                if observed != expected:
                    pytest.fail("Task 6 reader changed the five exact applications")
            finally:
                await reader.close()

        asyncio.run(read())
    finally:
        catalog.close()


def test_snapshot_release_rechecks_newer_unpromoted_source_state(owned):
    """A delayed snapshot must not release its superseded positive fact."""
    from tests.test_contacts_catalog import _contact

    catalog, store = owned
    snapshot(store, "old", 1)
    old = next(
        fact for fact in facts(catalog, "old") if fact.resource_identity == "contact"
    )
    store.persist_contact(
        _contact(
            "contact",
            folder_id="folder",
            run="newer-discovery",
            observed="2026-10-02T00:00:00Z",
            raw={"jobTitle": "newer"},
        )
    )
    store.promote_snapshot("old")
    released = primary(catalog, "old")
    if {fact.resource_identity for fact in released} != {"folder", "default-contact"}:
        pytest.fail("Delayed snapshot released a superseded contact or lost winners")
    if old.fact_id in {fact.fact_id for fact in released}:
        pytest.fail("Write-time advancement bypassed release-time freshness")


def test_snapshot_reappearance_publishes_transition_without_rewriting_source(owned):
    """Present/absent/present authority changes must retain source identity."""
    catalog, store = owned
    for run, day, populated in (
        ("present", 1, True),
        ("absent", 2, False),
        ("returned", 3, True),
    ):
        snapshot(store, run, day, populated=populated)
        store.promote_snapshot(run)
    returned = entries(catalog, "returned")
    if len(returned) != 3 or any(
        entry["entry_kind"] != "transition" for entry, rows in returned
    ):
        pytest.fail("Reappearance lost transitions or fabricated new source versions")
    if any(
        fact.transition_reason != "present" or fact.authority_revision != "3"
        for entry, rows in returned
        for fact in rows
    ):
        pytest.fail("Reappearance did not bind the exact winning authority")


def test_later_stale_delta_ordinal_cannot_replace_prior_applied_entry(owned):
    """A skipped final ordinal cannot displace an earlier applied winner."""
    from tests.test_contacts_catalog import _contact

    catalog, store = owned
    revision = delta(store, "mixed", 3, [{"jobTitle": "winning"}])
    winner = facts(catalog, "mixed")[0]
    store.persist_delta_observation(
        _contact(
            "contact",
            folder_id="folder",
            kind="delta",
            run="mixed",
            observed="2026-10-02T00:00:00Z",
            raw={"@removed": {}},
        )
    )
    store.promote_delta(folder_id="folder", run_id="mixed", base_revision=revision)
    if primary(catalog, "mixed") != [winner]:
        pytest.fail("Skipped tail replaced exact applied sparse primary state")
    if any(
        fact.transition_reason == "delta_removed"
        for entry, rows in entries(catalog, "mixed")
        for fact in rows
    ):
        pytest.fail("Skipped tail published an authoritative removal")


def test_delta_presence_transition_binds_exact_final_ordinal(owned):
    """Presence proof must identify the same sparse winner as the resource."""
    catalog, store = owned
    delta(
        store,
        "ordered",
        1,
        [{"jobTitle": "first"}, {"@removed": {}}, {"jobTitle": "last"}],
    )
    winner = next(
        fact for fact in facts(catalog, "ordered") if fact.provider_order == 3
    )
    store.promote_delta(folder_id="folder", run_id="ordered", base_revision=None)
    released = [
        (entry, rows)
        for entry, rows in entries(catalog, "ordered")
        if entry["entry_kind"] == "transition"
    ]
    if len(released) != 1:
        pytest.fail("Winning presence has no exact transition entry")
    entry, rows = released[0]
    transition = next(
        fact for fact in rows if fact.fact_kind == "scoped_state_transition"
    )
    if transition.provider_order != 3:
        pytest.fail("Presence transition lost the final applied ordinal")
    if [winner.fact_id, "proof"] not in entry["facts"]:
        pytest.fail("Presence transition lacks its exact winning source proof")
