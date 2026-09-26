from __future__ import annotations

from scrapy.http import Request, Response
from scrapy.utils.misc import build_from_crawler
from scrapy.utils.test import get_crawler

from msgloom.middlewares import (
    MicrosoftGraphDeviceCodeAuthMiddleware,
    MicrosoftGraphInteractiveAuthMiddleware,
)


def _settings(tmp_path, *, username: str = "") -> dict:
    return {
        "MS_GRAPH_CLIENT_ID": "test-client-id",
        "MS_GRAPH_AUTHORITY": "https://login.microsoftonline.com/common",
        "MS_GRAPH_SCOPES": ["Mail.Read"],
        "MS_GRAPH_TOKEN_CACHE": str(tmp_path / "token-cache.json"),
        "MS_GRAPH_ACCOUNT_USERNAME": username,
    }


def _middleware(cls, tmp_path, *, username: str = ""):
    crawler = get_crawler(settings_dict=_settings(tmp_path, username=username))
    return build_from_crawler(cls, crawler)


def test_device_code_auth_removes_authorization_before_native_cache(tmp_path) -> None:
    middleware = _middleware(MicrosoftGraphDeviceCodeAuthMiddleware, tmp_path)
    request = Request(
        "https://graph.microsoft.com/v1.0/me/messages",
        headers={"Authorization": "Bearer secret"},
    )
    response = Response(request.url, request=request)

    returned = middleware.process_response(request, response)

    assert returned is response
    assert b"Authorization" not in request.headers
    assert middleware.stats.get_value("msgloom/auth/method") == "device_code"
    assert middleware.stats.get_value("msgloom/auth/token_cache_loaded") is False


def test_interactive_auth_uses_same_authentication_boundary(tmp_path) -> None:
    middleware = _middleware(MicrosoftGraphInteractiveAuthMiddleware, tmp_path)
    request = Request(
        "https://graph.microsoft.com/v1.0/me/messages",
        headers={"Authorization": "Bearer secret"},
    )
    response = Response(request.url, request=request)

    returned = middleware.process_response(request, response)

    assert returned is response
    assert b"Authorization" not in request.headers


def test_first_401_becomes_one_forced_authentication_retry(tmp_path) -> None:
    middleware = _middleware(MicrosoftGraphDeviceCodeAuthMiddleware, tmp_path)
    request = Request(
        "https://graph.microsoft.com/v1.0/me/messages",
        headers={"Authorization": "Bearer expired"},
    )
    response = Response(request.url, status=401, request=request)

    retry = middleware.process_response(request, response)

    assert isinstance(retry, Request)
    assert retry.dont_filter is True
    assert retry.meta["_msgloom_ms_auth_retry"] is True
    assert retry.meta["_msgloom_ms_force_refresh"] is True
    assert b"Authorization" not in retry.headers
    assert middleware.stats.get_value("msgloom/auth/401_retry_count") == 1


def test_second_401_is_returned_without_authentication_loop(tmp_path) -> None:
    middleware = _middleware(MicrosoftGraphDeviceCodeAuthMiddleware, tmp_path)
    request = Request(
        "https://graph.microsoft.com/v1.0/me/messages",
        headers={"Authorization": "Bearer still-invalid"},
        meta={"_msgloom_ms_auth_retry": True},
    )
    response = Response(request.url, status=401, request=request)

    returned = middleware.process_response(request, response)

    assert returned is response
    assert b"Authorization" not in request.headers
    assert middleware.stats.get_value("msgloom/auth/401_final_count") == 1


def test_cached_account_username_is_used_as_msal_account_filter(tmp_path) -> None:
    middleware = _middleware(
        MicrosoftGraphDeviceCodeAuthMiddleware,
        tmp_path,
        username="person@example.com",
    )

    class FakeApp:
        def __init__(self) -> None:
            self.username = None

        def get_accounts(self, username=None):
            self.username = username
            return [{"username": username}]

    app = FakeApp()
    accounts = middleware._cached_accounts(app)  # type: ignore[arg-type]

    assert app.username == "person@example.com"
    assert accounts == [{"username": "person@example.com"}]


def test_multiple_cached_accounts_require_explicit_username(tmp_path) -> None:
    middleware = _middleware(MicrosoftGraphDeviceCodeAuthMiddleware, tmp_path)

    class FakeApp:
        @staticmethod
        def get_accounts(username=None):
            assert username is None
            return [
                {"username": "one@example.com"},
                {"username": "two@example.com"},
            ]

    try:
        middleware._cached_accounts(FakeApp())  # type: ignore[arg-type]
    except RuntimeError as exc:
        assert "MSGLOOM_MS_USERNAME" in str(exc)
    else:
        raise AssertionError("Expected multiple cached accounts to be rejected")


def test_device_code_fallback_calls_device_flow(tmp_path) -> None:
    middleware = _middleware(MicrosoftGraphDeviceCodeAuthMiddleware, tmp_path)

    class FakeApp:
        def initiate_device_flow(self, scopes):
            assert scopes == ["Mail.Read"]
            return {"user_code": "CODE", "message": "Sign in"}

        @staticmethod
        def acquire_token_by_device_flow(flow):
            assert flow["user_code"] == "CODE"
            return {"access_token": "device-token", "expires_in": 3600}

    result = middleware._acquire_interactive_token(FakeApp())  # type: ignore[arg-type]
    assert result["access_token"] == "device-token"


def test_interactive_fallback_calls_msal_interactive_with_login_hint(tmp_path) -> None:
    middleware = _middleware(
        MicrosoftGraphInteractiveAuthMiddleware,
        tmp_path,
        username="person@example.com",
    )

    class FakeApp:
        @staticmethod
        def acquire_token_interactive(scopes, login_hint=None):
            assert scopes == ["Mail.Read"]
            assert login_hint == "person@example.com"
            return {"access_token": "interactive-token", "expires_in": 3600}

    result = middleware._acquire_interactive_token(FakeApp())  # type: ignore[arg-type]
    assert result["access_token"] == "interactive-token"
