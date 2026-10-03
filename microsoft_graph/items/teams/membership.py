"""Provider-only Microsoft Teams team and channel membership projections."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Self

from microsoft_graph.protocol import graph_object

ChannelMembershipSource = Literal["direct", "all"]


def _context_id(value: str, *, name: str) -> None:
    """Validate one caller-supplied opaque parent identity."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")


def _membership(resource: dict[str, Any], context: str) -> dict[str, Any]:
    """Require one membership object and its provider membership ID."""
    raw = graph_object(resource, context=context)
    membership_id = raw.get("id")
    if not isinstance(membership_id, str) or not membership_id:
        raise ValueError(f"{context} requires a non-empty id")
    return raw


class _MembershipProjection:
    """Shared field projection for conversation-member provider values."""

    __slots__ = ()

    raw: dict[str, Any]
    user_id: str | None
    tenant_id: str | None
    display_name: str | None
    email: str | None
    roles: list[str] | None
    visible_history_start_date_time: str | None
    original_source_membership_url: str | None

    def _project_membership(self) -> None:
        """Copy references to provider values without normalization."""
        self.user_id = self.raw.get("userId")
        self.tenant_id = self.raw.get("tenantId")
        self.display_name = self.raw.get("displayName")
        self.email = self.raw.get("email")
        self.roles = self.raw.get("roles")
        self.visible_history_start_date_time = self.raw.get(
            "visibleHistoryStartDateTime"
        )
        self.original_source_membership_url = self.raw.get(
            "@microsoft.graph.originalSourceMembershipUrl"
        )


@dataclass(slots=True)
class TeamsTeamMembershipItem(_MembershipProjection):
    """One team membership under an explicit team identity."""

    team_id: str
    membership_id: str
    raw: dict[str, Any]
    user_id: str | None = field(init=False)
    tenant_id: str | None = field(init=False)
    display_name: str | None = field(init=False)
    email: str | None = field(init=False)
    roles: list[str] | None = field(init=False)
    visible_history_start_date_time: str | None = field(init=False)
    original_source_membership_url: str | None = field(init=False)

    def __post_init__(self) -> None:
        """Validate parent identity and preserve membership fields."""
        _context_id(self.team_id, name="team ID")
        self._project_membership()

    @classmethod
    def from_graph(
        cls,
        resource: dict[str, Any],
        *,
        team_id: str,
        **kwargs: Any,
    ) -> Self:
        """Parse a team member without interpreting its identity subtype."""
        _context_id(team_id, name="team ID")
        raw = _membership(resource, "Teams team member")
        return cls(
            team_id=team_id,
            membership_id=raw["id"],
            raw=raw,
            **kwargs,
        )


@dataclass(slots=True)
class TeamsChannelMembershipItem(_MembershipProjection):
    """
    One direct or allMembers channel membership path.

    Identity is not collapsed to user ID. Multiple rows for the same user,
    including different originalSourceMembershipUrl values, remain distinct
    provider observations.
    """

    host_team_id: str
    channel_id: str
    membership_id: str
    membership_source: ChannelMembershipSource
    raw: dict[str, Any]
    user_id: str | None = field(init=False)
    tenant_id: str | None = field(init=False)
    display_name: str | None = field(init=False)
    email: str | None = field(init=False)
    roles: list[str] | None = field(init=False)
    visible_history_start_date_time: str | None = field(init=False)
    original_source_membership_url: str | None = field(init=False)

    def __post_init__(self) -> None:
        """Validate channel scope while retaining direct/indirect provenance."""
        _context_id(self.host_team_id, name="host team ID")
        _context_id(self.channel_id, name="channel ID")
        if self.membership_source not in {"direct", "all"}:
            raise ValueError("Unknown Teams channel membership source")
        self._project_membership()

    @classmethod
    def from_direct(
        cls,
        resource: dict[str, Any],
        *,
        host_team_id: str,
        channel_id: str,
        **kwargs: Any,
    ) -> Self:
        """Parse a direct channel-members collection entry."""
        return cls._from_graph(
            resource,
            host_team_id=host_team_id,
            channel_id=channel_id,
            membership_source="direct",
            **kwargs,
        )

    @classmethod
    def from_all_members(
        cls,
        resource: dict[str, Any],
        *,
        host_team_id: str,
        channel_id: str,
        **kwargs: Any,
    ) -> Self:
        """Parse one direct or indirect allMembers membership path."""
        return cls._from_graph(
            resource,
            host_team_id=host_team_id,
            channel_id=channel_id,
            membership_source="all",
            **kwargs,
        )

    @classmethod
    def _from_graph(
        cls,
        resource: dict[str, Any],
        *,
        host_team_id: str,
        channel_id: str,
        membership_source: ChannelMembershipSource,
        **kwargs: Any,
    ) -> Self:
        """Validate shared channel-member identity and construct one observation."""
        _context_id(host_team_id, name="host team ID")
        _context_id(channel_id, name="channel ID")
        raw = _membership(resource, "Teams channel member")
        return cls(
            host_team_id=host_team_id,
            channel_id=channel_id,
            membership_id=raw["id"],
            membership_source=membership_source,
            raw=raw,
            **kwargs,
        )


__all__ = [
    "ChannelMembershipSource",
    "TeamsChannelMembershipItem",
    "TeamsTeamMembershipItem",
]
