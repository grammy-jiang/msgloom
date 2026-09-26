from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import UTC, datetime
from abc import ABC, abstractmethod
from pathlib import Path
from email.utils import parsedate_to_datetime
from math import ceil
from urllib.parse import urlsplit

import msal
from scrapy.downloadermiddlewares.retry import get_retry_request
from scrapy.exceptions import NotConfigured

logger = logging.getLogger(__name__)
_GRAPH_HOST = "graph.microsoft.com"
_AUTH_RETRY_META = "_msgloom_ms_auth_retry"
_FORCE_REFRESH_META = "_msgloom_ms_force_refresh"


class MicrosoftGraphThrottleMiddleware:
    """Honor Microsoft Graph 429 Retry-After using Scrapy retry mechanics."""

    def __init__(
        self,
        *,
        max_retries: int,
        fallback_base_seconds: int,
        fallback_max_seconds: int,
        crawler,
    ) -> None:
        self.max_retries = max_retries
        self.fallback_base_seconds = fallback_base_seconds
        self.fallback_max_seconds = fallback_max_seconds
        self.crawler = crawler
        self.stats = crawler.stats

    @classmethod
    def from_crawler(cls, crawler):
        if not crawler.settings.getbool("MS_GRAPH_THROTTLE_ENABLED"):
            raise NotConfigured("Microsoft Graph throttling middleware disabled")
        return cls(
            max_retries=crawler.settings.getint("MS_GRAPH_THROTTLE_MAX_RETRIES"),
            fallback_base_seconds=crawler.settings.getint(
                "MS_GRAPH_THROTTLE_FALLBACK_BASE_SECONDS"
            ),
            fallback_max_seconds=crawler.settings.getint(
                "MS_GRAPH_THROTTLE_FALLBACK_MAX_SECONDS"
            ),
            crawler=crawler,
        )

    async def process_response(self, request, response):
        if urlsplit(request.url).hostname != _GRAPH_HOST or response.status != 429:
            return response

        self.stats.inc_value("msgloom/throttle/429_count")
        assert self.crawler.spider is not None
        previous_retry_times = int(request.meta.get("retry_times", 0))
        retry = get_retry_request(
            request,
            spider=self.crawler.spider,
            reason="microsoft_graph_429",
            max_retry_times=self.max_retries,
            stats_base_key="msgloom/throttle",
        )
        if retry is None:
            # Prevent the built-in RetryMiddleware, which runs next on the
            # response path, from starting a second independent retry loop.
            request.meta["dont_retry"] = True
            return response

        delay, source = self._retry_delay(response, previous_retry_times)
        self.stats.inc_value(f"msgloom/throttle/delay_source_count/{source}")
        self.stats.inc_value("msgloom/throttle/wait_seconds_total", count=ceil(delay))
        await asyncio.sleep(delay)
        return retry

    def _retry_delay(self, response, retry_count: int) -> tuple[float, str]:
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

        self.stats.inc_value("msgloom/throttle/missing_retry_after_count")
        delay = min(
            self.fallback_base_seconds * (2**retry_count),
            self.fallback_max_seconds,
        )
        return float(delay), "exponential-backoff"


