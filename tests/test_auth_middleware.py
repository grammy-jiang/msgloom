"""
Exercise token reuse, account selection, and the single authentication refresh
retry.
"""

from __future__ import annotations

import asyncio

import pytest
from scrapy import Spider
from scrapy.exceptions import NotConfigured
from scrapy.http import Request, Response
from scrapy.utils.misc import build_from_crawler
from scrapy.utils.test import get_crawler

from message_ingest.providers.microsoft_graph.auth import (
    MicrosoftGraphDeviceCodeAuthMiddleware,
    MicrosoftGraphInteractiveAuthMiddleware,
)


def _settings(
    tmp_path, *, username: str = "", auth_method: str = "device_code"
) -> dict:
    return {
        "MS_GRAPH_AUTH_ENABLED": True,
        "MS_GRAPH_AUTH_METHOD": auth_method,
        "MS_GRAPH_CLIENT_ID": "test-client-id",
        "MS_GRAPH_AUTHORITY": "https://login.microsoftonline.com/common",
        "MS_GRAPH_SCOPES": ["Mail.Read"],
        "MS_GRAPH_TOKEN_CACHE": str(tmp_path / "token-cache.json"),
        "MS_GRAPH_ACCOUNT_USERNAME": username,
    }


def _middleware(cls, tmp_path, *, username: str = ""):
    crawler = get_crawler(
        settings_dict=_settings(
            tmp_path,
            username=username,
            auth_method=cls.auth_method,
        )
    )
    return build_from_crawler(cls, crawler)


@pytest.mark.parametrize(
    "middleware_cls",
    [
        MicrosoftGraphDeviceCodeAuthMiddleware,
        MicrosoftGraphInteractiveAuthMiddleware,
    ],
)
def test_outlook_resource_scope_reaches_selected_auth_middleware(
    tmp_path,
    middleware_cls,
) -> None:
    from message_ingest.spiders.outlook_discover import OutlookDiscoverSpider

    crawler = get_crawler(
        OutlookDiscoverSpider,
        settings_dict={
            "MS_GRAPH_AUTH_METHOD": middleware_cls.auth_method,
            "MS_GRAPH_CLIENT_ID": "test-client-id",
            "MS_GRAPH_AUTHORITY": "https://login.microsoftonline.com/common",
            "MS_GRAPH_TOKEN_CACHE": str(tmp_path / "token-cache.json"),
            "MS_GRAPH_ACCOUNT_USERNAME": "",
        },
    )
    middleware = build_from_crawler(middleware_cls, crawler)
    if middleware.scopes != ["Mail.Read"]:
        pytest.fail('Expected: middleware.scopes == ["Mail.Read"]')


class NonGraphSpider(Spider):
    """Fixture spider for provider applicability."""

    name = "non_graph"


def test_non_graph_resource_disables_graph_auth(tmp_path) -> None:
    crawler = get_crawler(
        NonGraphSpider,
        settings_dict={
            "MS_GRAPH_AUTH_METHOD": "device_code",
            "MS_GRAPH_CLIENT_ID": "test-client-id",
            "MS_GRAPH_AUTHORITY": "https://login.microsoftonline.com/common",
            "MS_GRAPH_TOKEN_CACHE": str(tmp_path / "token-cache.json"),
            "MS_GRAPH_ACCOUNT_USERNAME": "",
        },
    )
    with pytest.raises(NotConfigured):
        build_from_crawler(MicrosoftGraphDeviceCodeAuthMiddleware, crawler)


@pytest.mark.parametrize(
    "middleware_cls",
    [
        MicrosoftGraphDeviceCodeAuthMiddleware,
        MicrosoftGraphInteractiveAuthMiddleware,
    ],
)
def test_auth_method_none_disables_components_before_scope_validation(
    tmp_path,
    middleware_cls,
) -> None:
    settings = _settings(tmp_path, auth_method="none")
    settings["MS_GRAPH_SCOPES"] = []
    crawler = get_crawler(settings_dict=settings)
    with pytest.raises(NotConfigured):
        build_from_crawler(middleware_cls, crawler)


