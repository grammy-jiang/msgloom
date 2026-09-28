"""Generic Scrapy retries with URL-safe replacement log records."""

from __future__ import annotations

import logging

from scrapy.downloadermiddlewares.retry import RetryMiddleware, get_retry_request

from microsoft_graph.request import graph_operation

logger = logging.getLogger(__name__)
# Scrapy's retry helper formats the full Request repr. Use an unregistered
# logger above CRITICAL so helper messages cannot expose Graph URLs; the
# middleware emits its own bounded replacement records.
_retry_helper_logger = logging.Logger(  # noqa: LOG001
    "microsoft_graph.transport_retry_helper.silent",
    level=logging.CRITICAL + 1,
)


class PrivacySafeRetryMiddleware(RetryMiddleware):
    """Preserve Scrapy retry semantics without logging request URLs."""

    def _retry(self, request, reason):
        """Delegate retry construction while replacing URL-bearing logs."""
        max_retry_times = request.meta.get("max_retry_times", self.max_retry_times)
        priority_adjust = request.meta.get("priority_adjust", self.priority_adjust)
        give_up_log_level = request.meta.get(
            "give_up_log_level", self.give_up_log_level
        )
        if (spider := self.crawler.spider) is None:
            raise RuntimeError("Scrapy retries require an active spider")

        retry = get_retry_request(
            request,
            reason=reason,
            spider=spider,
            max_retry_times=max_retry_times,
            priority_adjust=priority_adjust,
            logger=_retry_helper_logger,
            give_up_log_level=give_up_log_level,
        )
        retry_number = int(request.meta.get("retry_times", 0)) + 1
        purpose = graph_operation(request)
        reason_label = self._reason_label(reason)
        if retry is None:
            level = (
                self.give_up_log_level
                if give_up_log_level is None
                else give_up_log_level
            )
            if isinstance(level, str):
                level = logging.getLevelName(level)
            if not isinstance(level, int):
                raise ValueError(f"Invalid give-up log level: {give_up_log_level!r}")
            logger.log(
                level,
                "Scrapy retry limit reached: purpose=%s reason=%s retries=%s",
                purpose,
                reason_label,
                retry_number,
                extra={"spider": spider},
            )
            return None
        logger.debug(
            "Scrapy retry scheduled: purpose=%s reason=%s retry=%s/%s",
            purpose,
            reason_label,
            retry_number,
            max_retry_times,
            extra={"spider": spider},
        )
        return retry

    @staticmethod
    def _reason_label(reason) -> str:
        """Return a bounded retry reason without arbitrary exception text."""
        if isinstance(reason, str):
            first = reason.split(maxsplit=1)[0] if reason else ""
            return f"http_{first}" if first.isdigit() else "string"
        if isinstance(reason, type):
            return reason.__name__
        return type(reason).__name__
