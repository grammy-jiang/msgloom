"""Calendar authority fixtures using the real evidence and provider writers."""

import json

import pytest
from calendar_handoff_helpers import LATER, NOW, _capture, _facts, _item, _persist
from calendar_handoff_helpers import env as calendar_env
from sqlalchemy import select

from message_ingest.acquisition.handoff import AcquisitionStream
from message_ingest.catalog.models.handoff import AcquisitionReleaseGroup
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.items.microsoft.outlook.calendar import (
    OutlookCalendarDeltaObservationItem,
)
from message_ingest.sync.microsoft.outlook.calendar.checkpoints import (
    CalendarDeltaCheckpointStore,
)
from msgloom.sources.handoff_catalog import HandoffCatalog

env = calendar_env


def checkpoint(env, *, end=LATER):
    """Borrow the catalog for one fixed window."""
    return CalendarDeltaCheckpointStore(
        env[1],
        source_id="source-1",
        start_datetime=NOW,
        end_datetime=end,
    )


def stage(
    env,
    run,
    version="A",
    *,
    event="event-1",
    attempt=0,
    page=1,
    index=0,
    at=NOW,
    kind="upsert",
    evidence=None,
    end=LATER,
):
    """Persist evidence before one ordered authority-staged observation."""
    evidence = evidence or f"{run}-{attempt}-{page}-{index}"
    raw = {"id": event, "changeKey": version}
    if kind == "removed":
        raw = {"id": event, "@removed": {"reason": "deleted"}}
    _capture(env[0], evidence, at=at, body=json.dumps({"value": [raw]}).encode())
    item = OutlookCalendarDeltaObservationItem(
        event_id=event,
        kind=kind,
        raw=raw,
        observed_at=at,
        evidence_id=evidence,
        run_id=run,
        attempt=attempt,
        page_number=page,
        entry_index=index,
        start_datetime=NOW,
        end_datetime=end,
        removed_reason="deleted" if kind == "removed" else None,
    )
    _persist(env[0], item)
    matches = [
        f
        for f in _facts(env[1])
        if f.run_id == run
        and f.evidence_id == evidence
        and f.scope_identity is not None
        and json.loads(f.transition_reason or "{}").get("attempt") == attempt
    ]
    if len(matches) != 1:
        pytest.fail(f"Expected one exact staged observation, got {matches}")
    return matches[0]


def candidate(store, run, *, attempt=0):
    """Stage the terminal candidate against the current revision."""
    current = store.get_checkpoint()
    store.write_candidate(
        run_id=run,
        attempt=attempt,
        base_revision=None if current is None else current.revision,
        delta_link=f"https://graph.microsoft.com/delta/{run}/{attempt}",
        evidence_id=f"terminal-{run}-{attempt}",
        observed_at=LATER,
    )


def entries(env):
    """Read published entries through the frozen A1 ledger API."""
    return AcquisitionHandoffStore(env[1]).list_release_entries(
        "source-1",
        AcquisitionStream.OUTLOOK_CALENDAR,
    )


def published(env):
    """Load exact immutable facts through the public ledger reader."""
    handoff = AcquisitionHandoffStore(env[1])
    return [
        f
        for e in entries(env)
        for f in handoff.load_release_facts(e["release_entry_seq"])
    ]


def groups(env):
    """Read immutable authority metadata."""
    with env[1].Session() as session:
        return [
            json.loads(row.payload)
            for row in session.scalars(select(AcquisitionReleaseGroup))
        ]


def snapshot(env):
    """Capture every authority-owned row for publication fault injection."""
    names = (
        "calendar_delta_checkpoints",
        "calendar_delta_checkpoint_candidates",
        "calendar_delta_event_states",
        "acquisition_facts",
        "acquisition_effective_states",
        "acquisition_release_groups",
        "acquisition_release_entries",
        "acquisition_release_entry_facts",
    )
    with env[1].engine.connect() as connection:
        return {
            name: connection.exec_driver_sql(
                f'SELECT * FROM "{name}" ORDER BY rowid'
            ).all()
            for name in names
        }


def newer_event(env):
    """Write a later ordinary event so a pending delta is stale at release."""
    _capture(env[0], "newer", at=LATER)
    item = _item("event", "newer", "newer", LATER, "newer")
    _persist(env[0], item)


async def reader_facts(path):
    """Validate Task6's exact entry and fact wire contracts."""
    reader = HandoffCatalog(path)
    try:
        ceiling = await reader.max_release_entry_seq("source-1", "outlook_calendar")
        page = await reader.list_release_entries(
            "source-1",
            "outlook_calendar",
            through_seq=ceiling,
            limit=100,
        )
        return [
            (entry, await reader.get_release_facts(entry)) for entry in page.entries
        ]
    finally:
        await reader.close()
