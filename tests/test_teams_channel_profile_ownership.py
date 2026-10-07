"""Keep selected channel acquisition policy in the application."""

import pytest
from scrapy.settings import Settings

from message_ingest.spiders.microsoft.teams.channel import (
    MicrosoftTeamsChannelDiscoverSpider,
)
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
