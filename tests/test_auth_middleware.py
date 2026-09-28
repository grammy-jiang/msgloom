"""
Exercise token reuse, account selection, and the single authentication refresh
retry.
"""

from __future__ import annotations

import asyncio
import pickle
from typing import ClassVar, cast

import pytest
from scrapy import Spider
from scrapy.core.downloader.middleware import DownloaderMiddlewareManager
from scrapy.downloadermiddlewares.redirect import RedirectMiddleware
from scrapy.exceptions import DownloadTimeoutError, IgnoreRequest, NotConfigured
from scrapy.http import Request, Response
from scrapy.utils.misc import build_from_crawler
from scrapy.utils.test import get_crawler

from message_ingest.providers.microsoft_graph.auth import (
    MicrosoftGraphDeviceCodeAuthMiddleware,
    MicrosoftGraphInteractiveAuthMiddleware,
)
from message_ingest.providers.microsoft_graph.auth_session import (
    MicrosoftGraphAuthSession,
)
from message_ingest.providers.microsoft_graph.errors import (
    PrivacySafeRetryMiddleware,
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
        "MSGLOOM_CATALOG_ENABLED": False,
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
            "MSGLOOM_CATALOG_ENABLED": False,
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


def test_auth_method_selection_uses_final_crawler_settings(tmp_path) -> None:
    crawler = get_crawler(settings_dict=_settings(tmp_path, auth_method="interactive"))
    interactive = build_from_crawler(MicrosoftGraphInteractiveAuthMiddleware, crawler)
    if interactive.auth_method != "interactive":
        pytest.fail('Expected: interactive.auth_method == "interactive"')
    with pytest.raises(NotConfigured):
        build_from_crawler(MicrosoftGraphDeviceCodeAuthMiddleware, crawler)


@pytest.mark.parametrize("access_token", [None, 42])
def test_auth_rejects_non_string_tokens_before_setting_authorization(
    tmp_path,
    monkeypatch,
    access_token,
) -> None:
    middleware = _middleware(MicrosoftGraphDeviceCodeAuthMiddleware, tmp_path)

    async def invalid_token(*, force_refresh: bool = False):
        return access_token

    monkeypatch.setattr(middleware.session, "get_access_token", invalid_token)
    request = Request("https://graph.microsoft.com/v1.0/me/messages")

    with pytest.raises(TypeError):
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


def test_catalog_disabled_auth_can_respect_external_authorization(tmp_path) -> None:
    middleware = _middleware(MicrosoftGraphDeviceCodeAuthMiddleware, tmp_path)
    request = Request(
        "https://graph.microsoft.com/v1.0/me/messages",
        headers={"Authorization": "Bearer externally-managed"},
    )

    asyncio.run(middleware.process_request(request))

    if request.headers.get("Authorization") != b"Bearer externally-managed":
        pytest.fail("Expected catalog-disabled crawl to preserve explicit auth")


def test_catalog_backed_auth_replaces_unverified_authorization_header() -> None:
    class FakeSession:
        scopes: ClassVar[list[str]] = ["Mail.Read"]
        source_identity = object()

        async def get_access_token(self, *, force_refresh: bool = False) -> str:
            return "source-pinned-token"

        def clear_memory_token(self) -> None:
            pass

    middleware = MicrosoftGraphDeviceCodeAuthMiddleware(
        cast(MicrosoftGraphAuthSession, FakeSession())
    )
    request = Request(
        "https://graph.microsoft.com/v1.0/me/messages",
        headers={"Authorization": "Bearer unverified-external-token"},
    )

    asyncio.run(middleware.process_request(request))

    if request.headers.get("Authorization") != b"Bearer source-pinned-token":
        pytest.fail("Expected persisted crawl to replace external Authorization")


def test_external_authorization_401_forces_refresh_on_first_session_token(
    tmp_path,
) -> None:
    middleware = _middleware(MicrosoftGraphDeviceCodeAuthMiddleware, tmp_path)
    account = {
        "home_account_id": "account-a",
        "username": "person@example.com",
    }
    force_values: list[bool] = []

    class FakeApp:
        @staticmethod
        def get_accounts(username=None):
            return [account]

        @staticmethod
        def acquire_token_silent_with_error(scopes, account, force_refresh=False):
            force_values.append(force_refresh)
            token = "fresh-token" if force_refresh else "cached-rejected"
            return {"access_token": token, "expires_in": 3600}

    middleware.session._app = FakeApp()  # type: ignore[assignment]
    request = Request(
        "https://graph.microsoft.com/v1.0/me/messages",
        headers={"Authorization": "Bearer externally-managed"},
    )

    asyncio.run(middleware.process_request(request))
    response = Response(request.url, status=401, request=request)
    retry = middleware.process_response(request, response)
    if not isinstance(retry, Request):
        pytest.fail("Expected first 401 to create a retry Request")

    asyncio.run(middleware.process_request(retry))

    if force_values != [True]:
        pytest.fail(f"Expected first session token to force refresh: {force_values!r}")
    if retry.headers.get("Authorization") != b"Bearer fresh-token":
        pytest.fail("Expected retry to use the forced-refresh token")


def test_transport_retry_does_not_serialize_bearer_token() -> None:
    from message_ingest.spiders.outlook_discover import OutlookDiscoverSpider

    crawler = get_crawler(
        OutlookDiscoverSpider,
        settings_dict={"RETRY_TIMES": 1},
    )
    spider = OutlookDiscoverSpider.from_crawler(crawler)
    crawler.spider = spider

    class FakeSession:
        scopes: ClassVar[list[str]] = ["Mail.Read"]
        source_identity = object()

        async def get_access_token(self, *, force_refresh: bool = False) -> str:
            return "transport-secret-token"

        def clear_memory_token(self) -> None:
            pass

    auth = MicrosoftGraphDeviceCodeAuthMiddleware(
        cast(MicrosoftGraphAuthSession, FakeSession()),
        stats=crawler.stats,
    )
    retry = PrivacySafeRetryMiddleware.from_crawler(crawler)
    manager = DownloaderMiddlewareManager(retry, auth, crawler=crawler)
    request = Request(
        "https://graph.microsoft.com/v1.0/me/messages",
        cb_kwargs={"purpose": "message-list"},
    )

    async def fail_download(_request):
        raise DownloadTimeoutError("private transport failure")

    retry_request = asyncio.run(manager.download_async(fail_download, request))

    if not isinstance(retry_request, Request):
        pytest.fail("Expected native retry middleware to return a Request")
    if retry_request.headers.get("Authorization") is not None:
        pytest.fail("Expected transport retry not to retain Authorization")
    serialized = pickle.dumps(retry_request.to_dict(spider=spider))
    if b"transport-secret-token" in serialized:
        pytest.fail("Expected JOBDIR-serializable retry not to contain bearer token")
    if crawler.stats.get_value("msgloom/auth/credential_stripped_exception_count") != 1:
        pytest.fail("Expected auth exception cleanup counter")


def test_https_to_http_graph_redirect_is_refused_without_token() -> None:
    from message_ingest.spiders.outlook_discover import OutlookDiscoverSpider

    crawler = get_crawler(OutlookDiscoverSpider)
    spider = OutlookDiscoverSpider.from_crawler(crawler)
    crawler.spider = spider

    class FakeSession:
        scopes: ClassVar[list[str]] = ["Mail.Read"]
        source_identity = object()

        async def get_access_token(self, *, force_refresh: bool = False) -> str:
            return "redirect-secret-token"

        def clear_memory_token(self) -> None:
            pass

    auth = MicrosoftGraphDeviceCodeAuthMiddleware(
        cast(MicrosoftGraphAuthSession, FakeSession()),
        stats=crawler.stats,
    )
    redirect = RedirectMiddleware.from_crawler(crawler)
    original = Request(
        "https://graph.microsoft.com/v1.0/me/messages",
        cb_kwargs={"purpose": "message-list"},
    )
    asyncio.run(auth.process_request(original))
    response = Response(
        original.url,
        status=302,
        headers={"Location": "http://graph.microsoft.com/v1.0/me/messages"},
        request=original,
    )
    auth.process_response(original, response)
    downgraded = redirect.process_response(original, response)
    if not isinstance(downgraded, Request):
        pytest.fail("Expected native redirect middleware to return Request")

    with pytest.raises(IgnoreRequest, match="non-HTTPS Microsoft Graph"):
        asyncio.run(auth.process_request(downgraded))

    if downgraded.headers.get("Authorization") is not None:
        pytest.fail("Expected downgraded Graph redirect to contain no bearer token")
    if crawler.stats.get_value("msgloom/auth/insecure_scheme_blocked_count") != 1:
        pytest.fail("Expected insecure Graph scheme to be counted")
