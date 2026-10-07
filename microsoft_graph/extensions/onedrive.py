"""Sanitize native transport logs for marked OneDrive content requests."""

import logging
from weakref import WeakSet

from scrapy import Request, signals

from microsoft_graph.spiders.onedrive import (
    ONEDRIVE_CONTENT_META_KEY,
    MicrosoftOneDriveSpider,
)

from ._logfilters import MicrosoftGraphScrapyPrivacyFilter

_TRANSPORT_LOGGERS = (
    "scrapy.core.downloader.handlers.http11",
    "scrapy.downloadermiddlewares.httpcompression",
)


class _ContentPrivacyFilter(MicrosoftGraphScrapyPrivacyFilter):
    """Redact requests and recognize native URL warning text."""

    spider_class = MicrosoftOneDriveSpider

    def __init__(self, crawler) -> None:
        super().__init__(crawler)
        self.requests: WeakSet[Request] = WeakSet()

    def track_request(self, request: Request) -> None:
        """Observe marked downloads without retaining requests or URLs."""
        if request.meta.get(ONEDRIVE_CONTENT_META_KEY):
            self.requests.add(request)

    def filter(self, record: logging.LogRecord) -> bool:
        """Sanitize this crawler's marked requests and URL warnings."""
        spider = self.crawler.spider
        if not isinstance(spider, self.spider_class):
            return True
        record_spider = getattr(record, "spider", None)
        if record_spider is not None and record_spider is not spider:
            return True
        args = record.args.values() if isinstance(record.args, dict) else record.args
        requests = (
            (*args, getattr(record, "request", None))
            if args
            else (getattr(record, "request", None),)
        )
        marked = any(
            isinstance(request, Request) and request.meta.get(ONEDRIVE_CONTENT_META_KEY)
            for request in requests
        )
        if record.name in _TRANSPORT_LOGGERS:
            # HTTP/1.1 and compression size/data-loss warnings embed URLs
            # without a Request or spider. Match live marked downloads so a
            # concurrent crawler's unrelated diagnostics remain unchanged.
            message = record.getMessage()
            marked = marked or any(request.url in message for request in self.requests)
            if marked:
                record.msg = "OneDrive content transport diagnostic: component=%s"
                record.args = (record.name,)
        return super().filter(record) if marked else True


class OneDriveContentPrivacyExtension:
    """
    Supplement core Graph privacy without replacing redirect or auth handling.

    This supplements the core Graph privacy extension. It covers
    native redirect, dupefilter, HTTP/1.1, and compression records only. Weak
    references survive downloader response middleware without retaining secret
    URLs after their requests are released. In particular, removing requests
    at ``request_left_downloader`` would precede compression warnings.
    """

    def __init__(self, crawler) -> None:
        self._filter = _ContentPrivacyFilter(crawler)
        self._targets = tuple(
            logging.getLogger(name)
            for name in (
                "scrapy.downloadermiddlewares.redirect",
                "scrapy.dupefilters",
                *_TRANSPORT_LOGGERS,
            )
        )
        self._installed = False

    @classmethod
    def from_crawler(cls, crawler):
        """Observe downloads and install filters for OneDrive crawlers."""
        extension = cls(crawler)
        crawler.signals.connect(extension.spider_opened, signals.spider_opened)
        crawler.signals.connect(extension.engine_stopped, signals.engine_stopped)
        crawler.signals.connect(
            extension._filter.track_request, signals.request_reached_downloader
        )
        return extension

    def spider_opened(self, spider) -> None:
        """Install once without changing unmarked or other product records."""
        if not isinstance(spider, MicrosoftOneDriveSpider) or self._installed:
            return
        for target in self._targets:
            target.addFilter(self._filter)
        self._installed = True

    def engine_stopped(self) -> None:
        """Remove crawler filters and weak references after shutdown."""
        for target in self._targets:
            target.removeFilter(self._filter)
        self._filter.requests.clear()
        self._installed = False
