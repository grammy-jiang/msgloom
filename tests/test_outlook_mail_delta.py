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
from scrapy import signals
from scrapy.exceptions import CloseSpider
from scrapy.http import Request, TextResponse
from scrapy.utils.misc import build_from_crawler
from scrapy.utils.test import get_crawler
from twisted.python.failure import Failure

from message_ingest.checkpoints import OutlookDeltaCheckpointStore
from message_ingest.extensions.catalog import CatalogService
from message_ingest.extensions.delta_checkpoint import OutlookDeltaCheckpointExtension
from message_ingest.items import (
    AcquisitionFailureItem,
    OutlookDeltaCheckpointCandidateItem,
    OutlookMailFolderItem,
    OutlookMailItem,
    OutlookMailRemovalItem,
)
from message_ingest.pipelines.catalog import CatalogPipeline
from message_ingest.spiders.outlook_delta import OutlookDeltaSpider

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


def test_item_pipeline_error_blocks_delta_checkpoint_commit(tmp_path: Path) -> None:
    crawler = _crawler(tmp_path)
    spider = OutlookDeltaSpider.from_crawler(crawler)
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
                evidence_id=None,
            )
        )
    )

    extension = build_from_crawler(OutlookDeltaCheckpointExtension, crawler)
    crawler.stats.set_value("msgloom/persistence/item_error_count", 1)
    with pytest.raises(CloseSpider) as excinfo:
        extension.spider_idle(spider)
    if excinfo.value.reason != "delta_incomplete":
        pytest.fail('Expected: excinfo.value.reason == "delta_incomplete"')

    store = OutlookDeltaCheckpointStore(_db_url(tmp_path), "test-source")
    try:
        if store.get_delta_link("folder-inbox") is not None:
            pytest.fail('Expected: store.get_delta_link("folder-inbox") is None')
    finally:
        store.close()


def test_delta_execution_state_restores_run_identity_for_jobdir_resume(
    tmp_path: Path,
) -> None:
    crawler1 = _crawler(tmp_path)
    spider1 = OutlookDeltaSpider.from_crawler(crawler1)
    spider1.state = {}
    asyncio.run(_collect_start(spider1))
    original_run_id = spider1.run_id
    spider1._seen_folder_ids = {"folder-one", "folder-two"}
    spider1._started_folder_ids = {"folder-one", "folder-two"}
    spider1._completed_folder_ids = {"folder-one"}
    spider1._folder_inventory_pending = 1
    spider1._reconcile_complete = True
    spider1._delta_start_scheduled = True
    spider1._persist_execution_state()
    saved_state = json.loads(json.dumps(spider1.state))
    CatalogService.from_crawler(crawler1).spider_closed(spider1, "shutdown")

    crawler2 = _crawler(tmp_path)
    spider2 = OutlookDeltaSpider.from_crawler(crawler2)
    spider2.state = saved_state
    output = asyncio.run(_collect_start(spider2))

    if output != []:
        pytest.fail("Expected: output == []")
    if spider2.run_id != original_run_id:
        pytest.fail("Expected: spider2.run_id == original_run_id")
    if spider2._started_folder_ids != {"folder-one", "folder-two"}:
        pytest.fail(
            'Expected: spider2._started_folder_ids == {"folder-one", "folder-two"}'
        )
    if spider2._completed_folder_ids != {"folder-one"}:
        pytest.fail('Expected: spider2._completed_folder_ids == {"folder-one"}')
    if spider2._folder_inventory_pending != 1:
        pytest.fail("Expected: spider2._folder_inventory_pending == 1")
    if spider2.crawler.stats.get_value("msgloom/crawl/delta/job_resumed") is not True:
        pytest.fail(
            'Expected: spider2.crawler.stats.get_value("msgloom/crawl/delta/job_resumed") is True'
        )
    if spider2.crawler.stats.get_value("msgloom/crawl/reconcile/completed") is not True:
        pytest.fail(
            'Expected: spider2.crawler.stats.get_value("msgloom/crawl/reconcile/completed") is True'
        )
    CatalogService.from_crawler(crawler2).spider_closed(spider2, "finished")


def test_item_pipeline_error_blocks_checkpoint_commit_even_when_candidates_complete(
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
                delta_link="https://graph.microsoft.com/v1.0/me/mailFolders/folder-inbox/messages/delta?$deltatoken=must-not-commit",
                observed_at="2026-09-26T00:00:00+00:00",
                evidence_id=None,
            )
        )
    )

    extension = build_from_crawler(OutlookDeltaCheckpointExtension, crawler)
    extension.item_error(
        item=object(),
        response=None,
        spider=spider,
        failure=Failure(RuntimeError("catalog write failed")),
    )

    with pytest.raises(CloseSpider) as excinfo:
        extension.spider_idle(spider)
    if excinfo.value.reason != "delta_incomplete":
        pytest.fail('Expected: excinfo.value.reason == "delta_incomplete"')
    if "item_error" not in spider.delta_execution_snapshot()["failure_reasons"]:
        pytest.fail(
            'Expected: "item_error" in spider.delta_execution_snapshot()["failure_reasons"]'
        )

    store = OutlookDeltaCheckpointStore(_db_url(tmp_path), "test-source")
    try:
        if store.get_delta_link("folder-inbox") is not None:
            pytest.fail('Expected: store.get_delta_link("folder-inbox") is None')
    finally:
        store.close()
    CatalogService.from_crawler(crawler).spider_closed(spider, "delta_incomplete")


