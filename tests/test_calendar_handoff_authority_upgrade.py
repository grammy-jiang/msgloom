"""Keep future-only Calendar authority upgrades from backfilling old state."""

import pytest
from calendar_authority_helpers import candidate, checkpoint, entries, stage
from calendar_authority_helpers import env as calendar_env
from calendar_handoff_helpers import LATER, NOW

from message_ingest.catalog import CalendarDeltaEventState

env = calendar_env


def test_unchanged_preledger_window_is_not_new_primary_work(env):
    """Keep unchanged legacy state out of future-only publication."""
    store = checkpoint(env)
    candidate(store, "legacy")
    store.commit(run_id="legacy", attempt=0)
    with env[1].writer_session() as session:
        session.add(
            CalendarDeltaEventState(
                source_id="source-1",
                calendar_scope="default",
                start_datetime=NOW,
                end_datetime=LATER,
                event_id="event-1",
                is_present=True,
                last_kind="upsert",
                removed_reason=None,
                latest_run_id="legacy",
                latest_attempt=0,
                latest_revision=1,
                latest_observed_at=NOW,
                latest_evidence_id="legacy",
                raw={"id": "event-1", "changeKey": "A"},
            )
        )
    stage(env, "same", "A")
    candidate(store, "same")
    store.commit(run_id="same", attempt=0)
    if entries(env):
        pytest.fail("Future-only upgrade fabricated work from unchanged legacy state")
    stage(env, "changed", "B")
    candidate(store, "changed")
    store.commit(run_id="changed", attempt=0)
    if len(entries(env)) != 1:
        pytest.fail("A genuinely advanced post-ledger state must publish")
