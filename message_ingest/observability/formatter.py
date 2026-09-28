"""Summarize acquisition events without exposing acquired private content."""

from __future__ import annotations

import logging
from typing import Any

from scrapy.logformatter import LogFormatter, LogFormatterResult

from .item_summary import summarize_item


class MessageIngestLogFormatter(LogFormatter):
    """Keep Scrapy logs useful without rendering provider payloads or URLs."""

    def crawled(self, request, response, spider) -> LogFormatterResult:
        """Log response metadata without URLs that may contain private tokens."""
        return {
            "level": logging.DEBUG,
            "msg": (
                "Crawled acquisition response: status=%(status)s method=%(method)s "
                "purpose=%(purpose)s cached=%(cached)s"
            ),
            "args": {
                "status": response.status,
                "method": request.method,
                "purpose": request.cb_kwargs.get("purpose", "unknown"),
                "cached": "cached" in response.flags,
            },
        }

    def spider_error(self, failure, request, response, spider) -> LogFormatterResult:
        """Summarize callback failure without formatting response content."""
        return {
            "level": logging.ERROR,
            "msg": (
                "Spider error processing acquisition request: "
                "method=%(method)s purpose=%(purpose)s"
            ),
            "args": {
                "method": request.method,
                "purpose": request.cb_kwargs.get("purpose", "unknown"),
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
        error_type = failure.type.__name__ if failure.type else "UnknownError"
        return {
            "level": logging.ERROR,
            "msg": (
                "Error downloading acquisition request: method=%(method)s "
                "purpose=%(purpose)s error_type=%(error_type)s"
            ),
            "args": {
                "method": request.method,
                "purpose": request.cb_kwargs.get("purpose", "unknown"),
                "error_type": error_type,
            },
        }

    def scraped(self, item: Any, response, spider) -> LogFormatterResult:
        """Replace Scrapy's default item repr with a bounded summary."""
        return {
            "level": logging.DEBUG,
            "msg": "Scraped %(summary)s",
            "args": {"summary": summarize_item(item)},
        }

    def dropped(self, item: Any, exception, response, spider) -> LogFormatterResult:
        """Honor configured drop level while avoiding full item contents."""
        level = getattr(exception, "log_level", None)
        if level is None:
            level = spider.crawler.settings["DEFAULT_DROPITEM_LOG_LEVEL"]
        if isinstance(level, str):
            level = getattr(logging, level)
        return {
            "level": level,
            "msg": "Dropped %(summary)s: error_type=%(error_type)s",
            "args": {
                "summary": summarize_item(item),
                "error_type": type(exception).__name__,
            },
        }

    def item_error(self, item: Any, exception, response, spider) -> LogFormatterResult:
        """Record persistence failure without exposing failed item payload."""
        return {
            "level": logging.ERROR,
            "msg": "Error processing %(summary)s",
            "args": {"summary": summarize_item(item)},
        }


__all__ = ["MessageIngestLogFormatter"]