@pytest.mark.parametrize("signal_name", ["spider_error", "item_error", "item_dropped"])
def test_acquisition_error_signal_marks_delta_run_failed(
    tmp_path: Path,
    signal_name: str,
) -> None:
    crawler = _crawler(tmp_path)
    spider = OutlookDeltaSpider.from_crawler(crawler)
    extension = build_from_crawler(OutlookDeltaCheckpointExtension, crawler)

    crawler.signals.send_catch_log(
        signal=getattr(signals, signal_name),
        failure=Failure(RuntimeError("parse failed")),
        response=None,
        spider=spider,
        item=object(),
        exception=RuntimeError("item dropped"),
    )

    snapshot = spider.delta_execution_snapshot()
    if snapshot["run_failed"] is not True:
        pytest.fail('Expected: snapshot["run_failed"] is True')
    if signal_name not in snapshot["failure_reasons"]:
        pytest.fail('Expected: signal_name in snapshot["failure_reasons"]')
    with pytest.raises(CloseSpider) as excinfo:
        extension.spider_idle(spider)
    if excinfo.value.reason != "delta_incomplete":
        pytest.fail('Expected: excinfo.value.reason == "delta_incomplete"')
    CatalogService.from_crawler(crawler).spider_closed(spider, signal_name)


def test_checkpoint_candidate_read_failure_closes_delta_as_failed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    crawler = _crawler(tmp_path)
    spider = OutlookDeltaSpider.from_crawler(crawler)
    extension = build_from_crawler(OutlookDeltaCheckpointExtension, crawler)

    def fail_load(_run_id: str):
        raise RuntimeError("candidate read failed")

    monkeypatch.setattr(extension.store, "load_candidates", fail_load)

    with pytest.raises(CloseSpider) as excinfo:
        extension.spider_idle(spider)

    if excinfo.value.reason != "checkpoint_candidate_load_failed":
        pytest.fail(
            'Expected: excinfo.value.reason == "checkpoint_candidate_load_failed"'
        )
    if crawler.stats.get_value("msgloom/checkpoint/outcome") != "error":
        pytest.fail(
            'Expected: crawler.stats.get_value("msgloom/checkpoint/outcome") == "error"'
        )
    if crawler.stats.get_value("msgloom/checkpoint/error_stage") != "candidate_load":
        pytest.fail(
            'Expected: crawler.stats.get_value("msgloom/checkpoint/error_stage") == "candidate_load"'
        )
    snapshot = spider.delta_execution_snapshot()
    if snapshot["run_failed"] is not True:
        pytest.fail('Expected: snapshot["run_failed"] is True')
    if "checkpoint_candidate_load_failed" not in snapshot["failure_reasons"]:
        pytest.fail(
            'Expected: "checkpoint_candidate_load_failed" in snapshot["failure_reasons"]'
        )
    CatalogService.from_crawler(crawler).spider_closed(
        spider, "checkpoint_candidate_load_failed"
    )


def test_checkpoint_snapshot_failure_closes_delta_as_failed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    crawler = _crawler(tmp_path)
    spider = OutlookDeltaSpider.from_crawler(crawler)
    extension = build_from_crawler(OutlookDeltaCheckpointExtension, crawler)

    def fail_snapshot():
        raise RuntimeError("private snapshot failure")

    monkeypatch.setattr(spider, "delta_execution_snapshot", fail_snapshot)

    with pytest.raises(CloseSpider) as excinfo:
        extension.spider_idle(spider)

    if excinfo.value.reason != "checkpoint_evaluation_failed":
        pytest.fail('Expected: excinfo.value.reason == "checkpoint_evaluation_failed"')
    if crawler.stats.get_value("msgloom/checkpoint/outcome") != "error":
        pytest.fail(
            'Expected: crawler.stats.get_value("msgloom/checkpoint/outcome") == "error"'
        )
    if crawler.stats.get_value("msgloom/checkpoint/error_stage") != "snapshot":
        pytest.fail(
            'Expected: crawler.stats.get_value("msgloom/checkpoint/error_stage") == "snapshot"'
        )
    if spider.run_failed is not True:
        pytest.fail("Expected: spider.run_failed is True")
    if "checkpoint_evaluation_failed" not in spider.failure_reasons:
        pytest.fail(
            'Expected: "checkpoint_evaluation_failed" in spider.failure_reasons'
        )
    CatalogService.from_crawler(crawler).spider_closed(
        spider, "checkpoint_evaluation_failed"
    )