def test_device_code_auth_removes_authorization_before_native_cache(tmp_path) -> None:
    middleware = _middleware(MicrosoftGraphDeviceCodeAuthMiddleware, tmp_path)
    request = Request(
        "https://graph.microsoft.com/v1.0/me/messages",
        headers={"Authorization": "Bearer secret"},
    )
    response = Response(request.url, request=request)

    returned = middleware.process_response(request, response)

    if returned is not response:
        pytest.fail("Expected: returned is response")
    if b"Authorization" in request.headers:
        pytest.fail('Expected: b"Authorization" not in request.headers')
    if middleware.stats.get_value("msgloom/auth/method") != "device_code":
        pytest.fail(
            'Expected: middleware.stats.get_value("msgloom/auth/method") == "device_code"'
        )
    if middleware.stats.get_value("msgloom/auth/token_cache_loaded") is not False:
        pytest.fail(
            'Expected: middleware.stats.get_value("msgloom/auth/token_cache_loaded") is False'
        )


def test_interactive_auth_uses_same_authentication_boundary(tmp_path) -> None:
    middleware = _middleware(MicrosoftGraphInteractiveAuthMiddleware, tmp_path)
    request = Request(
        "https://graph.microsoft.com/v1.0/me/messages",
        headers={"Authorization": "Bearer secret"},
    )
    response = Response(request.url, request=request)

    returned = middleware.process_response(request, response)

    if returned is not response:
        pytest.fail("Expected: returned is response")
    if b"Authorization" in request.headers:
        pytest.fail('Expected: b"Authorization" not in request.headers')


def test_first_401_becomes_one_forced_authentication_retry(tmp_path) -> None:
    middleware = _middleware(MicrosoftGraphDeviceCodeAuthMiddleware, tmp_path)
    request = Request(
        "https://graph.microsoft.com/v1.0/me/messages",
        headers={"Authorization": "Bearer expired"},
    )
    response = Response(request.url, status=401, request=request)

    retry = middleware.process_response(request, response)

    if not isinstance(retry, Request):
        pytest.fail("Expected: isinstance(retry, Request)")
    if retry.dont_filter is not True:
        pytest.fail("Expected: retry.dont_filter is True")
    if retry.meta["_msgloom_ms_auth_retry"] is not True:
        pytest.fail('Expected: retry.meta["_msgloom_ms_auth_retry"] is True')
    if retry.meta["_msgloom_ms_force_refresh"] is not True:
        pytest.fail('Expected: retry.meta["_msgloom_ms_force_refresh"] is True')
    if b"Authorization" in retry.headers:
        pytest.fail('Expected: b"Authorization" not in retry.headers')
    if middleware.stats.get_value("msgloom/auth/401_retry_count") != 1:
        pytest.fail(
            'Expected: middleware.stats.get_value("msgloom/auth/401_retry_count") == 1'
        )


def test_second_401_is_returned_without_authentication_loop(tmp_path) -> None:
    middleware = _middleware(MicrosoftGraphDeviceCodeAuthMiddleware, tmp_path)
    request = Request(
        "https://graph.microsoft.com/v1.0/me/messages",
        headers={"Authorization": "Bearer still-invalid"},
        meta={"_msgloom_ms_auth_retry": True},
    )
    response = Response(request.url, status=401, request=request)

    returned = middleware.process_response(request, response)

    if returned is not response:
        pytest.fail("Expected: returned is response")
    if b"Authorization" in request.headers:
        pytest.fail('Expected: b"Authorization" not in request.headers')
    if middleware.stats.get_value("msgloom/auth/401_final_count") != 1:
        pytest.fail(
            'Expected: middleware.stats.get_value("msgloom/auth/401_final_count") == 1'
        )


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

    if app.username != "person@example.com":
        pytest.fail('Expected: app.username == "person@example.com"')
    if accounts != [{"username": "person@example.com"}]:
        pytest.fail('Expected: accounts == [{"username": "person@example.com"}]')


