"""Format Graph crawl records without provider payloads or request URLs."""

from __future__ import annotations

import logging
from typing import Any

from scrapy.logformatter import LogFormatter, LogFormatterResult

from microsoft_graph.request import graph_operation
from microsoft_graph.spiders.graph import MicrosoftGraphSpider


class MicrosoftGraphLogFormatter(LogFormatter):
    """Keep Scrapy logs useful without rendering provider payloads or URLs."""

    def _redact(self, spider) -> bool:
        """Limit the formatter to Graph crawls unless a consumer broadens it."""
        return isinstance(spider, MicrosoftGraphSpider)

    @staticmethod
    def _item_summary(item: Any) -> str:
        """Expose only the item type; consumers may supply bounded summaries."""
        return type(item).__name__

    def crawled(self, request, response, spider) -> LogFormatterResult:
        """Log response metadata without URLs that may contain private tokens."""
        if not self._redact(spider):
            return super().crawled(request, response, spider)
        return {
            "level": logging.DEBUG,
            "msg": (
                "Crawled acquisition response: status=%(status)s method=%(method)s "
                "purpose=%(purpose)s cached=%(cached)s"
            ),
            "args": {
                "status": response.status,
                "method": request.method,
                "purpose": graph_operation(request),
                "cached": "cached" in response.flags,
            },
        }

    def spider_error(self, failure, request, response, spider) -> LogFormatterResult:
        """Summarize callback failure without formatting response content."""
        if not self._redact(spider):
            return super().spider_error(failure, request, response, spider)
        return {
            "level": logging.ERROR,
            "msg": (
                "Spider error processing acquisition request: "
                "method=%(method)s purpose=%(purpose)s"
            ),
            "args": {
                "method": request.method,
                "purpose": graph_operation(request),
            },
        }

    def download_error(
        self,
        failure,
        request,
        spider,
        errmsg=None,
    ) -> LogFormatterResult:
        """Report a transport failure without arbitrary exception text."""
        if not self._redact(spider):
            return super().download_error(failure, request, spider, errmsg)
        error_type = failure.type.__name__ if failure.type else "UnknownError"
        return {
            "level": logging.ERROR,
            "msg": (
                "Error downloading acquisition request: method=%(method)s "
                "purpose=%(purpose)s error_type=%(error_type)s"
            ),
            "args": {
                "method": request.method,
                "purpose": graph_operation(request),
                "error_type": error_type,
            },
        }

    def scraped(self, item: Any, response, spider) -> LogFormatterResult:
        """Replace Scrapy's default item repr with a bounded summary."""
        if not self._redact(spider):
            return super().scraped(item, response, spider)
        return {
            "level": logging.DEBUG,
            "msg": "Scraped %(summary)s",
            "args": {"summary": self._item_summary(item)},
        }

    def dropped(self, item: Any, exception, response, spider) -> LogFormatterResult:
        """Honor configured drop level while avoiding full item contents."""
        if not self._redact(spider):
            return super().dropped(item, exception, response, spider)
        level = getattr(exception, "log_level", None)
        if level is None:
            level = spider.crawler.settings["DEFAULT_DROPITEM_LOG_LEVEL"]
        if isinstance(level, str):
            level = getattr(logging, level)
        return {
            "level": level,
            "msg": "Dropped %(summary)s: error_type=%(error_type)s",
            "args": {
                "summary": self._item_summary(item),
                "error_type": type(exception).__name__,
            },
        }

    def item_error(self, item: Any, exception, response, spider) -> LogFormatterResult:
        """Report a pipeline exception without item payload or exception text."""
        if not self._redact(spider):
            return super().item_error(item, exception, response, spider)
        return {
            "level": logging.ERROR,
            "msg": "Error processing %(summary)s",
            "args": {"summary": self._item_summary(item)},
        }


__all__ = ["MicrosoftGraphLogFormatter"]
