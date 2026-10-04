"""Qualify To Do authority publication through native Scrapy command paths."""

import json

import pytest
from sqlalchemy import select

from message_ingest.acquisition.handoff import AcquisitionStream
from message_ingest.catalog import Catalog
from message_ingest.catalog.models.handoff import (
    AcquisitionFact,
    AcquisitionReleaseGroup,
)
from message_ingest.catalog.models.microsoft.todo import TodoSnapshotState
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from tests import test_todo_crawl as crawl_fixture

graph_server = crawl_fixture.graph_server


def _feed(catalog):
    """Read actual immutable entries from the synthetic source."""
    return AcquisitionHandoffStore(catalog).list_release_entries(
        "todo-fixture",
        AcquisitionStream.TODO,
        limit=1000,
    )


def test_real_sync_releases_once_after_awaited_pipeline(tmp_path, graph_server):
    """Native idle must release all persisted families without repeat churn."""
    origin, _state, _requests, _pages = graph_server
    result = crawl_fixture._crawl(tmp_path, origin, action="sync")
    if result.returncode:
        pytest.fail(result.stderr)
    crawl_fixture._private_logs(result.stderr)
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        first = _feed(catalog)
        facts = [
            fact
            for entry in first
            for fact in AcquisitionHandoffStore(catalog).load_release_facts(
                entry["release_entry_seq"],
            )
        ]
        positives = [f for f in facts if f.fact_kind != "scoped_state_transition"]
        if len(positives) != 8:
            pytest.fail("Native crawl did not publish all exact resource families")
        again = crawl_fixture._crawl(tmp_path, origin, action="sync")
        if again.returncode:
            pytest.fail(again.stderr)
        if _feed(catalog) != first:
            pytest.fail("Unchanged real crawl generated repeated work")
        with catalog.Session() as session:
            state = session.get(TodoSnapshotState, "todo-fixture")
            if state is None or state.revision != 2:
                pytest.fail("Zero-entry authority round did not advance revision")
    finally:
        catalog.close()


def test_real_release_sql_failure_rolls_back_authority(tmp_path, graph_server):
    """An entry insert failure must propagate through the actual idle owner."""
    origin, _state, _requests, _pages = graph_server
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.writer_session() as session:
            session.connection().exec_driver_sql(
                "CREATE TRIGGER reject_task9c BEFORE INSERT ON "
                "acquisition_release_entries "
                "BEGIN SELECT RAISE(ABORT, 'injected release failure'); END"
            )
        result = crawl_fixture._crawl(tmp_path, origin, action="sync")
        if result.returncode != 1:
            pytest.fail("Release failure did not fail the real sync command")
        with catalog.Session() as session:
            if session.get(TodoSnapshotState, "todo-fixture") is not None:
                pytest.fail("Failed real release advanced authority")
            if session.scalars(select(AcquisitionReleaseGroup)).first():
                pytest.fail("Failed real release left a partial group")
            facts = session.scalars(select(AcquisitionFact.payload)).all()
            if not facts or any(
                json.loads(row)["fact_kind"] == "scoped_state_transition"
                for row in facts
            ):
                pytest.fail("Failure lost durable content or retained transitions")
        if _feed(catalog):
            pytest.fail("Partial failed authority became downstream work")
    finally:
        catalog.close()


@pytest.mark.parametrize("failure", ["malformed", "incomplete"])
def test_real_partial_snapshot_keeps_release_anchor(
    tmp_path,
    graph_server,
    failure,
):
    """Broken response or missing continuation cannot publish absence."""
    origin, state, _requests, _pages = graph_server
    result = crawl_fixture._crawl(tmp_path, origin, action="sync")
    if result.returncode:
        pytest.fail(result.stderr)
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        before = _feed(catalog)
        if not before:
            pytest.fail("Initial release missing")
        settings = {}
        if failure == "malformed":
            state["mode"] = "malformed"
        else:
            settings["SPIDER_MIDDLEWARES"] = json.dumps(
                {
                    "todo_sync_failures.DropChecklistContinuationMiddleware": 700,
                }
            )
        result = crawl_fixture._crawl(
            tmp_path,
            origin,
            action="sync",
            extra_settings=settings,
        )
        if result.returncode != 1 or _feed(catalog) != before:
            pytest.fail("Partial traversal changed the durable release anchor")
    finally:
        catalog.close()
