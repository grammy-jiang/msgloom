"""Exercise authoritative To Do snapshot state and stale-run exclusion."""

from __future__ import annotations

import pytest
from scrapy.utils.test import get_crawler
from sqlalchemy import select

from message_ingest.catalog import Catalog
from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.models.microsoft.todo import (
    TodoChecklistItemPresence,
    TodoLinkedResourcePresence,
    TodoSnapshotCandidate,
    TodoSnapshotState,
    TodoTaskListPresence,
    TodoTaskPresence,
    TodoTraversalCompletion,
)
from message_ingest.catalog.stores.microsoft.todo import TodoStore
from message_ingest.extensions.catalog import CatalogService
from message_ingest.extensions.microsoft.todo.snapshot import TodoSnapshotExtension
from message_ingest.items.microsoft.todo import (
    TodoChecklistItem,
    TodoLinkedResourceItem,
    TodoTaskItem,
    TodoTaskListItem,
    TodoTraversalCompleteItem,
)
from message_ingest.spiders.microsoft.todo.sync import MicrosoftTodoSyncSpider
from message_ingest.sync.microsoft.todo.snapshots import TodoSnapshotStore


def _catalog(tmp_path):
    return Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")


def _evidence(catalog, *, evidence_id, source_id, run_id, observed_at):
    row = RawHttpEvidence(
        evidence_id=evidence_id,
        source_id=source_id,
        run_id=run_id,
        purpose="todo-test-page",
        observed_at=observed_at,
        origin="network",
        request_fingerprint="0" * 64,
        request_url="https://example.test/synthetic",
        request_method="GET",
        request_headers={},
        request_body_sha256="0" * 64,
        request_body_path="",
        request_body_bytes=0,
        response_url="https://example.test/synthetic",
        response_status=200,
        response_headers={},
        response_body_sha256="1" * 64,
        response_body_path="synthetic",
        response_body_bytes=2,
        response_flags=[],
        error_type=None,
        error_message=None,
    )
    with catalog.Session() as session, session.begin():
        session.add(row)


def _item(cls, *, run_id, observed_at, evidence_id, **context):
    return cls.from_graph(
        {"id": context.pop("resource_id"), **context.pop("raw", {})},
        **context,
        observed_at=observed_at,
        evidence_id=evidence_id,
        run_id=run_id,
    )


def _completion(kind, *, run_id, observed_at, evidence_id, list_id=None, task_id=None):
    return TodoTraversalCompleteItem(
        collection_kind=kind,
        list_id=list_id,
        task_id=task_id,
        observed_at=observed_at,
        evidence_id=evidence_id,
        run_id=run_id,
    )


def _persist_full_snapshot(
    catalog,
    *,
    source_id,
    run_id,
    observed_at,
    list_id="list-a",
    task_id="task-a",
    checklist_id="check-a",
    linked_id="link-a",
    task_raw=None,
):
    evidence_id = f"ev-{run_id}"
    _evidence(
        catalog,
        evidence_id=evidence_id,
        source_id=source_id,
        run_id=run_id,
        observed_at=observed_at,
    )
    content = TodoStore(catalog, source_id=source_id)
    snapshots = TodoSnapshotStore(catalog, source_id=source_id)
    task_list = _item(
        TodoTaskListItem,
        run_id=run_id,
        observed_at=observed_at,
        evidence_id=evidence_id,
        resource_id=list_id,
    )
    task = _item(
        TodoTaskItem,
        run_id=run_id,
        observed_at=observed_at,
        evidence_id=evidence_id,
        resource_id=task_id,
        list_id=list_id,
        raw=task_raw or {},
    )
    checklist = _item(
        TodoChecklistItem,
        run_id=run_id,
        observed_at=observed_at,
        evidence_id=evidence_id,
        resource_id=checklist_id,
        list_id=list_id,
        task_id=task_id,
    )
    linked = _item(
        TodoLinkedResourceItem,
        run_id=run_id,
        observed_at=observed_at,
        evidence_id=evidence_id,
        resource_id=linked_id,
        list_id=list_id,
        task_id=task_id,
    )
    for item, operation in [
        (task_list, content.persist_task_list),
        (task, content.persist_task),
        (checklist, content.persist_checklist_item),
        (linked, content.persist_linked_resource),
    ]:
        operation(item)
        snapshots.record_sighting(item)
    for kind, list_value, task_value in [
        ("task_lists", None, None),
        ("tasks", list_id, None),
        ("checklist_items", list_id, task_id),
        ("linked_resources", list_id, task_id),
    ]:
        snapshots.record_completion(
            _completion(
                kind,
                run_id=run_id,
                observed_at=observed_at,
                evidence_id=evidence_id,
                list_id=list_value,
                task_id=task_value,
            )
        )
    return snapshots


