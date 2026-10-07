"""Verify atomic To Do facts, independent components, and retry recovery."""

import asyncio
import json
from dataclasses import asdict, replace

import pytest
from scrapy.utils.test import get_crawler
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from message_ingest.acquisition.handoff import AcquisitionStream, StorageRelation
from message_ingest.catalog import Catalog
from message_ingest.catalog.models.handoff import (
    AcquisitionEffectiveState,
    AcquisitionFact,
)
from message_ingest.catalog.models.microsoft.todo import TodoTaskRecord
from message_ingest.catalog.stores.microsoft.todo import TodoStore
from message_ingest.items.microsoft.todo import TodoTaskItem
from message_ingest.pipelines.microsoft.todo import TodoPipeline
from message_ingest.spiders.microsoft.todo.sync import MicrosoftTodoSyncSpider
from message_ingest.sync.microsoft.todo.snapshots import TodoSnapshotStore
from tests._todo_contacts_handoff import facts, publish, reject_facts
from tests.test_todo_catalog import CASES, _item
from tests.test_todo_sync import _persist_full_snapshot


@pytest.fixture
def catalog(tmp_path):
    """Provide a fresh local ledger and domain database."""
    value = Catalog(f"sqlite:///{tmp_path / 'todo.sqlite3'}")
    yield value
    value.close()


@pytest.mark.parametrize("cls,model,kind,operation,context,raw,projection", CASES)
def test_all_todo_families_stage_exact_facts(
    catalog, cls, model, kind, operation, context, raw, projection
):
    """Preserve exact recovery, semantic keys and component parents."""
    store = TodoStore(catalog, source_id="source")
    item = _item(cls, raw=raw, **context)
    getattr(store, operation)(item)
    first = facts(catalog, "run")[0]
    if first.storage_relation != StorageRelation.ADVANCED:
        pytest.fail("First observation must advance")
    locator = first.source_version_locator
    if locator is None or locator.evidence_id != "evidence":
        pytest.fail("Exact source locator must pin canonical evidence")
    if first.evidence_id != "evidence" or first.run_id != "run":
        pytest.fail("Evidence and logical run are independent provenance")
    if kind in {"checklist_item", "linked_resource"}:
        if first.parent_resource_kind != "todo_task" or json.loads(
            first.parent_resource_identity or "null"
        ) != ["list", "task"]:
            pytest.fail("Child fact lost its exact task parent")
        if first.component_kind != kind:
            pytest.fail("Independent child state requires a component key")
    getattr(store, operation)(
        replace(item, run_id="retry", observed_at="2026-10-01T00:00:00Z")
    )
    second = facts(catalog, "retry")[0]
    if (
        second.storage_relation != StorageRelation.CURRENT_EQUIVALENT
        or second.source_state_key != first.source_state_key
    ):
        pytest.fail("Capture metadata must not change semantic state")
    getattr(store, operation)(item)
    if len(facts(catalog, "run")) != 2:
        # Replaying the older item now records a distinct stale observation.
        pytest.fail("Provider stale classification must remain separate")


@pytest.mark.parametrize("cls,model,kind,operation,context,raw,projection", CASES)
@pytest.mark.parametrize("existing", [False, True])
def test_fact_failure_rolls_back_every_todo_family(
    catalog, cls, model, kind, operation, context, raw, projection, existing
):
    """Neither a new row nor a replacement may commit without its fact."""
    store = TodoStore(catalog, source_id="source")
    item = _item(cls, raw=raw, **context)
    if existing:
        getattr(store, operation)(item)
    reject_facts(catalog)
    newer = _item(
        cls,
        observed="2026-10-02T00:00:00Z",
        raw={"displayName": "changed", "title": "changed"},
        **context,
    )
    with pytest.raises(IntegrityError, match="injected fact failure"):
        getattr(store, operation)(newer)
    with catalog.Session() as session:
        record = session.scalars(select(model)).one_or_none()
        if (record is None) != (not existing):
            pytest.fail("Fact failure did not roll back the domain insert")
        if record is not None and record.raw != item.raw:
            pytest.fail("Fact failure committed the domain replacement")
        if len(session.scalars(select(AcquisitionFact)).all()) != int(existing):
            pytest.fail("Fact failure left partial ledger state")
        if len(session.scalars(select(AcquisitionEffectiveState)).all()) != int(
            existing
        ):
            pytest.fail("Fact failure left a partial effective pointer")


def test_unchanged_full_snapshot_recovery_and_no_repeated_work(catalog):
    """Recover an unreleased snapshot once without repeating work."""
    original_ids: set[str] = set()
    for index, run in enumerate(("failed", "retry", "unchanged"), 1):
        snapshots = _persist_full_snapshot(
            catalog,
            source_id="source",
            run_id=run,
            observed_at=f"2026-10-0{index}T00:00:00Z",
        )
        rows = facts(catalog, run)
        if len(rows) != 4:
            pytest.fail("Full snapshot must stage all resource families")
        if run == "failed":
            with pytest.raises(ValueError, match="candidate"):
                snapshots.promote_snapshot(run, base_revision=None)
            original_ids = {row.fact_id for row in rows}
            continue
        revision = snapshots.load_revision()
        snapshots.stage_candidate(run, base_revision=revision)
        snapshots.promote_snapshot(run, base_revision=revision)
        entries = publish(catalog, run, AcquisitionStream.TODO, rows)
        if len(entries) != 8:
            pytest.fail("Snapshot must retain four exact impacts and four transitions")
        from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore

        released = {
            fact.fact_id
            for entry in entries
            for fact in AcquisitionHandoffStore(catalog).load_release_facts(
                entry["release_entry_seq"]
            )
            if fact.fact_kind != "scoped_state_transition"
        }
        transitions = [
            fact
            for entry in entries
            for fact in AcquisitionHandoffStore(catalog).load_release_facts(
                entry["release_entry_seq"]
            )
            if fact.fact_kind == "scoped_state_transition"
        ]
        if len(transitions) != 4 or any(
            fact.run_id != "retry" or fact.authority_revision != "1"
            for fact in transitions
        ):
            pytest.fail("Unchanged snapshot fabricated authority transitions")
        if released != original_ids:
            pytest.fail("Equivalent retry must adopt exact original advanced facts")


