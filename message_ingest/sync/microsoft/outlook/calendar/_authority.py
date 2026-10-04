"""Publish one Calendar authority decision inside its Core transaction."""

from __future__ import annotations

import json
from typing import cast

from sqlalchemy import Connection, Table, select

from message_ingest.acquisition.handoff import (
    AcquisitionFactKind,
    AcquisitionStream,
    FactRole,
    FactSpec,
    ReleaseEntryKind,
    ReleaseEntrySpec,
    ReleaseGroupSpec,
    ReleaseKind,
    canonical_json,
    source_state_key,
)
from message_ingest.catalog import CalendarEventRecord
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.catalog.stores.microsoft.outlook._calendar_handoff import (
    event_projection,
)
from message_ingest.catalog.stores.microsoft.outlook.calendar import (
    OutlookCalendarStore,
)

from ._authority_observations import window_identity
from .state import CalendarDeltaTransition


def _superseded_event(
    connection: Connection,
    scope: dict[str, str],
    fact: FactSpec,
) -> bool:
    """Reject a stale primary against the provider's current freshness rule."""
    events = cast(Table, CalendarEventRecord.__table__)
    current = (
        connection.execute(
            select(events).filter_by(
                source_id=scope["source_id"],
                event_id=fact.resource_identity,
            )
        )
        .mappings()
        .one_or_none()
    )
    if current is None:
        return False
    return OutlookCalendarStore._is_older_capture(
        fact.provider_observed_at,
        str(current["latest_observed_at"]),
    ) and fact.source_state_key != source_state_key(
        {
            "event": event_projection(current["raw"]),
            "kind": "upsert",
        }
    )


def publish_calendar_authority(
    connection: Connection,
    handoff: AcquisitionHandoffStore,
    transitions: tuple[CalendarDeltaTransition, ...],
    *,
    scope: dict[str, str],
    run_id: str,
    attempt: int,
    revision: int,
    committed_at: str,
    terminal_observed_at: str,
    terminal_evidence_id: str,
) -> str:
    """
    Bind winning observations, membership facts, group and entries atomically.

    The checkpoint caller owns BEGIN IMMEDIATE and lifecycle/CAS validation.
    This helper never opens a transaction. Provider payloads and opaque cursors
    stay outside the ledger. Exact staged resource facts retain their original
    locators; scoped membership facts carry only bounded transition metadata.
    """
    identity = window_identity(scope)
    entries: list[ReleaseEntrySpec] = []
    winning: list[str] = []
    for transition in transitions:
        fact = transition.fact
        if (
            fact is not None
            and not transition.state_changed
            and handoff.current_effective_state(connection, fact.effective_key) is None
        ):
            # Unchanged pre-ledger authority has no advanced fact to recover.
            # Future-only bootstrap must not invent a historical publication.
            continue
        if (
            fact is not None
            and transition.is_present
            and (_superseded_event(connection, scope, fact))
        ):
            continue
        reason = json.loads(fact.transition_reason or "{}") if fact else {}
        membership = handoff.stage_state_fact_in_session(
            connection,
            FactSpec(
                source_id=scope["source_id"],
                stream=AcquisitionStream.OUTLOOK_CALENDAR,
                run_id=run_id,
                spider_name="outlook_calendar_delta",
                fact_kind=AcquisitionFactKind.SCOPED_STATE_TRANSITION,
                resource_kind="calendar_event",
                resource_identity=transition.event_id,
                scope_kind="calendar_window",
                scope_identity=identity,
                component_kind="window_membership",
                provider_observed_at=(
                    fact.provider_observed_at if fact else terminal_observed_at
                ),
                evidence_id=fact.evidence_id if fact else terminal_evidence_id,
                source_state_key=source_state_key(
                    {
                        "is_present": transition.is_present,
                    }
                ),
                authority_revision=str(revision),
                provider_order=fact.provider_order if fact else None,
                transition_reason=canonical_json(
                    {
                        "attempt": attempt,
                        "kind": (
                            "present"
                            if transition.is_present
                            else "removed"
                            if fact
                            else "rebaseline_absence"
                        ),
                        "removed_reason": reason.get("removed_reason"),
                    }
                ),
            ),
        )
        members: list[tuple[str, FactRole]] = [
            (membership.fact_id, "transition"),
        ]
        if fact is not None:
            winning.append(fact.fact_id)
            members.insert(
                0,
                (
                    fact.fact_id,
                    "primary" if transition.is_present else "proof",
                ),
            )
        entries.append(
            ReleaseEntrySpec(
                resource_kind="calendar_event",
                resource_identity=transition.event_id,
                scope_kind="calendar_window",
                scope_identity=identity,
                entry_kind=(
                    ReleaseEntryKind.RESOURCE
                    if transition.is_present
                    else ReleaseEntryKind.TRANSITION
                ),
                facts=tuple(members),
            )
        )
    return handoff.release_authority_group_in_session(
        connection,
        ReleaseGroupSpec(
            source_id=scope["source_id"],
            stream=AcquisitionStream.OUTLOOK_CALENDAR,
            release_kind=ReleaseKind.AUTHORITY_SCOPE,
            subject_kind="calendar_window",
            subject_identity=canonical_json([identity, attempt]),
            scope_kind="calendar_window",
            scope_identity=identity,
            owner_run_id=run_id,
            released_at=committed_at,
            coverage_kind="complete",
            authority_revision=str(revision),
        ),
        entries,
        winning_fact_ids=winning,
    )
