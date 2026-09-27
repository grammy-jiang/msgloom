"""Materialize committed membership for one fixed Calendar delta view."""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy import Table, delete, insert, select, update
from sqlalchemy.engine import Connection

from message_ingest.catalog import (
    CalendarDeltaEventState,
    CalendarDeltaObservation,
)


def apply_calendar_delta_state(
    connection: Connection,
    *,
    scope: dict[str, str],
    run_id: str,
    attempt: int,
    revision: int,
    rebaseline: bool,
) -> int:
    """
    Apply one winning delta attempt to the committed fixed-window view.

    This runs inside the same transaction that advances the provider checkpoint.
    A rebaseline clears previous membership first because a restarted initial
    delta enumerates current membership rather than removals from the old token.
    """
    observation_table = cast(Table, CalendarDeltaObservation.__table__)
    state_table = cast(Table, CalendarDeltaEventState.__table__)

    if rebaseline:
        connection.execute(delete(state_table).filter_by(**scope))

    observations = (
        connection.execute(
            select(observation_table)
            .filter_by(
                **scope,
                run_id=run_id,
                attempt=attempt,
            )
            .order_by(
                observation_table.c.page_number,
                observation_table.c.entry_index,
                observation_table.c.observation_id,
            )
        )
        .mappings()
        .all()
    )

    for observation in observations:
        kind = str(observation["kind"])
        if kind not in {"upsert", "removed"}:
            raise ValueError(
                f"Unsupported Calendar delta observation kind: {kind!r}"
            )
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
                select(state_table.c.id).filter_by(
                    **scope,
                    event_id=event_id,
                )
            )
            .mappings()
            .one_or_none()
        )
        if current is None:
            connection.execute(
                insert(state_table).values(
                    **scope,
                    event_id=event_id,
                    **values,
                )
            )
            continue
        connection.execute(
            update(state_table)
            .where(state_table.c.id == current["id"])
            .values(**values)
        )

    return len(observations)
