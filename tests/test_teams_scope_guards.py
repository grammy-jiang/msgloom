"""Keep effective Teams application permissions inside each selected profile."""

import pytest
from scrapy.crawler import Crawler
from scrapy.settings import Settings

from message_ingest.spiders.microsoft.teams.channel import (
    MicrosoftTeamsChannelDiscoverSpider,
)
from message_ingest.spiders.microsoft.teams.chat import MicrosoftTeamsChatDiscoverSpider
from message_ingest.spiders.microsoft.teams.notifications import (
    MicrosoftTeamsNotificationReconcileSpider,
)
from microsoft_graph.spiders.teams.channel import MicrosoftTeamsChannelSpider

_PROFILES = [
    (MicrosoftTeamsChatDiscoverSpider, ("Chat.Read",)),
    (
        MicrosoftTeamsChannelDiscoverSpider,
        (
            "Team.ReadBasic.All",
            "Channel.ReadBasic.All",
            "ChannelMessage.Read.All",
            "TeamMember.Read.All",
            "ChannelMember.Read.All",
        ),
    ),
    (
        MicrosoftTeamsNotificationReconcileSpider,
        ("Chat.Read", "ChannelMessage.Read.All"),
    ),
]


def _settings(scopes):
    settings = Settings()
    settings.setmodule("message_ingest.settings")
    settings.set("MS_GRAPH_SCOPES", list(scopes), priority="cmdline")
    return settings


@pytest.mark.parametrize("spider_type,required", _PROFILES)
@pytest.mark.parametrize(
    "override", ["extra_read", "write", "application", "missing", "empty"]
)
def test_application_rejects_incompatible_scopes_before_construction(
    spider_type, required, override, monkeypatch
):
    """A command override must fail before constructor, auth, or network work."""
    scopes = list(required)
    additions = {
        "extra_read": "Files.Read.All",
        "write": "Chat.ReadWrite",
        "application": "Chat.Read.All",
    }
    if extra := additions.get(override):
        scopes.append(extra)
    elif override == "missing":
        scopes.pop()
    else:
        scopes.clear()
    crawler = Crawler(spider_type, _settings(scopes))

    def forbid_construction(self, *args, **kwargs):
        raise RuntimeError("Invalid scopes reached spider construction")

    monkeypatch.setattr(spider_type, "__init__", forbid_construction)
    with pytest.raises(ValueError, match="requires exactly"):
        spider_type.from_crawler(crawler)


@pytest.mark.parametrize("spider_type,required", _PROFILES)
def test_application_accepts_exact_profile_in_any_order(spider_type, required):
    """Scope ordering does not change the selected delegated permission set."""
    crawler = Crawler(spider_type, _settings(reversed(required)))
    spider = spider_type.from_crawler(crawler)
    if not isinstance(spider, spider_type):
        pytest.fail("Exact delegated profile did not initialize the Teams spider")
    if set(crawler.settings.getlist("MS_GRAPH_SCOPES")) != set(required):
        pytest.fail("Application initialization changed the selected scope set")


def test_standalone_provider_keeps_explicit_consumer_scope_override():
    """The application policy must not constrain the reusable Graph provider."""
    crawler = Crawler(MicrosoftTeamsChannelSpider, _settings(["Files.Read.All"]))
    MicrosoftTeamsChannelSpider.from_crawler(crawler, name="provider-scope-probe")
    if crawler.settings.getlist("MS_GRAPH_SCOPES") != ["Files.Read.All"]:
        pytest.fail("Teams application scope policy leaked into the provider")