def test_snapshot_promotes_presence_and_repeat_run_is_idempotent(tmp_path):
    catalog = _catalog(tmp_path)
    try:
        first = _persist_full_snapshot(
            catalog,
            source_id="source-a",
            run_id="run-a",
            observed_at="2026-09-29T00:00:00Z",
        )
        if first.load_revision() is not None:
            pytest.fail("Unpromoted snapshot must not advance the revision")
        first.stage_candidate("run-a", base_revision=None)
        result = first.promote_snapshot("run-a", base_revision=None)
        if result["revision"] != 1 or result["present"] != 4 or result["absent"] != 0:
            pytest.fail(f"Unexpected first snapshot result: {result!r}")
        repeated = first.promote_snapshot("run-a", base_revision=None)
        if repeated != result:
            pytest.fail("Repeating the same promotion must be idempotent")

        second = _persist_full_snapshot(
            catalog,
            source_id="source-a",
            run_id="run-b",
            observed_at="2026-09-30T00:00:00Z",
        )
        second.stage_candidate("run-b", base_revision=1)
        result = second.promote_snapshot("run-b", base_revision=1)
        if result["revision"] != 2 or result["absent"] != 0:
            pytest.fail("Equivalent authoritative snapshot changed presence")
        with catalog.Session() as session:
            state = session.get(TodoSnapshotState, "source-a")
            candidates = session.scalars(select(TodoSnapshotCandidate)).all()
            if state is None or state.run_id != "run-b" or len(candidates) != 2:
                pytest.fail("Snapshot revision/candidate history was not durable")
    finally:
        catalog.close()


def test_snapshot_marks_removed_and_moved_keys_without_erasing_history(tmp_path):
    catalog = _catalog(tmp_path)
    try:
        first = _persist_full_snapshot(
            catalog,
            source_id="source-a",
            run_id="run-a",
            observed_at="2026-09-29T00:00:00Z",
        )
        first.stage_candidate("run-a", base_revision=None)
        first.promote_snapshot("run-a", base_revision=None)

        second = _persist_full_snapshot(
            catalog,
            source_id="source-a",
            run_id="run-b",
            observed_at="2026-09-30T00:00:00Z",
            list_id="list-b",
            task_id="task-a",
            checklist_id="check-b",
            linked_id="link-b",
        )
        second.stage_candidate("run-b", base_revision=1)
        result = second.promote_snapshot("run-b", base_revision=1)
        if result["present"] != 4 or result["absent"] != 4:
            pytest.fail(f"Moved/removed keys were not reconciled: {result!r}")
        with catalog.Session() as session:
            old_list = session.get(TodoTaskListPresence, ("source-a", "list-a"))
            old_task = session.get(TodoTaskPresence, ("source-a", "list-a", "task-a"))
            old_check = session.get(
                TodoChecklistItemPresence,
                ("source-a", "list-a", "task-a", "check-a"),
            )
            old_link = session.get(
                TodoLinkedResourcePresence,
                ("source-a", "list-a", "task-a", "link-a"),
            )
            new_task = session.get(TodoTaskPresence, ("source-a", "list-b", "task-a"))
            if any(
                row is None or row.is_present
                for row in (old_list, old_task, old_check, old_link)
            ):
                pytest.fail(
                    "Removed historical keys must have explicit absent presence"
                )
            if new_task is None or not new_task.is_present:
                pytest.fail("Moved task must be present under its new list key")
    finally:
        catalog.close()


