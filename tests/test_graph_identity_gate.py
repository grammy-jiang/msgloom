"""Verify Microsoft Graph source identity gates before request execution."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import pytest
from scrapy.exceptions import CloseSpider, NotConfigured
from scrapy.utils.misc import build_from_crawler
from scrapy.utils.test import get_crawler

import message_ingest.providers.microsoft_graph.identity_gate as gate_module
from message_ingest.providers.microsoft_graph.accounts import (
    MicrosoftGraphAuthError,
)
from message_ingest.providers.microsoft_graph.identity_gate import (
    MicrosoftGraphSourceIdentityExtension,
)
from message_ingest.spiders.outlook_discover import OutlookDiscoverSpider


def _crawler(
    tmp_path: Path,
    *,
    auth_method: str = "device_code",
    catalog=True,
    identity_required: bool = True,
):
    crawler = get_crawler(
        OutlookDiscoverSpider,
        settings_dict={
            "MS_GRAPH_AUTH_METHOD": auth_method,
            "MS_GRAPH_CLIENT_ID": "test-client-id",
            "MS_GRAPH_TOKEN_CACHE": str(tmp_path / "token-cache.json"),
            "MSGLOOM_CATALOG_ENABLED": catalog,
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_SOURCE_ID": "source-1",
            "MSGLOOM_SOURCE_IDENTITY_REQUIRED": identity_required,
        },
    )
    spider = OutlookDiscoverSpider.from_crawler(crawler)
    crawler.spider = spider
    return crawler, spider


def test_real_graph_with_auth_disabled_closes_before_requests(tmp_path: Path) -> None:
    crawler, spider = _crawler(tmp_path, auth_method="none")
    extension = build_from_crawler(MicrosoftGraphSourceIdentityExtension, crawler)

    with pytest.raises(CloseSpider) as excinfo:
        asyncio.run(extension.spider_opened(spider))

    if excinfo.value.reason != "source_identity_failed":
        pytest.fail("Expected source identity close reason")
    if spider.run_failed is not True:
        pytest.fail("Expected identity gate failure to mark logical run failed")
    if crawler.stats.get_value("downloader/request_count") is not None:
        pytest.fail("Expected no downloader request before identity gate")
    if crawler.stats.get_value("msgloom/source_identity/gate_state") != "failed":
        pytest.fail("Expected failed source identity gate stat")


def test_explicitly_disabled_identity_requirement_skips_gate(
    tmp_path: Path,
) -> None:
    crawler, spider = _crawler(
        tmp_path,
        auth_method="none",
        identity_required=False,
    )
    extension = build_from_crawler(MicrosoftGraphSourceIdentityExtension, crawler)

    asyncio.run(extension.spider_opened(spider))

    if crawler.stats.get_value("msgloom/source_identity/gate_state") != "disabled":
        pytest.fail("Expected explicit identity requirement disable to skip gate")
    if spider.run_failed:
        pytest.fail("Expected explicit gate disable not to fail logical run")


def test_successful_gate_awaits_shared_auth_session(
    tmp_path: Path,
    monkeypatch,
) -> None:
    crawler, spider = _crawler(tmp_path)
    extension = build_from_crawler(MicrosoftGraphSourceIdentityExtension, crawler)

    class FakeSession:
        def __init__(self) -> None:
            self.called = False

        async def establish_source_identity(self) -> None:
            self.called = True

    fake = FakeSession()
    monkeypatch.setattr(
        gate_module.MicrosoftGraphAuthSession,
        "from_crawler",
        lambda crawler: fake,
    )

    asyncio.run(extension.spider_opened(spider))

    if fake.called is not True:
        pytest.fail("Expected startup gate to await auth session identity")
    if spider.run_failed:
        pytest.fail("Expected successful identity gate not to fail run")


def test_catalog_disabled_does_not_install_identity_gate(tmp_path: Path) -> None:
    crawler, _spider = _crawler(tmp_path, catalog=False)

    with pytest.raises(NotConfigured):
        build_from_crawler(MicrosoftGraphSourceIdentityExtension, crawler)


def test_scrapy_contract_check_skips_live_identity_gate(
    tmp_path: Path,
    monkeypatch,
) -> None:
    crawler, spider = _crawler(tmp_path, auth_method="none")
    extension = build_from_crawler(MicrosoftGraphSourceIdentityExtension, crawler)
    monkeypatch.setenv("SCRAPY_CHECK", "true")

    asyncio.run(extension.spider_opened(spider))

    if crawler.stats.get_value("msgloom/source_identity/gate_state") != (
        "contract_check_skipped"
    ):
        pytest.fail("Expected Scrapy contract mode to skip live account gate")
    if spider.run_failed:
        pytest.fail("Expected contract check skip not to fail logical run")



def test_safe_auth_gate_error_detail_is_logged(
    tmp_path: Path,
    monkeypatch,
    caplog,
) -> None:
    crawler, spider = _crawler(tmp_path)
    extension = build_from_crawler(MicrosoftGraphSourceIdentityExtension, crawler)

    class FakeSession:
        async def establish_source_identity(self) -> None:
            raise MicrosoftGraphAuthError(
                "Set MSGLOOM_MS_CLIENT_ID before a live Microsoft Graph crawl"
            )

    monkeypatch.setattr(
        gate_module.MicrosoftGraphAuthSession,
        "from_crawler",
        lambda crawler: FakeSession(),
    )
    caplog.set_level(
        logging.ERROR,
        logger="message_ingest.providers.microsoft_graph.identity_gate",
    )

    with pytest.raises(CloseSpider):
        asyncio.run(extension.spider_opened(spider))

    if "Set MSGLOOM_MS_CLIENT_ID" not in caplog.text:
        pytest.fail("Expected safe actionable authentication detail in gate log")


def test_unknown_gate_exception_text_is_not_logged(
    tmp_path: Path,
    monkeypatch,
    caplog,
) -> None:
    crawler, spider = _crawler(tmp_path)
    extension = build_from_crawler(MicrosoftGraphSourceIdentityExtension, crawler)

    class FakeSession:
        async def establish_source_identity(self) -> None:
            raise RuntimeError("private-provider-secret")

    monkeypatch.setattr(
        gate_module.MicrosoftGraphAuthSession,
        "from_crawler",
        lambda crawler: FakeSession(),
    )
    caplog.set_level(
        logging.ERROR,
        logger="message_ingest.providers.microsoft_graph.identity_gate",
    )

    with pytest.raises(CloseSpider):
        asyncio.run(extension.spider_opened(spider))

    if "RuntimeError" not in caplog.text:
        pytest.fail("Expected unknown gate error type in log")
    if "private-provider-secret" in caplog.text:
        pytest.fail("Expected arbitrary exception text not to enter gate log")
