"""
Invalid framework state must fail explicitly, including optimized Python runs.
"""

from __future__ import annotations

import asyncio

import pytest
from scrapy import Request
from scrapy.http import TextResponse
from scrapy.utils.test import get_crawler

from message_ingest.commands._common import run_graph
from message_ingest.commands.microsoft import Command
from message_ingest.middlewares.microsoft_graph.errors import (
    MicrosoftGraphErrorMiddleware,
)
from message_ingest.spiders.microsoft.outlook.email.discover import (
    OutlookDiscoverSpider,
)


def test_command_requires_an_initialized_crawler_process() -> None:
    """Direct command invocation must not hide a missing Scrapy process."""
    with pytest.raises(RuntimeError, match="initialize the crawler process"):
        run_graph(Command(), "outlook_delta", {})


def test_evidence_requires_the_original_request() -> None:
    """A response without its request cannot provide complete HTTP evidence."""
    spider = OutlookDiscoverSpider.from_crawler(get_crawler(OutlookDiscoverSpider))
    response = TextResponse("https://graph.microsoft.com/v1.0/me/messages")
    with pytest.raises(ValueError, match="linked to its Scrapy request"):
        list(spider.parse(response))


def test_graph_retry_requires_an_active_spider() -> None:
    """
    Scrapy's retry helper needs a live spider for settings and retry stats.
    """
    middleware = MicrosoftGraphErrorMiddleware(
        max_retries=1,
        fallback_base_seconds=1,
        fallback_max_seconds=1,
        crawler=get_crawler(OutlookDiscoverSpider),
    )
    request = Request("https://graph.microsoft.com/v1.0/me/messages")
    response = TextResponse(request.url, request=request, status=429)
    with pytest.raises(RuntimeError, match="active Scrapy spider"):
        asyncio.run(middleware.process_response(request, response))


def test_msal_runtime_matches_source_identity_contract() -> None:
    """Pin the observed MSAL account metadata contract used by source identity."""
    import inspect

    import msal

    if msal.__version__ != "1.39.0":
        pytest.fail('Expected: msal.__version__ == "1.39.0"')
    source = inspect.getsource(msal.PublicClientApplication._find_msal_accounts)
    if '"home_account_id"' not in source:
        pytest.fail("Expected MSAL account enumeration to expose home_account_id")