class MicrosoftGraphDelegatedAuthMiddleware(ABC):
    """Common delegated Microsoft Graph authentication behavior."""

    auth_method = "delegated"

    def __init__(
        self,
        client_id: str,
        authority: str,
        scopes: list[str],
        token_cache_path: str,
        account_username: str = "",
        stats=None,
    ) -> None:
        self.stats = stats
        self.client_id = client_id
        self.authority = authority
        self.scopes = scopes
        self.account_username = account_username.strip()
        self.token_cache_path = Path(token_cache_path)
        self.token_cache = msal.SerializableTokenCache()
        token_cache_exists = self.token_cache_path.exists()
        if token_cache_exists:
            self.token_cache.deserialize(
                self.token_cache_path.read_text(encoding="utf-8")
            )

        self._app: msal.PublicClientApplication | None = None
        self._access_token: str | None = None
        self._expires_at = 0.0
        self._lock = asyncio.Lock()
        self._set("msgloom/auth/method", self.auth_method)
        self._set("msgloom/auth/token_cache_loaded", token_cache_exists)

    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        return cls(
            client_id=settings["MS_GRAPH_CLIENT_ID"],
            authority=settings["MS_GRAPH_AUTHORITY"],
            scopes=settings.getlist("MS_GRAPH_SCOPES"),
            token_cache_path=settings["MS_GRAPH_TOKEN_CACHE"],
            account_username=settings["MS_GRAPH_ACCOUNT_USERNAME"],
            stats=crawler.stats,
        )

    async def process_request(self, request):
        if urlsplit(request.url).hostname != _GRAPH_HOST:
            return None
        if request.headers.get("Authorization"):
            return None
        if not self.client_id:
            raise RuntimeError(
                "Set MSGLOOM_MS_CLIENT_ID to the application (client) ID of a "
                "Microsoft Entra public-client application before a live crawl."
            )

        force_refresh = bool(request.meta.pop(_FORCE_REFRESH_META, False))
        token = await self._get_access_token(force_refresh=force_refresh)
        request.headers["Authorization"] = f"Bearer {token}"
        self._inc("msgloom/auth/request_authenticated_count")
        return None

    def process_response(self, request, response):
        if urlsplit(request.url).hostname != _GRAPH_HOST:
            return response

        # Authentication state is transient. Remove it before Scrapy's native
        # filesystem HTTP cache persists request headers.
        request.headers.pop("Authorization", None)

        # A token can be revoked before its advertised expiry. Retry one 401
        # with forced silent refresh, then let a second 401 pass through.
        if response.status == 401 and not request.meta.get(_AUTH_RETRY_META, False):
            self._inc("msgloom/auth/401_retry_count")
            self._access_token = None
            self._expires_at = 0.0
            retry = request.copy()
            retry.dont_filter = True
            retry.meta[_AUTH_RETRY_META] = True
            retry.meta[_FORCE_REFRESH_META] = True
            return retry

        if response.status == 401:
            self._inc("msgloom/auth/401_final_count")
        return response

    async def _get_access_token(self, *, force_refresh: bool = False) -> str:
        now = time.time()
        if (
            not force_refresh
            and self._access_token
            and now < self._expires_at - 60
        ):
            self._inc("msgloom/auth/memory_token_hit_count")
            return self._access_token

        async with self._lock:
            now = time.time()
            if (
                not force_refresh
                and self._access_token
                and now < self._expires_at - 60
            ):
                self._inc("msgloom/auth/memory_token_hit_count")
                return self._access_token

            result = await asyncio.to_thread(
                self._acquire_access_token,
                force_refresh=force_refresh,
            )
            self._access_token = result["access_token"]
            self._expires_at = now + int(result.get("expires_in", 300))
            return self._access_token

    def _acquire_access_token(self, *, force_refresh: bool = False) -> dict:
        app = self._application()
        accounts = self._cached_accounts(app)
        result = None

        if accounts:
            self._inc("msgloom/auth/silent_attempt_count")
            result = app.acquire_token_silent(
                self.scopes,
                account=accounts[0],
                force_refresh=force_refresh,
            )
            if result and "access_token" in result:
                self._inc("msgloom/auth/silent_success_count")

        if not result:
            self._inc("msgloom/auth/user_interaction_count")
            result = self._acquire_interactive_token(app)

        if "access_token" not in result:
            error = result.get("error", "authentication_failed")
            description = result.get("error_description", "No access token returned")
            raise RuntimeError(f"Microsoft authentication failed: {error}: {description}")

        self._save_token_cache()
        return result

    @abstractmethod
    def _acquire_interactive_token(
        self, app: msal.PublicClientApplication
    ) -> dict:
        """Acquire a delegated token when silent MSAL acquisition is unavailable."""

    def _cached_accounts(self, app: msal.PublicClientApplication) -> list[dict]:
        if self.account_username:
            return app.get_accounts(username=self.account_username)

        accounts = app.get_accounts()
        if len(accounts) > 1:
            usernames = ", ".join(
                sorted(
                    account.get("username", "<unknown>")
                    for account in accounts
                )
            )
            raise RuntimeError(
                "Multiple Microsoft accounts exist in the token cache. Set "
                f"MSGLOOM_MS_USERNAME to select one account. Cached accounts: {usernames}"
            )
        return accounts

    def _application(self) -> msal.PublicClientApplication:
        if self._app is None:
            self._app = msal.PublicClientApplication(
                client_id=self.client_id,
                authority=self.authority,
                token_cache=self.token_cache,
            )
        return self._app

    def _save_token_cache(self) -> None:
        if not self.token_cache.has_state_changed:
            return
        self.token_cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_cache_path.write_text(self.token_cache.serialize(), encoding="utf-8")
        os.chmod(self.token_cache_path, 0o600)
        self._inc("msgloom/auth/token_cache_save_count")

    def _inc(self, key: str, count: int = 1) -> None:
        if self.stats is not None:
            self.stats.inc_value(key, count=count)

    def _set(self, key: str, value) -> None:
        if self.stats is not None:
            self.stats.set_value(key, value)


class MicrosoftGraphDeviceCodeAuthMiddleware(MicrosoftGraphDelegatedAuthMiddleware):
    """Delegated Microsoft Graph authentication for headless/CLI environments."""

    auth_method = "device_code"

    def _acquire_interactive_token(
        self, app: msal.PublicClientApplication
    ) -> dict:
        flow = app.initiate_device_flow(scopes=self.scopes)
        if "user_code" not in flow:
            raise RuntimeError(
                f"Unable to start Microsoft device-code authentication: {flow}"
            )
        logger.warning("Microsoft sign-in required: %s", flow["message"])
        self._inc("msgloom/auth/device_code_count")
        return app.acquire_token_by_device_flow(flow)


class MicrosoftGraphInteractiveAuthMiddleware(MicrosoftGraphDelegatedAuthMiddleware):
    """Delegated Microsoft Graph authentication through browser auth code + PKCE."""

    auth_method = "interactive"

    def _acquire_interactive_token(
        self, app: msal.PublicClientApplication
    ) -> dict:
        self._inc("msgloom/auth/browser_interactive_count")
        return app.acquire_token_interactive(
            scopes=self.scopes,
            login_hint=self.account_username or None,
        )
