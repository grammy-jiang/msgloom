"""Application Teams topology items with raw-evidence provenance."""

from dataclasses import dataclass
from typing import Any, Literal, Self

from microsoft_graph.items.teams.channel import (
    TeamsChannelItem as GraphTeamsChannelItem,
)
from microsoft_graph.items.teams.channel import (
    TeamsSharedWithTeamItem as GraphTeamsSharedWithTeamItem,
)
from microsoft_graph.items.teams.channel import TeamsTeamItem as GraphTeamsTeamItem
from microsoft_graph.items.teams.chat import TeamsChatItem as GraphTeamsChatItem
from microsoft_graph.items.teams.chat import (
    TeamsChatMemberItem as GraphTeamsChatMemberItem,
)
from microsoft_graph.items.teams.chat import TeamsChatPinItem as GraphTeamsChatPinItem
from microsoft_graph.items.teams.membership import (
    TeamsChannelMembershipItem as GraphTeamsChannelMembershipItem,
)
from microsoft_graph.items.teams.membership import (
    TeamsTeamMembershipItem as GraphTeamsTeamMembershipItem,
)


@dataclass(slots=True)
class TeamsChatItem(GraphTeamsChatItem):
    """One chat observation linked to canonicalizable raw evidence."""

    source_id: str
    observed_at: str
    evidence_id: str | None
    run_id: str


@dataclass(slots=True)
class TeamsChatMemberItem(GraphTeamsChatMemberItem):
    """One explicit chat membership observation."""

    source_id: str
    observed_at: str
    evidence_id: str | None
    run_id: str


@dataclass(slots=True)
class TeamsChatPinItem(GraphTeamsChatPinItem):
    """One positive pin relation observation."""

    source_id: str
    observed_at: str
    evidence_id: str | None
    run_id: str


@dataclass(slots=True)
class TeamsTeamItem(GraphTeamsTeamItem):
    """One team discovery or detail representation."""

    source_id: str
    observed_at: str
    evidence_id: str | None
    run_id: str

    detail_complete: bool
    detail_limitation: str | None

    def __post_init__(self) -> None:
        """Validate application completeness, then project provider fields."""
        if self.detail_complete:
            if self.representation != "detail" or self.detail_limitation is not None:
                raise ValueError(
                    "Complete team detail must come from a detail response"
                )
        elif not isinstance(self.detail_limitation, str) or not self.detail_limitation:
            raise ValueError("Partial team representations require a detail limitation")
        GraphTeamsTeamItem.__post_init__(self)

    @classmethod
    def from_associated(
        cls,
        resource: dict[str, Any],
        *,
        detail_limitation: str = (
            "associatedTeams is discovery-only; full team detail is not observed"
        ),
        **kwargs: Any,
    ) -> Self:
        """Retain associated-team discovery until separate detail is observed."""
        return super(TeamsTeamItem, cls).from_associated(
            resource,
            detail_complete=False,
            detail_limitation=detail_limitation,
            **kwargs,
        )

    @classmethod
    def from_joined(
        cls,
        resource: dict[str, Any],
        *,
        detail_limitation: str = (
            "joinedTeams is discovery-only; full team detail is not observed"
        ),
        **kwargs: Any,
    ) -> Self:
        """Retain joined-team discovery until separate detail is observed."""
        return super(TeamsTeamItem, cls).from_joined(
            resource,
            detail_complete=False,
            detail_limitation=detail_limitation,
            **kwargs,
        )

    @classmethod
    def from_detail(cls, resource: dict[str, Any], **kwargs: Any) -> Self:
        """Mark a separate team detail observation complete."""
        return super(TeamsTeamItem, cls).from_detail(
            resource,
            detail_complete=True,
            detail_limitation=None,
            **kwargs,
        )


