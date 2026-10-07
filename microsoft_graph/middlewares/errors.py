"""Provider-specific retries layered on Scrapy's retry helpers."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from math import ceil
from urllib.parse import urlsplit

from scrapy.downloadermiddlewares.retry import get_retry_request
from scrapy.exceptions import NotConfigured

from microsoft_graph.protocol import GraphError, GraphProtocolError
from microsoft_graph.request import graph_host, graph_operation
from microsoft_graph.stats import stats_prefix

logger = logging.getLogger(__name__)
_SAFE_GRAPH_CODE = re.compile(r"[A-Za-z0-9_.-]{1,64}")
# Scrapy's retry helper formats the full Request repr. Use an unregistered
# logger above CRITICAL so helper messages cannot expose Graph URLs; the
# middleware emits its own bounded replacement records.
_retry_helper_logger = logging.Logger(  # noqa: LOG001
    "microsoft_graph.retry_helper.silent",
    level=logging.CRITICAL + 1,
)


class MicrosoftGraphErrorMiddleware:
    """
    Handle only Microsoft Graph error cases with provider-specific retry
    semantics.
    """

    retry_meta_key = "_microsoft_graph_error_retry"
    default_stats_prefix = "microsoft_graph"
    default_retry_http_codes = (429, 503)
    logger = logger

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
        self.stats_prefix = stats_prefix(
            crawler.settings, default=self.default_stats_prefix
        )
        self.graph_host = graph_host(crawler)
        # Consumers can retain counters serialized in existing JOBDIRs.
        self.retry_meta_key = crawler.settings.get(
            "MS_GRAPH_ERROR_RETRY_META_KEY", self.retry_meta_key
        )
        self.retry_http_codes = {
            int(code)
            for code in crawler.settings.getlist(
                "MS_GRAPH_ERROR_RETRY_HTTP_CODES", self.default_retry_http_codes
            )
        }
        self.retry_409_codes = {
            code.casefold()
            for code in crawler.settings.getlist(
                "MS_GRAPH_ERROR_RETRY_409_CODES", ["Directory_ConcurrencyViolation"]
            )
        }

    @classmethod
    def from_crawler(cls, crawler):
        """
        Read the final Graph retry/backoff settings or disable this component.
        """
        if not crawler.settings.getbool("MS_GRAPH_ERROR_MIDDLEWARE_ENABLED", True):
            raise NotConfigured("Microsoft Graph error middleware disabled")
        return cls(
            max_retries=crawler.settings.getint("MS_GRAPH_ERROR_MAX_RETRIES", 8),
            fallback_base_seconds=crawler.settings.getint(
                "MS_GRAPH_ERROR_FALLBACK_BASE_SECONDS", 1
            ),
            fallback_max_seconds=crawler.settings.getint(
                "MS_GRAPH_ERROR_FALLBACK_MAX_SECONDS", 60
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
        if urlsplit(request.url).hostname != self.graph_host:
            return response
        if request.meta.get("dont_retry", False):
            return response

        graph_codes = self._graph_error_codes(response)
        if not self._should_retry(response.status, graph_codes):
            if response.status >= 400:
                self.logger.debug(
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
                f"{self.stats_prefix}graph_error/exhausted_purpose_count/{purpose}"
            )
            self.stats.inc_value(
                f"{self.stats_prefix}graph_error/exhausted_status_count/{response.status}"
            )
            self.logger.error(
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
        self.stats.inc_value(
            f"{self.stats_prefix}graph_error/retry_purpose_count/{purpose}"
        )
        self.stats.inc_value(
            f"{self.stats_prefix}graph_error/status_count/{response.status}"
        )
        self.stats.inc_value(
            f"{self.stats_prefix}graph_error/delay_source_count/{source}"
        )
        self.stats.inc_value(
            f"{self.stats_prefix}graph_error/wait_seconds_total", count=ceil(delay)
        )
        self.stats.max_value(f"{self.stats_prefix}graph_error/max_delay_seconds", delay)
        self.logger.warning(
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

    def _should_retry(self, status: int, graph_codes: tuple[str, ...]) -> bool:
        """
        Retry configured HTTP statuses and provider-specific 409 codes.
        """
        if status in self.retry_http_codes:
            return True
        if status == 409:
            return any(code.casefold() in self.retry_409_codes for code in graph_codes)
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
            stats_base_key=f"{self.stats_prefix}graph_error_retry",
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

    _purpose = staticmethod(graph_operation)

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
        try:
            return GraphError.from_payload(payload).codes
        except GraphProtocolError:
            return ()
