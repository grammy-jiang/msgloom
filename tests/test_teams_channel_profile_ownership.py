"""Keep selected channel acquisition policy in the application."""

from types import SimpleNamespace

import pytest
from scrapy import Request
from scrapy.http import TextResponse
from scrapy.settings import Settings

from message_ingest.items.microsoft.teams.topology import (
    TeamsChannelItem,
    TeamsTeamItem,
)
from message_ingest.spiders.microsoft.teams.channel import (
    MicrosoftTeamsChannelDiscoverSpider,
)
from microsoft_graph.fingerprints import GraphRequestFingerprinter
from microsoft_graph.spiders.teams.channel import MicrosoftTeamsChannelSpider
from microsoft_graph.spiders.teams.channel_composition import (
    MicrosoftTeamsChannelCompositionSpider,
)

SCOPES = (
    "Team.ReadBasic.All",
    "Channel.ReadBasic.All",
    "ChannelMessage.Read.All",
    "TeamMember.Read.All",
    "ChannelMember.Read.All",
)


@pytest.mark.parametrize(
    "provider", [MicrosoftTeamsChannelSpider, MicrosoftTeamsChannelCompositionSpider]
)
def test_provider_channel_helpers_do_not_select_an_acquisition_bundle(provider):
    settings = Settings()
    provider.update_settings(settings)
    if provider.required_graph_permissions(settings):
        pytest.fail("Provider channel helper selected application permissions")
    if settings.getlist("MS_GRAPH_SCOPES"):
        pytest.fail("Provider channel helper configured application permissions")


def test_application_retains_exact_complete_t2_permissions():
    settings = Settings()
    MicrosoftTeamsChannelDiscoverSpider.update_settings(settings)
    if (
        MicrosoftTeamsChannelDiscoverSpider.required_graph_permissions(settings)
        != SCOPES
    ):
        pytest.fail("Application complete-T2 permissions changed")
    if settings.getlist("MS_GRAPH_SCOPES") != list(SCOPES):
        pytest.fail("Application scope defaults changed")


@pytest.mark.parametrize(
    "path",
    [
        MicrosoftTeamsChannelSpider.all_channels_path("team"),
        MicrosoftTeamsChannelSpider.incoming_channels_path("team"),
        MicrosoftTeamsChannelSpider.channel_path("team", "channel"),
        MicrosoftTeamsChannelSpider.team_members_path("team"),
        MicrosoftTeamsChannelSpider.channel_members_path("team", "channel"),
        MicrosoftTeamsChannelSpider.root_messages_path("team", "channel"),
        MicrosoftTeamsChannelSpider.replies_path("team", "channel", "root"),
    ],
)
def test_provider_queries_have_no_selected_profile_defaults(path: str):
    if "?" in path:
        pytest.fail("Provider helper selected a projection or page size")


def test_application_followups_preserve_selected_channel_queries():
    spider = MicrosoftTeamsChannelDiscoverSpider()
    provenance = {
        "source_id": "source",
        "observed_at": "now",
        "evidence_id": None,
        "run_id": "run",
    }
    team = TeamsTeamItem.from_associated({"id": "team"}, **provenance)
    channel = TeamsChannelItem.from_all_channels(
        {"id": "channel"}, host_team_id="team", **provenance
    )
    requests = [
        *spider._team_followups(team),
        *spider._channel_followups(channel, detail_path=None),
    ]
    paths = [request.url.removeprefix(spider.graph_root) for request in requests]
    selected = (
        "?%24select=id%2CcreatedDateTime%2CdisplayName%2Cdescription%2CisArchived"
        "%2CisFavoriteByDefault%2ClayoutType%2CmembershipType%2CmigrationMode"
        "%2CoriginalCreatedDateTime%2CtenantId%2CwebUrl"
    )
    expected = {
        "/teams/team",
        "/teams/team/allChannels" + selected,
        "/teams/team/incomingChannels" + selected,
        "/teams/team/members?%24top=999",
        "/teams/team/channels/channel" + selected,
        "/teams/team/channels/channel/members?%24top=999",
        "/teams/team/channels/channel/allMembers",
        "/teams/team/channels/channel/messages?%24top=50",
    }
    if set(paths) != expected:
        pytest.fail(f"Application channel profile changed: {paths}")


def test_application_root_callback_keeps_selected_reply_page_size(monkeypatch):
    spider = MicrosoftTeamsChannelDiscoverSpider()
    spider.source_id = "source"
    monkeypatch.setattr(
        spider,
        "crawler",
        SimpleNamespace(request_fingerprinter=GraphRequestFingerprinter()),
        raising=False,
    )
    request = Request(
        "https://graph.microsoft.com/v1.0/teams/team/channels/channel/messages"
    )
    response = TextResponse(
        request.url,
        request=request,
        body=b'{"value":[{"id":"root"}]}',
        encoding="utf-8",
    )
    outputs = list(
        spider.parse_root_messages(
            response,
            purpose="teams-channel-root-messages",
            host_team_id="team",
            channel_id="channel",
        )
    )
    replies = [
        output
        for output in outputs
        if isinstance(output, Request) and output.callback == spider.parse_replies
    ]
    if len(replies) != 1 or replies[0].url != (
        "https://graph.microsoft.com/v1.0/teams/team/channels/channel/messages/root/replies?%24top=50"
    ):
        pytest.fail("Application root callback lost the selected reply page size")
