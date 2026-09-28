"""Crawler-scoped Microsoft Graph delegated authentication state."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import msal
from scrapy.exceptions import NotConfigured

from .accounts import (
    MicrosoftGraphAuthError,
    account_key,
    account_key_set,
    all_accounts,
    find_account_by_key,
    find_bound_account,
    select_after_interaction,
    select_unbound_cached_account,
)
from .binding import MicrosoftGraphAccountBinding
from .management import (
    MICROSOFT_GRAPH_CLI_CLIENT_ID,
    classify_client_id,
)

logger = logging.getLogger(__name__)
_SESSION_ATTR = "_msgloom_microsoft_graph_auth_session"
_SAFE_ERROR_CODE = re.compile(r"[A-Za-z0-9_.-]{1,96}")


class MicrosoftGraphAuthSession:
    """Own one crawler MSAL cache, pinned account, and access token."""

    def __init__(
        self,
        *,
        client_id: str,
        authority: str,
        scopes: list[str],
        token_cache_path: str,
        auth_method: str,
        account_username: str,
        allow_interactive: bool,
        account_binding: MicrosoftGraphAccountBinding | None = None,
        stats=None,
    ) -> None:
        """Load cache state while deferring application construction."""
        self.client_id = client_id
        self.application_mode, self.application_name = classify_client_id(client_id)
        self.authority = authority
        self.scopes = scopes
        self.auth_method = auth_method
        self.account_username = account_username.strip()
        self.allow_interactive = allow_interactive
        self.account_binding = account_binding
        self.stats = stats
        self.token_cache_path = Path(token_cache_path)
        self.token_cache = msal.SerializableTokenCache()
        cache_exists = self.token_cache_path.exists()
        if cache_exists:
            self.token_cache.deserialize(
                self.token_cache_path.read_text(encoding="utf-8")
            )
        self._app: msal.PublicClientApplication | None = None
        self._pinned_account: dict[str, Any] | None = None
        self._pinned_account_key: str | None = None
        self._access_token: str | None = None
        self._expires_at = 0.0
        self._account_binding_ready = account_binding is None
        self._lock = asyncio.Lock()
        self._set("msgloom/auth/method", auth_method)
        self._set("msgloom/auth/application_mode", self.application_mode)
        self._set("msgloom/auth/token_cache_loaded", cache_exists)
        logger.info(
            "Microsoft authentication configured: application_mode=%s "
            "application=%s auth_method=%s token_cache=%s",
            self.application_mode,
            self.application_name,
            self.auth_method,
            "present" if cache_exists else "empty",
        )
        if self.application_mode == "development":
            logger.warning(
                "Microsoft development authentication is active. Consent "
                "screens will identify %s rather than msgloom. Use this client "
                "for development/testing only. Run 'scrapy "
                "microsoft auth status' for details.",
                self.application_name,
            )

    @classmethod
    def from_crawler(cls, crawler):
        """Return the auth session shared by startup gate and middleware."""
        if (existing := getattr(crawler, _SESSION_ATTR, None)) is not None:
            return existing
        settings = crawler.settings
        if not settings.getbool("MS_GRAPH_AUTH_ENABLED"):
            raise NotConfigured("Microsoft Graph authentication disabled")
        method = settings.get("MS_GRAPH_AUTH_METHOD", "device_code").strip().lower()
        if method not in {"device_code", "interactive"}:
            raise NotConfigured("Microsoft Graph delegated authentication disabled")
        scopes = settings.getlist("MS_GRAPH_SCOPES")
        if not scopes:
            raise RuntimeError(
                "Microsoft Graph resource must configure MS_GRAPH_SCOPES"
            )
        session = cls(
            client_id=settings["MS_GRAPH_CLIENT_ID"],
            authority=settings["MS_GRAPH_AUTHORITY"],
            scopes=scopes,
            token_cache_path=settings["MS_GRAPH_TOKEN_CACHE"],
            auth_method=method,
            account_username=settings["MS_GRAPH_ACCOUNT_USERNAME"],
            allow_interactive=settings.getbool("MS_GRAPH_AUTH_ALLOW_INTERACTIVE"),
            account_binding=None,
            stats=crawler.stats,
        )
        setattr(crawler, _SESSION_ATTR, session)
        return session

    @property
    def account_binding_ready(self) -> bool:
        """Return whether an attached application account binding is verified."""
        return self._account_binding_ready

    def attach_account_binding(
        self,
        binding: MicrosoftGraphAccountBinding,
    ) -> None:
        """Attach one application binding before the first token is used."""
        if self._pinned_account is not None or self._access_token is not None:
            raise MicrosoftGraphAuthError(
                "Cannot attach a Microsoft account binding after token use"
            )
        if self.account_binding is not None and self.account_binding is not binding:
            raise MicrosoftGraphAuthError(
                "A different Microsoft account binding is already attached"
            )
        self.account_binding = binding
        self._account_binding_ready = False

    async def establish_account_binding(self) -> None:
        """Resolve, authenticate, bind, and pin one application account."""
        if self.account_binding is None:
            self._account_binding_ready = True
            return
        if self._account_binding_ready:
            return
        self._require_client_id()
        async with self._lock:
            if self._account_binding_ready:
                return
            binding = self.account_binding
            if binding is None:
                raise MicrosoftGraphAuthError(
                    "Microsoft account binding disappeared during startup"
                )
            async with binding.write_lock:
                account, result = await asyncio.to_thread(
                    self._establish_bound_session_sync
                )
            self._pin(account, result)
            self._account_binding_ready = True

    async def get_access_token(self, *, force_refresh: bool = False) -> str:
        """Return a token that belongs to the pinned account."""
        now = time.time()
        if self._memory_token_valid(now, force_refresh):
            self._inc("msgloom/auth/memory_token_hit_count")
            return self._access_token or ""
        async with self._lock:
            now = time.time()
            if self._memory_token_valid(now, force_refresh):
                self._inc("msgloom/auth/memory_token_hit_count")
                return self._access_token or ""
            if self.account_binding is not None and not self._account_binding_ready:
                raise MicrosoftGraphAuthError(
                    "Microsoft Graph account binding gate has not completed"
                )
            if self._pinned_account is None:
                account, result = await asyncio.to_thread(
                    self._establish_unbound_session_sync,
                    force_refresh,
                )
            else:
                account = self._pinned_account
                result = await asyncio.to_thread(
                    self._token_for_pinned_account_sync, force_refresh
                )
            self._pin(account, result)
            return self._access_token or ""

    def clear_memory_token(self) -> None:
        """Force the next request to reacquire for the pinned account."""
        self._access_token = None
        self._expires_at = 0.0

    def _establish_bound_session_sync(
        self,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Pin a token-owning account and persist/verify its application binding."""
        binding = self.account_binding
        if binding is None:
            raise MicrosoftGraphAuthError("Microsoft account binding is unavailable")
        app = self._application()
        before = all_accounts(app)
        if binding.has_binding():
            account = find_bound_account(before, binding)
            result = self._silent_result(app, account) if account else None
            if not self._has_token(result):
                self._require_interaction(result)
                self._perform_interaction(app)
                account = find_bound_account(all_accounts(app), binding)
                if account is None:
                    raise MicrosoftGraphAuthError(
                        "Interactive sign-in did not restore the account "
                        "bound to this source"
                    )
                result = self._require_silent_token(app, account)
        else:
            account = select_unbound_cached_account(app, before, self.account_username)
            result = self._silent_result(app, account) if account else None
            if not self._has_token(result):
                self._require_interaction(result)
                before_keys = account_key_set(before)
                self._perform_interaction(app)
                account = select_after_interaction(
                    app, before_keys, self.account_username
                )
                result = self._require_silent_token(app, account)
        if account is None or result is None:
            raise MicrosoftGraphAuthError("No pinned Microsoft account/token")
        binding.bind_or_verify_account_key(account_key(account))
        self._save_token_cache()
        return account, result

    def _establish_unbound_session_sync(
        self, force_refresh: bool = False
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Authenticate without persistence, honoring a requested refresh."""
        self._require_client_id()
        app = self._application()
        before = all_accounts(app)
        account = select_unbound_cached_account(app, before, self.account_username)
        result = (
            self._silent_result(
                app,
                account,
                force_refresh=force_refresh,
            )
            if account
            else None
        )
        if not self._has_token(result):
            self._require_interaction(result)
            before_keys = account_key_set(before)
            self._perform_interaction(app)
            account = select_after_interaction(app, before_keys, self.account_username)
            result = self._require_silent_token(app, account)
        if account is None or result is None:
            raise MicrosoftGraphAuthError("Unable to select a Microsoft account")
        self._save_token_cache()
        return account, result

    def _token_for_pinned_account_sync(self, force_refresh: bool) -> dict[str, Any]:
        """Refresh only the pinned account, optionally reauthenticating it."""
        if self._pinned_account is None or self._pinned_account_key is None:
            raise MicrosoftGraphAuthError("No Microsoft account is pinned")
        app = self._application()
        result = self._silent_result(
            app, self._pinned_account, force_refresh=force_refresh
        )
        if self._has_token(result):
            self._save_token_cache()
            return result or {}
        self._require_interaction(result)
        self._perform_interaction(app)
        account = find_account_by_key(all_accounts(app), self._pinned_account_key)
        if account is None:
            raise MicrosoftGraphAuthError(
                "Interactive sign-in did not restore the pinned Microsoft account"
            )
        result = self._require_silent_token(app, account)
        self._pinned_account = account
        self._save_token_cache()
        return result

    def _silent_result(
        self,
        app: msal.PublicClientApplication,
        account: dict[str, Any] | None,
        *,
        force_refresh: bool = False,
    ) -> dict[str, Any] | None:
        """Acquire silently for one account while preserving MSAL errors."""
        if account is None:
            return None
        self._inc("msgloom/auth/silent_attempt_count")
        result = app.acquire_token_silent_with_error(
            self.scopes, account=account, force_refresh=force_refresh
        )
        if self._has_token(result):
            self._inc("msgloom/auth/silent_success_count")
        return result

    def _require_silent_token(
        self, app: msal.PublicClientApplication, account: dict[str, Any]
    ) -> dict[str, Any]:
        """Require cache to return a token for the selected account."""
        result = self._silent_result(app, account)
        if not self._has_token(result):
            raise self._result_error(result, "No token for selected Microsoft account")
        return result or {}

    def _perform_interaction(self, app: msal.PublicClientApplication) -> None:
        """Run configured interaction but discard its returned token."""
        if not self.allow_interactive:
            raise MicrosoftGraphAuthError("Interactive Microsoft auth is disabled")
        logger.warning(
            "Microsoft sign-in or consent is required: application_mode=%s "
            "application=%s auth_method=%s scopes=%s",
            self.application_mode,
            self.application_name,
            self.auth_method,
            ",".join(sorted(self.scopes)),
        )
        self._inc("msgloom/auth/user_interaction_count")
        if self.auth_method == "device_code":
            flow = app.initiate_device_flow(scopes=self.scopes)
            if "user_code" not in flow:
                raise MicrosoftGraphAuthError("Unable to start device-code auth")
            logger.warning("Microsoft sign-in required: %s", flow["message"])
            self._inc("msgloom/auth/device_code_count")
            result = app.acquire_token_by_device_flow(flow)
        else:
            self._inc("msgloom/auth/browser_interactive_count")
            result = app.acquire_token_interactive(
                scopes=self.scopes,
                login_hint=self.account_username or None,
            )
        if not self._has_token(result):
            raise self._result_error(result, "Microsoft interactive sign-in failed")

    def _require_interaction(self, result: dict[str, Any] | None) -> None:
        """Fail closed in unattended mode instead of starting a prompt."""
        if self.allow_interactive:
            return
        raise self._result_error(
            result, "Silent Microsoft authentication did not yield a token"
        )

    @staticmethod
    def _has_token(result: dict[str, Any] | None) -> bool:
        """Return whether a result contains a usable string token."""
        return bool(result and isinstance(result.get("access_token"), str))

    @staticmethod
    def _result_error(
        result: dict[str, Any] | None, fallback: str
    ) -> MicrosoftGraphAuthError:
        """Expose only a bounded provider error code."""
        code = result.get("error") if result else None
        if isinstance(code, str) and _SAFE_ERROR_CODE.fullmatch(code):
            return MicrosoftGraphAuthError(f"{fallback}: {code}")
        return MicrosoftGraphAuthError(fallback)

    def _pin(self, account: dict[str, Any], result: dict[str, Any]) -> None:
        """Pin account metadata and cache its validated token in memory."""
        token = result.get("access_token")
        if not isinstance(token, str):
            raise TypeError("Microsoft authentication returned a non-string token")
        self._pinned_account = dict(account)
        self._pinned_account_key = account_key(account)
        self._access_token = token
        self._expires_at = time.time() + int(result.get("expires_in", 300))

    def _memory_token_valid(self, now: float, force_refresh: bool) -> bool:
        """Return whether memory token is outside the refresh margin."""
        return bool(
            not force_refresh and self._access_token and now < self._expires_at - 60
        )

    def _require_client_id(self) -> None:
        """Reject live auth with actionable application-identity guidance."""
        if self.client_id:
            return
        raise MicrosoftGraphAuthError(
            "Microsoft application Client ID is not configured. Run "
            "'scrapy microsoft auth status' for local diagnostics. During "
            "development, MSGLOOM_MS_CLIENT_ID may use the documented "
            "Microsoft Graph Command Line Tools client "
            f"({MICROSOFT_GRAPH_CLI_CLIENT_ID}); real deployments should use "
            "the msgloom managed application or an operator-supplied Entra "
            "public-client application ID."
        )

    def _application(self) -> msal.PublicClientApplication:
        """Lazily construct one MSAL client for this crawler."""
        if self._app is None:
            self._app = msal.PublicClientApplication(
                client_id=self.client_id,
                authority=self.authority,
                token_cache=self.token_cache,
            )
        return self._app

    def _save_token_cache(self) -> None:
        """Atomically persist verified MSAL cache state with mode 0600."""
        if not self.token_cache.has_state_changed:
            return
        self.token_cache_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.token_cache_path.with_name(
            f".{self.token_cache_path.name}.{os.getpid()}.{uuid4().hex}.tmp"
        )
        data = self.token_cache.serialize().encode("utf-8")
        fd = -1
        try:
            fd = os.open(
                temp_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
            with os.fdopen(fd, "wb") as handle:
                fd = -1
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, self.token_cache_path)
            os.chmod(self.token_cache_path, 0o600)
        except Exception:
            # SerializableTokenCache.serialize() clears this flag before I/O.
            # Re-arm it when persistence fails so a later attempt can retry.
            self.token_cache.has_state_changed = True
            raise
        finally:
            if fd >= 0:
                os.close(fd)
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass
        self._inc("msgloom/auth/token_cache_save_count")

    def _inc(self, key: str, count: int = 1) -> None:
        """Publish authentication counters without account identifiers."""
        if self.stats is not None:
            self.stats.inc_value(key, count=count)

    def _set(self, key: str, value) -> None:
        """Publish bounded authentication state."""
        if self.stats is not None:
            self.stats.set_value(key, value)
