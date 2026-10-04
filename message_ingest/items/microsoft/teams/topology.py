"""Application Teams topology items with raw-evidence provenance."""

from dataclasses import dataclass
from typing import Literal

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


@dataclass(slots=True)
class TeamsChannelItem(GraphTeamsChannelItem):
    """One channel discovery or detail representation."""

    source_id: str
    observed_at: str
    evidence_id: str | None
    run_id: str


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
