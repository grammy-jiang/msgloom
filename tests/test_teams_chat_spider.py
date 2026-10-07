"""Qualify the Teams chat application spider boundary and startup contract."""

import asyncio
import json

import pytest
from scrapy import Request
from scrapy.crawler import Crawler
from scrapy.http import TextResponse
from scrapy.settings import Settings

from message_ingest.spiders.microsoft._graph import MicrosoftGraphSpider
from message_ingest.spiders.microsoft.teams._base import MicrosoftTeamsBaseSpider
from message_ingest.spiders.microsoft.teams.chat import (
    MicrosoftTeamsChatDiscoverSpider,
)
from microsoft_graph.spiders.teams.chat_composition import (
    MicrosoftTeamsChatCompositionSpider,
)


def _settings() -> Settings:
    """Return normal project settings without starting crawler components."""
    settings = Settings()
    settings.setmodule("message_ingest.settings")
    return settings


def test_chat_spider_uses_frozen_provider_first_mro_and_scope() -> None:
    """The concrete spider must retain provider and application Graph owners."""
    if MicrosoftTeamsChatDiscoverSpider.__bases__ != (
        MicrosoftTeamsChatCompositionSpider,
        MicrosoftTeamsBaseSpider,
    ):
        pytest.fail("Teams chat spider must use the frozen two-parent MRO")
    if not issubclass(MicrosoftTeamsChatDiscoverSpider, MicrosoftGraphSpider):
        pytest.fail("Teams chat spider must remain an application Graph spider")

    crawler = Crawler(MicrosoftTeamsChatDiscoverSpider, _settings())
    spider = MicrosoftTeamsChatDiscoverSpider.from_crawler(crawler)
    if spider.name != "microsoft_teams_chat_discover":
        pytest.fail("Unexpected public Teams chat spider name")
    if crawler.settings.getlist("MS_GRAPH_SCOPES") != ["Chat.Read"]:
        pytest.fail("T1 chat discovery must request only Chat.Read")
    if spider.source_id != "microsoft-teams-default":
        pytest.fail("Chat discovery must use the shared default Teams source")


def test_chat_spider_rejects_incompatible_scope_override() -> None:
    """Extra or missing scopes must fail before any request can be scheduled."""
    settings = _settings()
    settings.set("MS_GRAPH_SCOPES", ["Chat.Read", "User.Read"], priority="cmdline")
    crawler = Crawler(MicrosoftTeamsChatDiscoverSpider, settings)
    with pytest.raises(ValueError, match="exactly Chat.Read"):
        MicrosoftTeamsChatDiscoverSpider.from_crawler(crawler)


async def _first_start_request(
    spider: MicrosoftTeamsChatDiscoverSpider,
) -> Request:
    """Return the first startup request through a concrete coroutine."""
    request = await anext(spider.start())
    if not isinstance(request, Request):
        pytest.fail("Chat discovery must start with a Scrapy Request")
    return request


def test_chat_start_request_is_named_fresh_and_evidence_contextual() -> None:
    """Startup uses the native Graph request with explicit callback purpose."""
    crawler = Crawler(MicrosoftTeamsChatDiscoverSpider, _settings())
    spider = MicrosoftTeamsChatDiscoverSpider.from_crawler(crawler)
    request = asyncio.run(_first_start_request(spider))

    if request.callback != spider.parse_chats or request.errback != spider.errback:
        pytest.fail("Chat inventory must use named application callbacks")
    if request.cb_kwargs != {"purpose": "teams-chat-list"}:
        pytest.fail("Chat inventory request must carry explicit evidence purpose")
    if not request.meta.get("dont_cache"):
        pytest.fail("Teams discovery reads must remain uncached")
    if not request.url.endswith("/me/chats?%24top=50"):
        pytest.fail(f"Unexpected provider-built chat inventory URL: {request.url}")


def test_chat_spider_rejects_jobdir_before_network() -> None:
    """Initial chat discovery must keep persistent scheduler resume disabled."""
    settings = _settings()
    settings.set("JOBDIR", "/tmp/unsupported-teams-job", priority="cmdline")
    crawler = Crawler(MicrosoftTeamsChatDiscoverSpider, settings)
    with pytest.raises(ValueError, match="JOBDIR"):
        MicrosoftTeamsChatDiscoverSpider.from_crawler(crawler)


def test_chat_discovery_selects_message_page_size_in_application() -> None:
    crawler = Crawler(MicrosoftTeamsChatDiscoverSpider, _settings())
    spider = MicrosoftTeamsChatDiscoverSpider.from_crawler(crawler)
    request = asyncio.run(_first_start_request(spider))
    response = TextResponse(
        request.url,
        request=request,
        body=json.dumps({"value": [{"id": "chat-1", "chatType": "oneOnOne"}]}).encode(),
        encoding="utf-8",
    )
    output = list(spider.parse_chats(response, **request.cb_kwargs))
    messages = next(
        value
        for value in output
        if isinstance(value, Request) and value.callback == spider.parse_chat_messages
    )
    if (
        messages.url
        != "https://graph.microsoft.com/v1.0/chats/chat-1/messages?%24top=50"
    ):
        pytest.fail("Application message traversal must retain selected page size")
    if messages.headers.get("Prefer") != b"include-unknown-enum-members":
        pytest.fail("Application message traversal must retain representation headers")
