"""Verify delegated auth host scoping without contacting an authority."""

import asyncio
from unittest.mock import AsyncMock, Mock, call

import pytest
from scrapy.exceptions import IgnoreRequest
from scrapy.http import Request, Response
from scrapy.utils.misc import build_from_crawler
from scrapy.utils.test import get_crawler

from microsoft_graph.middlewares.authentication import (
    MicrosoftGraphDeviceCodeAuthMiddleware,
    MicrosoftGraphInteractiveAuthMiddleware,
)


@pytest.fixture(
    params=[
        MicrosoftGraphDeviceCodeAuthMiddleware,
        MicrosoftGraphInteractiveAuthMiddleware,
    ],
    ids=["device_code", "interactive"],
)
def auth(request, tmp_path, monkeypatch):
    """Build from crawler settings without live token operations."""
    crawler = get_crawler(
        settings_dict={
            "MS_GRAPH_SERVICE_ROOT": "https://graph.example/beta",
            "MS_GRAPH_AUTH_ENABLED": True,
            "MS_GRAPH_AUTH_METHOD": request.param.auth_method,
            "MS_GRAPH_CLIENT_ID": "test-client-id",
            "MS_GRAPH_AUTHORITY": "https://login.microsoftonline.com/common",
            "MS_GRAPH_SCOPES": ["Mail.Read"],
            "MS_GRAPH_TOKEN_CACHE": str(tmp_path / "token-cache.json"),
            "MS_GRAPH_ACCOUNT_USERNAME": "",
        }
    )
    middleware = build_from_crawler(request.param, crawler)
    token = AsyncMock(return_value="test-token")
    clear_token = Mock()
    monkeypatch.setattr(middleware.session, "get_access_token", token)
    monkeypatch.setattr(middleware.session, "clear_memory_token", clear_token)
    return middleware, token, clear_token


@pytest.mark.parametrize(
    "host, authenticated",
    [
        ("graph.example", True),
        ("graph.microsoft.com", False),
        ("other.example", False),
        ("sub.graph.example", False),
    ],
)
def test_request_authenticates_only_configured_host(auth, host, authenticated):
    middleware, token, _ = auth
    request = Request(f"https://{host}/beta/me")

    returned = asyncio.run(middleware.process_request(request))

    if returned is not None:
        pytest.fail("Authentication must continue the downloader chain")
    expected_header = b"Bearer test-token" if authenticated else None
    if request.headers.get("Authorization") != expected_header:
        pytest.fail("Only the configured Graph host may receive a token")
    expected_calls = [call(force_refresh=False)] if authenticated else []
    if token.await_args_list != expected_calls:
        pytest.fail("Other hosts must not acquire a Graph token")
    expected_count = 1 if authenticated else 0
    if (
        middleware.stats.get_value(
            "microsoft_graph/auth/request_authenticated_count", 0
        )
        != expected_count
    ):
        pytest.fail("Authentication must retain neutral default stats")


def test_configured_host_401_refreshes_once(auth):
    middleware, token, clear_token = auth
    request = Request(
        "https://graph.example/beta/me",
        headers={"Authorization": "Bearer expired-token"},
    )
    response = Response(request.url, status=401, request=request)

    retry = middleware.process_response(request, response)

    if not isinstance(retry, Request) or retry is request:
        pytest.fail("The configured host's first 401 must create a retry")
    if not retry.dont_filter:
        pytest.fail("The refresh retry must bypass duplicate filtering")
    if retry.meta != {
        "_microsoft_graph_auth_retry": True,
        "_microsoft_graph_force_refresh": True,
    }:
        pytest.fail("The refresh retry must retain neutral default meta keys")
    if "Authorization" in request.headers or "Authorization" in retry.headers:
        pytest.fail("A rejected token must not reach cache or retry storage")
    if clear_token.call_count != 1:
        pytest.fail("A rejected token must clear the session's memory token")

    asyncio.run(middleware.process_request(retry))

    if token.await_args_list != [call(force_refresh=True)]:
        pytest.fail("The retry must force token refresh")
    if retry.headers.get("Authorization") != b"Bearer test-token":
        pytest.fail("The retry must receive the refreshed token")
    if "_microsoft_graph_force_refresh" in retry.meta:
        pytest.fail("The force-refresh flag must be consumed")
    final_response = Response(retry.url, status=401, request=retry)
    if middleware.process_response(retry, final_response) is not final_response:
        pytest.fail("A second 401 must not start another authentication retry")
    if "Authorization" in retry.headers or clear_token.call_count != 1:
        pytest.fail("The final 401 must strip the token without refreshing again")
    for key in ("401_retry_count", "401_final_count"):
        if middleware.stats.get_value(f"microsoft_graph/auth/{key}") != 1:
            pytest.fail(f"Expected one neutral auth counter for {key}")


@pytest.mark.parametrize("host", ["graph.microsoft.com", "other.example"])
def test_other_host_401_leaves_authentication_untouched(auth, host):
    middleware, token, clear_token = auth
    request = Request(
        f"https://{host}/beta/me",
        headers={"Authorization": "Bearer external-token"},
        meta={"_microsoft_graph_force_refresh": True},
    )
    response = Response(request.url, status=401, request=request)
    initial_stats = middleware.stats.get_stats().copy()

    asyncio.run(middleware.process_request(request))
    returned = middleware.process_response(request, response)

    if returned is not response:
        pytest.fail("A different host's 401 must not trigger Graph refresh")
    if request.headers.get("Authorization") != b"Bearer external-token":
        pytest.fail("A different host's credentials must remain unchanged")
    if request.meta != {"_microsoft_graph_force_refresh": True}:
        pytest.fail("A different host's metadata must remain unchanged")
    if token.await_count or clear_token.call_count:
        pytest.fail("A different host must not acquire or clear a Graph token")
    if middleware.stats.get_stats() != initial_stats:
        pytest.fail("A different host must not change Graph auth stats")


@pytest.mark.parametrize(
    "host, stripped",
    [("graph.example", True), ("graph.microsoft.com", False)],
)
def test_exception_strips_credentials_only_for_configured_host(auth, host, stripped):
    middleware, _, _ = auth
    request = Request(
        f"https://{host}/beta/me",
        headers={"Authorization": "Bearer test-token"},
    )

    returned = middleware.process_exception(request, OSError("transport failure"))

    if returned is not None:
        pytest.fail("Exception cleanup must continue native error handling")
    expected_header = None if stripped else b"Bearer test-token"
    if request.headers.get("Authorization") != expected_header:
        pytest.fail("Exception cleanup must use the configured Graph host")
    if middleware.stats.get_value(
        "microsoft_graph/auth/credential_stripped_exception_count", 0
    ) != int(stripped):
        pytest.fail("Exception cleanup must retain neutral default stats")


def test_configured_host_still_requires_https(auth):
    middleware, token, _ = auth
    request = Request(
        "http://graph.example/beta/me",
        headers={"Authorization": "Bearer external-token"},
    )

    with pytest.raises(IgnoreRequest, match="non-HTTPS Microsoft Graph"):
        asyncio.run(middleware.process_request(request))

    if "Authorization" in request.headers or token.await_count:
        pytest.fail("An insecure Graph request must not retain or acquire a token")
    if (
        middleware.stats.get_value("microsoft_graph/auth/insecure_scheme_blocked_count")
        != 1
    ):
        pytest.fail("Insecure Graph requests must retain neutral default stats")
