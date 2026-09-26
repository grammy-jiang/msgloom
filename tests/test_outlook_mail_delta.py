from __future__ import annotations

import asyncio
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from scrapy.exceptions import CloseSpider
from scrapy.http import Request, TextResponse
from scrapy.utils.misc import build_from_crawler
from scrapy.utils.test import get_crawler
from twisted.python.failure import Failure

from msgloom.checkpoints import OutlookDeltaCheckpointStore
from msgloom.extensions import OutlookDeltaCheckpointExtension
from msgloom.items import (
    AcquisitionFailureItem,
    OutlookDeltaCheckpointCandidateItem,
    OutlookMailFolderItem,
    OutlookMailItem,
    OutlookMailRemovalItem,
)
from msgloom.pipelines import CatalogPipeline
from msgloom.spiders.outlook_mail import OutlookMailSpider
from msgloom.services import get_catalog_service


FIXTURES = Path(__file__).parent / "fixtures" / "microsoft_graph"


def _db_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'catalog.sqlite3'}"


def _crawler(tmp_path: Path):
    return get_crawler(
        OutlookMailSpider,
        settings_dict={
            "MSGLOOM_DATABASE_URL": _db_url(tmp_path),
            "MSGLOOM_SOURCE_ID": "test-source",
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_DELTA_CHECKPOINT_ENABLED": True,
        },
    )


def _spider(tmp_path: Path, **kwargs) -> OutlookMailSpider:
    return OutlookMailSpider.from_crawler(_crawler(tmp_path), **kwargs)


async def _collect_start(spider: OutlookMailSpider) -> list[object]:
    return [value async for value in spider.start()]


def _response(request: Request, filename: str) -> TextResponse:
    return TextResponse(
        url=request.url,
        request=request,
        status=200,
        headers={"Content-Type": "application/json"},
        body=(FIXTURES / filename).read_bytes(),
        encoding="utf-8",
    )


def test_delta_mode_starts_with_uncached_hidden_folder_inventory(tmp_path: Path) -> None:
    spider = _spider(tmp_path, sync_mode="delta", page_size="100")
    request = asyncio.run(_collect_start(spider))[0]
    assert isinstance(request, Request)
    parsed = urlsplit(request.url)
    assert parsed.path == "/v1.0/me/mailFolders"
    query = parse_qs(parsed.query)
    assert query["includeHiddenFolders"] == ["true"]
    assert query["$top"] == ["100"]
    assert request.meta["dont_cache"] is True
    assert request.cb_kwargs["purpose"] == "folder-list"
    assert "parent_folder_id" not in request.meta


def test_folder_inventory_recurses_and_starts_one_delta_per_unique_folder(tmp_path: Path) -> None:
    spider = _spider(tmp_path, sync_mode="delta")
    root_request = asyncio.run(_collect_start(spider))[0]
    output = list(spider.parse_folders(_response(root_request, "mail_folders_root.json"), **root_request.cb_kwargs))

    folder_items = [value for value in output if isinstance(value, OutlookMailFolderItem)]
    requests = [value for value in output if isinstance(value, Request)]
    assert {item.folder_id for item in folder_items} == {"folder-inbox", "folder-hidden"}
    assert len([r for r in requests if r.cb_kwargs["purpose"] == "message-delta"]) == 2
    assert len([r for r in requests if r.cb_kwargs["purpose"] == "folder-child-list"]) == 1
    assert len([r for r in requests if r.cb_kwargs["purpose"] == "folder-list"]) == 1
    assert all(r.meta["dont_cache"] is True for r in requests)


