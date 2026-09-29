"""Exercise To Do callback ordering, context, settings, and framework reuse."""

import asyncio
import importlib
import json
from typing import Any

import pytest
from scrapy import Request
from scrapy.crawler import Crawler
from scrapy.http import TextResponse
from scrapy.settings import Settings
from scrapy.spidermiddlewares.httperror import HttpError
from scrapy.utils.request import request_from_dict
from scrapy.utils.test import get_crawler
from twisted.python.failure import Failure

from message_ingest.items.acquisition import AcquisitionFailureItem, RawHttpEvidenceItem
from message_ingest.items.microsoft import todo
from message_ingest.spiders.microsoft._graph import MicrosoftGraphSpider
from message_ingest.spiders.microsoft.outlook.email.discover import (
    OutlookDiscoverSpider,
)
from message_ingest.spiders.microsoft.todo.discover import MicrosoftTodoDiscoverSpider
from message_ingest.spiders.microsoft.todo.sync import MicrosoftTodoSyncSpider
from microsoft_graph.items import todo as provider
from microsoft_graph.spiders.todo import MicrosoftTodoSpider


def _spider():
    crawler = get_crawler(MicrosoftTodoDiscoverSpider)
    return MicrosoftTodoDiscoverSpider.from_crawler(crawler)


def _response(request, payload, status=200):
    return TextResponse(
        request.url,
        request=request,
        status=status,
        body=json.dumps(payload).encode(),
        encoding="utf-8",
    )


def _first(spider):
    async def start():
        return await anext(spider.start())

    return asyncio.run(start())


def _parse(request, payload):
    if request.callback is None:
        pytest.fail("Request must have a bound callback")
    return list(request.callback(_response(request, payload), **request.cb_kwargs))


def test_application_items_inherit_mapping_and_add_provenance():
    for name, context in [
        ("TodoTaskListItem", {}),
        ("TodoTaskItem", {"list_id": "list"}),
        ("TodoChecklistItem", {"list_id": "list", "task_id": "task"}),
        ("TodoLinkedResourceItem", {"list_id": "list", "task_id": "task"}),
    ]:
        raw = {"id": "resource", "displayName": "", "isChecked": False}
        item = getattr(todo, name).from_graph(
            raw, **context, observed_at="observed", evidence_id="evidence", run_id="run"
        )
        if not isinstance(item, getattr(provider, name)) or item.raw is not raw:
            pytest.fail("Application items must reuse the provider projection")
        if (item.observed_at, item.evidence_id, item.run_id) != (
            "observed",
            "evidence",
            "run",
        ):
            pytest.fail("Application provenance was lost")


def test_spider_mro_scope_and_initial_request():
    spider = _spider()
    if not isinstance(spider, (MicrosoftTodoSpider, MicrosoftGraphSpider)):
        pytest.fail("To Do must compose provider and application Graph bases")
    mro = type(spider).__mro__
    if mro.index(MicrosoftTodoSpider) >= mro.index(MicrosoftGraphSpider):
        pytest.fail("Provider methods must precede the application adapter")
    if spider.mailbox_targeted or spider.graph_prefer is not None:
        pytest.fail("To Do must not inherit Outlook mailbox representation policy")
    if spider.crawler.settings.getlist("MS_GRAPH_SCOPES") != ["Tasks.Read"]:
        pytest.fail("To Do must declare Tasks.Read only")
    request = _first(spider)
    if request.url != "https://graph.microsoft.com/v1.0/me/todo/lists?%24top=100":
        pytest.fail("Discovery must start with task lists")
    if request.errback != spider.errback or request.method != "GET":
        pytest.fail("Discovery must use the shared request/errback contract")


