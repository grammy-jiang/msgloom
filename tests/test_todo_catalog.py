"""Verify To Do schema, current-state writes, and pipeline lifecycle."""

import asyncio
from threading import Event

import pytest
from scrapy.exceptions import NotConfigured
from scrapy.utils.test import get_crawler
from sqlalchemy import create_engine, inspect, select

from message_ingest.catalog import Base, Catalog
from message_ingest.catalog.models.microsoft.todo import (
    TodoChecklistItemRecord,
    TodoLinkedResourceRecord,
    TodoTaskListRecord,
    TodoTaskRecord,
)
from message_ingest.catalog.stores.microsoft.todo import TodoStore
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.microsoft.todo import (
    TodoChecklistItem,
    TodoLinkedResourceItem,
    TodoTaskItem,
    TodoTaskListItem,
)
from message_ingest.pipelines.microsoft.todo import TodoPipeline
from message_ingest.spiders.microsoft.todo.discover import MicrosoftTodoDiscoverSpider

CASES = [
    (
        TodoTaskListItem,
        TodoTaskListRecord,
        "task_list",
        "persist_task_list",
        {},
        {
            "displayName": "",
            "isOwner": False,
            "isShared": False,
            "wellknownListName": "flaggedEmails",
        },
        {
            "display_name": "",
            "is_owner": False,
            "is_shared": False,
            "wellknown_list_name": "flaggedEmails",
        },
    ),
    (
        TodoTaskItem,
        TodoTaskRecord,
        "task",
        "persist_task",
        {"list_id": "list"},
        {
            "title": "",
            "status": "notStarted",
            "importance": "normal",
            "body": {},
            "categories": [],
            "createdDateTime": "2026-01-01T00:00:00Z",
            "lastModifiedDateTime": "2026-02-01T00:00:00Z",
            "bodyLastModifiedDateTime": "",
            "dueDateTime": {"dateTime": "2026-10-01T00:00:00", "timeZone": "UTC"},
            "startDateTime": {},
            "completedDateTime": None,
            "reminderDateTime": {},
            "isReminderOn": False,
            "recurrence": {},
        },
        {
            "title": "",
            "status": "notStarted",
            "importance": "normal",
            "body": {},
            "categories": [],
            "created_date_time": "2026-01-01T00:00:00Z",
            "last_modified_date_time": "2026-02-01T00:00:00Z",
            "body_last_modified_date_time": "",
            "due_date_time": {"dateTime": "2026-10-01T00:00:00", "timeZone": "UTC"},
            "start_date_time": {},
            "completed_date_time": None,
            "reminder_date_time": {},
            "is_reminder_on": False,
            "recurrence": {},
        },
    ),
    (
        TodoChecklistItem,
        TodoChecklistItemRecord,
        "checklist_item",
        "persist_checklist_item",
        {"list_id": "list", "task_id": "task"},
        {
            "displayName": "",
            "isChecked": False,
            "createdDateTime": "",
            "checkedDateTime": None,
        },
        {
            "display_name": "",
            "is_checked": False,
            "created_date_time": "",
            "checked_date_time": None,
        },
    ),
    (
        TodoLinkedResourceItem,
        TodoLinkedResourceRecord,
        "linked_resource",
        "persist_linked_resource",
        {"list_id": "list", "task_id": "task"},
        {"applicationName": "", "displayName": "", "externalId": ""},
        {
            "web_url": None,
            "application_name": "",
            "display_name": "",
            "external_id": "",
        },
    ),
]


def _crawler(tmp_path):
    return get_crawler(
        MicrosoftTodoDiscoverSpider,
        {
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_TODO_SOURCE_ID": "todo-source",
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
        },
    )


def _item(cls=TodoTaskItem, *, observed="2026-09-29T00:00:00Z", raw=None, **context):
    return cls.from_graph(
        {"id": "resource", **(raw or {})},
        **context,
        observed_at=observed,
        evidence_id="evidence",
        run_id="run",
    )


