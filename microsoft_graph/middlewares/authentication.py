"""Attach crawler-scoped Microsoft Graph delegated tokens to requests."""

from __future__ import annotations

import logging
from urllib.parse import urlsplit

from scrapy.exceptions import IgnoreRequest, NotConfigured

from .. import GRAPH_HOST
from ..auth.session import (
    MicrosoftGraphAuthSession,
)

logger = logging.getLogger(__name__)
_AUTH_RETRY_META = "_msgloom_ms_auth_retry"
_FORCE_REFRESH_META = "_msgloom_ms_force_refresh"


class MicrosoftGraphDelegatedAuthMiddleware:
    """Use the crawler auth session at the downloader boundary."""

    auth_method = "delegated"

    def __init__(self, session: MicrosoftGraphAuthSession, stats=None) -> None:
        """Borrow crawler-scoped auth state; do not own a second MSAL cache."""
        self.session = session
        self.stats = stats
        self.scopes = session.scopes

    @classmethod
    def from_crawler(cls, crawler):
        """Enable only the middleware matching the selected delegated flow."""
        session = MicrosoftGraphAuthSession.from_crawler(crawler)
        if session.auth_method != cls.auth_method:
            raise NotConfigured
        return cls(session, stats=crawler.stats)

    async def process_request(self, request):
        """Attach only a token owned by the source-pinned account."""
        parsed = urlsplit(request.url)
        if parsed.hostname != GRAPH_HOST:
            return
        if parsed.scheme.lower() != "https":
            request.headers.pop("Authorization", None)
            self._inc("msgloom/auth/insecure_scheme_blocked_count")
            raise IgnoreRequest("Refusing non-HTTPS Microsoft Graph request")
        if (
            request.headers.get("Authorization")
            and self.session.account_binding is None
        ):
            return
        force_refresh = bool(request.meta.pop(_FORCE_REFRESH_META, False))
        token = await self.session.get_access_token(force_refresh=force_refresh)
        if not isinstance(token, str):
            raise TypeError(
                "Microsoft authentication returned a non-string access token"
            )
        request.headers["Authorization"] = f"Bearer {token}"
        self._inc("msgloom/auth/request_authenticated_count")

    def process_exception(self, request, exception):
        """Strip bearer credentials before native retry/error recovery."""
        if urlsplit(request.url).hostname != GRAPH_HOST:
            return
        if request.headers.pop("Authorization", None) is not None:
            self._inc("msgloom/auth/credential_stripped_exception_count")
        return

    def process_response(self, request, response):
        """Strip credentials before cache storage and retry one rejected token."""
        if urlsplit(request.url).hostname != GRAPH_HOST:
            return response
        request.headers.pop("Authorization", None)

        if response.status == 401 and not request.meta.get(_AUTH_RETRY_META, False):
            self._inc("msgloom/auth/401_retry_count")
            logger.info(
                "Microsoft Graph access token rejected; retrying once with "
                "forced refresh: purpose=%s",
                request.cb_kwargs.get("purpose", "unknown"),
            )
            self.session.clear_memory_token()
            retry = request.copy()
            retry.dont_filter = True
            retry.meta[_AUTH_RETRY_META] = True
            retry.meta[_FORCE_REFRESH_META] = True
            return retry

        if response.status == 401:
            self._inc("msgloom/auth/401_final_count")
            logger.error(
                "Microsoft Graph authentication failed after refresh retry: purpose=%s",
                request.cb_kwargs.get("purpose", "unknown"),
            )
        return response

    def _inc(self, key: str, count: int = 1) -> None:
        """Keep transport counters separate from session decisions."""
        if self.stats is not None:
            self.stats.inc_value(key, count=count)


class MicrosoftGraphDeviceCodeAuthMiddleware(MicrosoftGraphDelegatedAuthMiddleware):
    """Downloader adapter for the device-code auth session."""

    auth_method = "device_code"


class MicrosoftGraphInteractiveAuthMiddleware(MicrosoftGraphDelegatedAuthMiddleware):
    """Downloader adapter for the browser-interactive auth session."""

    auth_method = "interactive"
