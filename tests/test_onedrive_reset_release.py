"""Qualify winning reset publication against immutable staged identities."""

import pytest
from sqlalchemy import select

from message_ingest.acquisition.handoff import StorageRelation
from message_ingest.catalog.models.microsoft.onedrive import (
    OneDriveDeltaResyncObservation,
    OneDriveItemRecord,
)
from tests._onedrive_authority import (
    T0,
    T1,
    T2,
    T3,
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


def test_reset_releases_last_applied_observation_and_exact_absence(catalog):
    """Repeated, skipped, and foreign attempts cannot contaminate winners."""
    base(catalog)
    item(catalog, "old", "absent")
    item(catalog, "old", "seen")
    item(catalog, "old", "raced")
    start_reset(catalog)
    sighting(catalog, {"id": "seen", "eTag": "A"})
    sighting(catalog, {"id": "seen", "eTag": "B"}, page=2)
    sighting(catalog, {"id": "new", "eTag": "C"}, page=2, index=1)
    sighting(catalog, {"id": "skipped", "eTag": "old"}, page=2, index=2)
    item(catalog, "concurrent", "skipped", at=T3, tag="new")
    item(catalog, "concurrent", "raced", at=T3, tag="new")
    # Residue from the pre-410 chain and another reset must remain unreleased.
    item(catalog, "reset", "expired-chain", at=T0)
    start_reset(catalog, "other")
    sighting(catalog, {"id": "foreign"}, run="other")
    candidate(catalog, "reset", 1)
    promote(catalog, "reset", 1, reset=1)
    facts = primary(catalog)
    if {fact.resource_identity for fact in facts} != {"seen", "new"}:
        pytest.fail("Reset release included skipped, expired, or foreign facts")
    with catalog.Session() as session:
        final = session.scalar(
            select(OneDriveDeltaResyncObservation).where(
                OneDriveDeltaResyncObservation.item_id == "seen",
                OneDriveDeltaResyncObservation.page_number == 2,
            )
        )
        if final is None:
            pytest.fail("Missing final ordered observation fixture")
        selected = next(fact for fact in facts if fact.resource_identity == "seen")
        locator = selected.source_version_locator
        if locator is None or locator.observation_id != str(final.observation_id):
            pytest.fail("Reset entry did not retain its last applied locator")
        if selected.evidence_id != final.evidence_id:
            pytest.fail("Reset entry reconstructed from a mutable current row")
    if any(fact.storage_relation != StorageRelation.AUTHORITY_STAGED for fact in facts):
        pytest.fail("Reset copied observations instead of referencing staged facts")
    absent = [
        fact
        for fact in transitions(catalog)
        if fact.transition_reason == "resync_absent"
    ]
    if {fact.resource_identity for fact in absent} != {"absent", "expired-chain"}:
        pytest.fail("Reset invented absence for a seen or newer resource")
    if any(
        (fact.scope_kind, fact.scope_identity, fact.authority_revision)
        != ("onedrive_source", "source", "2")
        for fact in absent
    ):
        pytest.fail("Derived absence lost its exact source/revision authority")
    if any(fact.source_version_locator is not None for fact in absent):
        pytest.fail("Inferred absence fabricated a provider representation")
    before = released(catalog)
    item(catalog, "later", "seen", at=T3, tag="later")
    if released(catalog) != before:
        pytest.fail("Mutable current advancement rewrote a released reset")


def test_incomplete_reset_cannot_publish_positive_or_absence(catalog):
    """Staged rows without a terminal candidate grant no authority."""
    base(catalog)
    item(catalog, "old", "absent")
    start_reset(catalog)
    sighting(catalog, {"id": "new"})
    before = snapshot(catalog)
    with pytest.raises(ValueError, match="candidate"):
        promote(catalog, "reset", 1, reset=1)
    if snapshot(catalog) != before or released(catalog):
        pytest.fail("Incomplete reset published state or absence")


def test_stale_reset_cannot_publish_or_materialize(catalog):
    """A losing checkpoint cannot promote even valid complete reset input."""
    base(catalog)
    item(catalog, "old", "absent")
    start_reset(catalog)
    sighting(catalog, {"id": "new"})
    candidate(catalog, "reset", 1)
    candidate(catalog, "winner", 1)
    promote(catalog, "winner", 1)
    before = snapshot(catalog)
    with pytest.raises(ValueError, match="revision"):
        promote(catalog, "reset", 1, reset=1)
    if snapshot(catalog) != before or primary(catalog):
        pytest.fail("Stale reset materialized or published its observations")


def test_reset_equivalent_recovery_once_and_no_unchanged_churn(catalog):
    """Reset can recover exact old state but cannot republish unchanged rows."""
    base(catalog)
    item(catalog, "failed")
    original = run_facts(catalog, "failed")[0]
    start_reset(catalog)
    sighting(catalog, {"id": "item", "name": "private-name", "eTag": "A"})
    candidate(catalog, "reset", 1)
    promote(catalog, "reset", 1, reset=1)
    if primary(catalog) != [original]:
        pytest.fail("Equivalent reset did not adopt unreleased exact bytes")
    before = released(catalog)
    start_reset(catalog, "again", base_revision=2)
    sighting(
        catalog,
        {"id": "item", "name": "private-name", "eTag": "A"},
        run="again",
        base_revision=2,
    )
    candidate(catalog, "again", 2)
    promote(catalog, "again", 2, reset=1)
    if released(catalog) != before:
        pytest.fail("Unchanged winning reset created repetitive work")
    if len(groups(catalog)) != 3:
        pytest.fail("Zero-change authority round lost its durable group")


def test_reset_older_later_position_does_not_override_applied_winner(catalog):
    """Provider ordering cannot bypass the existing capture-time freshness."""
    base(catalog)
    start_reset(catalog)
    sighting(catalog, {"id": "item", "eTag": "new"}, at=T2)
    sighting(catalog, {"id": "item", "eTag": "old"}, page=2, at=T1)
    candidate(catalog, "reset", 1)
    promote(catalog, "reset", 1, reset=1)
    facts = primary(catalog)
    if len(facts) != 1 or facts[0].evidence_id != "reset-page-1-0":
        pytest.fail("Skipped later position replaced the actual applied winner")


def test_source_scoped_absence_does_not_touch_other_source(catalog):
    """Reset reconciliation and transition scope must remain source-local."""
    base(catalog)
    with catalog.writer_session() as session:
        session.add(
            OneDriveItemRecord(
                source_id="elsewhere",
                item_id="foreign",
                raw={"id": "foreign"},
                is_deleted=False,
                latest_observed_at=T0,
                latest_evidence_id=None,
                latest_run_id="old",
            )
        )
    item(catalog, "old", "absent")
    start_reset(catalog)
    candidate(catalog, "reset", 1)
    promote(catalog, "reset", 1, reset=1)
    changes = transitions(catalog)
    if [fact.resource_identity for fact in changes] != ["absent"]:
        pytest.fail("Empty completed reset lost or widened source absence")
    with catalog.Session() as session:
        foreign = session.get(OneDriveItemRecord, ("elsewhere", "foreign"))
        if foreign is None or foreign.is_deleted:
            pytest.fail("Source-local reset changed another source")
