"""Install crawler-scoped privacy filters around Scrapy core logging."""

from __future__ import annotations

import logging

from scrapy import signals
from scrapy.exceptions import NotConfigured

from message_ingest.logfilters import OutlookScrapyPrivacyFilter
from message_ingest.spiders.outlook_mail import OutlookMailSpider


class OutlookLogPrivacyExtension:
    """Keep Scrapy core exception records privacy-safe for Outlook crawls."""

    def __init__(self, crawler) -> None:
        """Prepare one crawler-scoped filter and its target loggers."""
        self.crawler = crawler
        self._filter = OutlookScrapyPrivacyFilter(crawler)
        self._targets = (
            logging.getLogger("scrapy.core.engine"),
            logging.getLogger("scrapy.core.scraper"),
            logging.getLogger("scrapy.utils.signal"),
        )
        self._installed = False

    @classmethod
    def from_crawler(cls, crawler):
        """Enable privacy filtering independently of final-status reporting."""
        if not crawler.settings.getbool("MSGLOOM_LOG_PRIVACY_ENABLED"):
            raise NotConfigured("msgloom log privacy extension disabled")
        extension = cls(crawler)
        crawler.signals.connect(extension.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(extension.engine_stopped, signal=signals.engine_stopped)
        return extension

    def spider_opened(self, spider) -> None:
        """Install filters only for the shared Outlook spider hierarchy."""
        if not isinstance(spider, OutlookMailSpider) or self._installed:
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
