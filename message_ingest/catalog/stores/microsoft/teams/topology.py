"""Persistence for immutable Teams topology observations and current state."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from message_ingest.catalog.models.microsoft.teams.topology import (
    TeamsTopologyCurrent,
    TeamsTopologyObservation,
)
from message_ingest.catalog.store import Catalog
from message_ingest.items.microsoft.teams.topology import (
    TeamsChannelItem,
    TeamsChannelMembershipItem,
    TeamsChatItem,
    TeamsChatMemberItem,
    TeamsChatPinItem,
    TeamsPinStateItem,
    TeamsSharedWithTeamItem,
    TeamsTeamItem,
    TeamsTeamMembershipItem,
    TopologyItem,
)

from ._common import (
    Outcome,
    compare_observed,
    require_evidence,
    require_source,
    scope_digest,
)


class TeamsTopologyStore:
    """Store additive provider topology without absence-based relation changes."""

    def __init__(self, catalog: Catalog, *, source_id: str) -> None:
        self.catalog = catalog
        self.source_id = source_id

    def persist(self, item: TopologyItem) -> Outcome:
        """Append one observation and update current only when strictly newer."""
        require_source(item.source_id, self.source_id)
        kind, scope, raw, context = self._projection(item)
        scope_key, digest = scope_digest(scope)
        with self.catalog.writer_session() as session:
            evidence = require_evidence(
                session,
                source_id=self.source_id,
                evidence_id=item.evidence_id,
                observed_at=item.observed_at,
            )
            existing = session.scalar(
                select(TeamsTopologyObservation).filter_by(
                    source_id=self.source_id,
                    scope_key_sha256=digest,
                    evidence_id=item.evidence_id,
                )
            )
            if existing is not None:
                if existing.raw != raw or existing.context != context:
                    raise ValueError("Teams topology replay changed immutable facts")
                return "replay"

            observation = TeamsTopologyObservation(
                source_id=self.source_id,
                resource_kind=kind,
                scope_key=scope_key,
                scope_key_sha256=digest,
                observed_at=item.observed_at,
                evidence_id=item.evidence_id,
                run_id=item.run_id,
                evidence_run_id=evidence.run_id,
                raw=raw,
                context=context,
            )
            session.add(observation)
            session.flush()

            current = session.get(
                TeamsTopologyCurrent,
                (self.source_id, digest),
            )
            if current is None:
                session.add(
                    TeamsTopologyCurrent(
                        source_id=self.source_id,
                        scope_key_sha256=digest,
                        resource_kind=kind,
                        scope_key=scope_key,
                        observation_id=observation.observation_id,
                        latest_observed_at=item.observed_at,
                        latest_evidence_id=item.evidence_id,
                        latest_run_id=item.run_id,
                        latest_evidence_run_id=evidence.run_id,
                        raw=raw,
                        context=context,
                    )
                )
                return "created"

            ordering = compare_observed(
                item.observed_at,
                current.latest_observed_at,
            )
            if ordering < 0:
                return "stale"
            if ordering == 0:
                return "tie"
            current.resource_kind = kind
            current.scope_key = scope_key
            current.observation_id = observation.observation_id
            current.latest_observed_at = item.observed_at
            current.latest_evidence_id = evidence.evidence_id
            current.latest_run_id = item.run_id
            current.latest_evidence_run_id = evidence.run_id
            current.raw = raw
            current.context = context
            return "advanced"

    @staticmethod
    def _projection(
        item: TopologyItem,
    ) -> tuple[str, tuple[str | None, ...], dict[str, Any] | None, dict[str, Any]]:
        """Project only already-parsed item facts into durable context."""
        if isinstance(item, TeamsChatItem):
            return (
                "chat",
                ("chat", item.chat_id),
                item.raw,
                {
                    "chat_id": item.chat_id,
                    "chat_type": item.chat_type,
                    "tenant_id": item.tenant_id,
                },
            )
        if isinstance(item, TeamsChatMemberItem):
            return (
                "chat-member",
                (
                    "chat-member",
                    item.chat_id,
                    item.member_id,
                ),
                item.raw,
                {
                    "chat_id": item.chat_id,
                    "member_id": item.member_id,
                    "tenant_id": item.tenant_id,
                    "user_id": item.user_id,
                },
            )
        if isinstance(item, TeamsChatPinItem):
            return (
                "pin",
                ("pin", item.chat_id, item.message_id),
                item.raw,
                {
                    "chat_id": item.chat_id,
                    "message_id": item.message_id,
                    "state": "pinned",
                    "reason": "provider pin collection",
                },
            )
        if isinstance(item, TeamsPinStateItem):
            return (
                "pin",
                ("pin", item.chat_id, item.message_id),
                None,
                {
                    "chat_id": item.chat_id,
                    "message_id": item.message_id,
                    "state": item.state,
                    "reason": item.reason,
                },
            )
        if isinstance(item, TeamsTeamItem):
            return (
                "team",
                ("team", item.team_id),
                item.raw,
                {
                    "team_id": item.team_id,
                    "representation": item.representation,
                    "detail_complete": item.detail_complete,
                    "detail_limitation": item.detail_limitation,
                    "tenant_id": item.tenant_id,
                },
            )
        if isinstance(item, TeamsChannelItem):
            return (
                "channel",
                (
                    "channel",
                    item.host_team_id,
                    item.channel_id,
                    item.receiving_team_id,
                ),
                item.raw,
                {
                    "channel_id": item.channel_id,
                    "host_team_id": item.host_team_id,
                    "host_tenant_id": item.host_tenant_id,
                    "receiving_team_id": item.receiving_team_id,
                    "receiving_tenant_id": item.receiving_tenant_id,
                    "representation": item.representation,
                    "detail_complete": item.detail_complete,
                    "detail_limitation": item.detail_limitation,
                    "original_resource_link": item.original_resource_link,
                },
            )
        if isinstance(item, TeamsSharedWithTeamItem):
            return (
                "shared-with-team",
                (
                    "shared-with-team",
                    item.host_team_id,
                    item.channel_id,
                    item.receiving_team_id,
                ),
                item.raw,
                {
                    "host_team_id": item.host_team_id,
                    "host_tenant_id": item.host_tenant_id,
                    "channel_id": item.channel_id,
                    "receiving_team_id": item.receiving_team_id,
                    "receiving_tenant_id": item.receiving_tenant_id,
                },
            )
        if isinstance(item, TeamsTeamMembershipItem):
            return (
                "team-membership",
                (
                    "team-membership",
                    item.team_id,
                    item.membership_id,
                ),
                item.raw,
                {
                    "team_id": item.team_id,
                    "membership_id": item.membership_id,
                    "user_id": item.user_id,
                    "tenant_id": item.tenant_id,
                    "original_source_membership_url": (
                        item.original_source_membership_url
                    ),
                },
            )
        if isinstance(item, TeamsChannelMembershipItem):
            return (
                "channel-membership",
                (
                    "channel-membership",
                    item.host_team_id,
                    item.channel_id,
                    item.membership_source,
                    item.membership_id,
                    item.original_source_membership_url,
                ),
                item.raw,
                {
                    "host_team_id": item.host_team_id,
                    "channel_id": item.channel_id,
                    "membership_id": item.membership_id,
                    "membership_source": item.membership_source,
                    "user_id": item.user_id,
                    "tenant_id": item.tenant_id,
                    "original_source_membership_url": (
                        item.original_source_membership_url
                    ),
                },
            )
        raise TypeError(f"Unsupported Teams topology item: {type(item).__name__}")


__all__ = ["TeamsTopologyStore"]
