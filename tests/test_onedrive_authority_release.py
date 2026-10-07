"""Prove normal OneDrive checkpoint publication and rollback boundaries."""

import pytest
from sqlalchemy import event

from message_ingest.catalog.models.microsoft.onedrive import OneDriveItemRecord
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from tests._onedrive_authority import (
    T0,
    T1,
    T2,
    base,
    candidate,
    catalog,
    groups,
    item,
    primary,
    promote,
    released,
    run_facts,
    sighting,
    snapshot,
    start_reset,
    transitions,
)

__all__ = ["catalog"]


def test_delta_publishes_exact_run_state_only_after_winning_checkpoint(catalog):
    """A candidate alone or another run cannot publish resource effects."""
    item(catalog, "owner")
    item(catalog, "other", "unrelated")
    original = run_facts(catalog, "owner")[0]
    candidate(catalog, "owner", None)
    if released(catalog) or groups(catalog):
        pytest.fail("Staging published before checkpoint promotion")
    promote(catalog, "owner", None)
    if primary(catalog) != [original]:
        pytest.fail("Winning delta did not bind its exact run fact")
    rows = groups(catalog)
    if len(rows) != 1 or rows[0]["authority_revision"] != "1":
        pytest.fail("Checkpoint lacks one revision-bound authority group")
    if rows[0]["release_kind"] != "authority_scope":
        pytest.fail("Checkpoint used non-authoritative publication")
    saved = snapshot(catalog)
    promote(catalog, "owner", None)
    if snapshot(catalog) != saved:
        pytest.fail("Repeated checkpoint promotion churned ledger state")
    if "private" in repr(released(catalog)) or "private" in repr(rows):
        pytest.fail("Provider body or opaque cursor leaked into release metadata")


def test_delta_current_equivalent_recovers_unreleased_fact_once(catalog):
    """Recovery pins original bytes without manufacturing another version."""
    base(catalog)
    item(catalog, "failed")
    original = run_facts(catalog, "failed")[0]
    item(catalog, "retry", at=T1)
    candidate(catalog, "retry", 1)
    promote(catalog, "retry", 1)
    if primary(catalog) != [original]:
        pytest.fail("Equivalent retry lost the unreleased exact advancement")
    before = released(catalog)
    item(catalog, "unchanged", at=T2)
    candidate(catalog, "unchanged", 2)
    promote(catalog, "unchanged", 2)
    if released(catalog) != before:
        pytest.fail("Already released unchanged state created more work")


def test_delta_drops_superseded_and_stale_facts_within_winning_run(catalog):
    """Winning cursor cannot grant stale resource state publication rights."""
    item(catalog, "owner", "superseded")
    item(catalog, "newer", "superseded", at=T2, tag="B")
    item(catalog, "newer", "stale", at=T2, tag="B")
    item(catalog, "owner", "stale", at=T0)
    item(catalog, "owner", "winning", at=T1)
    candidate(catalog, "owner", None)
    promote(catalog, "owner", None)
    if [fact.resource_identity for fact in primary(catalog)] != ["winning"]:
        pytest.fail("Authority published a superseded or stale observation")


def test_delta_repeated_identity_publishes_only_final_effective_application(
    catalog,
):
    """A/B/A/B/A in one run preserves reapplication and immutable locators."""
    first = item(catalog, "owner")
    second = item(catalog, "owner", tag="B")
    # Reuse exact captures, without rewriting evidence fixture rows.
    from tests._onedrive_authority import store

    for value in (first, second, first):
        store(catalog).persist_item(value)
    facts = run_facts(catalog, "owner")
    if len(facts) != 5:
        pytest.fail("Fixture did not preserve all five accepted applications")
    candidate(catalog, "owner", None)
    promote(catalog, "owner", None)
    selected = primary(catalog)
    if len(selected) != 1 or selected[0].fact_id != facts[-1].fact_id:
        pytest.fail("Publication did not select the final exact A application")
    if selected[0].source_version_locator != facts[0].source_version_locator:
        pytest.fail("Release sequence changed the immutable provider locator")