@dataclass(slots=True)
class TeamsChannelItem(GraphTeamsChannelItem):
    """One channel discovery or detail representation."""

    source_id: str
    observed_at: str
    evidence_id: str | None
    run_id: str

    detail_complete: bool
    detail_limitation: str | None

    def __post_init__(self) -> None:
        """Validate application completeness, then project provider fields."""
        if self.detail_complete:
            if self.representation != "detail" or self.detail_limitation is not None:
                raise ValueError(
                    "Complete channel detail must come from detail response"
                )
        elif not isinstance(self.detail_limitation, str) or not self.detail_limitation:
            raise ValueError("Channel discovery requires a detail limitation")
        GraphTeamsChannelItem.__post_init__(self)

    @classmethod
    def from_all_channels(
        cls,
        resource: dict[str, Any],
        *,
        host_team_id: str,
        detail_limitation: str = (
            "allChannels is a discovery projection; full channel detail is not observed"
        ),
        **kwargs: Any,
    ) -> Self:
        """Keep selected allChannels discovery distinct from hydrated detail."""
        return super(TeamsChannelItem, cls).from_all_channels(
            resource,
            host_team_id=host_team_id,
            detail_complete=False,
            detail_limitation=detail_limitation,
            **kwargs,
        )

    @classmethod
    def from_incoming(
        cls,
        resource: dict[str, Any],
        *,
        host_team_id: str,
        receiving_team_id: str,
        detail_limitation: str = (
            "incomingChannels is a discovery projection; full channel detail is not observed"
        ),
        **kwargs: Any,
    ) -> Self:
        """Keep incoming channel discovery distinct from hydrated detail."""
        return super(TeamsChannelItem, cls).from_incoming(
            resource,
            host_team_id=host_team_id,
            receiving_team_id=receiving_team_id,
            detail_complete=False,
            detail_limitation=detail_limitation,
            **kwargs,
        )

    @classmethod
    def from_detail(
        cls,
        resource: dict[str, Any],
        *,
        host_team_id: str,
        **kwargs: Any,
    ) -> Self:
        """Mark a separate channel detail observation complete."""
        return super(TeamsChannelItem, cls).from_detail(
            resource,
            host_team_id=host_team_id,
            detail_complete=True,
            detail_limitation=None,
            **kwargs,
        )


@dataclass(slots=True)
class TeamsSharedWithTeamItem(GraphTeamsSharedWithTeamItem):
    """One host-channel to receiving-team sharing observation."""

    source_id: str
    observed_at: str
    evidence_id: str | None
    run_id: str


@dataclass(slots=True)
class TeamsTeamMembershipItem(GraphTeamsTeamMembershipItem):
    """One explicit team membership observation."""

    source_id: str
    observed_at: str
    evidence_id: str | None
    run_id: str


@dataclass(slots=True)
class TeamsChannelMembershipItem(GraphTeamsChannelMembershipItem):
    """One direct or indirect channel membership path observation."""

    source_id: str
    observed_at: str
    evidence_id: str | None
    run_id: str


PinState = Literal["pinned", "unpinned"]


@dataclass(slots=True)
class TeamsPinStateItem:
    """Explicit pin-state transition, including evidence-backed unpin."""

    source_id: str
    chat_id: str
    message_id: str
    state: PinState
    observed_at: str
    evidence_id: str | None
    run_id: str
    reason: str | None = None

    def __post_init__(self) -> None:
        """Reject invented relation states while preserving opaque IDs."""
        if self.state not in {"pinned", "unpinned"}:
            raise ValueError("Unknown Teams pin state")
        for name in ("chat_id", "message_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"Teams pin state requires non-empty {name}")


TopologyItem = (
    TeamsChatItem
    | TeamsChatMemberItem
    | TeamsChatPinItem
    | TeamsTeamItem
    | TeamsChannelItem
    | TeamsSharedWithTeamItem
    | TeamsTeamMembershipItem
    | TeamsChannelMembershipItem
    | TeamsPinStateItem
)


__all__ = [
    "PinState",
    "TeamsChannelItem",
    "TeamsChannelMembershipItem",
    "TeamsChatItem",
    "TeamsChatMemberItem",
    "TeamsChatPinItem",
    "TeamsPinStateItem",
    "TeamsSharedWithTeamItem",
    "TeamsTeamItem",
    "TeamsTeamMembershipItem",
    "TopologyItem",
]
