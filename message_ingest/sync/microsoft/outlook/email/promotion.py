"""Validate one complete Outlook Mail delta run before durable promotion."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ValidatedMailDeltaRun:
    """Bounded runtime handoff produced only after delta integrity validates."""

    run_id: str
    expected_folder_ids: frozenset[str]
    reconcile_messages: bool
    candidate_folder_ids: frozenset[str]


def validate_mail_delta_run(
    snapshot: Mapping[str, object],
    candidates: Mapping[str, object],
) -> ValidatedMailDeltaRun:
    """Return the exact validated delta handoff or fail closed."""

    run_id = snapshot.get("run_id")
    started = snapshot.get("started_folder_ids")
    completed = snapshot.get("completed_folder_ids")
    reconcile_messages = snapshot.get("reconcile_messages")

    if not isinstance(run_id, str) or not run_id:
        raise ValueError("delta run is incomplete")
    if not isinstance(started, (set, frozenset)) or not all(
        isinstance(value, str) for value in started
    ):
        raise ValueError("delta run is incomplete")
    if not isinstance(completed, (set, frozenset)) or not all(
        isinstance(value, str) for value in completed
    ):
        raise ValueError("delta run is incomplete")
    if not isinstance(reconcile_messages, bool):
        raise TypeError("delta run reconcile mode has invalid type")

    expected = frozenset(started)
    completed_ids = frozenset(completed)
    candidate_ids = frozenset(candidates)

    if (
        bool(snapshot.get("run_failed"))
        or bool(snapshot.get("folder_inventory_failed"))
        or not bool(snapshot.get("folder_inventory_complete"))
        or not bool(snapshot.get("reconcile_complete"))
        or expected != completed_ids
        or completed_ids != candidate_ids
    ):
        raise ValueError("delta run is incomplete")

    return ValidatedMailDeltaRun(
        run_id=run_id,
        expected_folder_ids=expected,
        reconcile_messages=reconcile_messages,
        candidate_folder_ids=candidate_ids,
    )


__all__ = [
    "ValidatedMailDeltaRun",
    "promote_validated_mail_delta",
    "validate_mail_delta_run",
]


def promote_validated_mail_delta(
    catalog,
    *,
    source_id: str,
    validated: ValidatedMailDeltaRun,
) -> dict[str, int]:
    """Atomically promote lifecycle state and message-delta cursors."""

    from datetime import UTC, datetime

    from sqlalchemy import select

    from message_ingest.catalog.models.microsoft.outlook.email import (
        DeltaCheckpointCandidate,
    )
    from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
    from message_ingest.sync.microsoft.outlook.email.checkpoints import (
        OutlookDeltaCheckpointStore,
    )

    from ._release import release_mail_authority

    lifecycle = OutlookMailStore(catalog, source_id=source_id)
    checkpoints = OutlookDeltaCheckpointStore(catalog, source_id)
    committed_at = datetime.now(UTC).isoformat()
    with catalog.writer_session() as session:
        candidate_ids = frozenset(
            session.scalars(
                select(DeltaCheckpointCandidate.folder_id).filter_by(
                    source_id=source_id,
                    run_id=validated.run_id,
                )
            )
        )
        if not (
            candidate_ids
            == validated.candidate_folder_ids
            == validated.expected_folder_ids
        ):
            raise ValueError("Persisted delta candidate set changed")
        outcome = lifecycle.commit_delta_lifecycle_in_session(
            session,
            validated,
            committed_at=committed_at,
        )
        committed = checkpoints.commit_in_session(
            session,
            validated,
            committed_at=committed_at,
        )
        release_mail_authority(
            catalog,
            session,
            source_id=source_id,
            run_id=validated.run_id,
            committed_at=committed_at,
            subject="message_delta",
        )
        return {
            **outcome,
            "committed_folders": committed,
        }