@pytest.mark.parametrize("override", [None, "explicit-source"])
def test_source_setting_priority_and_outlook_unchanged(override):
    settings = Settings()
    settings.setmodule("message_ingest.settings", priority="project")
    settings.set("MSGLOOM_TODO_SOURCE_ID", "todo-source", priority="project")
    original = settings["MSGLOOM_SOURCE_ID"]
    if override is not None:
        settings.set("MSGLOOM_SOURCE_ID", override, priority="cmdline")
    crawler = Crawler(MicrosoftTodoDiscoverSpider, settings)
    if crawler.settings["MSGLOOM_SOURCE_ID"] != (override or "todo-source"):
        pytest.fail("To Do source must override project defaults but honor cmdline")
    outlook = Crawler(OutlookDiscoverSpider, settings)
    if outlook.settings["MSGLOOM_SOURCE_ID"] != (override or original):
        pytest.fail("Outlook source behavior changed")
    if settings["MSGLOOM_SOURCE_ID"] != (override or original):
        pytest.fail("Crawler-local source settings leaked into shared settings")
    for key in (
        "DOWNLOADER_MIDDLEWARES",
        "EXTENSIONS",
        "LOG_FORMATTER",
        "REQUEST_FINGERPRINTER_CLASS",
        "CONCURRENT_ITEMS",
    ):
        if crawler.settings[key] != settings[key]:
            pytest.fail(f"To Do replaced shared framework configuration: {key}")
    for key in (
        "MSGLOOM_DELTA_CHECKPOINT_ENABLED",
        "MSGLOOM_FOLDER_DELTA_CHECKPOINT_ENABLED",
        "MSGLOOM_CALENDAR_DELTA_CHECKPOINT_ENABLED",
        "MSGLOOM_CRAWL_STATUS_ENABLED",
    ):
        if crawler.settings.getbool(key):
            pytest.fail("To Do must disable Outlook lifecycle modes")
    if crawler.settings.getdict("ITEM_PIPELINES") != {
        "message_ingest.pipelines.evidence.RawEvidencePipeline": 200,
        "message_ingest.acquisition.evidence_link.EvidenceLinkPipeline": 250,
        "message_ingest.pipelines.microsoft.todo.TodoPipeline": 300,
    }:
        pytest.fail("To Do persistence must follow raw evidence and evidence linking")


def test_todo_source_environment_default(monkeypatch):
    import message_ingest.settings as settings_module

    monkeypatch.delenv("MSGLOOM_TODO_SOURCE_ID", raising=False)
    try:
        importlib.reload(settings_module)
        if settings_module.MSGLOOM_TODO_SOURCE_ID != "microsoft-todo-default":
            pytest.fail("Unexpected To Do default source")
        monkeypatch.setenv("MSGLOOM_TODO_SOURCE_ID", "environment-todo")
        importlib.reload(settings_module)
        if settings_module.MSGLOOM_TODO_SOURCE_ID != "environment-todo":
            pytest.fail("To Do source setting must read its own environment value")
    finally:
        monkeypatch.undo()
        importlib.reload(settings_module)


def test_traversal_emits_evidence_then_items_and_fetches_both_relations():
    spider = _spider()
    lists = _parse(
        _first(spider),
        {
            "value": [
                {"id": "list/+%2F", "wellknownListName": "defaultList"},
                {"id": "flagged", "wellknownListName": "flaggedEmails"},
            ]
        },
    )
    if not isinstance(lists[0], RawHttpEvidenceItem):
        pytest.fail("List page must emit evidence first")
    items = [item for item in lists if isinstance(item, todo.TodoTaskListItem)]
    requests = [item for item in lists if isinstance(item, Request)]
    if len(items) != 2 or len(requests) != 2:
        pytest.fail("Every list, including built-in lists, must produce task traversal")
    task_request = requests[0]
    if task_request.cb_kwargs["list_id"] != "list/+%2F":
        pytest.fail("Parent ID must travel through cb_kwargs unchanged")
    tasks = _parse(
        task_request,
        {
            "value": [
                {"id": "task/+", "linkedResources": [{"id": "embedded-only"}]},
                {"id": "second"},
            ]
        },
    )
    if not isinstance(tasks[0], RawHttpEvidenceItem):
        pytest.fail("Task page must emit evidence first")
    task_items = [item for item in tasks if isinstance(item, todo.TodoTaskItem)]
    relations = [item for item in tasks if isinstance(item, Request)]
    if len(task_items) != 2 or len(relations) != 4:
        pytest.fail("Every task must fetch checklistItems and linkedResources")
    if any(isinstance(item, todo.TodoLinkedResourceItem) for item in tasks):
        pytest.fail("Embedded relations must not supply authoritative relation rows")
    for request in relations[:2]:
        if (request.cb_kwargs["list_id"], request.cb_kwargs["task_id"]) != (
            "list/+%2F",
            "task/+",
        ):
            pytest.fail("Task/list context must be explicit")
        output = _parse(request, {"value": [{"id": "relation", "isChecked": False}]})
        if not isinstance(output[0], RawHttpEvidenceItem) or len(output) != 2:
            pytest.fail("Relation responses must emit evidence before their item")
        if output[1].evidence_id != output[0].evidence_id:
            pytest.fail("Semantic item lost its response evidence")
        if (
            output[1].observed_at != output[0].observed_at
            or output[1].run_id != spider.run_id
        ):
            pytest.fail("Semantic item lost observation/run provenance")
    for key in spider.crawler.stats.get_stats():
        if any(identifier in key for identifier in ("list/+", "task/+", "flagged")):
            pytest.fail("Provider IDs must not appear in stats labels")


