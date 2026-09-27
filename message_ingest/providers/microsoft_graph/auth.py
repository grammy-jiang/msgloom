"""Delegated Microsoft Graph authentication with MSAL."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from abc import ABC, abstractmethod
from pathlib import Path
from urllib.parse import urlsplit

import msal
from scrapy.exceptions import NotConfigured

from message_ingest.middlewares import GRAPH_HOST

logger = logging.getLogger(__name__)
_AUTH_RETRY_META = "_msgloom_ms_auth_retry"
_FORCE_REFRESH_META = "_msgloom_ms_force_refresh"


class MicrosoftGraphDelegatedAuthMiddleware(ABC):
    """
    Attach delegated tokens only to Microsoft Graph requests.

    The async lock serializes MSAL access. Blocking login runs in a worker
    thread; credentials are removed on response before native HTTP cache writes
    headers. One authentication refresh retry has its own budget, separate from
    Graph errors.
    """

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
        """
        Load the selected account's token cache and defer MSAL application
        construction.
        """
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
        """
        Disable unselected authentication methods using Scrapy's
        :exc:`~scrapy.exceptions.NotConfigured` contract.
        """
        settings = crawler.settings
        if not settings.getbool("MS_GRAPH_AUTH_ENABLED"):
            raise NotConfigured("Microsoft Graph authentication disabled")
        selected = settings.get("MS_GRAPH_AUTH_METHOD", "device_code").strip().lower()
        if selected != cls.auth_method:
            raise NotConfigured
        scopes = settings.getlist("MS_GRAPH_SCOPES")
        if not scopes:
            raise RuntimeError(
                "Microsoft Graph resource must configure MS_GRAPH_SCOPES"
            )
        return cls(
            client_id=settings["MS_GRAPH_CLIENT_ID"],
            authority=settings["MS_GRAPH_AUTHORITY"],
            scopes=scopes,
            token_cache_path=settings["MS_GRAPH_TOKEN_CACHE"],
            account_username=settings["MS_GRAPH_ACCOUNT_USERNAME"],
            stats=crawler.stats,
        )

    async def process_request(self, request):
        """
        Respect an existing ``Authorization`` header and otherwise obtain a
        Graph-only token.
        """
        if urlsplit(request.url).hostname != GRAPH_HOST:
            return
        if request.headers.get("Authorization"):
            return
        if not self.client_id:
            raise RuntimeError(
                "Set MSGLOOM_MS_CLIENT_ID to the application (client) ID of a "
                "Microsoft Entra public-client application before a live crawl."
            )

        force_refresh = bool(request.meta.pop(_FORCE_REFRESH_META, False))
        token = await self._get_access_token(force_refresh=force_refresh)
        request.headers["Authorization"] = f"Bearer {token}"
        self._inc("msgloom/auth/request_authenticated_count")

    def process_response(self, request, response):
        """
        Remove transient credentials and allow exactly one forced-refresh
        replay of a 401.
        """
        if urlsplit(request.url).hostname != GRAPH_HOST:
            return response

        # Authentication state is transient. Remove it before Scrapy's native
        # filesystem HTTP cache persists request headers.
        request.headers.pop("Authorization", None)

        # A token can be revoked before its advertised expiry. Retry one 401
        # with forced silent refresh, then let a second 401 pass through.
        if response.status == 401 and not request.meta.get(_AUTH_RETRY_META, False):
            self._inc("msgloom/auth/401_retry_count")
            logger.info(
                "Microsoft Graph access token rejected; retrying once with forced refresh: purpose=%s",
                request.cb_kwargs.get("purpose", "unknown"),
            )
            self._access_token = None
            self._expires_at = 0.0
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

    async def _get_access_token(self, *, force_refresh: bool = False) -> str:
        """
        Reuse an unexpired token or acquire one under the async lock.

        Check again after taking the lock: another request may already have
        refreshed it. The 60-second margin avoids scheduling requests with a
        token near expiry.
        """
        now = time.time()
        if not force_refresh and self._access_token and now < self._expires_at - 60:
            self._inc("msgloom/auth/memory_token_hit_count")
            return self._access_token

        async with self._lock:
            now = time.time()
            if not force_refresh and self._access_token and now < self._expires_at - 60:
                self._inc("msgloom/auth/memory_token_hit_count")
                return self._access_token

            result = await asyncio.to_thread(
                self._acquire_access_token,
                force_refresh=force_refresh,
            )
            access_token = result["access_token"]
            if not isinstance(access_token, str):
                raise TypeError(
                    "Microsoft authentication returned a non-string access token"
                )
            self._access_token = access_token
            self._expires_at = now + int(result.get("expires_in", 300))
            return access_token

    def _acquire_access_token(self, *, force_refresh: bool = False) -> dict:
        """
        Try the selected cached account before requesting user interaction.

        Persist MSAL cache changes only after successful acquisition.
        Authentication errors propagate and never result in an empty
        ``Authorization`` header.
        """
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
                logger.debug("Microsoft token acquired silently from MSAL cache")

        if not result:
            self._inc("msgloom/auth/user_interaction_count")
            result = self._acquire_interactive_token(app)

        if "access_token" not in result:
            error = result.get("error", "authentication_failed")
            description = result.get("error_description", "No access token returned")
            raise RuntimeError(
                f"Microsoft authentication failed: {error}: {description}"
            )

        self._save_token_cache()
        return result

    @abstractmethod
    def _acquire_interactive_token(self, app: msal.PublicClientApplication) -> dict:
        """
        Acquire a delegated token when silent MSAL acquisition is unavailable.
        """

    def _cached_accounts(self, app: msal.PublicClientApplication) -> list[dict]:
        """
        Require explicit account selection when the cache contains multiple
        users.
        """
        if self.account_username:
            return app.get_accounts(username=self.account_username)

        accounts = app.get_accounts()
        if len(accounts) > 1:
            usernames = ", ".join(
                sorted(account.get("username", "<unknown>") for account in accounts)
            )
            raise RuntimeError(
                "Multiple Microsoft accounts exist in the token cache. Set "
                f"MSGLOOM_MS_USERNAME to select one account. Cached accounts: {usernames}"
            )
        return accounts

    def _application(self) -> msal.PublicClientApplication:
        """
        Lazily construct one MSAL client after the Graph request requires
        authentication.
        """
        if self._app is None:
            self._app = msal.PublicClientApplication(
                client_id=self.client_id,
                authority=self.authority,
                token_cache=self.token_cache,
            )
        return self._app

    def _save_token_cache(self) -> None:
        """
        Write only a changed MSAL cache and restrict access to its credentials.
        """
        if not self.token_cache.has_state_changed:
            return
        self.token_cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_cache_path.write_text(self.token_cache.serialize(), encoding="utf-8")
        os.chmod(self.token_cache_path, 0o600)
        self._inc("msgloom/auth/token_cache_save_count")

    def _inc(self, key: str, count: int = 1) -> None:
        """Keep optional statistics separate from authentication decisions."""
        if self.stats is not None:
            self.stats.inc_value(key, count=count)

    def _set(self, key: str, value) -> None:
        """
        Publish optional startup diagnostics without requiring a stats
        collector.
        """
        if self.stats is not None:
            self.stats.set_value(key, value)


class MicrosoftGraphDeviceCodeAuthMiddleware(MicrosoftGraphDelegatedAuthMiddleware):
    """
    Delegated Microsoft Graph authentication for headless/CLI environments.
    """

    auth_method = "device_code"

    def _acquire_interactive_token(self, app: msal.PublicClientApplication) -> dict:
        """
        Wait for device-code approval in the worker thread used by token
        acquisition.
        """
        flow = app.initiate_device_flow(scopes=self.scopes)
        if "user_code" not in flow:
            raise RuntimeError(
                f"Unable to start Microsoft device-code authentication: {flow}"
            )
        logger.warning("Microsoft sign-in required: %s", flow["message"])
        self._inc("msgloom/auth/device_code_count")
        return app.acquire_token_by_device_flow(flow)


class MicrosoftGraphInteractiveAuthMiddleware(MicrosoftGraphDelegatedAuthMiddleware):
    """
    Delegated Microsoft Graph authentication through browser auth code + PKCE.
    """

    auth_method = "interactive"

    def _acquire_interactive_token(self, app: msal.PublicClientApplication) -> dict:
        """
        Open browser authorization with the configured account as a login hint.
        """
        self._inc("msgloom/auth/browser_interactive_count")
        return app.acquire_token_interactive(
            scopes=self.scopes,
            login_hint=self.account_username or None,
        )
