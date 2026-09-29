"""Cover native content transport logs that bypass Graph log formatting."""

import logging

from message_ingest.spiders.microsoft.onedrive.content import (
    MicrosoftOneDriveContentSpider,
)
from microsoft_graph.extensions._logfilters import MicrosoftGraphScrapyPrivacyFilter
from microsoft_graph.extensions.privacy import MicrosoftGraphLogPrivacyExtension

# Native handlers format URLs into strings before logging size/data-loss
# warnings. Compression warnings can also render full URLs. These records
# have no structured request to pass through the shared Graph filter.
_TRANSPORT_LOGGERS = (
    "scrapy.core.downloader.handlers.http11",
    "scrapy.downloadermiddlewares.httpcompression",
)


class _ContentPrivacyFilter(MicrosoftGraphScrapyPrivacyFilter):
    """Reuse Graph request redaction; bound native content warning text."""

    spider_class = MicrosoftOneDriveContentSpider

    def filter(self, record: logging.LogRecord) -> bool:
        """Redact preformatted transport messages only during content crawls."""
        spider = self.crawler.spider
        if (
            isinstance(spider, self.spider_class)
            and getattr(record, "spider", spider) is spider
            and record.name in _TRANSPORT_LOGGERS
        ):
            record.msg = "OneDrive content transport diagnostic: component=%s"
            record.args = (record.name,)
        return super().filter(record)


class OneDriveContentPrivacyExtension(MicrosoftGraphLogPrivacyExtension):
    """
    Extend log coverage without replacing redirects, auth, or shared privacy.

    Two-host integration showed native RedirectMiddleware logs Request reprs
    at DEBUG, and the HTTP/1.1 handler embeds URLs in size-limit warnings. Reuse
    the existing filter for structured Requests and redact native warning text.
    The content errback records the bounded error type and sanitized evidence.
    Filters are crawler-scoped and removed by the inherited engine-stop hook.
    """

    filter_class = _ContentPrivacyFilter

    def __init__(self, crawler) -> None:
        super().__init__(crawler)
        self._targets = tuple(
            logging.getLogger(name)
            for name in (
                "scrapy.downloadermiddlewares.redirect",
                "scrapy.dupefilters",
                *_TRANSPORT_LOGGERS,
            )
        )
