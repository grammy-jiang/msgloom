"""
Verify folder traversal, checkpoint integrity gates, and persisted delta
execution state.
"""

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

from message_ingest.checkpoints import OutlookDeltaCheckpointStore
from message_ingest.extensions.catalog import CatalogService
from message_ingest.extensions.delta_checkpoint import OutlookDeltaCheckpointExtension
from message_ingest.items.acquisition import AcquisitionFailureItem
from message_ingest.items.microsoft.outlook.email import (
    OutlookDeltaCheckpointCandidateItem,
    OutlookMailFolderItem,
    OutlookMailItem,
    OutlookMailRemovalItem,
)
from message_ingest.pipelines.catalog import CatalogPipeline
from message_ingest.spiders.microsoft.outlook.email.delta import OutlookDeltaSpider

FIXTURES = Path(__file__).parent / "fixtures" / "microsoft_graph"


def _db_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'catalog.sqlite3'}"


def _crawler(tmp_path: Path):
    return get_crawler(
        OutlookDeltaSpider,
        settings_dict={
            "MSGLOOM_DATABASE_URL": _db_url(tmp_path),
            "MSGLOOM_SOURCE_ID": "test-source",
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_DELTA_CHECKPOINT_ENABLED": True,
        },
    )


def _spider(tmp_path: Path, **kwargs) -> OutlookDeltaSpider:
    return OutlookDeltaSpider.from_crawler(_crawler(tmp_path), **kwargs)


async def _collect_start(spider: OutlookDeltaSpider) -> list[Request]:
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


def test_delta_mode_starts_with_uncached_hidden_folder_inventory(
    tmp_path: Path,
) -> None:
    spider = _spider(tmp_path, page_size="100")
    request = asyncio.run(_collect_start(spider))[0]
    if not isinstance(request, Request):
        pytest.fail("Expected: isinstance(request, Request)")
    parsed = urlsplit(request.url)
    if parsed.path != "/v1.0/me/mailFolders":
        pytest.fail('Expected: parsed.path == "/v1.0/me/mailFolders"')
    query = parse_qs(parsed.query)
    if query["includeHiddenFolders"] != ["true"]:
        pytest.fail('Expected: query["includeHiddenFolders"] == ["true"]')
    if query["$top"] != ["100"]:
        pytest.fail('Expected: query["$top"] == ["100"]')
    if request.meta["dont_cache"] is not True:
        pytest.fail('Expected: request.meta["dont_cache"] is True')
    if request.cb_kwargs["purpose"] != "folder-list":
        pytest.fail('Expected: request.cb_kwargs["purpose"] == "folder-list"')
    if "parent_folder_id" in request.meta:
        pytest.fail('Expected: "parent_folder_id" not in request.meta')


def test_folder_inventory_recurses_and_starts_one_delta_per_unique_folder(
    tmp_path: Path,
) -> None:
    spider = _spider(tmp_path)
    root_request = asyncio.run(_collect_start(spider))[0]
    output = list(
        spider.parse_folders(
            _response(root_request, "mail_folders_root.json"), **root_request.cb_kwargs
        )
    )

    folder_items = [
        value for value in output if isinstance(value, OutlookMailFolderItem)
    ]
    requests = [value for value in output if isinstance(value, Request)]
    if {item.folder_id for item in folder_items} != {"folder-inbox", "folder-hidden"}:
        pytest.fail(
            'Expected: {item.folder_id for item in folder_items} == {"folder-inbox", "folder-hidden"}'
        )
    if len([r for r in requests if r.cb_kwargs["purpose"] == "message-delta"]) != 2:
        pytest.fail(
            'Expected: len([r for r in requests if r.cb_kwargs["purpose"] == "message-delta"]) == 2'
        )
    if len([r for r in requests if r.cb_kwargs["purpose"] == "folder-child-list"]) != 1:
        pytest.fail(
            'Expected: len([r for r in requests if r.cb_kwargs["purpose"] == "folder-child-list"]) == 1'
        )
    if len([r for r in requests if r.cb_kwargs["purpose"] == "folder-list"]) != 1:
        pytest.fail(
            'Expected: len([r for r in requests if r.cb_kwargs["purpose"] == "folder-list"]) == 1'
        )
    if not all(r.meta["dont_cache"] is True for r in requests):
        pytest.fail('Expected: all(r.meta["dont_cache"] is True for r in requests)')


