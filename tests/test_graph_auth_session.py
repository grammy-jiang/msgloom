"""Verify crawler-scoped MSAL account selection and token pinning."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import pytest
from scrapy.utils.test import get_crawler

from message_ingest.spiders.microsoft.outlook.email.discover import (
    OutlookDiscoverSpider,
)
from microsoft_graph.auth.session import (
    MicrosoftGraphAuthError,
    MicrosoftGraphAuthSession,
)


def _crawler(
    tmp_path: Path,
    *,
    auth_method: str = "device_code",
    username: str = "",
    allow_interactive: bool = True,
    catalog: bool = True,
    identity_required: bool = True,
):
    return get_crawler(
        OutlookDiscoverSpider,
        settings_dict={
            "MS_GRAPH_AUTH_METHOD": auth_method,
            "MS_GRAPH_CLIENT_ID": "test-client-id",
            "MS_GRAPH_AUTHORITY": "https://login.microsoftonline.com/common",
            "MS_GRAPH_TOKEN_CACHE": str(tmp_path / "token-cache.json"),
            "MS_GRAPH_ACCOUNT_USERNAME": username,
            "MS_GRAPH_AUTH_ALLOW_INTERACTIVE": allow_interactive,
            "MSGLOOM_CATALOG_ENABLED": catalog,
            "MSGLOOM_SOURCE_IDENTITY_REQUIRED": identity_required,
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_SOURCE_ID": "source-1",
        },
    )


def _account(key: str, username: str = "person@example.com") -> dict:
    return {"home_account_id": key, "username": username}


class _MemoryBinding:
    """Small auth-only binding fake with no msgloom persistence dependency."""

    def __init__(self, bound_key: str | None = None) -> None:
        self.bound_key = bound_key
        self.write_lock = asyncio.Lock()

    def has_binding(self) -> bool:
        return self.bound_key is not None

    def matches_account_key(self, account_key: str) -> bool:
        return self.bound_key == account_key

    def bind_or_verify_account_key(self, account_key: str) -> str:
        if self.bound_key is None:
            self.bound_key = account_key
            return "bound"
        if self.bound_key != account_key:
            raise MicrosoftGraphAuthError(
                "Microsoft account does not match the account bound to this source"
            )
        return "verified"


def _bound_session(crawler, *, bound_key: str | None = None):
    session = MicrosoftGraphAuthSession.from_crawler(crawler)
    binding = _MemoryBinding(bound_key)
    session.attach_account_binding(binding)
    return session, binding


def test_silent_token_is_pinned_to_the_bound_account(tmp_path: Path) -> None:
    crawler = _crawler(tmp_path)
    session, binding = _bound_session(crawler)
    account = _account("account-a")

    class FakeApp:
        @staticmethod
        def get_accounts(username=None):
            return [account]

        @staticmethod
        def acquire_token_silent_with_error(scopes, account, force_refresh=False):
            return {"access_token": "silent-a", "expires_in": 3600}

    session._app = FakeApp()  # type: ignore[assignment]
    asyncio.run(session.establish_account_binding())

    if session.account_binding_ready is not True:
        pytest.fail("Expected source identity gate to be ready")
    if asyncio.run(session.get_access_token()) != "silent-a":
        pytest.fail("Expected token from the verified account")
    if binding.bound_key != "account-a":
        pytest.fail("Expected Microsoft home-account binding")


def test_interactive_token_is_discarded_then_reacquired_for_selected_account(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path)
    session, _binding = _bound_session(crawler)
    account = _account("account-b")

    class FakeApp:
        def __init__(self) -> None:
            self.signed_in = False
            self.silent_calls = 0

        def get_accounts(self, username=None):
            return [account] if self.signed_in else []

        @staticmethod
        def initiate_device_flow(scopes):
            return {"user_code": "CODE", "message": "Sign in"}

        def acquire_token_by_device_flow(self, flow):
            self.signed_in = True
            return {"access_token": "interactive-token", "expires_in": 3600}

        def acquire_token_silent_with_error(self, scopes, account, force_refresh=False):
            self.silent_calls += 1
            return {"access_token": "silent-for-b", "expires_in": 3600}

    app = FakeApp()
    session._app = app  # type: ignore[assignment]
    asyncio.run(session.establish_account_binding())

    if app.silent_calls != 1:
        pytest.fail("Expected post-interaction token to be reacquired silently")
    if asyncio.run(session.get_access_token()) != "silent-for-b":
        pytest.fail("Expected interactive token itself never to be used")


def test_existing_binding_ignores_username_and_selects_matching_account(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path, username="renamed@example.com")
    session, _binding = _bound_session(crawler, bound_key="account-a")
    account_a = _account("account-a", "old@example.com")
    account_b = _account("account-b", "renamed@example.com")

    class FakeApp:
        @staticmethod
        def get_accounts(username=None):
            if username is not None:
                return [account_b]
            return [account_a, account_b]

        @staticmethod
        def acquire_token_silent_with_error(scopes, account, force_refresh=False):
            if account["home_account_id"] != "account-a":
                pytest.fail("Expected persisted binding to select account-a")
            return {"access_token": "token-a", "expires_in": 3600}

    session._app = FakeApp()  # type: ignore[assignment]
    asyncio.run(session.establish_account_binding())

    if asyncio.run(session.get_access_token()) != "token-a":
        pytest.fail("Expected token for account bound to source")


def test_interactive_login_cannot_switch_existing_binding(tmp_path: Path) -> None:
    crawler = _crawler(tmp_path)
    session, _binding = _bound_session(crawler, bound_key="account-a")
    account_b = _account("account-b")

    class FakeApp:
        def __init__(self) -> None:
            self.signed_in = False

        def get_accounts(self, username=None):
            return [account_b] if self.signed_in else []

        @staticmethod
        def initiate_device_flow(scopes):
            return {"user_code": "CODE", "message": "Sign in"}

        def acquire_token_by_device_flow(self, flow):
            self.signed_in = True
            return {"access_token": "token-b", "expires_in": 3600}

        @staticmethod
        def acquire_token_silent_with_error(scopes, account, force_refresh=False):
            return None

    session._app = FakeApp()  # type: ignore[assignment]

    with pytest.raises(MicrosoftGraphAuthError, match="bound"):
        asyncio.run(session.establish_account_binding())


def test_duplicate_username_matches_are_rejected_for_first_binding(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path, username="same@example.com")
    session, _binding = _bound_session(crawler)
    accounts = [
        _account("account-a", "same@example.com"),
        _account("account-b", "same@example.com"),
    ]

    class FakeApp:
        @staticmethod
        def get_accounts(username=None):
            return accounts

    session._app = FakeApp()  # type: ignore[assignment]

    with pytest.raises(MicrosoftGraphAuthError, match="multiple cached accounts"):
        asyncio.run(session.establish_account_binding())


def test_multiple_cached_accounts_require_first_binding_selection(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path)
    session, _binding = _bound_session(crawler)

    class FakeApp:
        @staticmethod
        def get_accounts(username=None):
            return [_account("account-a"), _account("account-b")]

    session._app = FakeApp()  # type: ignore[assignment]

    with pytest.raises(MicrosoftGraphAuthError, match="Multiple Microsoft accounts"):
        asyncio.run(session.establish_account_binding())


def test_unattended_mode_never_starts_interaction(tmp_path: Path) -> None:
    crawler = _crawler(tmp_path, allow_interactive=False)
    session, _binding = _bound_session(crawler)

    class FakeApp:
        @staticmethod
        def get_accounts(username=None):
            return []

        @staticmethod
        def initiate_device_flow(scopes):
            pytest.fail("Interactive flow must not start in unattended mode")

    session._app = FakeApp()  # type: ignore[assignment]

    with pytest.raises(MicrosoftGraphAuthError, match="Silent Microsoft"):
        asyncio.run(session.establish_account_binding())


def test_missing_home_account_id_fails_closed(tmp_path: Path) -> None:
    crawler = _crawler(tmp_path)
    session, _binding = _bound_session(crawler)

    class FakeApp:
        @staticmethod
        def get_accounts(username=None):
            return [{"username": "person@example.com"}]

    session._app = FakeApp()  # type: ignore[assignment]

    with pytest.raises(MicrosoftGraphAuthError, match="home_account_id"):
        asyncio.run(session.establish_account_binding())


def test_force_refresh_remains_on_pinned_account(tmp_path: Path) -> None:
    crawler = _crawler(tmp_path)
    session, _binding = _bound_session(crawler)
    account = _account("account-a")
    calls: list[bool] = []

    class FakeApp:
        @staticmethod
        def get_accounts(username=None):
            return [account]

        @staticmethod
        def acquire_token_silent_with_error(scopes, account, force_refresh=False):
            calls.append(force_refresh)
            token = "refreshed-a" if force_refresh else "initial-a"
            return {"access_token": token, "expires_in": 3600}

    session._app = FakeApp()  # type: ignore[assignment]
    asyncio.run(session.establish_account_binding())

    token = asyncio.run(session.get_access_token(force_refresh=True))

    if token != "refreshed-a" or calls != [False, True]:
        pytest.fail("Expected forced refresh to stay on the pinned account")


def test_catalog_disabled_session_can_authenticate_without_binding(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path, catalog=False)
    session = MicrosoftGraphAuthSession.from_crawler(crawler)
    account = _account("account-a")

    class FakeApp:
        @staticmethod
        def get_accounts(username=None):
            return [account]

        @staticmethod
        def acquire_token_silent_with_error(scopes, account, force_refresh=False):
            return {"access_token": "token-a", "expires_in": 3600}

    session._app = FakeApp()  # type: ignore[assignment]

    if asyncio.run(session.get_access_token()) != "token-a":
        pytest.fail("Expected catalog-disabled auth to remain usable")


def test_browser_interactive_result_is_discarded_before_token_use(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path, auth_method="interactive")
    session, _binding = _bound_session(crawler)
    account = _account("browser-account")

    class FakeApp:
        def __init__(self) -> None:
            self.signed_in = False
            self.interactive_calls = 0
            self.silent_calls = 0

        def get_accounts(self, username=None):
            return [account] if self.signed_in else []

        def acquire_token_interactive(self, scopes, login_hint=None):
            self.interactive_calls += 1
            self.signed_in = True
            return {"access_token": "discard-me", "expires_in": 3600}

        def acquire_token_silent_with_error(self, scopes, account, force_refresh=False):
            self.silent_calls += 1
            if account["home_account_id"] != "browser-account":
                pytest.fail("Expected silent reacquire for browser-selected account")
            return {"access_token": "browser-silent", "expires_in": 3600}

    app = FakeApp()
    session._app = app  # type: ignore[assignment]

    asyncio.run(session.establish_account_binding())

    if app.interactive_calls != 1 or app.silent_calls != 1:
        pytest.fail("Expected one browser interaction and one silent reacquire")
    if asyncio.run(session.get_access_token()) != "browser-silent":
        pytest.fail("Expected browser interactive token itself never to be used")


def test_first_binding_with_username_cannot_use_different_interactive_token(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path, username="a@example.com")
    session, binding = _bound_session(crawler)
    account_a = _account("account-a", "a@example.com")
    account_b = _account("account-b", "b@example.com")

    class FakeApp:
        def __init__(self) -> None:
            self.interactive = False

        def get_accounts(self, username=None):
            accounts = [account_a, account_b] if self.interactive else [account_a]
            if username is None:
                return accounts
            return [
                account
                for account in accounts
                if account["username"].lower() == username.lower()
            ]

        @staticmethod
        def acquire_token_silent_with_error(scopes, account, force_refresh=False):
            if account["home_account_id"] == "account-a":
                return None
            return {"access_token": "token-b", "expires_in": 3600}

        @staticmethod
        def initiate_device_flow(scopes):
            return {"user_code": "CODE", "message": "Sign in"}

        def acquire_token_by_device_flow(self, flow):
            self.interactive = True
            return {"access_token": "interactive-b", "expires_in": 3600}

    session._app = FakeApp()  # type: ignore[assignment]

    with pytest.raises(MicrosoftGraphAuthError):
        asyncio.run(session.establish_account_binding())

    if binding.bound_key is not None:
        pytest.fail("Expected wrong interactive account not to become first binding")


def test_explicit_identity_opt_out_keeps_catalog_but_skips_binding(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path, catalog=True, identity_required=False)
    session = MicrosoftGraphAuthSession.from_crawler(crawler)
    account = _account("account-a")

    class FakeApp:
        @staticmethod
        def get_accounts(username=None):
            return [account]

        @staticmethod
        def acquire_token_silent_with_error(scopes, account, force_refresh=False):
            return {"access_token": "token-a", "expires_in": 3600}

    session._app = FakeApp()  # type: ignore[assignment]

    if session.account_binding is not None:
        pytest.fail("Expected explicit source identity opt-out to skip binding service")
    if asyncio.run(session.get_access_token()) != "token-a":
        pytest.fail("Expected Graph authentication to remain usable after opt-out")
    if hasattr(crawler, "_msgloom_source_identity_service"):
        pytest.fail("Expected opt-out not to construct source identity service")


def test_development_client_logs_application_identity(
    tmp_path: Path,
    caplog,
) -> None:
    from microsoft_graph.auth.management import (
        MICROSOFT_GRAPH_CLI_CLIENT_ID,
    )

    caplog.set_level(logging.INFO)
    MicrosoftGraphAuthSession(
        client_id=MICROSOFT_GRAPH_CLI_CLIENT_ID,
        authority="https://login.microsoftonline.com/common",
        scopes=["Mail.Read"],
        token_cache_path=str(tmp_path / "token-cache.json"),
        auth_method="device_code",
        account_username="",
        allow_interactive=True,
        account_binding=None,
    )

    if "application_mode=development" not in caplog.text:
        pytest.fail("Expected application mode in authentication log")
    if "Microsoft Graph Command Line Tools" not in caplog.text:
        pytest.fail("Expected development application identity warning")
    if "development/testing only" not in caplog.text:
        pytest.fail("Expected development-only guidance")


def test_missing_client_id_error_points_to_status_command(tmp_path: Path) -> None:
    session = MicrosoftGraphAuthSession(
        client_id="",
        authority="https://login.microsoftonline.com/common",
        scopes=["Mail.Read"],
        token_cache_path=str(tmp_path / "token-cache.json"),
        auth_method="device_code",
        account_username="",
        allow_interactive=True,
        account_binding=None,
    )

    with pytest.raises(MicrosoftGraphAuthError) as caught:
        session._require_client_id()
    message = str(caught.value)
    if "microsoft auth status" not in message:
        pytest.fail("Expected status-command remediation for missing Client ID")
    if "development" not in message or "real deployments" not in message:
        pytest.fail("Expected development and production remediation")