def test_completion_reopen_due_and_reminder_keep_latest_observation(tmp_path):
    catalog = _catalog(tmp_path)
    try:
        content = TodoStore(catalog, source_id="source-a")
        first = _item(
            TodoTaskItem,
            run_id="run-a",
            observed_at="2026-09-29T00:00:00Z",
            evidence_id=None,
            resource_id="task",
            list_id="list",
            raw={
                "status": "completed",
                "completedDateTime": {
                    "dateTime": "2026-09-29T00:00:00",
                    "timeZone": "UTC",
                },
                "dueDateTime": {"dateTime": "2026-10-01T00:00:00", "timeZone": "UTC"},
                "reminderDateTime": {
                    "dateTime": "2026-09-30T00:00:00",
                    "timeZone": "UTC",
                },
                "isReminderOn": True,
            },
        )
        reopened = _item(
            TodoTaskItem,
            run_id="run-b",
            observed_at="2026-09-30T00:00:00Z",
            evidence_id=None,
            resource_id="task",
            list_id="list",
            raw={
                "status": "notStarted",
                "completedDateTime": None,
                "dueDateTime": {},
                "reminderDateTime": {},
                "isReminderOn": False,
            },
        )
        equal = _item(
            TodoTaskItem,
            run_id="run-c",
            observed_at="2026-09-30T00:00:00Z",
            evidence_id=None,
            resource_id="task",
            list_id="list",
            raw={
                "status": "inProgress",
                "completedDateTime": None,
                "dueDateTime": None,
                "reminderDateTime": None,
                "isReminderOn": False,
            },
        )
        stale = _item(
            TodoTaskItem,
            run_id="run-old",
            observed_at="2026-09-29T09:00:00+10:00",
            evidence_id=None,
            resource_id="task",
            list_id="list",
            raw={"status": "completed", "isReminderOn": True},
        )
        for item in (first, reopened, equal, stale):
            content.persist_task(item)
        with catalog.Session() as session:
            from message_ingest.catalog.models.microsoft.todo import TodoTaskRecord

            row = session.get(TodoTaskRecord, ("source-a", "list", "task"))
            if row is None:
                pytest.fail("Task state was not persisted")
            if (
                row.status != "inProgress"
                or row.completed_date_time is not None
                or row.due_date_time is not None
                or row.reminder_date_time is not None
                or row.is_reminder_on is not False
            ):
                pytest.fail(
                    "Equal-time processing order or false/null values were lost"
                )
    finally:
        catalog.close()


def test_stale_competing_run_cannot_promote_or_change_presence(tmp_path):
    catalog = _catalog(tmp_path)
    try:
        winner = _persist_full_snapshot(
            catalog,
            source_id="source-a",
            run_id="winner",
            observed_at="2026-09-30T00:00:00Z",
        )
        stale = _persist_full_snapshot(
            catalog,
            source_id="source-a",
            run_id="stale",
            observed_at="2026-09-29T00:00:00Z",
            list_id="stale-list",
            task_id="stale-task",
            checklist_id="stale-check",
            linked_id="stale-link",
        )
        winner.stage_candidate("winner", base_revision=None)
        stale.stage_candidate("stale", base_revision=None)
        winner.promote_snapshot("winner", base_revision=None)
        with pytest.raises(ValueError, match="revision changed"):
            stale.promote_snapshot("stale", base_revision=None)
        with catalog.Session() as session:
            state = session.get(TodoSnapshotState, "source-a")
            if state is None or state.run_id != "winner" or state.revision != 1:
                pytest.fail("Stale run changed the promoted snapshot state")
            stale_presence = session.get(
                TodoTaskListPresence, ("source-a", "stale-list")
            )
            if (
                stale_presence is None
                or stale_presence.is_present
                or stale_presence.latest_run_id != "winner"
            ):
                pytest.fail("Winner did not retain authority over stale-run presence")
    finally:
        catalog.close()


