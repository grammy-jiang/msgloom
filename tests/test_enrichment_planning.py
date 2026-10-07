"""
Plan Full-v1 gaps from persisted surfaces, including terminal unsupported
attachments.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from outlook_mail_handoff_fixtures import saved_mail_evidence
from scrapy import Request
from scrapy.http import TextResponse
from scrapy.utils.test import get_crawler
from test_mail_inventory_bindings import seed_inventory

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


def _primary(catalog, message_id):
    """Seed exact saved primary evidence before any Full component fixture."""
    store = OutlookMailStore(catalog, source_id="source-1")
    message = {"id": message_id, "changeKey": "fixture-v1"}
    evidence_id = f"primary-{message_id}"
    saved_mail_evidence(
        catalog,
        evidence_id=evidence_id,
        body=json.dumps(message).encode(),
        observed_at="2026-09-26T04:00:00+00:00",
    )
    return store.record_message(
        run_id="fixture-run",
        message=message,
        kind="detail",
        selection_id=f"selection-{message_id}",
        evidence_id=evidence_id,
        observed_at="2026-09-26T04:00:00+00:00",
    ).fact.source_state_key


def _seed_surface(
    catalog: Catalog,
    message_id: str,
    surface: str,
    *,
    status: str = "acquired",
    profile_version: str | None = FULL_V1,
) -> None:
    parent = _primary(catalog, message_id)
    if surface == "attachments":
        seed_inventory(
            OutlookMailStore(catalog, source_id="source-1"),
            message_id,
            f"selection-{message_id}",
            parent,
            f"primary-{message_id}",
            [],
            when="2026-09-26T04:00:00+00:00",
            status=status,
            profile=profile_version,
        )
        return
    saved_mail_evidence(catalog, evidence_id=f"ev-{surface}")
    OutlookMailStore(catalog, source_id="source-1").set_surface(
        run_id="fixture-run",
        message_id=message_id,
        surface=surface,
        resource_version=parent,
        selection_id=f"selection-{message_id}",
        parent_evidence_id=f"primary-{message_id}",
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
    parent = _primary(catalog, message_id)
    seed_inventory(
        OutlookMailStore(catalog, source_id="source-1"),
        message_id,
        f"selection-{message_id}",
        parent,
        f"primary-{message_id}",
        [
            {
                "id": attachment_id,
                "@odata.type": attachment_type,
                "name": attachment_id,
                "size": 10,
                "isInline": False,
            }
        ],
        when="2026-09-26T04:00:00+00:00",
    )


async def _start(spider: OutlookFullSpider) -> list[object]:
    result: list[object] = [value async for value in spider.start()]
    if spider.operation == "refresh":
        for request in list(result):
            if not isinstance(request, Request):
                continue
            payload = {"id": request.cb_kwargs["message_id"], "changeKey": "fixture-v1"}
            response = TextResponse(
                request.url,
                request=request,
                body=json.dumps(payload).encode(),
                encoding="utf-8",
            )
            result.extend(
                child
                for child in spider.parse_message_detail(
                    response,
                    **request.cb_kwargs,
                )
                if isinstance(child, Request)
            )
    return result


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
