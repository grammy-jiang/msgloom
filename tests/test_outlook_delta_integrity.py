"""Verify delta checkpoint integrity, failure gates, and JOBDIR resume state."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from scrapy import signals
from scrapy.exceptions import CloseSpider
from scrapy.utils.misc import build_from_crawler
from scrapy.utils.test import get_crawler
from twisted.python.failure import Failure

from message_ingest.checkpoints import OutlookDeltaCheckpointStore
from message_ingest.extensions.catalog import CatalogService
from message_ingest.extensions.delta_checkpoint import OutlookDeltaCheckpointExtension
from message_ingest.items import OutlookDeltaCheckpointCandidateItem
from message_ingest.pipelines.catalog import CatalogPipeline
from message_ingest.spiders.outlook_delta import OutlookDeltaSpider


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


async def _collect_start(spider: OutlookDeltaSpider):
    return [value async for value in spider.start()]


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