def test_schema_adds_only_todo_tables_and_preserves_existing_data(tmp_path):
    url = f"sqlite:///{tmp_path / 'existing.sqlite3'}"
    expected = {
        "todo_task_lists": ("source_id", "list_id"),
        "todo_tasks": ("source_id", "list_id", "task_id"),
        "todo_checklist_items": (
            "source_id",
            "list_id",
            "task_id",
            "checklist_item_id",
        ),
        "todo_linked_resources": (
            "source_id",
            "list_id",
            "task_id",
            "linked_resource_id",
        ),
        "todo_task_list_sightings": ("source_id", "run_id", "list_id"),
        "todo_task_sightings": ("source_id", "run_id", "list_id", "task_id"),
        "todo_checklist_item_sightings": (
            "source_id",
            "run_id",
            "list_id",
            "task_id",
            "checklist_item_id",
        ),
        "todo_linked_resource_sightings": (
            "source_id",
            "run_id",
            "list_id",
            "task_id",
            "linked_resource_id",
        ),
        "todo_traversal_completions": ("source_id", "run_id", "scope_key"),
        "todo_snapshot_candidates": ("source_id", "run_id"),
        "todo_snapshot_state": ("source_id",),
        "todo_task_list_presence": ("source_id", "list_id"),
        "todo_task_presence": ("source_id", "list_id", "task_id"),
        "todo_checklist_item_presence": (
            "source_id",
            "list_id",
            "task_id",
            "checklist_item_id",
        ),
        "todo_linked_resource_presence": (
            "source_id",
            "list_id",
            "task_id",
            "linked_resource_id",
        ),
    }
    engine = create_engine(url)
    try:
        Base.metadata.create_all(
            engine,
            tables=[
                table
                for name, table in Base.metadata.tables.items()
                if name not in expected
            ],
        )
        with engine.begin() as connection:
            connection.exec_driver_sql("CREATE TABLE preserved (value TEXT)")
            connection.exec_driver_sql("INSERT INTO preserved VALUES ('old data')")
        before = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    catalog = Catalog(url)
    try:
        schema = inspect(catalog.engine)
        if set(schema.get_table_names()) - before != set(expected):
            pytest.fail("To Do schema must be additive")
        for name, keys in expected.items():
            if tuple(schema.get_pk_constraint(name)["constrained_columns"]) != keys:
                pytest.fail(f"Wrong provider/source primary key for {name}")
        with catalog.engine.connect() as connection:
            if (
                connection.exec_driver_sql("SELECT value FROM preserved").scalar()
                != "old data"
            ):
                pytest.fail("Schema initialization modified existing data")
    finally:
        catalog.close()