def test_multiple_cached_accounts_require_explicit_username(tmp_path) -> None:
    middleware = _middleware(MicrosoftGraphDeviceCodeAuthMiddleware, tmp_path)

    class FakeApp:
        @staticmethod
        def get_accounts(username=None):
            if username is not None:
                pytest.fail("Expected: username is None")
            return [
                {"username": "one@example.com"},
                {"username": "two@example.com"},
            ]

    try:
        middleware._cached_accounts(FakeApp())  # type: ignore[arg-type]
    except RuntimeError as exc:
        if "MSGLOOM_MS_USERNAME" not in str(exc):
            pytest.fail('Expected: "MSGLOOM_MS_USERNAME" in str(exc)')
    else:
        raise AssertionError("Expected multiple cached accounts to be rejected")


def test_device_code_fallback_calls_device_flow(tmp_path) -> None:
    middleware = _middleware(MicrosoftGraphDeviceCodeAuthMiddleware, tmp_path)

    class FakeApp:
        def initiate_device_flow(self, scopes):
            if scopes != ["Mail.Read"]:
                pytest.fail('Expected: scopes == ["Mail.Read"]')
            return {"user_code": "CODE", "message": "Sign in"}

        @staticmethod
        def acquire_token_by_device_flow(flow):
            if flow["user_code"] != "CODE":
                pytest.fail('Expected: flow["user_code"] == "CODE"')
            return {"access_token": "device-token", "expires_in": 3600}

    result = middleware._acquire_interactive_token(FakeApp())  # type: ignore[arg-type]
    if result["access_token"] != "device-token":
        pytest.fail('Expected: result["access_token"] == "device-token"')


def test_interactive_fallback_calls_msal_interactive_with_login_hint(tmp_path) -> None:
    middleware = _middleware(
        MicrosoftGraphInteractiveAuthMiddleware,
        tmp_path,
        username="person@example.com",
    )

    class FakeApp:
        @staticmethod
        def acquire_token_interactive(scopes, login_hint=None):
            if scopes != ["Mail.Read"]:
                pytest.fail('Expected: scopes == ["Mail.Read"]')
            if login_hint != "person@example.com":
                pytest.fail('Expected: login_hint == "person@example.com"')
            return {"access_token": "interactive-token", "expires_in": 3600}

    result = middleware._acquire_interactive_token(FakeApp())  # type: ignore[arg-type]
    if result["access_token"] != "interactive-token":
        pytest.fail('Expected: result["access_token"] == "interactive-token"')


def test_auth_method_selection_uses_final_crawler_settings(tmp_path) -> None:
    from scrapy.exceptions import NotConfigured

    crawler = get_crawler(settings_dict=_settings(tmp_path, auth_method="interactive"))
    interactive = build_from_crawler(MicrosoftGraphInteractiveAuthMiddleware, crawler)
    if interactive.auth_method != "interactive":
        pytest.fail('Expected: interactive.auth_method == "interactive"')
    try:
        build_from_crawler(MicrosoftGraphDeviceCodeAuthMiddleware, crawler)
    except NotConfigured:
        pass
    else:
        raise AssertionError("Unselected device-code middleware should be disabled")


@pytest.mark.parametrize("access_token", [None, 42])
def test_auth_rejects_non_string_tokens_before_setting_authorization(
    tmp_path,
    monkeypatch,
    access_token,
) -> None:
    middleware = _middleware(MicrosoftGraphDeviceCodeAuthMiddleware, tmp_path)
    monkeypatch.setattr(
        middleware,
        "_acquire_access_token",
        lambda **kwargs: {"access_token": access_token, "expires_in": 300},
    )
    request = Request("https://graph.microsoft.com/v1.0/me/messages")

    with pytest.raises(TypeError, match="non-string access token"):
        asyncio.run(middleware.process_request(request))

    if b"Authorization" in request.headers:
        pytest.fail('Expected: b"Authorization" not in request.headers')



def test_selected_graph_auth_requires_resource_scopes(tmp_path) -> None:
    settings = _settings(tmp_path)
    settings["MS_GRAPH_SCOPES"] = []
    crawler = get_crawler(settings_dict=settings)

    with pytest.raises(
        RuntimeError,
        match="Microsoft Graph resource must configure MS_GRAPH_SCOPES",
    ):
        build_from_crawler(MicrosoftGraphDeviceCodeAuthMiddleware, crawler)
