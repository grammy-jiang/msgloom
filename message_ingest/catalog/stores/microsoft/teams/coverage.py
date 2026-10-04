"""Persistence for additive Teams coverage and sticky history uncertainty."""

from __future__ import annotations

from sqlalchemy import select

from message_ingest.catalog.models.microsoft.teams.coverage import (
    TeamsCoverageCurrent,
    TeamsCoverageObservation,
)
from message_ingest.catalog.store import Catalog
from message_ingest.items.microsoft.teams.coverage import TeamsCoverageItem

from ._common import (
    Outcome,
    compare_observed,
    require_evidence,
    require_source,
    scope_digest,
)


class TeamsCoverageStore:
    """Retain coverage history without letting reconciliation erase known gaps."""

    def __init__(self, catalog: Catalog, *, source_id: str) -> None:
        self.catalog = catalog
        self.source_id = source_id

    def persist(self, item: TeamsCoverageItem) -> Outcome:
        """Append one fact and update latest fields with sticky incompleteness."""
        require_source(item.source_id, self.source_id)
        scope_key, digest = scope_digest(("coverage", item.scope_kind, *item.scope))
        with self.catalog.writer_session() as session:
            evidence = require_evidence(
                session,
                source_id=self.source_id,
                evidence_id=item.evidence_id,
                observed_at=item.observed_at,
            )
            existing = session.scalar(
                select(TeamsCoverageObservation).filter_by(
                    source_id=self.source_id,
                    scope_key_sha256=digest,
                    evidence_id=evidence.evidence_id,
                )
            )
            if existing is not None:
                if (
                    existing.fact_kind != item.fact_kind
                    or existing.status != item.status
                    or existing.details != item.details
                    or existing.history_incomplete != item.history_incomplete
                    or existing.visible_scope != item.visible_scope
                    or existing.retention_limitations != item.retention_limitations
                    or existing.subscription_id != item.subscription_id
                    or existing.subscription_valid_from != item.subscription_valid_from
                    or existing.subscription_valid_until
                    != item.subscription_valid_until
                    or existing.gap_kind != item.gap_kind
                ):
                    raise ValueError("Teams coverage replay changed immutable facts")
                return "replay"
            observation = TeamsCoverageObservation(
                source_id=self.source_id,
                scope_kind=item.scope_kind,
                scope_key=[value for value in scope_key if value is not None],
                scope_key_sha256=digest,
                fact_kind=item.fact_kind,
                status=item.status,
                history_incomplete=item.history_incomplete,
                visible_scope=item.visible_scope,
                retention_limitations=item.retention_limitations,
                subscription_id=item.subscription_id,
                subscription_valid_from=item.subscription_valid_from,
                subscription_valid_until=item.subscription_valid_until,
                gap_kind=item.gap_kind,
                details=item.details,
                observed_at=item.observed_at,
                evidence_id=evidence.evidence_id,
                run_id=item.run_id,
                evidence_run_id=evidence.run_id,
            )
            session.add(observation)
            session.flush()
            current = session.get(
                TeamsCoverageCurrent,
                (self.source_id, digest),
            )
            if current is None:
                session.add(
                    TeamsCoverageCurrent(
                        source_id=self.source_id,
                        scope_key_sha256=digest,
                        scope_kind=item.scope_kind,
                        scope_key=[value for value in scope_key if value is not None],
                        observation_id=observation.observation_id,
                        history_incomplete=item.history_incomplete,
                        latest_fact_kind=item.fact_kind,
                        latest_status=item.status,
                        latest_observed_at=item.observed_at,
                        latest_evidence_id=evidence.evidence_id,
                        latest_run_id=item.run_id,
                        latest_evidence_run_id=evidence.run_id,
                        visible_scope=item.visible_scope,
                        retention_limitations=item.retention_limitations,
                        subscription_id=item.subscription_id,
                        subscription_valid_from=item.subscription_valid_from,
                        subscription_valid_until=item.subscription_valid_until,
                        gap_kind=item.gap_kind,
                        details=item.details,
                    )
                )
                return "created"

            sticky_incomplete = current.history_incomplete or item.history_incomplete
            ordering = compare_observed(
                item.observed_at,
                current.latest_observed_at,
            )
            if ordering < 0:
                if sticky_incomplete != current.history_incomplete:
                    current.history_incomplete = sticky_incomplete
                return "stale"
            if ordering == 0:
                if sticky_incomplete != current.history_incomplete:
                    current.history_incomplete = sticky_incomplete
                return "tie"
            current.observation_id = observation.observation_id
            current.history_incomplete = sticky_incomplete
            current.latest_fact_kind = item.fact_kind
            current.latest_status = item.status
            current.latest_observed_at = item.observed_at
            current.latest_evidence_id = evidence.evidence_id
            current.latest_run_id = item.run_id
            current.latest_evidence_run_id = evidence.run_id
            current.visible_scope = item.visible_scope
            current.retention_limitations = item.retention_limitations
            current.subscription_id = item.subscription_id
            current.subscription_valid_from = item.subscription_valid_from
            current.subscription_valid_until = item.subscription_valid_until
            current.gap_kind = item.gap_kind
            current.details = item.details
            return "advanced"


__all__ = ["TeamsCoverageStore"]