@pytest.mark.parametrize("cls,model,kind,operation,context,raw,projection", CASES)
def test_pipeline_preserves_projection_and_applies_latest_capture(
    tmp_path, cls, model, kind, operation, context, raw, projection
):
    crawler = _crawler(tmp_path)
    pipeline = TodoPipeline.from_crawler(crawler)
    item = _item(cls, raw=raw, **context)
    try:
        if asyncio.run(pipeline.process_item(item)) is not item:
            pytest.fail("Pipeline must return the original item after committing")
        with pipeline.catalog.Session() as session:
            record = session.scalars(select(model)).one()
            for key, expected in {
                **context,
                **projection,
                "raw": item.raw,
                "latest_observed_at": item.observed_at,
                "latest_evidence_id": "evidence",
                "source_id": "todo-source",
            }.items():
                if getattr(record, key) != expected:
                    pytest.fail(f"Persistence changed field {key}")
        # Lexically later text can still name an older instant.
        stale = _item(cls, observed="2026-09-29T09:00:00+10:00", raw={}, **context)
        asyncio.run(pipeline.process_item(stale))
        with pipeline.catalog.Session() as session:
            if session.scalars(select(model)).one().raw != item.raw:
                pytest.fail("Older capture overwrote current provider state")
        current = _item(cls, observed="2026-09-30T00:00:00Z", **context)
        asyncio.run(pipeline.process_item(current))
        with pipeline.catalog.Session() as session:
            record = session.scalars(select(model)).one()
            if (
                record.raw != current.raw
                or record.latest_observed_at != current.observed_at
            ):
                pytest.fail("Newer capture did not replace current state")
            if any(getattr(record, name) is not None for name in projection):
                pytest.fail("Missing optional fields in a new capture must remain None")
        asyncio.run(pipeline.process_item(current))
        stats = crawler.stats.get_stats()
        for outcome in ("created", "stale", "changed", "unchanged"):
            if stats.get(f"msgloom/catalog/todo/{kind}_{outcome}_count") != 1:
                pytest.fail(f"Missing bounded {kind}/{outcome} counter")
        if any(
            "resource" in key.removeprefix("msgloom/catalog/todo/linked_resource")
            or "todo-source" in key
            for key in stats
            if key.startswith("msgloom/catalog/todo/")
        ):
            pytest.fail("Catalog counters must not label provider/source IDs")
    finally:
        pipeline.close_spider()
    if not pipeline.service._closed:
        pytest.fail("Persistence pipeline must close the shared service")


@pytest.mark.parametrize("cls,model,kind,operation,context,raw,projection", CASES)
def test_store_isolates_source_and_parent_identity(
    tmp_path, cls, model, kind, operation, context, raw, projection
):
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        first = TodoStore(catalog, source_id="first")
        second = TodoStore(catalog, source_id="second")
        item = _item(cls, raw=raw, **context)
        getattr(first, operation)(item)
        getattr(second, operation)(item)
        for parent in context:
            getattr(first, operation)(_item(cls, **{**context, parent: "other"}))
        with catalog.Session() as session:
            if len(session.scalars(select(model)).all()) != 2 + len(context):
                pytest.fail("Equal resource IDs in different sources/parents collided")
        with pytest.raises(ValueError, match="timezone"):
            getattr(first, operation)(_item(cls, observed="2026-10-01", **context))
    finally:
        catalog.close()


def test_catalog_disabled_rejects_todo_pipeline():
    crawler = get_crawler(
        MicrosoftTodoDiscoverSpider, {"MSGLOOM_CATALOG_ENABLED": False}
    )
    with pytest.raises(NotConfigured):
        TodoPipeline.from_crawler(crawler)


def test_pipeline_awaits_worker_under_shared_write_lock(tmp_path, monkeypatch):
    crawler = _crawler(tmp_path)
    pipeline = TodoPipeline.from_crawler(crawler)
    item = _item(list_id="list")
    release = Event()
    original = pipeline.store.persist_task

    async def exercise():
        service = CatalogService.from_crawler(crawler)
        entered = asyncio.Event()
        loop = asyncio.get_running_loop()

        def blocked_write(item):
            if not service.write_lock.locked():
                raise RuntimeError("Worker ran outside the shared write lock")
            loop.call_soon_threadsafe(entered.set)
            if not release.wait(5):
                raise RuntimeError("Test did not release catalog write")
            return original(item)

        monkeypatch.setattr(pipeline.store, "persist_task", blocked_write)
        await service.write_lock.acquire()
        task = asyncio.create_task(pipeline.process_item(item))
        try:
            await asyncio.sleep(0)
            if entered.is_set():
                pytest.fail("Worker did not wait for the shared lock")
            service.write_lock.release()
            await asyncio.wait_for(entered.wait(), 5)
            if task.done():
                pytest.fail("Pipeline returned before the worker committed")
        finally:
            release.set()
            await task
        marker = object()
        if await pipeline.process_item(marker) is not marker:
            pytest.fail("Unrelated items must pass through")

    try:
        asyncio.run(exercise())
    finally:
        pipeline.close_spider()
