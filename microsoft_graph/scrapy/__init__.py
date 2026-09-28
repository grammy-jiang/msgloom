"""Reusable Microsoft Graph components for native Scrapy crawlers."""

from .addon import MicrosoftGraphAddon
from .resources import GraphCollectionSpider, GraphObjectSpider
from .spiders import MicrosoftGraphSpider

__all__ = [
    "GraphCollectionSpider",
    "GraphObjectSpider",
    "MicrosoftGraphAddon",
    "MicrosoftGraphSpider",
]
