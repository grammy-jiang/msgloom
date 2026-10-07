"""Prove Calendar authority publishes exact winning state atomically."""

import asyncio
import json

import pytest
from calendar_authority_helpers import (
    candidate,
    checkpoint,
    entries,
    groups,
    newer_event,
    published,
    reader_facts,
    snapshot,
    stage,
)
from calendar_authority_helpers import env as calendar_env
from calendar_handoff_helpers import LATER, NOW
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from message_ingest.catalog import CalendarDeltaEventState
from message_ingest.sync.microsoft.outlook.calendar.checkpoints import (
    CalendarDeltaCheckpointConflict,
)

env = calendar_env


def test_ordered_winner_retains_exact_locator_and_revision(env, tmp_path):
    """Only the final provider-ordered event state may become primary."""
    store = checkpoint(env)
    first = stage(env, "winner", "A", page=1, at=LATER)
    last = stage(env, "winner", "B", page=2, at=NOW)
    candidate(store, "winner")
    if entries(env):
        pytest.fail("Staged observations leaked before authority promotion")
    state = store.commit(run_id="winner", attempt=0)
    rows = entries(env)
    if len(rows) != 1:
        pytest.fail("Winning authority must publish one final resource impact")
    facts = published(env)
    primary = [f for f in facts if f.fact_kind == "resource_observation"]
    if primary != [last] or first in facts:
        pytest.fail("Release lost provider order or immutable observation locator")
    group = groups(env)[0]
    if (group["owner_run_id"], group["authority_revision"]) != ("winner", "1"):
        pytest.fail("Release group did not bind winning run and revision")
    if (
        group["scope_identity"]
        != '["default","2026-09-27T00:00:00+00:00","2026-09-28T00:00:00+00:00"]'
    ):
        pytest.fail("Release lost the exact fixed-window identity")
    before = snapshot(env)
    if store.commit(run_id="winner", attempt=0) != state or snapshot(env) != before:
        pytest.fail("Repeated checkpoint handling created publication churn")
    loaded = asyncio.run(reader_facts(tmp_path / "catalog.sqlite3"))
    if len(loaded) != 1:
        pytest.fail("Task6 reader could not consume the Calendar publication")


@pytest.mark.parametrize(
    "table",
    [
        "acquisition_facts",
        "acquisition_release_groups",
        "acquisition_release_entries",
        "acquisition_release_entry_facts",
    ],
)
def test_publication_failure_rolls_back_all_authority_rows(env, table):
    """Late fact/group/entry/member failures roll back the entire promotion."""
    store = checkpoint(env)
    stage(env, "base")
    candidate(store, "base")
    store.commit(run_id="base", attempt=0)
    stage(env, "next", "B")
    stage(env, "next", event="event-2", index=1)
    candidate(store, "next")
    before = snapshot(env)
    with env[1].writer_session() as session:
        session.connection().exec_driver_sql(
            f"CREATE TRIGGER fail_publication BEFORE INSERT ON {table} "
            "BEGIN SELECT RAISE(ABORT, 'injected publication failure'); END"
        )
    with pytest.raises(IntegrityError, match="injected publication failure"):
        store.commit(run_id="next", attempt=0)
    if snapshot(env) != before:
        pytest.fail("Publication failure partially committed authority")
    with env[1].writer_session() as session:
        session.connection().exec_driver_sql("DROP TRIGGER fail_publication")
    if store.commit(run_id="next", attempt=0).revision != 2:
        pytest.fail("Retry did not recover the rolled-back promotion")


def test_losing_candidate_cannot_publish(env):
    """Prevent a revision loser from publishing staged observations."""
    store = checkpoint(env)
    stage(env, "winner", "A")
    stage(env, "loser", "B")
    candidate(store, "winner")
    candidate(store, "loser")
    store.commit(run_id="winner", attempt=0)
    before = snapshot(env)
    with pytest.raises(CalendarDeltaCheckpointConflict, match="revision"):
        store.commit(run_id="loser", attempt=0)
    if snapshot(env) != before or not entries(env):
        pytest.fail("Losing candidate changed the winning publication")


def test_410_uses_winning_attempt_and_exact_window_absence(env):
    """Exclude superseded 410 observations and scope every removal."""
    store = checkpoint(env)
    other_end = "2026-09-30T00:00:00+00:00"
    other = checkpoint(env, end=other_end)
    for event in ("event-1", "event-2"):
        stage(env, "base", event=event, index=int(event[-1]))
    stage(env, "other", event="event-2", end=other_end)
    candidate(store, "base")
    store.commit(run_id="base", attempt=0)
    candidate(other, "other")
    other.commit(run_id="other", attempt=0)
    old = stage(env, "reset", "discard", event="ghost", attempt=0)
    winning = stage(env, "reset", "B", attempt=1)
    candidate(store, "reset", attempt=1)
    before = len(entries(env))
    store.commit(run_id="reset", attempt=1)
    added = entries(env)[before:]
    if {json.loads(e["payload"])["resource_identity"] for e in added} != {
        "event-1",
        "event-2",
    }:
        pytest.fail("Rebaseline lost exact changed/absent impacts")
    facts = published(env)
    if old in facts or winning not in facts:
        pytest.fail("A superseded 410 attempt leaked or winning locator was lost")
    absent = [
        f for f in facts if f.resource_identity == "event-2" and f.run_id == "reset"
    ]
    if not absent or any(f.scope_identity != winning.scope_identity for f in absent):
        pytest.fail("Rebaseline absence escaped the exact window")
    with env[1].Session() as session:
        rows = session.scalars(
            select(CalendarDeltaEventState).filter_by(
                end_datetime=other_end,
            )
        ).all()
        if len(rows) != 1 or not rows[0].is_present:
            pytest.fail("Window removal mutated another window")


