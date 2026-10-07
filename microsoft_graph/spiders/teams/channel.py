"""Reusable Microsoft Teams provider channel path surface."""

from typing import ClassVar

from microsoft_graph.spiders.graph import MicrosoftGraphSpider

from . import channel_paths


class MicrosoftTeamsChannelSpider(MicrosoftGraphSpider):
    """Supply pure Teams channel topology paths and representation requirements."""

    representation_prefer: ClassVar[str] = "include-unknown-enum-members"
    hosted_consistency_level: ClassVar[str] = "eventual"
    hosted_bytes_accept: ClassVar[str] = "application/octet-stream"

    associated_teams_path = staticmethod(channel_paths.associated_teams_path)
    joined_teams_path = staticmethod(channel_paths.joined_teams_path)
    team_path = staticmethod(channel_paths.team_path)
    all_channels_path = staticmethod(channel_paths.all_channels_path)
    incoming_channels_path = staticmethod(channel_paths.incoming_channels_path)
    channel_path = staticmethod(channel_paths.channel_path)
    shared_with_teams_path = staticmethod(channel_paths.shared_with_teams_path)
    team_members_path = staticmethod(channel_paths.team_members_path)
    channel_members_path = staticmethod(channel_paths.channel_members_path)
    all_channel_members_path = staticmethod(channel_paths.all_channel_members_path)
    root_messages_path = staticmethod(channel_paths.root_messages_path)
    root_message_path = staticmethod(channel_paths.root_message_path)
    replies_path = staticmethod(channel_paths.replies_path)
    reply_message_path = staticmethod(channel_paths.reply_message_path)
    hosted_contents_path = staticmethod(channel_paths.hosted_contents_path)
    hosted_content_path = staticmethod(channel_paths.hosted_content_path)
    hosted_content_bytes_path = staticmethod(channel_paths.hosted_content_bytes_path)
    resolve_trusted_channel_resource_link = staticmethod(
        channel_paths.resolve_trusted_channel_resource_link
    )


__all__ = ["MicrosoftTeamsChannelSpider"]
