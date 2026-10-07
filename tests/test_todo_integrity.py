"""Verify To Do uses shared evidence, account identity, and failure gates."""

import asyncio
import json

import pytest
from scrapy.exceptions import CloseSpider
from scrapy.http import TextResponse
from scrapy.pipelines import ItemPipelineManager
from scrapy.utils.test import get_crawler
from sqlalchemy import select

from message_ingest.catalog.models.acquisition import SourceBinding, SourceTargetBinding
from message_ingest.catalog.models.microsoft.todo import TodoTaskListRecord
from message_ingest.extensions.catalog import CatalogService
from message_ingest.extensions.microsoft_graph.identity import (
    MicrosoftGraphSourceIdentityExtension,
)
from message_ingest.items.microsoft.todo import TodoTaskListItem
from message_ingest.pipelines.microsoft.todo import TodoPipeline
from message_ingest.spiders.microsoft.todo.discover import MicrosoftTodoDiscoverSpider
from microsoft_graph.auth.session import MicrosoftGraphAuthSession


def _crawler(tmp_path, **settings):
    crawler = get_crawler(
        MicrosoftTodoDiscoverSpider,
        {
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
            "MSGLOOM_SOURCE_IDENTITY_REQUIRED": True,
            "MS_GRAPH_AUTH_METHOD": "device_code",
            **settings,
        },
    )
    crawler.spider = MicrosoftTodoDiscoverSpider.from_crawler(crawler)
    return crawler


def test_account_identity_is_enough_without_target_binding(tmp_path, monkeypatch):
    crawler = _crawler(tmp_path, MSGLOOM_TARGET_MAILBOX="outlook-only-target")

    class Session:
        def attach_account_binding(self, binding):
            self.binding = binding

        async def establish_account_binding(self):
            self.binding.bind_or_verify_account_key("opaque-account-key")

    monkeypatch.setattr(
        MicrosoftGraphAuthSession, "from_crawler", lambda crawler: Session()
    )
    gate = MicrosoftGraphSourceIdentityExtension.from_crawler(crawler)
    service = CatalogService.from_crawler(crawler)
    try:
        asyncio.run(gate.spider_opened(crawler.spider))
        with service.catalog.Session() as session:
            binding = session.get(SourceBinding, "microsoft-todo-default")
            if binding is None:
                pytest.fail("To Do must verify and persist the shared account binding")
            if session.scalars(select(SourceTargetBinding)).first() is not None:
                pytest.fail("To Do must not bind an Outlook mailbox target")
        if crawler.stats.get_value("msgloom/source_identity/gate_state") != "verified":
            pytest.fail("Shared account identity gate did not complete")
    finally:
        service.close()


def test_auth_disabled_fails_closed_with_identity_required(tmp_path):
    crawler = _crawler(tmp_path, MS_GRAPH_AUTH_METHOD="none")
    gate = MicrosoftGraphSourceIdentityExtension.from_crawler(crawler)
    with pytest.raises(CloseSpider):
        asyncio.run(gate.spider_opened(crawler.spider))
    if (
        not isinstance(crawler.spider, MicrosoftTodoDiscoverSpider)
        or not crawler.spider.run_failed
    ):
        pytest.fail("To Do must reuse shared identity failure integrity")


def test_native_pipeline_chain_canonicalizes_cache_evidence_and_refuses_missing_links(
    tmp_path,
):
    crawler = _crawler(tmp_path)
    spider = crawler.spider
    if not isinstance(spider, MicrosoftTodoDiscoverSpider):
        pytest.fail("Crawler must hold its To Do spider")
    manager = ItemPipelineManager.from_crawler(crawler)
    service = CatalogService.from_crawler(crawler)
    request = spider._request(
        spider.task_lists_path(),
        callback=spider.parse_task_lists,
        purpose="todo-task-lists-page",
        cb_kwargs={},
    )
    body = json.dumps({"value": [{"id": "list", "displayName": ""}]}).encode()
    response = TextResponse(request.url, request=request, body=body, encoding="utf-8")
    original = spider._raw_http_evidence_item(response, "todo-task-lists-page")
    original.observed_at = "2026-09-29T00:00:00Z"
    replay = spider._raw_http_evidence_item(response, "todo-task-lists-page")
    replay.origin = "http_cache"
    replay.observed_at = "2026-10-01T00:00:00Z"
    item = TodoTaskListItem.from_graph(
        {"id": "list", "displayName": ""},
        observed_at=replay.observed_at,
        evidence_id=replay.evidence_id,
        run_id=spider.run_id,
    )

    async def process():
        await manager.process_item_async(original)
        await manager.process_item_async(replay)
        await manager.process_item_async(item)
        if (item.evidence_id, item.observed_at) != (
            original.evidence_id,
            original.observed_at,
        ):
            pytest.fail(
                "Cache replay advanced To Do capture time or lost evidence alias"
            )
        missing = TodoTaskListItem.from_graph(
            {"id": "missing"},
            observed_at=item.observed_at,
            evidence_id="not-persisted",
            run_id=spider.run_id,
        )
        with pytest.raises(RuntimeError, match="has not been persisted"):
            await manager.process_item_async(missing)

    try:
        asyncio.run(process())
        with service.catalog.Session() as session:
            rows = session.scalars(select(TodoTaskListRecord)).all()
            if len(rows) != 1 or rows[0].latest_evidence_id != original.evidence_id:
                pytest.fail("Evidence gate failed to protect To Do state")
    finally:
        asyncio.run(manager.close_spider_async())


def test_pipeline_storage_error_propagates_without_success_stats(tmp_path, monkeypatch):
    crawler = _crawler(tmp_path)
    pipeline = TodoPipeline.from_crawler(crawler)

    def fail(item):
        raise RuntimeError("injected storage failure")

    monkeypatch.setattr(pipeline.store, "persist_task_list", fail)
    item = TodoTaskListItem.from_graph(
        {"id": "list"},
        observed_at="2026-09-29T00:00:00Z",
        evidence_id=None,
        run_id="run",
    )
    try:
        with pytest.raises(RuntimeError, match="injected storage failure"):
            asyncio.run(pipeline.process_item(item))
        if any(
            key.startswith("msgloom/catalog/todo/") for key in crawler.stats.get_stats()
        ):
            pytest.fail("Failed writes must not report successful processing")
    finally:
        pipeline.close_spider()