def test_unchanged_repeated_rounds_do_not_churn(env):
    """New captures of already released state create only zero-entry groups."""
    store = checkpoint(env)
    for run in ("first", "same", "again"):
        stage(env, run)
        candidate(store, run)
        store.commit(run_id=run, attempt=0)
    if len(entries(env)) != 1 or len(groups(env)) != 3:
        pytest.fail("Unchanged authority rounds created repetitive primary work")


def test_exact_capture_a_b_a_b_a_remains_reader_compatible(env, tmp_path):
    """Preserve canonical locators across each state reapplication."""
    store = checkpoint(env)
    for i, version in enumerate(("A", "B", "A", "B", "A")):
        run = f"round-{i}"
        stage(env, run, version, evidence=f"capture-{version}")
        candidate(store, run)
        store.commit(run_id=run, attempt=0)
    loaded = asyncio.run(reader_facts(tmp_path / "catalog.sqlite3"))
    if len(loaded) != 5:
        pytest.fail(f"Expected five admitted state applications, got {len(loaded)}")
    locators = [
        next(f.source_version_locator for f in facts if f.role == "primary")
        for _, facts in loaded
    ]
    if locators[0] != locators[2] or locators[2] != locators[4]:
        pytest.fail("Admission sequence changed immutable source version identity")
    if locators[1] != locators[3]:
        pytest.fail("Repeated B capture lost its immutable locator")


def test_stale_event_cannot_publish_after_newer_source_state(env):
    """A pending stale event may not be released as later effective content."""
    store = checkpoint(env)
    stage(env, "old", "old", at=NOW)
    newer_event(env)
    candidate(store, "old")
    store.commit(run_id="old", attempt=0)
    if entries(env):
        pytest.fail("Stale event leaked as a primary or membership impact")


def test_pending_and_missing_candidate_publish_nothing(env):
    """No completion proof means no authority publication."""
    store = checkpoint(env)
    stage(env, "pending")
    with pytest.raises(LookupError, match="missing"):
        store.commit(run_id="pending", attempt=0)
    if entries(env) or groups(env):
        pytest.fail("Incomplete work published a release")


def test_superseded_terminal_candidate_cannot_publish(env):
    """An older attempt cannot publish after a replacement candidate exists."""
    store = checkpoint(env)
    stage(env, "reset", attempt=0)
    candidate(store, "reset", attempt=0)
    candidate(store, "reset", attempt=1)
    before = snapshot(env)
    with pytest.raises(CalendarDeltaCheckpointConflict, match="superseded"):
        store.commit(run_id="reset", attempt=0)
    if snapshot(env) != before:
        pytest.fail("Superseded terminal candidate mutated authority")


def test_unreleased_equivalent_authority_state_recovers_once(env):
    """A winning equivalent fact recovers the exact unpublished state once."""
    from message_ingest.acquisition.handoff import (
        AcquisitionStream,
        ReleaseGroupSpec,
        ReleaseKind,
    )
    from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore

    original = stage(env, "previous")
    handoff = AcquisitionHandoffStore(env[1])
    with env[1].writer_session() as session:
        handoff.release_authority_group_in_session(
            session,
            ReleaseGroupSpec(
                source_id="source-1",
                stream=AcquisitionStream.OUTLOOK_CALENDAR,
                release_kind=ReleaseKind.AUTHORITY_SCOPE,
                subject_kind="calendar_window",
                subject_identity="prior-authority",
                owner_run_id="previous",
                released_at=NOW,
                coverage_kind="complete",
            ),
            [],
            winning_fact_ids=[original.fact_id],
        )
    store = checkpoint(env)
    for run in ("retry", "again"):
        stage(env, run)
        candidate(store, run)
        store.commit(run_id=run, attempt=0)
    if len(entries(env)) != 1:
        pytest.fail("Equivalent authority recovery did not publish exactly once")
    resource = [f for f in published(env) if f.fact_kind == "resource_observation"]
    if resource != [original]:
        pytest.fail("Recovery rewrote the exact previously effective fact")


def test_explicit_removal_and_reappearance_keep_window_scope(env):
    """Keep provider tombstones scoped to window membership."""
    store = checkpoint(env)
    stage(env, "present")
    candidate(store, "present")
    store.commit(run_id="present", attempt=0)
    for run in ("removed", "still-removed"):
        stage(env, run, kind="removed")
        candidate(store, run)
        store.commit(run_id=run, attempt=0)
    rows = entries(env)
    if len(rows) != 2:
        pytest.fail("Repeated absence generated extra downstream work")
    entry = json.loads(rows[-1]["payload"])
    if entry["entry_kind"] != "transition" or entry["scope_kind"] != "calendar_window":
        pytest.fail("Scoped removal became an unscoped primary event")
    stage(env, "returned")
    candidate(store, "returned")
    store.commit(run_id="returned", attempt=0)
    if len(entries(env)) != 3:
        pytest.fail("Reappearance failed to create a fresh membership impact")