def test_message_delta_follows_nextlink_then_emits_checkpoint_candidate(tmp_path: Path) -> None:
    spider = _spider(tmp_path, sync_mode="delta")
    asyncio.run(_collect_start(spider))
    first_request = spider._message_delta_start_request("folder-inbox")
    first_output = list(
        spider.parse_message_delta(
            _response(first_request, "message_delta_page_1.json"),
            **first_request.cb_kwargs,
        )
    )
    assert any(isinstance(value, OutlookMailItem) for value in first_output)
    next_request = next(value for value in first_output if isinstance(value, Request))
    expected_next = json.loads((FIXTURES / "message_delta_page_1.json").read_text())[
        "@odata.nextLink"
    ]
    assert next_request.url == expected_next
    assert next_request.meta["dont_cache"] is True

    second_output = list(
        spider.parse_message_delta(
            _response(next_request, "message_delta_page_2.json"),
            **next_request.cb_kwargs,
        )
    )
    removal = next(value for value in second_output if isinstance(value, OutlookMailRemovalItem))
    candidate = next(
        value for value in second_output if isinstance(value, OutlookDeltaCheckpointCandidateItem)
    )
    assert removal.message_id == "delta-message-removed"
    assert removal.removed_reason == "deleted"
    assert candidate.folder_id == "folder-inbox"
    assert "$deltatoken=opaque-delta" in candidate.delta_link


def test_successful_idle_commits_all_sqlalchemy_candidates_atomically(tmp_path: Path) -> None:
    crawler = _crawler(tmp_path)
    spider = OutlookMailSpider.from_crawler(crawler, sync_mode="delta")
    crawler.stats.set_value("msgloom/crawl/delta/folder_started_count", 1)
    crawler.stats.set_value("msgloom/crawl/delta/folder_completed_count", 1)
    crawler.stats.set_value("msgloom/crawl/delta/folder_inventory_completed", True)
    crawler.stats.set_value("msgloom/crawl/reconcile/completed", True)

    pipeline = CatalogPipeline.from_crawler(crawler)
    try:
        asyncio.run(pipeline.process_item(
            OutlookDeltaCheckpointCandidateItem(
                run_id=spider.run_id,
                folder_id="folder-inbox",
                delta_link="https://graph.microsoft.com/v1.0/me/mailFolders/folder-inbox/messages/delta?$deltatoken=committed",
                observed_at="2026-09-26T00:00:00+00:00",
                evidence_id="evidence-1",
            )
        ))
    finally:
        get_catalog_service(crawler).spider_closed(None, "test-finished")

    extension = build_from_crawler(OutlookDeltaCheckpointExtension, crawler)
    try:
        extension.spider_idle(spider)
    finally:
        get_catalog_service(crawler).spider_closed(spider, "finished")

    store = OutlookDeltaCheckpointStore(_db_url(tmp_path), "test-source")
    try:
        assert "$deltatoken=committed" in (store.get_delta_link("folder-inbox") or "")
    finally:
        store.close()
    assert crawler.stats.get_value("msgloom/checkpoint/commit_count") == 1
    assert (tmp_path / "catalog.sqlite3").stat().st_mode & 0o777 == 0o600


def test_incomplete_delta_round_does_not_advance_checkpoint(tmp_path: Path) -> None:
    crawler = _crawler(tmp_path)
    spider = OutlookMailSpider.from_crawler(crawler, sync_mode="delta")
    crawler.stats.set_value("msgloom/crawl/delta/folder_started_count", 2)
    crawler.stats.set_value("msgloom/crawl/delta/folder_completed_count", 1)
    extension = build_from_crawler(OutlookDeltaCheckpointExtension, crawler)
    try:
        with pytest.raises(CloseSpider) as excinfo:
            extension.spider_idle(spider)
        assert excinfo.value.reason == "delta_incomplete"
    finally:
        get_catalog_service(crawler).spider_closed(spider, "delta_incomplete")

    store = OutlookDeltaCheckpointStore(_db_url(tmp_path), "test-source")
    try:
        assert store.get_delta_link("folder-inbox") is None
    finally:
        store.close()


