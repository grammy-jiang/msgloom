"""Provider-specific retries layered on Scrapy's retry helpers."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from math import ceil
from urllib.parse import urlsplit

from scrapy.downloadermiddlewares.retry import RetryMiddleware, get_retry_request
from scrapy.exceptions import NotConfigured

from message_ingest.providers.microsoft_graph import GRAPH_HOST

logger = logging.getLogger(__name__)
_SAFE_GRAPH_CODE = re.compile(r"[A-Za-z0-9_.-]{1,64}")
# Scrapy's retry helper formats the full Request repr. Use an unregistered
# logger above CRITICAL so helper messages cannot expose Graph URLs; the
# middleware emits its own bounded replacement records.
_retry_helper_logger = logging.Logger(  # noqa: LOG001
    "message_ingest.retry_helper.silent",
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
        purpose = request.cb_kwargs.get("purpose", "unknown")
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


class MicrosoftGraphErrorMiddleware:
    """
    Handle only Microsoft Graph error cases with provider-specific retry
    semantics.
    """

    retry_meta_key = "_msgloom_graph_error_retry"

    def __init__(
        self,
        *,
        max_retries: int,
        fallback_base_seconds: int,
        fallback_max_seconds: int,
        crawler,
    ) -> None:
        """
        Keep provider retry limits separate from Scrapy's generic transport
        retry limits.
        """
        self.max_retries = max_retries
        self.fallback_base_seconds = fallback_base_seconds
        self.fallback_max_seconds = fallback_max_seconds
        self.crawler = crawler
        self.stats = crawler.stats

    @classmethod
    def from_crawler(cls, crawler):
        """
        Read the final Graph retry/backoff settings or disable this component.
        """
        if not crawler.settings.getbool("MS_GRAPH_ERROR_MIDDLEWARE_ENABLED"):
            raise NotConfigured("Microsoft Graph error middleware disabled")
        return cls(
            max_retries=crawler.settings.getint("MS_GRAPH_ERROR_MAX_RETRIES"),
            fallback_base_seconds=crawler.settings.getint(
                "MS_GRAPH_ERROR_FALLBACK_BASE_SECONDS"
            ),
            fallback_max_seconds=crawler.settings.getint(
                "MS_GRAPH_ERROR_FALLBACK_MAX_SECONDS"
            ),
            crawler=crawler,
        )

    async def process_response(self, request, response):
        """
        Apply delayed retries only to Graph-specific retryable errors.

        Returning a :class:`~scrapy.Request` restarts the native downloader
        chain. On exhaustion, set ``dont_retry`` so the generic
        :class:`~scrapy.downloadermiddlewares.retry.RetryMiddleware` cannot
        start a second retry budget. The original failure response then reaches
        the spider's usual error handling.
        """
        if urlsplit(request.url).hostname != GRAPH_HOST:
            return response
        if request.meta.get("dont_retry", False):
            return response

        graph_codes = self._graph_error_codes(response)
        if not self._should_retry(response.status, graph_codes):
            if response.status >= 400:
                logger.debug(
                    "Microsoft Graph response left to Scrapy/Spider handling: "
                    "status=%s code=%s purpose=%s",
                    response.status,
                    self._safe_graph_code(graph_codes[-1]) if graph_codes else None,
                    self._purpose(request),
                    extra={"spider": self.crawler.spider},
                )
            return response

        retry_count = int(request.meta.get(self.retry_meta_key, 0))
        retry = self._retry_request(request, response.status, retry_count, graph_codes)
        if retry is None:
            request.meta["dont_retry"] = True
            purpose = self._purpose(request)
            self.stats.inc_value(
                f"msgloom/graph_error/exhausted_purpose_count/{purpose}"
            )
            self.stats.inc_value(
                f"msgloom/graph_error/exhausted_status_count/{response.status}"
            )
            logger.error(
                "Microsoft Graph retry limit reached: status=%s code=%s retries=%s "
                "purpose=%s",
                response.status,
                self._safe_graph_code(graph_codes[-1]) if graph_codes else None,
                retry_count,
                purpose,
                extra={"spider": self.crawler.spider},
            )
            return response

        delay, source = self._retry_delay(response, retry_count)
        purpose = self._purpose(request)
        self.stats.inc_value(f"msgloom/graph_error/retry_purpose_count/{purpose}")
        self.stats.inc_value(f"msgloom/graph_error/status_count/{response.status}")
        self.stats.inc_value(f"msgloom/graph_error/delay_source_count/{source}")
        self.stats.inc_value(
            "msgloom/graph_error/wait_seconds_total", count=ceil(delay)
        )
        self.stats.max_value("msgloom/graph_error/max_delay_seconds", delay)
        logger.warning(
            "Microsoft Graph retry scheduled: status=%s code=%s retry=%s/%s "
            "delay=%.1fs source=%s purpose=%s",
            response.status,
            self._safe_graph_code(graph_codes[-1]) if graph_codes else None,
            retry_count + 1,
            self.max_retries,
            delay,
            source,
            self._purpose(request),
            extra={"spider": self.crawler.spider},
        )
        await asyncio.sleep(delay)
        return retry

    @staticmethod
    def _should_retry(status: int, graph_codes: tuple[str, ...]) -> bool:
        """
        Retry throttling/service pressure and only the documented transient
        Graph 409 code.
        """
        if status in {429, 503, 509}:
            return True
        if status == 409:
            return any(
                code.casefold() == "directory_concurrencyviolation"
                for code in graph_codes
            )
        return False

    def _retry_request(
        self,
        request,
        status: int,
        retry_count: int,
        graph_codes: tuple[str, ...],
    ):
        """
        Use Scrapy's retry helper while retaining the independent generic retry
        counter.
        """
        if (spider := self.crawler.spider) is None:
            raise RuntimeError("Graph retries require an active Scrapy spider")
        # Borrow Scrapy's request-copy and retry accounting without consuming
        # the generic transport retry budget stored in retry_times.
        retry_seed = request.copy()
        generic_retry_present = "retry_times" in request.meta
        generic_retry_times = request.meta.get("retry_times")
        retry_seed.meta["retry_times"] = retry_count
        reason_code = (
            self._safe_graph_code(graph_codes[-1]) if graph_codes else str(status)
        )
        retry = get_retry_request(
            retry_seed,
            spider=spider,
            reason=f"microsoft_graph_{status}_{reason_code}",
            max_retry_times=self.max_retries,
            logger=_retry_helper_logger,
            stats_base_key="msgloom/graph_error_retry",
        )
        if retry is None:
            return None
        retry.meta[self.retry_meta_key] = int(retry.meta["retry_times"])
        if status == 503:
            retry.headers["Connection"] = "close"
        if generic_retry_present:
            retry.meta["retry_times"] = generic_retry_times
        else:
            retry.meta.pop("retry_times", None)
        return retry

    def _retry_delay(self, response, retry_count: int) -> tuple[float, str]:
        """
        Honor Retry-After seconds or HTTP date; otherwise use bounded
        exponential backoff.
        """
        raw = response.headers.get("Retry-After")
        if raw:
            text = raw.decode("ascii", errors="ignore").strip()
            try:
                return max(0.0, float(text)), "retry-after"
            except ValueError:
                try:
                    target = parsedate_to_datetime(text)
                    if target.tzinfo is None:
                        target = target.replace(tzinfo=UTC)
                    return (
                        max(0.0, (target - datetime.now(UTC)).total_seconds()),
                        "retry-after",
                    )
                except (TypeError, ValueError, OverflowError):
                    pass

        delay = min(
            self.fallback_base_seconds * (2**retry_count),
            self.fallback_max_seconds,
        )
        return float(delay), "exponential-backoff"

    @staticmethod
    def _purpose(request) -> str:
        """
        Read callback context for logs without copying message data into
        metadata.
        """
        purpose = request.cb_kwargs.get("purpose")
        return str(purpose) if purpose else "unknown"

    @staticmethod
    def _safe_graph_code(code: str) -> str:
        """Bound provider error codes before logging or using them as stat labels."""
        return code if _SAFE_GRAPH_CODE.fullmatch(code) else "other"

    @staticmethod
    def _graph_error_codes(response) -> tuple[str, ...]:
        """
        Walk both Graph inner-error spellings, preserving outer-to-inner code
        order.
        """
        if response.status < 400 or not response.body:
            return ()
        try:
            payload = response.json()
        except (ValueError, AttributeError):
            return ()
        error = payload.get("error") if isinstance(payload, dict) else None
        if not isinstance(error, dict):
            return ()
        codes: list[str] = []
        current = error
        while isinstance(current, dict):
            code = current.get("code")
            if isinstance(code, str) and code:
                codes.append(code)
            nested = current.get("innerError")
            if nested is None:
                nested = current.get("innererror")
            if not isinstance(nested, dict):
                break
            current = nested
        return tuple(codes)