def test_stale_and_superseded_todo_facts_cannot_publish(catalog):
    """Reject delayed publication of observations superseded before idle."""
    store = TodoStore(catalog, source_id="source")
    item = _item(list_id="list", raw={"title": "old"})
    store.persist_task(item)
    old = facts(catalog, "run")
    store.persist_task(
        replace(
            item,
            run_id="new",
            observed_at="2026-10-02T00:00:00Z",
            raw={"id": "resource", "title": "new"},
        )
    )
    store.persist_task(replace(item, run_id="stale"))
    if facts(catalog, "stale")[0].storage_relation != StorageRelation.STALE:
        pytest.fail("Older write must be retained only as stale history")
    if publish(catalog, "old-release", AcquisitionStream.TODO, old):
        pytest.fail("Superseded source state became primary work")
    if publish(
        catalog, "stale-release", AcquisitionStream.TODO, facts(catalog, "stale")
    ):
        pytest.fail("Stale source state became primary work")


def test_task_and_components_have_separate_semantic_versions(catalog):
    """Keep child arrays and transport data out of task semantic state."""
    store = TodoStore(catalog, source_id="source")
    body = {"content": "x" * 70000, "contentType": "text"}
    raw = {
        "id": "task",
        "title": "t",
        "body": body,
        "lastModifiedDateTime": "version-1",
    }
    store.persist_task(
        TodoTaskItem.from_graph(
            raw,
            list_id="list",
            observed_at="2026-10-01T00:00:00Z",
            evidence_id="e1",
            run_id="a",
        )
    )
    store.persist_task(
        TodoTaskItem.from_graph(
            {
                **raw,
                "checklistItems": [{"id": "child", "isChecked": True}],
                "@odata.context": "transport",
            },
            list_id="list",
            observed_at="2026-10-02T00:00:00Z",
            evidence_id="e2",
            run_id="b",
        )
    )
    if (
        facts(catalog, "a")[0].source_state_key
        != facts(catalog, "b")[0].source_state_key
    ):
        pytest.fail("Child/transport changes changed the primary task version")
    payload = json.dumps(asdict(facts(catalog, "b")[0]))
    if "contentType" in payload or "transport" in payload or len(payload) > 5000:
        pytest.fail("Ledger copied provider content instead of its digest")


def test_todo_pipeline_keeps_fact_after_sighting_failure(tmp_path, monkeypatch):
    """A failed proof write leaves an advanced fact recoverable on retry."""
    crawler = get_crawler(
        MicrosoftTodoSyncSpider,
        {
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_TODO_SOURCE_ID": "source",
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'pipeline.sqlite3'}",
        },
    )
    pipeline = TodoPipeline.from_crawler(crawler)

    def fail(_item):
        raise RuntimeError("injected sighting failure")

    monkeypatch.setattr(pipeline.snapshot_store, "record_sighting", fail)
    try:
        with pytest.raises(RuntimeError, match="sighting failure"):
            asyncio.run(pipeline.process_item(_item(list_id="list")))
        row = facts(pipeline.catalog, "run")[0]
        if row.spider_name != "microsoft_todo_sync":
            pytest.fail("Pipeline did not forward actual logical spider provenance")
        with pipeline.catalog.Session() as session:
            if session.scalar(select(TodoTaskRecord)) is None:
                pytest.fail("Sighting failure should not erase committed content/fact")
        with pytest.raises(ValueError, match="incomplete"):
            TodoSnapshotStore(pipeline.catalog, source_id="source").stage_candidate(
                "run", base_revision=None
            )
    finally:
        pipeline.close_spider()


def test_equal_capture_reapplication_cannot_release_superseded_state(catalog):
    """An A/B/A processing sequence must not publish B after A wins again."""
    store = TodoStore(catalog, source_id="source")
    first = _item(list_id="list", raw={"title": "A"})
    second = replace(first, raw={"id": "resource", "title": "B"})
    store.persist_task(first)
    original = facts(catalog, "run")[0]
    store.persist_task(second)
    superseded = [row for row in facts(catalog, "run") if row != original]
    if len(superseded) != 1:
        pytest.fail("Fixture did not stage the intervening B state")
    if store.persist_task(first) != "changed":
        pytest.fail("To Do's existing equal-time processing order was changed")
    with catalog.Session() as session:
        current = session.scalars(select(TodoTaskRecord)).one()
        if current.title != "A":
            pytest.fail("Final provider state must follow existing processing order")
    if publish(catalog, "delayed-B", AcquisitionStream.TODO, superseded):
        pytest.fail("Frozen ledger published B even though current provider state is A")
