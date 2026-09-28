"""Observe application integrity failures before Graph log sanitization."""

from __future__ import annotations

import logging

from message_ingest.observability.item_summary import summarize_item
from message_ingest.spiders.microsoft._graph import MicrosoftGraphSpider
from microsoft_graph.extensions._logfilters import (
    MicrosoftGraphScrapyPrivacyFilter as GraphScrapyPrivacyFilter,
)


class MicrosoftGraphScrapyPrivacyFilter(GraphScrapyPrivacyFilter):
    """Retain item summaries and run integrity effects for application crawls."""

    spider_class = MicrosoftGraphSpider
    _item_summary = staticmethod(summarize_item)

    def _sanitize_engine_record(
        self, record: logging.LogRecord, error_type: str
    ) -> None:
        """Record close failure before the framework removes private details."""
        if stage := self._close_failures.get(str(record.msg)):
            self.crawler.stats.inc_value("msgloom/lifecycle/close_error_count")
            self.crawler.stats.inc_value(
                f"msgloom/lifecycle/close_error_stage_count/{stage}"
            )
            self.crawler.spider.mark_run_failed("framework_close_error")
        super()._sanitize_engine_record(record, error_type)

    def _sanitize_signal_record(
        self, record: logging.LogRecord, error_type: str
    ) -> None:
        """Invalidate the logical run, including already-published final status."""
        stats = self.crawler.stats
        stats.inc_value("msgloom/lifecycle/signal_error_count")
        self.crawler.spider.mark_run_failed("signal_handler_error")
        current = stats.get_value("msgloom/final/status")
        if current not in {None, "running", "failed"}:
            stats.set_value("msgloom/final/status", "failed")
            reasons = list(stats.get_value("msgloom/final/reason_codes", []))
            if "signal_handler_error" not in reasons:
                reasons.append("signal_handler_error")
                reasons.sort()
                stats.set_value("msgloom/final/reason_codes", reasons)
        super()._sanitize_signal_record(record, error_type)
