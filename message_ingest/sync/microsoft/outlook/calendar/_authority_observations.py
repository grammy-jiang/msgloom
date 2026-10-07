"""Resolve winning Calendar facts without rewriting immutable observations."""

from __future__ import annotations

import json
from typing import Any, cast

from sqlalchemy import Connection, Table, select

from message_ingest.acquisition.handoff import (
    AcquisitionStream,
    FactSpec,
    StorageRelation,
    canonical_json,
)
from message_ingest.catalog import CalendarDeltaObservation
from message_ingest.catalog.models.handoff import AcquisitionFact


def window_identity(scope: dict[str, str]) -> str:
    """Encode the exact Calendar scope without normalization."""
    return canonical_json(
        [
            scope["calendar_scope"],
            scope["start_datetime"],
            scope["end_datetime"],
        ]
    )


def winning_observations(
    connection: Connection,
    *,
    scope: dict[str, str],
    run_id: str,
    attempt: int,
) -> list[tuple[FactSpec, dict[str, Any]]]:
    """
    Resolve exact staged locators in this run's provider order.

    Capture deduplication retains the original observation row. The immutable
    fact owns the current run/attempt/order, while its locator still names that
    original row. Capture ownership need not equal acquisition ownership.
    Missing facts or mismatched locators fail the whole authority transaction.
    """
    facts = cast(Table, AcquisitionFact.__table__)
    observations = cast(Table, CalendarDeltaObservation.__table__)
    rows = connection.execute(
        select(facts.c.fact_id, facts.c.payload).where(
            facts.c.source_id == scope["source_id"],
            facts.c.stream == AcquisitionStream.OUTLOOK_CALENDAR,
            facts.c.run_id == run_id,
            facts.c.storage_relation == StorageRelation.AUTHORITY_STAGED,
        )
    )
    result = []
    bound: set[str] = set()
    positions: set[tuple[int, int]] = set()
    for fact_id, payload in rows:
        fact = FactSpec.from_json(payload)
        if fact.scope_kind != "calendar_window" or (
            fact.scope_identity != window_identity(scope)
        ):
            continue
        reason = json.loads(fact.transition_reason or "{}")
        if reason.get("attempt", -1) > attempt:
            raise ValueError("Calendar attempt superseded before publication")
        if reason.get("attempt") != attempt:
            continue
        locator = fact.source_version_locator
        if (
            fact.fact_id != fact_id
            or locator is None
            or (locator.kind != "observation" or not locator.observation_id)
        ):
            raise ValueError("Invalid Calendar authority observation locator")
        row = (
            connection.execute(
                select(observations).filter_by(
                    observation_id=locator.observation_id,
                    **scope,
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None or (
            row["event_id"] != fact.resource_identity
            or row["evidence_id"] != fact.evidence_id
            or row["kind"] != reason.get("kind")
            or locator.evidence_id != fact.evidence_id
            or locator.resource_identity != fact.resource_identity
            or fact.resource_kind != "calendar_event"
        ):
            raise ValueError("Calendar authority fact does not bind observation")
        page, index = reason["page_number"], reason["entry_index"]
        position = (page, index)
        if position in positions or fact.provider_order != (page << 32) + index:
            raise ValueError("Ambiguous Calendar authority provider order")
        positions.add(position)
        bound.add(str(row["observation_id"]))
        values = dict(row)
        values.update(
            run_id=run_id,
            attempt=attempt,
            page_number=page,
            entry_index=index,
            observed_at=fact.provider_observed_at,
        )
        result.append((fact, values))
    own_rows = set(
        connection.execute(
            select(observations.c.observation_id).filter_by(
                **scope,
                run_id=run_id,
                attempt=attempt,
            )
        ).scalars()
    )
    if not own_rows <= bound:
        raise ValueError("Calendar authority observation has no staged fact")
    return sorted(
        result,
        key=lambda pair: (
            pair[1]["page_number"],
            pair[1]["entry_index"],
            pair[1]["observation_id"],
        ),
    )
