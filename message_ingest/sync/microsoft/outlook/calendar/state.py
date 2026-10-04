"""Materialize committed membership for one fixed Calendar delta view."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from sqlalchemy import Table, delete, insert, select, update
from sqlalchemy.engine import Connection

from message_ingest.acquisition.handoff import FactSpec, source_state_key
from message_ingest.catalog import CalendarDeltaEventState
from message_ingest.catalog.stores.microsoft.outlook._calendar_handoff import (
    event_projection,
)

from ._authority_observations import winning_observations


@dataclass(frozen=True)
class CalendarDeltaTransition:
    """An exact applied final state or derived fixed-window absence."""

    event_id: str
    is_present: bool
    fact: FactSpec | None
    state_changed: bool = True


def apply_calendar_delta_state(
    connection: Connection,
    *,
    scope: dict[str, str],
    run_id: str,
    attempt: int,
    revision: int,
    rebaseline: bool,
) -> tuple[CalendarDeltaTransition, ...]:
    """
    Apply the winning attempt and return its exact final transition identities.

    The caller owns the checkpoint's explicit writer transaction. Capture
    locators remain immutable across replay. Provider page/entry order decides
    the final window state, never release sequence or capture time.

    Rebaseline deletes only this window's old membership. Previously present
    members missing from the new enumeration produce scoped absence identities
    while that deletion is applied. No later scan reconstructs the decision.
    """
    state_table = cast(Table, CalendarDeltaEventState.__table__)
    observations = winning_observations(
        connection,
        scope=scope,
        run_id=run_id,
        attempt=attempt,
    )
    previous_present: set[str] = set()
    initial: dict[str, str | None] = {}
    if rebaseline:
        for row in connection.execute(
            select(state_table).filter_by(**scope)
        ).mappings():
            initial[str(row["event_id"])] = _window_state_key(row)
            if row["is_present"]:
                previous_present.add(str(row["event_id"]))
        connection.execute(delete(state_table).filter_by(**scope))

    applied: dict[str, CalendarDeltaTransition] = {}
    for fact, observation in observations:
        kind = str(observation["kind"])
        if kind not in {"upsert", "removed"}:
            raise ValueError(f"Unsupported Calendar delta observation kind: {kind!r}")
        event_id = str(observation["event_id"])
        values: dict[str, Any] = {
            "is_present": kind == "upsert",
            "last_kind": kind,
            "removed_reason": observation["removed_reason"],
            "latest_run_id": run_id,
            "latest_attempt": attempt,
            "latest_revision": revision,
            "latest_observed_at": str(observation["observed_at"]),
            "latest_evidence_id": str(observation["evidence_id"]),
            "raw": observation["raw"],
        }
        current = (
            connection.execute(
                select(state_table).filter_by(**scope, event_id=event_id)
            )
            .mappings()
            .one_or_none()
        )
        if event_id not in initial:
            initial[event_id] = _window_state_key(current) if current else None
        if current is None:
            connection.execute(
                insert(state_table).values(
                    **scope,
                    event_id=event_id,
                    **values,
                )
            )
        else:
            connection.execute(
                update(state_table)
                .where(
                    state_table.c.id == current["id"],
                )
                .values(**values)
            )
        # Reinsert so final impacts follow their last provider position.
        applied.pop(event_id, None)
        applied[event_id] = CalendarDeltaTransition(
            event_id=event_id,
            is_present=kind == "upsert",
            fact=fact,
            state_changed=fact.source_state_key != initial[event_id],
        )

    for event_id in sorted(previous_present - applied.keys()):
        applied[event_id] = CalendarDeltaTransition(
            event_id=event_id,
            is_present=False,
            fact=None,
        )
    return tuple(applied.values())


def _window_state_key(row) -> str:
    """Compare semantic state before mutation for future-only bootstrap."""
    return source_state_key(
        {
            "event": event_projection(row["raw"]),
            "kind": row["last_kind"],
        }
    )
