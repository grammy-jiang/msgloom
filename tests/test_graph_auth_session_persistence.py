"""Verify Microsoft Graph auth-session persistence and gate contracts."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import pytest
from scrapy.utils.test import get_crawler

from message_ingest.acquisition.source_identity import SourceIdentityService
from message_ingest.providers.microsoft_graph.auth_session import (
    MicrosoftGraphAuthError,
    MicrosoftGraphAuthSession,
)
from message_ingest.spiders.outlook_discover import OutlookDiscoverSpider


def _crawler(
    tmp_path: Path,
    *,
    catalog: bool = True,
):
    return get_crawler(
        OutlookDiscoverSpider,
        settings_dict={
            "MS_GRAPH_AUTH_METHOD": "device_code",
            "MS_GRAPH_CLIENT_ID": "test-client-id",
            "MS_GRAPH_AUTHORITY": "https://login.microsoftonline.com/common",
            "MS_GRAPH_TOKEN_CACHE": str(tmp_path / "token-cache.json"),
            "MS_GRAPH_ACCOUNT_USERNAME": "",
            "MS_GRAPH_AUTH_ALLOW_INTERACTIVE": True,
            "MSGLOOM_CATALOG_ENABLED": catalog,
            "MSGLOOM_SOURCE_IDENTITY_REQUIRED": True,
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_SOURCE_ID": "source-1",
        },
    )


def _account(key: str, username: str = "person@example.com") -> dict:
    return {"home_account_id": key, "username": username}


def test_verified_token_cache_write_is_atomic_and_private(
    tmp_path: Path,
    monkeypatch,
) -> None:
    crawler = _crawler(tmp_path, catalog=False)
    session = MicrosoftGraphAuthSession.from_crawler(crawler)
    session.token_cache.has_state_changed = True
    monkeypatch.setattr(
        type(session.token_cache),
        "serialize",
        lambda self: '{"cache":"verified"}',
    )
    session.token_cache_path.parent.mkdir(parents=True, exist_ok=True)
    session.token_cache_path.write_text("old", encoding="utf-8")
    session.token_cache_path.chmod(0o644)

    session._save_token_cache()

    if session.token_cache_path.read_text(encoding="utf-8") != '{"cache":"verified"}':
        pytest.fail("Expected complete serialized token cache replacement")
    if session.token_cache_path.stat().st_mode & 0o777 != 0o600:
        pytest.fail("Expected token cache mode 0600 after atomic replace")
    leftovers = list(
        session.token_cache_path.parent.glob(
            f".{session.token_cache_path.name}.*.tmp"
        )
    )
    if leftovers:
        pytest.fail(f"Expected no token cache temp files, found {leftovers!r}")


def test_failed_token_cache_replace_rearms_dirty_state(
    tmp_path: Path,
    monkeypatch,
) -> None:
    crawler = _crawler(tmp_path, catalog=False)
    session = MicrosoftGraphAuthSession.from_crawler(crawler)
    session.token_cache.has_state_changed = True
    monkeypatch.setattr(
        type(session.token_cache),
        "serialize",
        lambda self: '{"cache":"new"}',
    )
    session.token_cache_path.parent.mkdir(parents=True, exist_ok=True)
    session.token_cache_path.write_text("old", encoding="utf-8")

    def fail_replace(_source, _target) -> None:
        raise OSError("injected replace failure")

    monkeypatch.setattr(
        "message_ingest.providers.microsoft_graph.auth_session.os.replace",
        fail_replace,
    )

    with pytest.raises(OSError, match="injected replace failure"):
        session._save_token_cache()

    if session.token_cache.has_state_changed is not True:
        pytest.fail("Expected failed cache persistence to remain dirty")
    if session.token_cache_path.read_text(encoding="utf-8") != "old":
        pytest.fail("Expected failed replacement to preserve old cache")
    leftovers = list(
        session.token_cache_path.parent.glob(
            f".{session.token_cache_path.name}.*.tmp"
        )
    )
    if leftovers:
        pytest.fail(f"Expected failed save to clean temp files: {leftovers!r}")



def test_catalog_backed_token_is_blocked_until_identity_gate(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path)
    session = MicrosoftGraphAuthSession.from_crawler(crawler)
    called = False

    class FakeApp:
        @staticmethod
        def get_accounts(username=None):
            nonlocal called
            called = True
            return [_account("account-a")]

    session._app = FakeApp()  # type: ignore[assignment]

    with pytest.raises(MicrosoftGraphAuthError, match="gate has not completed"):
        asyncio.run(session.get_access_token())

    if called:
        pytest.fail("Expected identity guard to fail before any MSAL account lookup")


def test_bound_account_identifiers_do_not_enter_stats_or_logs(
    tmp_path: Path,
    caplog,
) -> None:
    crawler = _crawler(tmp_path)
    session = MicrosoftGraphAuthSession.from_crawler(crawler)
    account = _account("private-account-key", "private-person@example.com")

    class FakeApp:
        @staticmethod
        def get_accounts(username=None):
            return [account]

        @staticmethod
        def acquire_token_silent_with_error(scopes, account, force_refresh=False):
            return {"access_token": "private-access-token", "expires_in": 3600}

    session._app = FakeApp()  # type: ignore[assignment]
    caplog.set_level(logging.DEBUG)
    asyncio.run(session.establish_source_identity())

    binding = SourceIdentityService.from_crawler(crawler).get_binding()
    if binding is None:
        pytest.fail("Expected persisted source binding")
    exposed = (
        repr(crawler.stats.get_stats())
        + caplog.text
        + repr(binding)
    )
    for secret in (
        "private-account-key",
        "private-person@example.com",
        "private-access-token",
    ):
        if secret in exposed:
            pytest.fail(f"Expected provider identity secret not to be exposed: {secret}")
