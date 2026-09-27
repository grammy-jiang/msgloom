"""
Keep shared bases abstract and expose the concrete acquisition spiders.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from scrapy.spiderloader import SpiderLoader
from scrapy.utils.project import get_project_settings

from message_ingest.providers.microsoft_graph.spider import MicrosoftGraphSpider
from message_ingest.spiders.microsoft_profile import MicrosoftProfileSpider
from message_ingest.spiders.outlook_calendar_delta import (
    OutlookCalendarDeltaSpider,
)
from message_ingest.spiders.outlook_calendar_discover import (
    OutlookCalendarDiscoverSpider,
)
from message_ingest.spiders.outlook_calendar_full import (
    OutlookCalendarFullSpider,
)
from message_ingest.spiders.outlook_calendar_window import (
    OutlookCalendarWindowSpider,
)
from message_ingest.spiders.outlook_delta import OutlookDeltaSpider
from message_ingest.spiders.outlook_discover import OutlookDiscoverSpider
from message_ingest.spiders.outlook_full import OutlookFullSpider
from message_ingest.spiders.outlook_mail import OutlookMailSpider


def test_scrapy_discovers_the_concrete_graph_resource_spiders() -> None:
    loader = SpiderLoader.from_settings(get_project_settings())
    expected = {
        "microsoft_profile": MicrosoftProfileSpider,
        "outlook_calendar_delta": OutlookCalendarDeltaSpider,
        "outlook_calendar_discover": OutlookCalendarDiscoverSpider,
        "outlook_calendar_full": OutlookCalendarFullSpider,
        "outlook_calendar_window": OutlookCalendarWindowSpider,
        "outlook_discover": OutlookDiscoverSpider,
        "outlook_delta": OutlookDeltaSpider,
        "outlook_full": OutlookFullSpider,
    }
    if set(loader.list()) != set(expected):
        pytest.fail("Expected: set(loader.list()) == set(expected)")
    for name, spider_cls in expected.items():
        if loader.load(name) is not spider_cls:
            pytest.fail("Expected: loader.load(name) is spider_cls")
        if not issubclass(spider_cls, MicrosoftGraphSpider):
            pytest.fail("Expected: issubclass(spider_cls, MicrosoftGraphSpider)")
        if inspect.isabstract(spider_cls):
            pytest.fail("Expected: not inspect.isabstract(spider_cls)")
        if not inspect.isasyncgenfunction(spider_cls.start):
            pytest.fail("Expected: inspect.isasyncgenfunction(spider_cls.start)")
    if not inspect.isabstract(OutlookMailSpider):
        pytest.fail("Expected: inspect.isabstract(OutlookMailSpider)")


@pytest.mark.parametrize(
    ("spider_cls", "kwargs", "error"),
    [
        (OutlookDiscoverSpider, {"page_size": "0"}, "page_size"),
        (OutlookDiscoverSpider, {"max_pages": "-1"}, "max_pages"),
        (OutlookDeltaSpider, {"page_size": "1001"}, "page_size"),
        (OutlookCalendarFullSpider, {"event_ids": " , "}, "event ID"),
        (OutlookCalendarFullSpider, {"event_ids": "e1", "page_size": "0"}, "page_size"),
        (OutlookFullSpider, {"message_ids": " , "}, "message ID"),
        (OutlookFullSpider, {"message_ids": "m1", "operation": "other"}, "operation"),
        (OutlookFullSpider, {"message_ids": "m1", "profile": "other"}, "profile"),
    ],
)
def test_each_spider_validates_its_own_arguments(spider_cls, kwargs, error) -> None:
    with pytest.raises(ValueError, match=error):
        spider_cls(**kwargs)


def test_all_message_ingest_modules_stay_below_500_lines() -> None:
    directory = Path(__file__).parents[1] / "message_ingest"
    oversized = {
        path.name: line_count
        for path in directory.rglob("*.py")
        if (line_count := len(path.read_text().splitlines())) >= 500
    }
    if oversized:
        pytest.fail("Expected: not oversized")