def test_message_delta_follows_nextlink_then_emits_checkpoint_candidate(
    tmp_path: Path,
) -> None:
    spider = _spider(tmp_path)
    asyncio.run(_collect_start(spider))
    first_request = spider._message_delta_start_request("folder-inbox")
    first_output = list(
        spider.parse_message_delta(
            _response(first_request, "message_delta_page_1.json"),
            **first_request.cb_kwargs,
        )
    )
    if not any(isinstance(value, OutlookMailItem) for value in first_output):
        pytest.fail(
            "Expected: any(isinstance(value, OutlookMailItem) for value in first_output)"
        )
    next_request = next(value for value in first_output if isinstance(value, Request))
    expected_next = json.loads((FIXTURES / "message_delta_page_1.json").read_text())[
        "@odata.nextLink"
    ]
    if next_request.url != expected_next:
        pytest.fail("Expected: next_request.url == expected_next")
    if next_request.meta["dont_cache"] is not True:
        pytest.fail('Expected: next_request.meta["dont_cache"] is True')

    second_output = list(
        spider.parse_message_delta(
            _response(next_request, "message_delta_page_2.json"),
            **next_request.cb_kwargs,
        )
    )
    removal = next(
        value for value in second_output if isinstance(value, OutlookMailRemovalItem)
    )
    candidate = next(
        value
        for value in second_output
        if isinstance(value, OutlookDeltaCheckpointCandidateItem)
    )
    if removal.message_id != "delta-message-removed":
        pytest.fail('Expected: removal.message_id == "delta-message-removed"')
    if removal.removed_reason != "deleted":
        pytest.fail('Expected: removal.removed_reason == "deleted"')
    if candidate.folder_id != "folder-inbox":
        pytest.fail('Expected: candidate.folder_id == "folder-inbox"')
    if "$deltatoken=opaque-delta" not in candidate.delta_link:
        pytest.fail('Expected: "$deltatoken=opaque-delta" in candidate.delta_link')


def test_successful_idle_commits_all_sqlalchemy_candidates_atomically(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path)
    spider = OutlookDeltaSpider.from_crawler(crawler)
    spider._started_folder_ids = {"folder-inbox"}
    spider._completed_folder_ids = {"folder-inbox"}
    spider._folder_inventory_complete = True
    spider._reconcile_complete = True
    spider._persist_execution_state()

    pipeline = CatalogPipeline.from_crawler(crawler)
    asyncio.run(
        pipeline.process_item(
            OutlookDeltaCheckpointCandidateItem(
                run_id=spider.run_id,
                folder_id="folder-inbox",
                delta_link="https://graph.microsoft.com/v1.0/me/mailFolders/folder-inbox/messages/delta?$deltatoken=committed",
                observed_at="2026-09-26T00:00:00+00:00",
                evidence_id=None,
            )
        )
    )

    extension = build_from_crawler(OutlookDeltaCheckpointExtension, crawler)
    try:
        extension.spider_idle(spider)
    finally:
        CatalogService.from_crawler(crawler).spider_closed(spider, "finished")

    store = OutlookDeltaCheckpointStore(_db_url(tmp_path), "test-source")
    try:
        if "$deltatoken=committed" not in (store.get_delta_link("folder-inbox") or ""):
            pytest.fail(
                'Expected: "$deltatoken=committed" in (store.get_delta_link("folder-inbox") or "")'
            )
    finally:
        store.close()
    if crawler.stats.get_value("msgloom/checkpoint/commit_count") != 1:
        pytest.fail(
            'Expected: crawler.stats.get_value("msgloom/checkpoint/commit_count") == 1'
        )
    if (tmp_path / "catalog.sqlite3").stat().st_mode & 511 != 384:
        pytest.fail(
            'Expected: (tmp_path / "catalog.sqlite3").stat().st_mode & 0o777 == 0o600'
        )