def test_incomplete_traversal_cannot_stage_terminal_candidate(tmp_path):
    catalog = _catalog(tmp_path)
    try:
        snapshots = _persist_full_snapshot(
            catalog,
            source_id="source-a",
            run_id="run-a",
            observed_at="2026-09-29T00:00:00Z",
        )
        with catalog.Session() as session, session.begin():
            row = session.scalars(
                select(TodoTraversalCompletion).filter_by(
                    source_id="source-a",
                    run_id="run-a",
                    collection_kind="linked_resources",
                )
            ).one()
            session.delete(row)
        with pytest.raises(ValueError, match="incomplete"):
            snapshots.stage_candidate("run-a", base_revision=None)
        with catalog.Session() as session:
            if session.get(TodoSnapshotCandidate, ("source-a", "run-a")) is not None:
                pytest.fail("Incomplete paging created a terminal candidate")
    finally:
        catalog.close()


def test_presence_and_revisions_are_source_isolated(tmp_path):
    catalog = _catalog(tmp_path)
    try:
        for source_id, run_id in (("source-a", "run-a"), ("source-b", "run-b")):
            snapshots = _persist_full_snapshot(
                catalog,
                source_id=source_id,
                run_id=run_id,
                observed_at="2026-09-29T00:00:00Z",
            )
            snapshots.stage_candidate(run_id, base_revision=None)
            snapshots.promote_snapshot(run_id, base_revision=None)
        with catalog.Session() as session:
            states = session.scalars(select(TodoSnapshotState)).all()
            presence = session.scalars(select(TodoTaskPresence)).all()
            if len(states) != 2 or len(presence) != 2:
                pytest.fail("Equal provider IDs collided across logical sources")
    finally:
        catalog.close()


def test_idle_promotion_finishes_before_catalog_shutdown(tmp_path):
    """Ensure idle promotion finishes before catalog shutdown."""
    database_url = f"sqlite:///{tmp_path / 'catalog.sqlite3'}"
    crawler = get_crawler(
        MicrosoftTodoSyncSpider,
        {
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
            "MSGLOOM_DATABASE_URL": database_url,
            "MSGLOOM_TODO_SOURCE_ID": "source-a",
        },
    )
    spider = MicrosoftTodoSyncSpider.from_crawler(crawler)
    crawler.spider = spider
    extension = TodoSnapshotExtension.from_crawler(crawler)
    extension.spider_opened(spider)
    service = CatalogService.from_crawler(crawler)
    _persist_full_snapshot(
        service.catalog,
        source_id="source-a",
        run_id=spider.run_id,
        observed_at="2026-09-29T00:00:00Z",
    )

    extension.spider_idle(spider)
    service.close()

    verifier = Catalog(database_url)
    try:
        with verifier.Session() as session:
            state = session.get(TodoSnapshotState, "source-a")
            candidate = session.get(TodoSnapshotCandidate, ("source-a", spider.run_id))
            if state is None or state.run_id != spider.run_id or state.revision != 1:
                pytest.fail("Idle promotion did not finish before catalog shutdown")
            if candidate is None or candidate.committed_at is None:
                pytest.fail("Catalog shutdown overtook terminal candidate promotion")
        if crawler.stats.get_value("msgloom/todo_snapshot/promoted_count") != 1:
            pytest.fail("Synchronous idle promotion lost its success stats")
    finally:
        verifier.close()
