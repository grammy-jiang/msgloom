"""Verify atomic Calendar membership projection and reset behavior."""

from pathlib import Path

import pytest
from calendar_checkpoint_helpers import _candidate, _observation, _store
from sqlalchemy import select

from message_ingest.calendar_checkpoints import CalendarDeltaCheckpointConflict
from message_ingest.catalog import CalendarDeltaEventState


def test_commit_materializes_only_winning_fixed_window_state(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        _observation(
            store,
            run_id="run-1",
            attempt=0,
            event_id="event-1",
            kind="upsert",
            page_number=1,
            entry_index=0,
            evidence_id="evidence-1",
            raw={"id": "event-1", "subject": "Initial"},
        )
        _observation(
            store,
            run_id="run-1",
            attempt=0,
            event_id="event-2",
            kind="upsert",
            page_number=1,
            entry_index=1,
            evidence_id="evidence-2",
            raw={"id": "event-2", "subject": "Second"},
        )
        _candidate(
            store,
            run_id="run-1",
            attempt=0,
            base_revision=None,
            delta_link="https://graph.microsoft.com/delta/one",
            evidence_id="terminal-1",
        )

        with store.catalog.Session() as session:
            if session.scalars(select(CalendarDeltaEventState)).all():
                pytest.fail(
                    "Pending Calendar delta observations must not change "
                    "committed view state"
                )

        first = store.commit(run_id="run-1", attempt=0)
        if first.revision != 1:
            pytest.fail("Expected first Calendar view revision")

        _observation(
            store,
            run_id="run-2",
            attempt=0,
            event_id="event-1",
            kind="upsert",
            page_number=1,
            entry_index=0,
            evidence_id="evidence-3",
            raw={"id": "event-1", "subject": "Moved"},
        )
        _observation(
            store,
            run_id="run-2",
            attempt=0,
            event_id="event-2",
            kind="removed",
            page_number=1,
            entry_index=1,
            evidence_id="evidence-4",
            raw={"id": "event-2", "@removed": {"reason": "deleted"}},
            removed_reason="deleted",
        )
        _candidate(
            store,
            run_id="run-2",
            attempt=0,
            base_revision=first.revision,
            delta_link="https://graph.microsoft.com/delta/two",
            evidence_id="terminal-2",
        )
        second = store.commit(run_id="run-2", attempt=0)

        with store.catalog.Session() as session:
            states = {
                row.event_id: row
                for row in session.scalars(select(CalendarDeltaEventState)).all()
            }
            event1 = states["event-1"]
            event2 = states["event-2"]
            if (
                event1.is_present is not True
                or event1.raw.get("subject") != "Moved"
                or event1.latest_revision != second.revision
            ):
                pytest.fail(f"Unexpected committed Calendar event-1 state: {event1!r}")
            if (
                event2.is_present is not False
                or event2.removed_reason != "deleted"
                or event2.latest_revision != second.revision
            ):
                pytest.fail(f"Unexpected committed Calendar event-2 state: {event2!r}")
    finally:
        store.close()


def test_stale_candidate_cannot_mutate_committed_view_state(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        _observation(
            store,
            run_id="base",
            attempt=0,
            event_id="event-1",
            kind="upsert",
            page_number=1,
            entry_index=0,
            evidence_id="base-evidence",
            raw={"id": "event-1", "subject": "Base"},
        )
        _candidate(
            store,
            run_id="base",
            attempt=0,
            base_revision=None,
            delta_link="https://graph.microsoft.com/delta/base",
            evidence_id="base-terminal",
        )
        first = store.commit(run_id="base", attempt=0)

        for run_id, subject in (("winner", "Winner"), ("stale", "Stale")):
            _observation(
                store,
                run_id=run_id,
                attempt=0,
                event_id="event-1",
                kind="upsert",
                page_number=1,
                entry_index=0,
                evidence_id=f"{run_id}-evidence",
                raw={"id": "event-1", "subject": subject},
            )
            _candidate(
                store,
                run_id=run_id,
                attempt=0,
                base_revision=first.revision,
                delta_link=f"https://graph.microsoft.com/delta/{run_id}",
                evidence_id=f"{run_id}-terminal",
            )

        winner = store.commit(run_id="winner", attempt=0)
        with pytest.raises(CalendarDeltaCheckpointConflict, match="revision"):
            store.commit(run_id="stale", attempt=0)

        with store.catalog.Session() as session:
            state = session.scalar(
                select(CalendarDeltaEventState).filter_by(event_id="event-1")
            )
            if (
                state is None
                or state.raw.get("subject") != "Winner"
                or state.latest_revision != winner.revision
            ):
                pytest.fail("Stale Calendar candidate changed committed view state")
    finally:
        store.close()


def test_reset_attempt_rebaselines_fixed_window_membership(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        for index, event_id in enumerate(("event-1", "event-2")):
            _observation(
                store,
                run_id="base",
                attempt=0,
                event_id=event_id,
                kind="upsert",
                page_number=1,
                entry_index=index,
                evidence_id=f"base-{event_id}",
                raw={"id": event_id},
            )
        _candidate(
            store,
            run_id="base",
            attempt=0,
            base_revision=None,
            delta_link="https://graph.microsoft.com/delta/base",
            evidence_id="base-terminal",
        )
        first = store.commit(run_id="base", attempt=0)

        _observation(
            store,
            run_id="reset",
            attempt=1,
            event_id="event-1",
            kind="upsert",
            page_number=1,
            entry_index=0,
            evidence_id="reset-event-1",
            raw={"id": "event-1", "subject": "Current"},
        )
        _candidate(
            store,
            run_id="reset",
            attempt=1,
            base_revision=first.revision,
            delta_link="https://graph.microsoft.com/delta/reset",
            evidence_id="reset-terminal",
        )
        store.commit(run_id="reset", attempt=1)

        with store.catalog.Session() as session:
            states = session.scalars(
                select(CalendarDeltaEventState).order_by(
                    CalendarDeltaEventState.event_id
                )
            ).all()
            if [row.event_id for row in states] != ["event-1"]:
                pytest.fail(
                    "Rebaseline must remove membership not present in the "
                    "restarted initial delta"
                )
    finally:
        store.close()