def test_losing_delta_cannot_create_authority_group(catalog):
    """Checkpoint CAS rejection leaves both cursor and publication unchanged."""
    base(catalog)
    item(catalog, "loser")
    candidate(catalog, "loser", 1)
    candidate(catalog, "winner", 1)
    promote(catalog, "winner", 1)
    before = snapshot(catalog)
    with pytest.raises(ValueError, match="revision"):
        promote(catalog, "loser", 1)
    if snapshot(catalog) != before:
        pytest.fail("Losing delta changed authority or ledger")


@pytest.mark.parametrize("reset", [False, True])
@pytest.mark.parametrize("failure", ["group", "entry", "membership"])
def test_release_write_failure_rolls_back_checkpoint_state_and_ledger(
    catalog, reset, failure
):
    """A real SQL failure at each publication layer rolls back every write."""
    base(catalog)
    item(catalog, "old", "absent")
    if reset:
        start_reset(catalog, "owner")
        sighting(catalog, {"id": "new", "eTag": "B"}, run="owner")
    else:
        item(catalog, "owner", "new", at=T2)
    candidate(catalog, "owner", 1)
    before = snapshot(catalog)
    table = {
        "group": "acquisition_release_groups",
        "entry": "acquisition_release_entries",
        "membership": "acquisition_release_entry_facts",
    }[failure]

    def fail_write(_conn, _cursor, statement, _parameters, _context, _many):
        if statement.startswith(f"INSERT INTO {table} "):
            raise OSError(f"injected {failure} write failure")

    event.listen(catalog.engine, "before_cursor_execute", fail_write)
    try:
        with pytest.raises(OSError, match="injected"):
            promote(catalog, "owner", 1, reset=1 if reset else None)
    finally:
        event.remove(catalog.engine, "before_cursor_execute", fail_write)
    if snapshot(catalog) != before:
        pytest.fail("Release failure committed checkpoint, presence, or ledger")
    promote(catalog, "owner", 1, reset=1 if reset else None)
    if [fact.resource_identity for fact in primary(catalog)] != ["new"]:
        pytest.fail("Rollback retry did not publish the exact winning resource")


def test_provider_tombstone_is_an_exact_resource_and_scoped_transition(catalog):
    """Provider deletion must retain immutable bytes and source scope."""
    item(catalog, "owner", raw={"id": "item", "deleted": {}})
    candidate(catalog, "owner", None)
    promote(catalog, "owner", None)
    facts = primary(catalog)
    changes = transitions(catalog)
    if len(facts) != 1 or facts[0].evidence_id != "owner-item-A":
        pytest.fail("Provider tombstone lost its exact observation")
    if len(changes) != 1 or changes[0].transition_reason != "provider_deleted":
        pytest.fail("Tombstone lost its typed transition")
    if (changes[0].scope_kind, changes[0].scope_identity) != (
        "onedrive_source",
        "source",
    ):
        pytest.fail("Deletion escaped its source authority scope")


def test_release_failure_after_all_inserts_restores_flushed_presence(
    catalog, monkeypatch
):
    """Even completed ledger SQL cannot survive failure of its transaction."""
    base(catalog)
    item(catalog, "old", "absent")
    start_reset(catalog)
    sighting(catalog, {"id": "new"})
    candidate(catalog, "reset", 1)
    before = snapshot(catalog)
    original = AcquisitionHandoffStore.release_authority_group_in_session

    def fail_after(self, writer, *args, **kwargs):
        original(self, writer, *args, **kwargs)
        writer.flush()
        row = writer.get(OneDriveItemRecord, ("source", "absent"))
        if row is None or not row.is_deleted:
            pytest.fail("Failure injection did not reach materialized absence")
        raise OSError("injected after publication")

    monkeypatch.setattr(
        AcquisitionHandoffStore, "release_authority_group_in_session", fail_after
    )
    with pytest.raises(OSError, match="after publication"):
        promote(catalog, "reset", 1, reset=1)
    if snapshot(catalog) != before:
        pytest.fail("Failed transaction retained materialized absence")
