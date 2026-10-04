"""Prove snapshot authority and exact handoff publication commit together."""

import json

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from message_ingest.acquisition.handoff import AcquisitionFactKind
from message_ingest.catalog.models.handoff import AcquisitionReleaseGroup
from message_ingest.catalog.models.microsoft.todo import TodoSnapshotCandidate
from tests import _todo_authority
from tests._todo_authority import (
    dump,
    empty_snapshot,
    entries,
    promote,
    released_facts,
    snapshot,
    staged,
)

catalog = _todo_authority.catalog


def test_snapshot_publishes_exact_resources_and_scoped_presence(catalog):
    """Missing automatic publication loses both content and authority facts."""
    store = snapshot(catalog, "first", 1)
    original = {fact.fact_id for fact in staged(catalog, "first")}
    promote(store, "first")
    facts = released_facts(catalog)
    positive = [f for f in facts if f.fact_kind != "scoped_state_transition"]
    transitions = [f for f in facts if f.fact_kind == "scoped_state_transition"]
    if {f.fact_id for f in positive} != original or len(transitions) != 4:
        pytest.fail("Promotion must bind four exact resources and presence facts")
    for fact in positive:
        if fact.source_version_locator is None:
            pytest.fail("Positive state lost its immutable evidence locator")
        if fact.source_version_locator.evidence_id != "ev-first":
            pytest.fail("Positive state points at the wrong capture")
    for fact in transitions:
        if (
            fact.scope_kind != "todo_source"
            or fact.scope_identity != "source"
            or fact.authority_revision != "1"
            or fact.transition_reason != "snapshot_present"
            or fact.evidence_id != "ev-first"
            or fact.source_version_locator is not None
        ):
            pytest.fail("Presence transition lost exact authority scope/proof")
    with catalog.Session() as session:
        groups = session.scalars(select(AcquisitionReleaseGroup)).all()
    if len(groups) != 1:
        pytest.fail("One winning snapshot must publish one atomic group")
    payload = json.loads(groups[0].payload)
    if payload["release_kind"] != "authority_scope":
        pytest.fail("Snapshot used a non-authoritative release")
    before = dump(catalog)
    store.promote_snapshot("first", base_revision=None)
    if dump(catalog) != before:
        pytest.fail("Retrying committed promotion changed immutable publication")


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize(
    "table",
    [
        "acquisition_facts",
        "acquisition_release_groups",
        "acquisition_release_entries",
        "acquisition_release_entry_facts",
    ],
)
def test_release_failure_rolls_back_entire_authority(catalog, existing, table):
    """SQL failure after CAS must roll back presence, facts and all entries."""
    if existing:
        promote(snapshot(catalog, "prior", 1), "prior")
    store = snapshot(catalog, "candidate", 2, list_id="new-list")
    base = store.load_revision()
    store.stage_candidate("candidate", base_revision=base)
    before = dump(catalog)
    with catalog.writer_session() as session:
        session.connection().exec_driver_sql(
            f"CREATE TRIGGER reject_task9c BEFORE INSERT ON {table} "
            "BEGIN SELECT RAISE(ABORT, 'injected release failure'); END"
        )
    try:
        with pytest.raises(IntegrityError, match="injected release failure"):
            store.promote_snapshot("candidate", base_revision=base)
        if dump(catalog) != before:
            pytest.fail("Release failure left a partial authority transaction")
    finally:
        with catalog.writer_session() as session:
            session.connection().exec_driver_sql("DROP TRIGGER reject_task9c")
    store.promote_snapshot("candidate", base_revision=base)
    if not entries(catalog):
        pytest.fail("Retry after release failure did not publish")
    with catalog.Session() as session:
        candidate = session.get(
            TodoSnapshotCandidate,
            ("source", "candidate"),
        )
        if candidate is None or candidate.committed_at is None:
            pytest.fail("Recovered authority did not commit its candidate")


def test_equivalent_unreleased_recovery_once_and_no_snapshot_churn(catalog):
    """Adopt original content once across all equivalent snapshots."""
    snapshot(catalog, "failed", 1)
    originals = {f.fact_id for f in staged(catalog, "failed")}
    promote(snapshot(catalog, "retry", 2), "retry")
    first = entries(catalog)
    if not first:
        pytest.fail("Equivalent retry lost unreleased advanced state")
    facts = released_facts(catalog)
    positive = {f.fact_id for f in facts if f.fact_kind != "scoped_state_transition"}
    if positive != originals:
        pytest.fail("Recovery fabricated a replacement source representation")
    promote(snapshot(catalog, "unchanged", 3), "unchanged")
    if entries(catalog) != first:
        pytest.fail("Unchanged released state generated repetitive work")
    if any(
        f.fact_kind == AcquisitionFactKind.SCOPED_STATE_TRANSITION
        for f in staged(catalog, "unchanged")
    ):
        pytest.fail("Unchanged presence fabricated a transition")


def test_absence_and_return_are_scoped_and_do_not_repeat(catalog):
    """Absent/present cycles must survive same-content reappearance."""
    promote(snapshot(catalog, "initial", 1), "initial")
    first_count = len(entries(catalog))
    promote(empty_snapshot(catalog, "empty", 2), "empty")
    absent_entries = entries(catalog)[first_count:]
    if len(absent_entries) != 4:
        pytest.fail("Complete empty snapshot did not publish four absences")
    absent = [f for f in released_facts(catalog) if f.run_id == "empty"]
    if len(absent) != 4 or any(
        f.transition_reason != "snapshot_absent"
        or f.scope_identity != "source"
        or f.authority_revision != "2"
        for f in absent
    ):
        pytest.fail("Absence is not the exact source-scoped authority transition")
    before = entries(catalog)
    promote(empty_snapshot(catalog, "still-empty", 3), "still-empty")
    if entries(catalog) != before:
        pytest.fail("Already absent state generated repetitive work")
    promote(snapshot(catalog, "returned", 4), "returned")
    returned = [f for f in released_facts(catalog) if f.run_id == "returned"]
    if len(returned) != 4 or any(
        f.transition_reason != "snapshot_present" or f.authority_revision != "4"
        for f in returned
    ):
        pytest.fail("Reappearance did not publish exact winning presence")
