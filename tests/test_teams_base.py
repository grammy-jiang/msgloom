"""Qualify shared Teams application settings and fail-closed initialization."""

import pytest
from scrapy.crawler import Crawler
from scrapy.settings import Settings

from message_ingest.spiders.microsoft._graph import MicrosoftGraphSpider
from message_ingest.spiders.microsoft.teams._base import MicrosoftTeamsBaseSpider
from message_ingest.spiders.microsoft.teams.channel import (
    MicrosoftTeamsChannelDiscoverSpider,
)
from message_ingest.spiders.microsoft.teams.chat import MicrosoftTeamsChatDiscoverSpider
from microsoft_graph.spiders.teams.chat_composition import (
    MicrosoftTeamsChatCompositionSpider,
)


class ChatProbe(MicrosoftTeamsChatCompositionSpider, MicrosoftTeamsBaseSpider):
    name = "teams-base-chat-probe"

    async def start(self):
        yield self.graph_request("/me/chats", callback=self.parse, errback=self.errback)


def _settings():
    settings = Settings()
    settings.setmodule("message_ingest.settings")
    return settings


@pytest.mark.parametrize(
    "spider_type,scopes",
    [
        (MicrosoftTeamsChatDiscoverSpider, {"Chat.Read"}),
        (
            MicrosoftTeamsChannelDiscoverSpider,
            {
                "Team.ReadBasic.All",
                "Channel.ReadBasic.All",
                "ChannelMessage.Read.All",
                "TeamMember.Read.All",
                "ChannelMember.Read.All",
            },
        ),
    ],
)
def test_teams_base_selects_native_integrity_and_storage(
    spider_type: type[MicrosoftTeamsBaseSpider], scopes: set[str]
):
    crawler = Crawler(spider_type, _settings())
    spider = spider_type.from_crawler(crawler)
    if not isinstance(spider, MicrosoftGraphSpider) or spider.run_failed:
        pytest.fail("Teams must retain the application Graph integrity owner")
    if spider.source_id != "microsoft-teams-default":
        pytest.fail("Both Teams lanes must share the delegated logical source")
    if set(crawler.settings.getlist("MS_GRAPH_SCOPES")) != scopes:
        pytest.fail("Teams application lost its selected permission profile")
    expected = {
        "message_ingest.pipelines.evidence.RawEvidencePipeline": 200,
        "message_ingest.acquisition.evidence_link.EvidenceLinkPipeline": 250,
        "message_ingest.pipelines.microsoft.teams.TeamsPipeline": 300,
    }
    if dict(crawler.settings.getdict("ITEM_PIPELINES")) != expected:
        pytest.fail("Teams must use the shared evidence-before-semantics chain")
    request = spider.graph_request(
        "/me/chats", callback=spider.parse, errback=spider.errback
    )
    if not request.meta.get("dont_cache") or request.errback != spider.errback:
        pytest.fail(
            "Teams discovery must use fresh reads and inherited request failure handling"
        )
    for key in ("MSGLOOM_DELTA_CHECKPOINT_ENABLED", "MSGLOOM_CRAWL_STATUS_ENABLED"):
        if crawler.settings.getbool(key):
            pytest.fail("Initial Teams discovery must not enable unrelated promotion")


@pytest.mark.parametrize(
    "key,value,match",
    [
        ("JOBDIR", "/unused-job", "JOBDIR"),
        ("CONCURRENT_ITEMS", 2, "CONCURRENT_ITEMS"),
        ("MSGLOOM_CATALOG_ENABLED", False, "catalog"),
        ("MSGLOOM_RAW_EVIDENCE_ENABLED", False, "evidence"),
    ],
)
def test_teams_base_rejects_unsafe_initialization(key, value, match):
    settings = _settings()
    settings.set(key, value, priority="cmdline")
    crawler = Crawler(ChatProbe, settings)
    with pytest.raises(ValueError, match=match):
        ChatProbe.from_crawler(crawler)


def test_teams_source_setting_keeps_explicit_command_priority():
    settings = _settings()
    settings.set("MSGLOOM_TEAMS_SOURCE_ID", "configured-teams", priority="project")
    settings.set("MSGLOOM_SOURCE_ID", "explicit-teams", priority="cmdline")
    crawler = Crawler(ChatProbe, settings)
    if ChatProbe.from_crawler(crawler).source_id != "explicit-teams":
        pytest.fail("Shared Teams defaults must preserve explicit source selection")
