"""Exercise concurrency, incomplete traversal and exact reapplication."""

import asyncio

import pytest
from sqlalchemy import select

from message_ingest.acquisition.handoff import AcquisitionStream
from message_ingest.catalog.models.handoff import AcquisitionReleaseGroup
from message_ingest.catalog.models.microsoft.todo import (
    TodoTaskPresence,
    TodoTraversalCompletion,
)
from message_ingest.catalog.stores.microsoft.todo import TodoStore
from message_ingest.items.microsoft.todo import TodoTaskItem
from tests import _todo_authority
from tests._todo_authority import (
    dump,
    empty_snapshot,
    entries,
    promote,
    released_facts,
    snapshot,
    staged,
)

catalog = _todo_authority.catalog


def test_newer_concurrent_content_skips_absence_without_entry(catalog):
    """A complete older empty snapshot cannot retire newer provider content."""
    snapshot(catalog, "new-content", 3)
    store = empty_snapshot(catalog, "older-empty", 2)
    promote(store, "older-empty")
    if entries(catalog) or staged(catalog, "older-empty"):
        pytest.fail("Skipped absence fabricated a transition or content entry")
    with catalog.Session() as session:
        if session.get(TodoTaskPresence, ("source", "list-a", "task-a")):
            pytest.fail("Skipped absence mutated presence")
        groups = session.scalars(select(AcquisitionReleaseGroup)).all()
    if len(groups) != 1:
        pytest.fail("Winning empty decision still needs a durable zero-entry group")


def test_delayed_snapshot_never_releases_superseded_positive(catalog):
    """Revalidate effective freshness when an older snapshot finishes."""
    store = snapshot(catalog, "older", 1)
    store.stage_candidate("older", base_revision=None)
    TodoStore(catalog, source_id="source").persist_task(
        TodoTaskItem.from_graph(
            {"id": "task-a", "title": "newer private body"},
            list_id="list-a",
            run_id="concurrent",
            observed_at="2026-10-03T00:00:00Z",
            evidence_id="newer-evidence",
        )
    )
    store.promote_snapshot("older", base_revision=None)
    facts = released_facts(catalog)
    if not facts:
        pytest.fail("Fixture must release unaffected winning state")
    if any(
        f.resource_kind == "todo_task" and f.fact_kind == "resource_observation"
        for f in facts
    ):
        pytest.fail("Delayed promotion published old or unvalidated newer content")
    if any("newer private body" in entry["payload"] for entry in entries(catalog)):
        pytest.fail("Provider body leaked into the ledger")


def test_stale_cas_cannot_publish_any_group(catalog):
    """Losing authority must leave the entire provider and ledger unchanged."""
    first = snapshot(catalog, "first", 1)
    second = snapshot(catalog, "second", 2)
    first.stage_candidate("first", base_revision=None)
    second.stage_candidate("second", base_revision=None)
    second.promote_snapshot("second", base_revision=None)
    before = dump(catalog)
    with pytest.raises(ValueError, match="revision changed"):
        first.promote_snapshot("first", base_revision=None)
    if dump(catalog) != before or not entries(catalog):
        pytest.fail("Losing snapshot altered the winner or winner never released")


def test_incomplete_snapshot_cannot_publish_absence(catalog):
    """Missing terminal child traversal must not infer disappearance."""
    promote(snapshot(catalog, "initial", 1), "initial")
    store = snapshot(catalog, "incomplete", 2, list_id="replacement")
    with catalog.writer_session() as session:
        row = session.scalars(
            select(TodoTraversalCompletion).filter_by(
                source_id="source",
                run_id="incomplete",
                collection_kind="linked_resources",
            )
        ).one()
        session.delete(row)
    before = entries(catalog)
    if not before:
        pytest.fail("Initial authoritative release missing")
    with pytest.raises(ValueError, match="incomplete"):
        store.stage_candidate("incomplete", base_revision=1)
    with pytest.raises(ValueError, match="candidate"):
        store.promote_snapshot("incomplete", base_revision=1)
    if entries(catalog) != before:
        pytest.fail("Incomplete traversal published authority changes")


