"""
Plan Full-v1 gaps from persisted surfaces, including terminal unsupported
attachments.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from scrapy import Request
from scrapy.utils.test import get_crawler

from message_ingest.acquisition.microsoft.outlook.email.profile import FULL_V1
from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from message_ingest.items.microsoft.outlook.email import OutlookMessageSurfaceItem
from message_ingest.spiders.microsoft.outlook.email.full import OutlookFullSpider


def _settings(tmp_path: Path) -> dict:
    return {
        "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
        "MSGLOOM_SOURCE_ID": "source-1",
        "MSGLOOM_CATALOG_ENABLED": True,
    }


def _seed_surface(
    catalog: Catalog,
    message_id: str,
    surface: str,
    *,
    status: str = "acquired",
    profile_version: str | None = FULL_V1,
) -> None:
    OutlookMailStore(catalog, source_id="source-1").set_surface(
        message_id=message_id,
        surface=surface,
        status=status,
        evidence_id=f"ev-{surface}",
        observed_at="2026-09-26T04:00:00+00:00",
        profile_version=profile_version,
    )


def _seed_attachment(
    catalog: Catalog,
    message_id: str,
    attachment_id: str,
    attachment_type: str,
) -> None:
    OutlookMailStore(catalog, source_id="source-1").upsert_attachment(
        message_id=message_id,
        attachment={
            "id": attachment_id,
            "@odata.type": attachment_type,
            "name": attachment_id,
            "size": 10,
            "isInline": False,
        },
        evidence_id=f"ev-{attachment_id}",
        observed_at="2026-09-26T04:00:00+00:00",
    )


async def _start(spider: OutlookFullSpider) -> list[object]:
    return [value async for value in spider.start()]


def test_enrich_emits_no_work_when_full_v1_is_complete(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    catalog = Catalog(settings["MSGLOOM_DATABASE_URL"])
    try:
        for surface in ("detail", "mime", "attachments"):
            _seed_surface(catalog, "m1", surface)
    finally:
        catalog.close()

    crawler = get_crawler(OutlookFullSpider, settings_dict=settings)
    spider = OutlookFullSpider.from_crawler(
        crawler,
        message_ids="m1",
        operation="enrich",
    )
    output = asyncio.run(_start(spider))

    if output != []:
        pytest.fail("Expected: output == []")
    if crawler.stats.get_value("msgloom/crawl/enrichment/already_complete_count") != 1:
        pytest.fail(
            'Expected: crawler.stats.get_value("msgloom/crawl/enrichment/already_complete_count") == 1'
        )


def test_enrich_only_requests_missing_base_surface(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    catalog = Catalog(settings["MSGLOOM_DATABASE_URL"])
    try:
        _seed_surface(catalog, "m1", "detail")
        _seed_surface(catalog, "m1", "attachments")
    finally:
        catalog.close()

    crawler = get_crawler(OutlookFullSpider, settings_dict=settings)
    spider = OutlookFullSpider.from_crawler(
        crawler,
        message_ids="m1",
        operation="enrich",
    )
    output = asyncio.run(_start(spider))

    if len(output) != 1:
        pytest.fail("Expected: len(output) == 1")
    request = output[0]
    if not isinstance(request, Request):
        pytest.fail("Expected: isinstance(request, Request)")
    if request.cb_kwargs["purpose"] != "message-mime":
        pytest.fail('Expected: request.cb_kwargs["purpose"] == "message-mime"')


def test_enrich_uses_attachment_catalog_for_missing_child_surface(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    catalog = Catalog(settings["MSGLOOM_DATABASE_URL"])
    try:
        for surface in ("detail", "mime", "attachments"):
            _seed_surface(catalog, "m1", surface)
        _seed_attachment(
            catalog,
            "m1",
            "a-file",
            "#microsoft.graph.fileAttachment",
        )
    finally:
        catalog.close()

    crawler = get_crawler(OutlookFullSpider, settings_dict=settings)
    spider = OutlookFullSpider.from_crawler(
        crawler,
        message_ids="m1",
        operation="enrich",
    )
    output = asyncio.run(_start(spider))

    if len(output) != 1:
        pytest.fail("Expected: len(output) == 1")
    request = output[0]
    if not isinstance(request, Request):
        pytest.fail("Expected: isinstance(request, Request)")
    if request.cb_kwargs["purpose"] != "attachment-raw":
        pytest.fail('Expected: request.cb_kwargs["purpose"] == "attachment-raw"')
    if request.cb_kwargs["attachment_id"] != "a-file":
        pytest.fail('Expected: request.cb_kwargs["attachment_id"] == "a-file"')


def test_enrich_reference_attachment_records_terminal_unsupported_without_network(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    catalog = Catalog(settings["MSGLOOM_DATABASE_URL"])
    try:
        for surface in ("detail", "mime", "attachments"):
            _seed_surface(catalog, "m1", surface)
        _seed_attachment(
            catalog,
            "m1",
            "a-ref",
            "#microsoft.graph.referenceAttachment",
        )
    finally:
        catalog.close()

    crawler = get_crawler(OutlookFullSpider, settings_dict=settings)
    spider = OutlookFullSpider.from_crawler(
        crawler,
        message_ids="m1",
        operation="enrich",
    )
    output = asyncio.run(_start(spider))

    if len(output) != 1:
        pytest.fail("Expected: len(output) == 1")
    item = output[0]
    if not isinstance(item, OutlookMessageSurfaceItem):
        pytest.fail("Expected: isinstance(item, OutlookMessageSurfaceItem)")
    if item.surface != "attachment_raw:a-ref":
        pytest.fail('Expected: item.surface == "attachment_raw:a-ref"')
    if item.status != "unsupported":
        pytest.fail('Expected: item.status == "unsupported"')
    if item.profile_version != FULL_V1:
        pytest.fail("Expected: item.profile_version == FULL_V1")


def test_enrich_old_unversioned_surface_is_not_treated_as_full_v1_complete(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    catalog = Catalog(settings["MSGLOOM_DATABASE_URL"])
    try:
        _seed_surface(catalog, "m1", "detail", profile_version=None)
        _seed_surface(catalog, "m1", "mime")
        _seed_surface(catalog, "m1", "attachments")
    finally:
        catalog.close()

    crawler = get_crawler(OutlookFullSpider, settings_dict=settings)
    spider = OutlookFullSpider.from_crawler(
        crawler,
        message_ids="m1",
        operation="enrich",
    )
    output = asyncio.run(_start(spider))

    if len(output) != 1:
        pytest.fail("Expected: len(output) == 1")
    if not isinstance(output[0], Request):
        pytest.fail("Expected: isinstance(output[0], Request)")
    if output[0].cb_kwargs["purpose"] != "message-detail":
        pytest.fail('Expected: output[0].cb_kwargs["purpose"] == "message-detail"')


def test_refresh_always_requests_all_base_full_v1_surfaces(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    catalog = Catalog(settings["MSGLOOM_DATABASE_URL"])
    try:
        for surface in ("detail", "mime", "attachments"):
            _seed_surface(catalog, "m1", surface)
    finally:
        catalog.close()

    crawler = get_crawler(OutlookFullSpider, settings_dict=settings)
    spider = OutlookFullSpider.from_crawler(
        crawler,
        message_ids="m1",
        operation="refresh",
    )
    output = asyncio.run(_start(spider))

    if len(output) != 3:
        pytest.fail("Expected: len(output) == 3")
    purposes = set()
    for request in output:
        if not isinstance(request, Request):
            pytest.fail("Expected: isinstance(request, Request)")
        purposes.add(request.cb_kwargs["purpose"])
    if purposes != {"message-detail", "message-mime", "attachments-list"}:
        pytest.fail(
            'Expected: purposes == { "message-detail", "message-mime", "attachments-list", }'
        )


def test_enrich_unknown_attachment_type_records_terminal_unsupported(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    catalog = Catalog(settings["MSGLOOM_DATABASE_URL"])
    try:
        for surface in ("detail", "mime", "attachments"):
            _seed_surface(catalog, "m1", surface)
        _seed_attachment(
            catalog,
            "m1",
            "a-unknown",
            "#microsoft.graph.futureAttachment",
        )
    finally:
        catalog.close()

    crawler = get_crawler(OutlookFullSpider, settings_dict=settings)
    spider = OutlookFullSpider.from_crawler(
        crawler,
        message_ids="m1",
        operation="enrich",
    )
    output = asyncio.run(_start(spider))

    if len(output) != 1:
        pytest.fail("Expected: len(output) == 1")
    item = output[0]
    if not isinstance(item, OutlookMessageSurfaceItem):
        pytest.fail("Expected: isinstance(item, OutlookMessageSurfaceItem)")
    if item.surface != "attachment_raw:a-unknown":
        pytest.fail('Expected: item.surface == "attachment_raw:a-unknown"')
    if item.status != "unsupported":
        pytest.fail('Expected: item.status == "unsupported"')
    if item.profile_version != FULL_V1:
        pytest.fail("Expected: item.profile_version == FULL_V1")
