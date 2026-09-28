"""Sanitize Scrapy core LogRecords for Microsoft Graph acquisition runs."""

from __future__ import annotations

import logging
from typing import ClassVar

from scrapy.http import Request

from message_ingest.logformatter import MessageIngestLogFormatter
from message_ingest.spiders.microsoft._graph import MicrosoftGraphSpider


class MicrosoftGraphScrapyPrivacyFilter(logging.Filter):
    """
    Redact Scrapy core records that bypass LogFormatter safeguards.

    Scrapy 2.19 attaches full items to scraper records and forces traceback
    output for callback, download, and pipeline exceptions. Engine close
    failures also log tracebacks before spider_closed. This filter keeps those
    records useful while preventing provider payloads, URLs, and arbitrary
    exception text from reaching handlers.
    """

    _close_failures: ClassVar[dict[str, str]] = {
        "Slot close failure": "slot",
        "Downloader close failure": "downloader",
        "Scraper close failure": "scraper",
        "Scheduler close failure": "scheduler",
    }

    def __init__(self, crawler) -> None:
        """Bind filtering and close-failure observation to one crawler."""
        super().__init__()
        self.crawler = crawler

    def filter(self, record: logging.LogRecord) -> bool:
        """Sanitize one Scrapy engine/scraper record in place."""
        spider = self.crawler.spider
        if not isinstance(spider, MicrosoftGraphSpider):
            return True
        record_spider = getattr(record, "spider", None)
        if record_spider is not None and record_spider is not spider:
            return True

        error_type = self._error_type(record)
        if record.name == "scrapy.core.scraper":
            self._sanitize_scraper_record(record, error_type)
        elif record.name == "scrapy.core.engine":
            self._sanitize_engine_record(record, error_type)
        elif record.name == "scrapy.utils.signal":
            self._sanitize_signal_record(record, error_type)
        elif record.name == "scrapy.downloadermiddlewares.httpcache":
            self._sanitize_httpcache_record(record, error_type)

        if record.exc_info:
            record.exc_info = None
            record.exc_text = None
        return True

    def _sanitize_scraper_record(
        self,
        record: logging.LogRecord,
        error_type: str,
    ) -> None:
        """Replace structured item/request fields with bounded summaries."""
        if "item" in record.__dict__:
            record.__dict__["item"] = MessageIngestLogFormatter._summary(
                record.__dict__["item"]
            )

        if isinstance(record.args, dict):
            args = dict(record.args)
            if isinstance(request := args.get("request"), Request):
                args["request"] = self._request_summary(request)
            if record.msg == "Scraper bug processing %(request)s":
                record.msg = (
                    "Scraper bug processing %(request)s: error_type=%(error_type)s"
                )
                args["error_type"] = error_type
            record.args = args

    def _sanitize_engine_record(
        self,
        record: logging.LogRecord,
        error_type: str,
    ) -> None:
        """Record close failures and sanitize start-error f-strings."""
        message = str(record.msg)
        if stage := self._close_failures.get(message):
            self.crawler.stats.inc_value("msgloom/lifecycle/close_error_count")
            self.crawler.stats.inc_value(
                f"msgloom/lifecycle/close_error_stage_count/{stage}"
            )
            if isinstance((spider := self.crawler.spider), MicrosoftGraphSpider):
                spider.mark_run_failed("framework_close_error")
            record.msg = f"{message}: error_type=%s"
            record.args = (error_type,)
            return

        if message.startswith("Error while reading start items and requests:"):
            record.msg = "Error while reading start items and requests: error_type=%s"
            record.args = (error_type,)

    @staticmethod
    def _sanitize_httpcache_record(
        record: logging.LogRecord,
        error_type: str,
    ) -> None:
        """Redact native cache-read failures that embed the full Request."""
        message = str(record.msg)
        if message.startswith("Could not read the cache entry for "):
            record.msg = (
                "Could not read Microsoft Graph cache entry; "
                "treating it as a cache miss: error_type=%s"
            )
            record.args = (error_type,)

    def _sanitize_signal_record(
        self,
        record: logging.LogRecord,
        error_type: str,
    ) -> None:
        """Redact signal-handler failures without rendering receiver objects."""
        stats = self.crawler.stats
        stats.inc_value("msgloom/lifecycle/signal_error_count")
        spider = self.crawler.spider
        if isinstance(spider, MicrosoftGraphSpider):
            spider.mark_run_failed("signal_handler_error")
            current = stats.get_value("msgloom/final/status")
            if current not in {None, "running", "failed"}:
                stats.set_value("msgloom/final/status", "failed")
                reasons = list(stats.get_value("msgloom/final/reason_codes", []))
                if "signal_handler_error" not in reasons:
                    reasons.append("signal_handler_error")
                    reasons.sort()
                    stats.set_value("msgloom/final/reason_codes", reasons)
        receiver = None
        if isinstance(record.args, dict):
            receiver = record.args.get("receiver")
        owner_obj = getattr(receiver, "__self__", None)
        if owner_obj is not None:
            owner = type(owner_obj).__name__
            name = getattr(receiver, "__name__", "handler")
            receiver_label = f"{owner}.{name}"
        else:
            receiver_label = getattr(
                receiver,
                "__qualname__",
                type(receiver).__name__ if receiver is not None else "unknown",
            )
        record.msg = (
            "Error caught on signal handler: receiver=%(receiver)s "
            "error_type=%(error_type)s"
        )
        record.args = {
            "receiver": str(receiver_label)[:96],
            "error_type": error_type,
        }

    @staticmethod
    def _error_type(record: logging.LogRecord) -> str:
        """Return only the exception class name carried by the record."""
        if record.exc_info and record.exc_info[0]:
            return record.exc_info[0].__name__
        return "UnknownError"

    @staticmethod
    def _request_summary(request: Request) -> str:
        """Summarize a Request without its URL or body."""
        purpose = request.cb_kwargs.get("purpose", "unknown")
        return f"Request(method={request.method!r}, purpose={purpose!r})"