def test_exact_five_reapplications_publish_only_final_fact(catalog, tmp_path):
    """A/B/A/B/A must preserve five facts and Task 6 readable identities."""
    store = snapshot(catalog, "cycle", 1, task_raw={"title": "A"})
    content = TodoStore(catalog, source_id="source")
    for title in ("B", "A", "B", "A"):
        content.persist_task(
            TodoTaskItem.from_graph(
                {"id": "task-a", "title": title},
                list_id="list-a",
                run_id="cycle",
                observed_at="2026-10-01T00:00:00Z",
                evidence_id="ev-cycle",
            )
        )
    originals = [
        f for f in staged(catalog, "cycle") if f.fact_kind == "resource_observation"
    ]
    if len(originals) != 5:
        pytest.fail("Exact five-application core fixture lost a fact")
    from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore

    ledger = AcquisitionHandoffStore(catalog)
    with catalog.Session() as session:
        effective = ledger.current_effective_state(
            session,
            originals[0].effective_key,
        )
    if effective is None:
        pytest.fail("Winning application missing")
    promote(store, "cycle")
    task_facts = [
        f for f in released_facts(catalog) if f.fact_kind == "resource_observation"
    ]
    if [f.fact_id for f in task_facts] != [effective["fact_id"]]:
        pytest.fail("Authority did not select only the fifth application")

    from msgloom.sources.handoff_catalog import HandoffCatalog

    async def read():
        reader = HandoffCatalog(tmp_path / "catalog.sqlite3")
        try:
            cutoff = await reader.max_release_entry_seq("source", "todo")
            page = await reader.list_release_entries(
                source_id="source",
                stream="todo",
                after_seq=0,
                through_seq=cutoff,
                limit=100,
            )
            return [
                fact
                for entry in page.entries
                for fact in await reader.get_release_facts(entry)
            ]
        finally:
            await reader.close()

    rows = asyncio.run(read())
    if {f.fact_id for f in rows} != {f.fact_id for f in released_facts(catalog)}:
        pytest.fail("Task 6 reader disagrees with immutable authority members")


def test_changed_component_has_exact_parent_without_primary_churn(catalog):
    """Publish a changed child without requeueing its unchanged task."""
    from message_ingest.items.microsoft.todo import TodoChecklistItem

    promote(snapshot(catalog, "initial", 1), "initial")
    count = len(entries(catalog))
    store = snapshot(catalog, "child-change", 2)
    item = TodoChecklistItem.from_graph(
        {"id": "check-a", "displayName": "private child", "isChecked": True},
        list_id="list-a",
        task_id="task-a",
        run_id="child-change",
        observed_at="2026-10-02T00:00:00Z",
        evidence_id="ev-child-change",
    )
    TodoStore(catalog, source_id="source").persist_checklist_item(item)
    store.record_sighting(item)
    promote(store, "child-change")
    added = entries(catalog)[count:]
    if len(added) != 1:
        pytest.fail("One changed child duplicated unrelated resource work")
    from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore

    facts = AcquisitionHandoffStore(catalog).load_release_facts(
        added[0]["release_entry_seq"],
    )
    if (
        len(facts) != 1
        or facts[0].component_kind != "checklist_item"
        or facts[0].parent_resource_kind != "todo_task"
        or facts[0].parent_resource_identity != '["list-a","task-a"]'
        or facts[0].evidence_id != "ev-child-change"
    ):
        pytest.fail("Component entry lost its exact task parent or source version")


def test_large_child_collection_keeps_entries_bounded(catalog):
    """Keep entries bounded for a valid task with over 128 children."""
    from message_ingest.items.microsoft.todo import TodoChecklistItem

    store = snapshot(catalog, "large", 1)
    content = TodoStore(catalog, source_id="source")
    for index in range(130):
        item = TodoChecklistItem.from_graph(
            {"id": f"extra-{index}"},
            list_id="list-a",
            task_id="task-a",
            run_id="large",
            observed_at="2026-10-01T00:00:00Z",
            evidence_id="ev-large",
        )
        content.persist_checklist_item(item)
        store.record_sighting(item)
    promote(store, "large")
    facts = released_facts(catalog)
    children = [
        f
        for f in facts
        if f.fact_kind == "component_observation"
        and f.component_kind == "checklist_item"
    ]
    if len(children) != 131:
        pytest.fail("Large collection lost exact child impacts")
    from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore

    ledger = AcquisitionHandoffStore(catalog)
    first_page = ledger.list_release_entries(
        "source",
        AcquisitionStream.TODO,
        limit=7,
    )
    if len(first_page) != 7 or len(entries(catalog)) != 268:
        pytest.fail("One atomic snapshot cannot be drained in bounded pages")