@pytest.mark.parametrize(
    "callback,context",
    [
        ("parse_task_lists", {}),
        ("parse_tasks", {"list_id": "list"}),
        ("parse_checklist_items", {"list_id": "list", "task_id": "task"}),
        ("parse_linked_resources", {"list_id": "list", "task_id": "task"}),
    ],
)
def test_all_collections_follow_opaque_links_and_preserve_serializable_context(
    callback, context
):
    spider = _spider()
    next_link = "https://graph.microsoft.com/v1.0/me/todo/lists?z=%2f&x=+&x=%20&$skiptoken=a%2Bb%252F"
    request = spider._request(
        spider.task_lists_path(),
        callback=getattr(spider, callback),
        purpose="todo-test-page",
        cb_kwargs=context,
    )
    output = _parse(request, {"value": [], "@odata.nextLink": next_link})
    if len(output) != 2 or not isinstance(output[0], RawHttpEvidenceItem):
        pytest.fail("Empty pages must emit evidence and follow nextLink")
    continuation = output[1]
    if (
        continuation.url != next_link
        or continuation.meta.get("verbatim_url") is not True
    ):
        pytest.fail("Continuation URL bytes must remain opaque")
    if continuation.cb_kwargs != request.cb_kwargs:
        pytest.fail("Continuation must retain parent context")
    restored = request_from_dict(continuation.to_dict(spider=spider), spider=spider)
    if restored.callback != request.callback or restored.errback != spider.errback:
        pytest.fail("Callbacks and errbacks must use the shared serializable contract")
    if len(_parse(request, {"value": []})) != 1:
        pytest.fail("Empty terminal pages must not infer removal")
    if request.callback is None:
        pytest.fail("Collection request lost its callback")
    output = request.callback(_response(request, {"value": None}), **request.cb_kwargs)
    if not isinstance(next(output), RawHttpEvidenceItem):
        pytest.fail("Malformed collections still require evidence first")
    with pytest.raises(ValueError):
        next(output)


def test_failure_context_uses_shared_evidence_and_run_integrity(caplog):
    spider = _spider()
    request = spider._request(
        spider.linked_resources_path("private-list", "private-task"),
        callback=spider.parse_linked_resources,
        purpose="todo-linked-resources-page",
        cb_kwargs={"list_id": "private-list", "task_id": "private-task"},
    )
    # Scrapy attaches request context dynamically to Twisted failures.
    failure: Any = Failure(HttpError(_response(request, {}, status=403)))
    failure.request = request
    evidence, item = list(spider.errback(failure))
    if not isinstance(evidence, RawHttpEvidenceItem) or not isinstance(
        item, AcquisitionFailureItem
    ):
        pytest.fail("Shared errback must emit evidence before failure semantics")
    if item.context != {"list_id": "private-list", "task_id": "private-task"}:
        pytest.fail("Persisted failure must retain both parent identities")
    if not spider.run_failed or item.evidence_id != evidence.evidence_id:
        pytest.fail("Terminal To Do failures must fail the logical run")
    if "private-list" in caplog.text or "private-task" in caplog.text:
        pytest.fail("Failure logging must not expose provider identities")


def test_discovery_refuses_jobdir(tmp_path):
    crawler = get_crawler(
        MicrosoftTodoDiscoverSpider, {"JOBDIR": str(tmp_path / "job")}
    )
    with pytest.raises(ValueError, match="does not support JOBDIR"):
        MicrosoftTodoDiscoverSpider.from_crawler(crawler)


@pytest.mark.parametrize("size", ["0", "1001", "invalid"])
def test_discovery_rejects_invalid_page_sizes(size):
    with pytest.raises(ValueError):
        MicrosoftTodoDiscoverSpider(page_size=size)


def test_sync_reuses_discovery_callbacks_and_forces_uncached_snapshot_reads():
    crawler = get_crawler(MicrosoftTodoSyncSpider)
    spider = MicrosoftTodoSyncSpider.from_crawler(crawler)
    request = _first(spider)
    if request.meta.get("dont_cache") is not True:
        pytest.fail("Authoritative To Do traversal must bypass HTTP cache")
    if (
        request.callback is None
        or request.callback.__func__ is not MicrosoftTodoDiscoverSpider.parse_task_lists
    ):
        pytest.fail("Sync must share the discovery traversal callbacks")
    if spider.required_graph_permissions(crawler.settings) != ("Tasks.Read",):
        pytest.fail("Authoritative sync must retain the read-only Tasks.Read scope")
    outputs = _parse(request, {"value": []})
    completions = [
        item for item in outputs if isinstance(item, todo.TodoTraversalCompleteItem)
    ]
    if len(completions) != 1 or completions[0].collection_kind != "task_lists":
        pytest.fail("Terminal root page did not emit durable traversal proof")
