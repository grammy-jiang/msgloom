"""Application Microsoft Teams acquisition item contracts."""

from .content import (
    TeamsHostedContentBytesItem,
    TeamsHostedContentFailureItem,
    TeamsHostedContentItem,
    TeamsReferenceResolutionItem,
)
from .coverage import TeamsCoverageItem
from .message import TeamsMessageDeletionItem, TeamsMessageItem, TeamsMessageTrigger
from .topology import (
    TeamsChannelItem,
    TeamsChannelMembershipItem,
    TeamsChatItem,
    TeamsChatMemberItem,
    TeamsChatPinItem,
    TeamsPinStateItem,
    TeamsSharedWithTeamItem,
    TeamsTeamItem,
    TeamsTeamMembershipItem,
)

__all__ = [
    "TeamsChannelItem",
    "TeamsChannelMembershipItem",
    "TeamsChatItem",
    "TeamsChatMemberItem",
    "TeamsChatPinItem",
    "TeamsCoverageItem",
    "TeamsHostedContentBytesItem",
    "TeamsHostedContentFailureItem",
    "TeamsHostedContentItem",
    "TeamsMessageDeletionItem",
    "TeamsMessageItem",
    "TeamsMessageTrigger",
    "TeamsPinStateItem",
    "TeamsReferenceResolutionItem",
    "TeamsSharedWithTeamItem",
    "TeamsTeamItem",
    "TeamsTeamMembershipItem",
]
