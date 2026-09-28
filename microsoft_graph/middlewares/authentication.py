"""Attach crawler-scoped Microsoft Graph delegated tokens to requests."""

from __future__ import annotations

import logging
from urllib.parse import urlsplit

from scrapy.exceptions import IgnoreRequest, NotConfigured

from .. import GRAPH_HOST
from ..auth.session import (
    MicrosoftGraphAuthSession,
)
from ..request import graph_host, graph_operation
from ..stats import stats_prefix

logger = logging.getLogger(__name__)
_AUTH_RETRY_META = "_microsoft_graph_auth_retry"
_FORCE_REFRESH_META = "_microsoft_graph_force_refresh"


class MicrosoftGraphDelegatedAuthMiddleware:
    """
    Use the crawler auth session for its Graph service-root hostname.

    Host scoping does not configure the token authority or scopes.
    """

    auth_method = "delegated"

    def __init__(
        self,
        session: MicrosoftGraphAuthSession,
        stats=None,
        *,
        host: str = GRAPH_HOST,
        stats_namespace: str = "microsoft_graph",
        retry_meta_key: str = _AUTH_RETRY_META,
        force_refresh_meta_key: str = _FORCE_REFRESH_META,
    ) -> None:
        """Borrow crawler-scoped auth state; do not own a second MSAL cache."""
        self.session = session
        self.stats = stats
        self.scopes = session.scopes
        self.graph_host = host
        self.stats_prefix = stats_prefix({"MS_GRAPH_STATS_PREFIX": stats_namespace})
        self.retry_meta_key = retry_meta_key
        self.force_refresh_meta_key = force_refresh_meta_key

    @classmethod
    def from_crawler(cls, crawler):
        """Enable only the middleware matching the selected delegated flow."""
        session = MicrosoftGraphAuthSession.from_crawler(crawler)
        if session.auth_method != cls.auth_method:
            raise NotConfigured
        # Settings keep consumer retry keys stable across JOBDIR resume.
        return cls(
            session,
            stats=crawler.stats,
            host=graph_host(crawler),
            stats_namespace=stats_prefix(crawler.settings),
            retry_meta_key=crawler.settings.get(
                "MS_GRAPH_AUTH_RETRY_META_KEY", _AUTH_RETRY_META
            ),
            force_refresh_meta_key=crawler.settings.get(
                "MS_GRAPH_AUTH_FORCE_REFRESH_META_KEY", _FORCE_REFRESH_META
            ),
        )

    async def process_request(self, request):
        """Attach only a token owned by the source-pinned account."""
        parsed = urlsplit(request.url)
        if parsed.hostname != self.graph_host:
            return
        if parsed.scheme.lower() != "https":
            request.headers.pop("Authorization", None)
            self._inc("insecure_scheme_blocked_count")
            raise IgnoreRequest("Refusing non-HTTPS Microsoft Graph request")
        if (
            request.headers.get("Authorization")
            and self.session.account_binding is None
        ):
            return
        force_refresh = bool(request.meta.pop(self.force_refresh_meta_key, False))
        token = await self.session.get_access_token(force_refresh=force_refresh)
        if not isinstance(token, str):
            raise TypeError(
                "Microsoft authentication returned a non-string access token"
            )
        request.headers["Authorization"] = f"Bearer {token}"
        self._inc("request_authenticated_count")

    def process_exception(self, request, exception):
        """Strip bearer credentials before native retry/error recovery."""
        if urlsplit(request.url).hostname != self.graph_host:
            return
        if request.headers.pop("Authorization", None) is not None:
            self._inc("credential_stripped_exception_count")
        return

    def process_response(self, request, response):
        """Strip credentials before cache storage and retry one rejected token."""
        if urlsplit(request.url).hostname != self.graph_host:
            return response
        request.headers.pop("Authorization", None)

        if response.status == 401 and not request.meta.get(self.retry_meta_key, False):
            self._inc("401_retry_count")
            logger.info(
                "Microsoft Graph access token rejected; retrying once with "
                "forced refresh: purpose=%s",
                graph_operation(request),
            )
            self.session.clear_memory_token()
            retry = request.copy()
            retry.dont_filter = True
            retry.meta[self.retry_meta_key] = True
            retry.meta[self.force_refresh_meta_key] = True
            return retry

        if response.status == 401:
            self._inc("401_final_count")
            logger.error(
                "Microsoft Graph authentication failed after refresh retry: purpose=%s",
                graph_operation(request),
            )
        return response

    def _inc(self, key: str, count: int = 1) -> None:
        """Keep transport counters separate from session decisions."""
        if self.stats is not None:
            self.stats.inc_value(f"{self.stats_prefix}auth/{key}", count=count)


class MicrosoftGraphDeviceCodeAuthMiddleware(MicrosoftGraphDelegatedAuthMiddleware):
    """Downloader adapter for the device-code auth session."""

    auth_method = "device_code"


class MicrosoftGraphInteractiveAuthMiddleware(MicrosoftGraphDelegatedAuthMiddleware):
    """Downloader adapter for the browser-interactive auth session."""

    auth_method = "interactive"
