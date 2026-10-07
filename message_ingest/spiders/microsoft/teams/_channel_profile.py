"""Selected msgloom complete-T2 channel acquisition profile."""

CHANNEL_GRAPH_PERMISSIONS = (
    "Team.ReadBasic.All",
    "Channel.ReadBasic.All",
    "ChannelMessage.Read.All",
    "TeamMember.Read.All",
    "ChannelMember.Read.All",
)

CHANNEL_SELECT_FIELDS = (
    "id",
    "createdDateTime",
    "displayName",
    "description",
    "isArchived",
    "isFavoriteByDefault",
    "layoutType",
    "membershipType",
    "migrationMode",
    "originalCreatedDateTime",
    "tenantId",
    "webUrl",
)
CHANNEL_MESSAGE_PAGE_SIZE = 50
TEAM_MEMBER_PAGE_SIZE = 999
CHANNEL_MEMBER_PAGE_SIZE = 999
