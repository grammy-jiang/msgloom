"""Pure Microsoft Teams channel paths and frozen v1.0 query helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import quote, urlencode, urlsplit

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

_TRUSTED_CHANNEL_LINK = re.compile(
    r"^/v1[.]0/tenants/([^/]+)/teams/([^/]+)/channels/([^/]+)$"
)


@dataclass(frozen=True, slots=True)
class TrustedChannelResourceLink:
    """Retain one accepted cross-tenant link and its unchanged path segments."""

    raw: str
    request_path: str
    tenant_path_segment: str
    team_path_segment: str
    channel_path_segment: str


def _segment(value: str, *, name: str) -> str:
    """Validate one opaque raw Graph ID and encode it exactly once."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
    return quote(value, safe="")


def _bounded_page_size(value: int, *, name: str, maximum: int) -> int:
    """Require an integer page size inside the frozen endpoint bounds."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 1 or value > maximum:
        raise ValueError(f"{name} must be >= 1 and <= {maximum}")
    return value


def _top(path: str, page_size: int, *, name: str, maximum: int) -> str:
    """Append exactly one validated page-size option to a new request path."""
    size = _bounded_page_size(page_size, name=name, maximum=maximum)
    return f"{path}?{urlencode({'$top': size})}"


def _channel_projection(path: str) -> str:
    """Append the frozen non-exhaustive channel projection."""
    return f"{path}?{urlencode({'$select': ','.join(CHANNEL_SELECT_FIELDS)})}"


def associated_teams_path() -> str:
    """List signed-in-user team associations, including shared-channel hosts."""
    return "/me/teamwork/associatedTeams"


def joined_teams_path() -> str:
    """List direct team membership separately from associated-team discovery."""
    return "/me/joinedTeams"


def team_path(team_id: str) -> str:
    """Address full detail for one raw team ID."""
    return f"/teams/{_segment(team_id, name='team ID')}"


def all_channels_path(team_id: str) -> str:
    """Discover all channels using the frozen channel projection."""
    return _channel_projection(f"{team_path(team_id)}/allChannels")


def incoming_channels_path(team_id: str) -> str:
    """Discover incoming shared channels for one receiving team."""
    return _channel_projection(f"{team_path(team_id)}/incomingChannels")


def channel_path(team_id: str, channel_id: str) -> str:
    """Address full channel detail using the same frozen projection."""
    base = f"{team_path(team_id)}/channels/{_segment(channel_id, name='channel ID')}"
    return _channel_projection(base)


def shared_with_teams_path(team_id: str, channel_id: str) -> str:
    """List teams that receive one hosted shared channel."""
    return (
        f"{team_path(team_id)}/channels/"
        f"{_segment(channel_id, name='channel ID')}/sharedWithTeams"
    )


def team_members_path(team_id: str, *, page_size: int = TEAM_MEMBER_PAGE_SIZE) -> str:
    """List team members with the frozen bounded page size."""
    return _top(
        f"{team_path(team_id)}/members",
        page_size,
        name="team member page size",
        maximum=999,
    )


def channel_members_path(
    team_id: str,
    channel_id: str,
    *,
    page_size: int = CHANNEL_MEMBER_PAGE_SIZE,
) -> str:
    """List direct channel members with the frozen bounded page size."""
    path = (
        f"{team_path(team_id)}/channels/"
        f"{_segment(channel_id, name='channel ID')}/members"
    )
    return _top(path, page_size, name="channel member page size", maximum=999)


def all_channel_members_path(team_id: str, channel_id: str) -> str:
    """List direct and indirect channel memberships without a page-size query."""
    return (
        f"{team_path(team_id)}/channels/"
        f"{_segment(channel_id, name='channel ID')}/allMembers"
    )


def root_messages_path(
    team_id: str,
    channel_id: str,
    *,
    page_size: int = CHANNEL_MESSAGE_PAGE_SIZE,
) -> str:
    """List channel root messages with the frozen bounded page size."""
    path = (
        f"{team_path(team_id)}/channels/"
        f"{_segment(channel_id, name='channel ID')}/messages"
    )
    return _top(path, page_size, name="channel message page size", maximum=50)


def root_message_path(team_id: str, channel_id: str, root_id: str) -> str:
    """Address one targeted root message."""
    return (
        f"{team_path(team_id)}/channels/"
        f"{_segment(channel_id, name='channel ID')}/messages/"
        f"{_segment(root_id, name='root message ID')}"
    )


def replies_path(
    team_id: str,
    channel_id: str,
    root_id: str,
    *,
    page_size: int = CHANNEL_MESSAGE_PAGE_SIZE,
) -> str:
    """List replies for one root without relying on reply expansion."""
    path = f"{root_message_path(team_id, channel_id, root_id)}/replies"
    return _top(path, page_size, name="channel reply page size", maximum=50)


def reply_message_path(
    team_id: str,
    channel_id: str,
    root_id: str,
    reply_id: str,
) -> str:
    """Address one targeted reply under its explicit root context."""
    return (
        f"{root_message_path(team_id, channel_id, root_id)}/replies/"
        f"{_segment(reply_id, name='reply message ID')}"
    )


def _message_path(
    team_id: str,
    channel_id: str,
    root_id: str,
    *,
    reply_id: str | None,
) -> str:
    """Select the exact root or reply context for hosted-content paths."""
    if reply_id is None:
        return root_message_path(team_id, channel_id, root_id)
    return reply_message_path(team_id, channel_id, root_id, reply_id)


def hosted_contents_path(
    team_id: str,
    channel_id: str,
    root_id: str,
    *,
    reply_id: str | None = None,
) -> str:
    """List hosted-content metadata for one root or reply."""
    return (
        f"{_message_path(team_id, channel_id, root_id, reply_id=reply_id)}"
        "/hostedContents"
    )


def hosted_content_path(
    team_id: str,
    channel_id: str,
    root_id: str,
    hosted_content_id: str,
    *,
    reply_id: str | None = None,
) -> str:
    """Address one hosted-content item without message-version binding."""
    hosted_id = _segment(hosted_content_id, name="hosted-content ID")
    return (
        f"{hosted_contents_path(team_id, channel_id, root_id, reply_id=reply_id)}"
        f"/{hosted_id}"
    )


def hosted_content_bytes_path(
    team_id: str,
    channel_id: str,
    root_id: str,
    hosted_content_id: str,
    *,
    reply_id: str | None = None,
) -> str:
    """Address bytes for one hosted item through its Graph resource path."""
    return (
        f"{hosted_content_path(team_id, channel_id, root_id, hosted_content_id, reply_id=reply_id)}"
        "/$value"
    )


def resolve_trusted_channel_resource_link(
    resource_link: str,
) -> TrustedChannelResourceLink | None:
    """
    Resolve only Microsoft's frozen tenant-prefixed shared-channel link shape.

    The helper is intentionally not a continuation or UI-URL normalizer. It
    removes only the leading tenant portion from the accepted Graph origin and
    preserves the remaining encoded path segments and query bytes.
    """
    if not isinstance(resource_link, str) or not resource_link:
        return None
    try:
        parsed = urlsplit(resource_link)
    except ValueError:
        # Malformed authorities remain unresolved, like other untrusted links.
        return None
    if (
        parsed.scheme != "https"
        or parsed.netloc != "graph.microsoft.com"
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
    ):
        return None
    match = _TRUSTED_CHANNEL_LINK.fullmatch(parsed.path)
    if match is None:
        return None
    tenant, team, channel = match.groups()
    request_path = f"/teams/{team}/channels/{channel}"
    if parsed.query:
        request_path = f"{request_path}?{parsed.query}"
    return TrustedChannelResourceLink(
        raw=resource_link,
        request_path=request_path,
        tenant_path_segment=tenant,
        team_path_segment=team,
        channel_path_segment=channel,
    )


__all__ = [
    "CHANNEL_MEMBER_PAGE_SIZE",
    "CHANNEL_MESSAGE_PAGE_SIZE",
    "CHANNEL_SELECT_FIELDS",
    "TEAM_MEMBER_PAGE_SIZE",
    "TrustedChannelResourceLink",
    "all_channel_members_path",
    "all_channels_path",
    "associated_teams_path",
    "channel_members_path",
    "channel_path",
    "hosted_content_bytes_path",
    "hosted_content_path",
    "hosted_contents_path",
    "incoming_channels_path",
    "joined_teams_path",
    "replies_path",
    "reply_message_path",
    "resolve_trusted_channel_resource_link",
    "root_message_path",
    "root_messages_path",
    "shared_with_teams_path",
    "team_members_path",
    "team_path",
]
