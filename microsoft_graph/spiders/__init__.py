"""Microsoft Graph spiders for native Scrapy request and item flow."""

from .graph import MicrosoftGraphSpider
from .resources import GraphCollectionSpider, GraphObjectSpider

__all__ = ["GraphCollectionSpider", "GraphObjectSpider", "MicrosoftGraphSpider"]
