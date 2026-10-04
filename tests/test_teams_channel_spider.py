"""Qualify the concrete Teams channel discovery spider contract."""

from __future__ import annotations

import asyncio

import pytest
from scrapy import Request
from scrapy.crawler import Crawler
from scrapy.settings import Settings

from message_ingest.spiders.microsoft._graph import MicrosoftGraphSpider
from message_ingest.spiders.microsoft.teams._base import MicrosoftTeamsBaseSpider
from message_ingest.spiders.microsoft.teams.channel import (
    MicrosoftTeamsChannelDiscoverSpider,
)
from microsoft_graph.spiders.teams.channel_composition import (
    MicrosoftTeamsChannelCompositionSpider,
)

SCOPES = {
    "Team.ReadBasic.All",
    "Channel.ReadBasic.All",
    "ChannelMessage.Read.All",
    "TeamMember.Read.All",
    "ChannelMember.Read.All",
}


def _settings() -> Settings:
    settings = Settings()
    settings.setmodule("message_ingest.settings")
    return settings


async def _start_requests(
    spider: MicrosoftTeamsChannelDiscoverSpider,
) -> list[Request]:
    return [request async for request in spider.start()]


def test_concrete_spider_keeps_frozen_mro_scope_and_start_surface() -> None:
    direct_bases = MicrosoftTeamsChannelDiscoverSpider.__bases__
    if direct_bases[:2] != (
        MicrosoftTeamsChannelCompositionSpider,
        MicrosoftTeamsBaseSpider,
    ):
        pytest.fail("Provider composition and shared Teams base must lead the MRO")

    crawler = Crawler(MicrosoftTeamsChannelDiscoverSpider, _settings())
    spider = MicrosoftTeamsChannelDiscoverSpider.from_crawler(crawler)
    if not isinstance(spider, MicrosoftGraphSpider):
        pytest.fail("Concrete Teams channel spider lost application Graph integrity")
    if spider.name != "microsoft_teams_channel_discover":
        pytest.fail("Frozen channel discovery spider name changed")
    if set(crawler.settings.getlist("MS_GRAPH_SCOPES")) != SCOPES:
        pytest.fail("Concrete channel spider must request exactly complete T2")
    if spider.source_id != "microsoft-teams-default":
        pytest.fail("Channel discovery must use the shared Teams source")

    requests = asyncio.run(_start_requests(spider))
    if len(requests) != 2:
        pytest.fail("Channel discovery must start from associated and joined teams")
    expected = {
        "/me/teamwork/associatedTeams": "parse_associated_teams",
        "/me/joinedTeams": "parse_joined_teams",
    }
    for request in requests:
        suffix = request.url.removeprefix(spider.graph_root)
        callback_name = getattr(request.callback, "__name__", None)
        if expected.get(suffix) != callback_name:
            pytest.fail(f"Unexpected initial Teams request: {request.url}")
        if request.cb_kwargs.get("purpose") is None:
            pytest.fail("Initial requests must carry explicit failure purpose")
        if not request.meta.get("dont_cache"):
            pytest.fail("Teams discovery requests must remain fresh")


def test_context_failure_keys_are_bounded_and_provider_identifiers_only() -> None:
    expected = {
        "team_id",
        "host_team_id",
        "receiving_team_id",
        "channel_id",
        "root_message_id",
        "hosted_content_id",
    }
    if set(MicrosoftTeamsChannelDiscoverSpider.failure_context_keys) != expected:
        pytest.fail("Terminal request failure context changed unexpectedly")
