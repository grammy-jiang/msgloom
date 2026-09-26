from __future__ import annotations

import asyncio

from scrapy import signals
from scrapy.exceptions import NotConfigured

from msgloom.catalog import Catalog

_SERVICE_ATTR = "_msgloom_catalog_service"


class CatalogService:
    """Crawler-scoped SQLAlchemy catalog service shared by Scrapy components."""

    def __init__(self, crawler) -> None:
        self.catalog = Catalog(crawler.settings["MSGLOOM_DATABASE_URL"])
        self.write_lock = asyncio.Lock()
        self._closed = False

    @classmethod
    def from_crawler(cls, crawler):
        if not crawler.settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            raise NotConfigured("SQLAlchemy catalog service disabled")
        existing = getattr(crawler, _SERVICE_ATTR, None)
        if existing is not None:
            return existing
        service = cls(crawler)
        setattr(crawler, _SERVICE_ATTR, service)
        crawler.signals.connect(service.spider_closed, signal=signals.spider_closed)
        return service

    def spider_closed(self, spider, reason) -> None:
        if not self._closed:
            self.catalog.close()
            self._closed = True


def get_catalog_service(crawler) -> CatalogService:
    service = getattr(crawler, _SERVICE_ATTR, None)
    if service is None:
        service = CatalogService.from_crawler(crawler)
    return service
