"""Install crawler-scoped privacy filters around Scrapy core logging."""

from __future__ import annotations

import logging

from scrapy import signals

from ._logfilters import (
    MicrosoftGraphScrapyPrivacyFilter,
)


class MicrosoftGraphLogPrivacyExtension:
    """Keep Scrapy core exception records privacy-safe for Graph crawls."""

    filter_class = MicrosoftGraphScrapyPrivacyFilter

    def __init__(self, crawler) -> None:
        """Prepare one crawler-scoped filter and its target loggers."""
        self.crawler = crawler
        self._filter = self.filter_class(crawler)
        self._targets = (
            logging.getLogger("scrapy.core.engine"),
            logging.getLogger("scrapy.core.scraper"),
            logging.getLogger("scrapy.utils.signal"),
            logging.getLogger("scrapy.downloadermiddlewares.httpcache"),
        )
        self._installed = False

    @classmethod
    def from_crawler(cls, crawler):
        """Enable Graph privacy filtering independently of status reporting."""
        extension = cls(crawler)
        crawler.signals.connect(extension.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(extension.engine_stopped, signal=signals.engine_stopped)
        return extension

    def spider_opened(self, spider) -> None:
        """Install filters only for the Microsoft Graph spider hierarchy."""
        if not isinstance(spider, self._filter.spider_class) or self._installed:
            return
        for target in self._targets:
            target.addFilter(self._filter)
        self._installed = True

    def engine_stopped(self) -> None:
        """Remove crawler-scoped filters after all spider-close handlers."""
        if not self._installed:
            return
        for target in self._targets:
            target.removeFilter(self._filter)
        self._installed = False
