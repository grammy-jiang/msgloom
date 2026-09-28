"""Microsoft Graph request correlation and diagnostic logging."""

from __future__ import annotations

import logging
from urllib.parse import urlsplit
from uuid import uuid4

from microsoft_graph.scrapy.request import graph_host, graph_operation
from microsoft_graph.scrapy.stats import stats_prefix

logger = logging.getLogger(__name__)


class MicrosoftGraphDiagnosticsMiddleware:
    """
    Add Graph correlation IDs plus per-attempt protocol diagnostics.

    This middleware runs after authentication on request and before
    authentication on response so 401 exchanges that become auth retries are
    still observable. Counters describe transport attempts, not business
    completion.
    """

    client_request_id_meta = "_microsoft_graph_client_request_id"
    default_stats_prefix = "microsoft_graph"
    logger = logger

    def __init__(self, crawler) -> None:
        """Keep crawler resources so logs and stats use the active spider."""
        self.crawler = crawler
        self.stats = crawler.stats
        self.stats_prefix = stats_prefix(
            crawler.settings, default=self.default_stats_prefix
        )
        self.graph_host = graph_host(crawler)

    @classmethod
    def from_crawler(cls, crawler):
        """Bind protocol diagnostics to the active crawler."""
        return cls(crawler)

    _purpose = staticmethod(graph_operation)

    def process_request(self, request):
        """Assign a fresh client request ID and count each Graph attempt."""
        if urlsplit(request.url).hostname != self.graph_host:
            return
        purpose = self._purpose(request)
        client_request_id = str(uuid4())
        request.headers["client-request-id"] = client_request_id
        request.meta[self.client_request_id_meta] = client_request_id
        self.stats.inc_value(f"{self.stats_prefix}graph/request_count")
        self.stats.inc_value(
            f"{self.stats_prefix}graph/request_purpose_count/{purpose}"
        )
        self.logger.debug(
            "Microsoft Graph request: method=%s purpose=%s client_request_id=%s",
            request.method,
            purpose,
            client_request_id,
            extra={"spider": self.crawler.spider},
        )

    def process_response(self, request, response):
        """Count and log a Graph response without payloads or request URLs."""
        if urlsplit(request.url).hostname != self.graph_host:
            return response
        purpose = self._purpose(request)
        if "cached" in response.flags:
            self.stats.inc_value(f"{self.stats_prefix}graph/cache_replay_count")
            self.stats.inc_value(
                f"{self.stats_prefix}graph/cache_replay_purpose_count/{purpose}"
            )
            self.logger.debug(
                "Microsoft Graph cached response: status=%s purpose=%s",
                response.status,
                purpose,
                extra={"spider": self.crawler.spider},
            )
            return response
        self.stats.inc_value(f"{self.stats_prefix}graph/response_count")
        self.stats.inc_value(
            f"{self.stats_prefix}graph/response_purpose_count/{purpose}"
        )
        self.stats.inc_value(
            f"{self.stats_prefix}graph/response_status_count/{response.status}"
        )
        self.stats.inc_value(
            f"{self.stats_prefix}graph/response_purpose_status_count/{purpose}/{response.status}"
        )

        server_request_id = response.headers.get("request-id")
        if isinstance(server_request_id, bytes):
            server_request_id = server_request_id.decode("ascii", errors="replace")
        if not server_request_id:
            self.stats.inc_value(
                f"{self.stats_prefix}graph/response_missing_request_id_count"
            )
        self.logger.debug(
            "Microsoft Graph response: status=%s purpose=%s "
            "client_request_id=%s request_id=%s",
            response.status,
            purpose,
            request.meta.get(self.client_request_id_meta),
            server_request_id,
            extra={"spider": self.crawler.spider},
        )
        return response

    def process_exception(self, request, exception):
        """Count download-handler failures that have no HTTP response."""
        if urlsplit(request.url).hostname != self.graph_host:
            return
        purpose = self._purpose(request)
        error_type = type(exception).__name__
        self.stats.inc_value(f"{self.stats_prefix}graph/exception_count")
        self.stats.inc_value(
            f"{self.stats_prefix}graph/exception_purpose_count/{purpose}"
        )
        self.stats.inc_value(
            f"{self.stats_prefix}graph/exception_type_count/{error_type}"
        )
        self.logger.debug(
            "Microsoft Graph transport exception: purpose=%s error_type=%s",
            purpose,
            error_type,
            extra={"spider": self.crawler.spider},
        )