def test_existing_checkpoint_is_used_verbatim_and_bypasses_http_cache(tmp_path: Path) -> None:
    store = OutlookDeltaCheckpointStore(_db_url(tmp_path), "test-source")
    store.write_candidate(
        run_id="setup",
        folder_id="folder-inbox",
        delta_link="https://graph.microsoft.com/v1.0/me/mailFolders/folder-inbox/messages/delta?$deltatoken=opaque-existing",
        observed_at="2026-09-26T00:00:00+00:00",
    )
    store.commit("setup")
    store.close()

    spider = _spider(tmp_path, sync_mode="delta")
    asyncio.run(_collect_start(spider))
    request = spider._message_delta_start_request("folder-inbox")
    assert request.url.endswith("$deltatoken=opaque-existing")
    assert request.meta["dont_cache"] is True
    assert request.cb_kwargs["folder_id"] == "folder-inbox"


def test_global_reconciliation_streams_only_orphans_without_accumulating_mailbox(tmp_path: Path) -> None:
    spider = _spider(tmp_path, sync_mode="delta")
    spider._seen_folder_ids.add("folder-inbox")
    request = spider._global_reconciliation_request()
    body = json.dumps(
        {
            "value": [
                {"id": "known", "parentFolderId": "folder-inbox"},
                {"id": "orphan", "parentFolderId": "unavailable-folder"},
            ]
        }
    ).encode()
    response = TextResponse(
        url=request.url,
        request=request,
        status=200,
        headers={"Content-Type": "application/json"},
        body=body,
        encoding="utf-8",
    )
    output = list(spider.parse_global_reconciliation(response, **request.cb_kwargs))
    recovery = [value for value in output if isinstance(value, Request)]
    assert len(recovery) == 1
    assert recovery[0].cb_kwargs["message_id"] == "orphan"
    assert not hasattr(spider, "_reconcile_messages")


def test_folder_request_failure_marks_inventory_failed_and_never_starts_reconciliation(tmp_path: Path) -> None:
    spider = _spider(tmp_path, sync_mode="delta")
    request = asyncio.run(_collect_start(spider))[0]
    failure = Failure(RuntimeError("boom"))
    failure.request = request

    output = list(spider.errback(failure))

    assert len(output) == 1
    assert isinstance(output[0], AcquisitionFailureItem)
    assert spider._folder_inventory_failed is True
    assert spider._folder_inventory_pending == 0
    assert spider.crawler.stats.get_value("msgloom/crawl/delta/folder_inventory_failed") is True


def test_item_pipeline_error_blocks_delta_checkpoint_commit(tmp_path: Path) -> None:
    crawler = _crawler(tmp_path)
    spider = OutlookMailSpider.from_crawler(crawler, sync_mode="delta")
    crawler.stats.set_value("msgloom/crawl/delta/folder_started_count", 1)
    crawler.stats.set_value("msgloom/crawl/delta/folder_completed_count", 1)
    crawler.stats.set_value("msgloom/crawl/delta/folder_inventory_completed", True)
    crawler.stats.set_value("msgloom/crawl/reconcile/completed", True)

    pipeline = CatalogPipeline.from_crawler(crawler)
    asyncio.run(
        pipeline.process_item(
            OutlookDeltaCheckpointCandidateItem(
                run_id=spider.run_id,
                folder_id="folder-inbox",
                delta_link="https://graph.microsoft.com/v1.0/me/mailFolders/folder-inbox/messages/delta?$deltatoken=pending",
                observed_at="2026-09-26T00:00:00+00:00",
                evidence_id="evidence-1",
            )
        )
    )

    extension = build_from_crawler(OutlookDeltaCheckpointExtension, crawler)
    crawler.stats.set_value("msgloom/persistence/item_error_count", 1)
    with pytest.raises(CloseSpider) as excinfo:
        extension.spider_idle(spider)
    assert excinfo.value.reason == "delta_incomplete"

    store = OutlookDeltaCheckpointStore(_db_url(tmp_path), "test-source")
    try:
        assert store.get_delta_link("folder-inbox") is None
    finally:
        store.close()