def test_incomplete_delta_round_does_not_advance_checkpoint(tmp_path: Path) -> None:
    crawler = _crawler(tmp_path)
    spider = OutlookDeltaSpider.from_crawler(crawler)
    spider._started_folder_ids = {"folder-one", "folder-two"}
    spider._completed_folder_ids = {"folder-one"}
    spider._folder_inventory_complete = True
    spider._reconcile_complete = True
    spider._persist_execution_state()
    extension = build_from_crawler(OutlookDeltaCheckpointExtension, crawler)
    try:
        with pytest.raises(CloseSpider) as excinfo:
            extension.spider_idle(spider)
        if excinfo.value.reason != "delta_incomplete":
            pytest.fail('Expected: excinfo.value.reason == "delta_incomplete"')
    finally:
        CatalogService.from_crawler(crawler).spider_closed(spider, "delta_incomplete")

    store = OutlookDeltaCheckpointStore(_db_url(tmp_path), "test-source")
    try:
        if store.get_delta_link("folder-inbox") is not None:
            pytest.fail('Expected: store.get_delta_link("folder-inbox") is None')
    finally:
        store.close()


def test_existing_checkpoint_is_used_verbatim_and_bypasses_http_cache(
    tmp_path: Path,
) -> None:
    store = OutlookDeltaCheckpointStore(_db_url(tmp_path), "test-source")
    store.write_candidate(
        run_id="setup",
        folder_id="folder-inbox",
        delta_link="https://graph.microsoft.com/v1.0/me/mailFolders/folder-inbox/messages/delta?$deltatoken=opaque-existing",
        observed_at="2026-09-26T00:00:00+00:00",
    )
    store.commit("setup")
    store.close()

    spider = _spider(tmp_path)
    asyncio.run(_collect_start(spider))
    request = spider._message_delta_start_request("folder-inbox")
    if not request.url.endswith("$deltatoken=opaque-existing"):
        pytest.fail('Expected: request.url.endswith("$deltatoken=opaque-existing")')
    if request.meta["dont_cache"] is not True:
        pytest.fail('Expected: request.meta["dont_cache"] is True')
    if request.cb_kwargs["folder_id"] != "folder-inbox":
        pytest.fail('Expected: request.cb_kwargs["folder_id"] == "folder-inbox"')


def test_global_reconciliation_streams_only_orphans_without_accumulating_mailbox(
    tmp_path: Path,
) -> None:
    spider = _spider(tmp_path)
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
    if len(recovery) != 1:
        pytest.fail("Expected: len(recovery) == 1")
    if recovery[0].cb_kwargs["message_id"] != "orphan":
        pytest.fail('Expected: recovery[0].cb_kwargs["message_id"] == "orphan"')
    if hasattr(spider, "_reconcile_messages"):
        pytest.fail('Expected: not hasattr(spider, "_reconcile_messages")')


def test_folder_request_failure_marks_inventory_failed_and_never_starts_reconciliation(
    tmp_path: Path,
) -> None:
    spider = _spider(tmp_path)
    request = asyncio.run(_collect_start(spider))[0]
    failure = Failure(RuntimeError("boom"))
    # Scrapy attaches this attribute dynamically before calling an errback.
    failure.__dict__["request"] = request

    output = list(spider.errback(failure))

    if not any(isinstance(value, AcquisitionFailureItem) for value in output):
        pytest.fail(
            "Expected: any(isinstance(value, AcquisitionFailureItem) for value in output)"
        )
    if spider._folder_inventory_failed is not True:
        pytest.fail("Expected: spider._folder_inventory_failed is True")
    if spider._folder_inventory_pending != 0:
        pytest.fail("Expected: spider._folder_inventory_pending == 0")
    if (
        spider.crawler.stats.get_value("msgloom/crawl/delta/folder_inventory_failed")
        is not True
    ):
        pytest.fail(
            'Expected: spider.crawler.stats.get_value("msgloom/crawl/delta/folder_inventory_failed") is True'
        )
