"""Prove additive traversal release from durable collection completion."""

import asyncio
import json

import pytest
from handoff_release_reader_helpers import bind_fixture_source, read_published
from outlook_mail_handoff_fixtures import saved_mail_evidence
from scrapy import Request, signals
from scrapy.crawler import Crawler
from scrapy.http import TextResponse
from scrapy.settings import Settings
from scrapy.statscollectors import MemoryStatsCollector
from scrapy.utils.request import RequestFingerprinter
from sqlalchemy import delete, select

from message_ingest.acquisition.evidence_link import EvidenceLinkPipeline
from message_ingest.acquisition.handoff import AcquisitionStream
from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.models.handoff import AcquisitionReleaseGroup
from message_ingest.catalog.models.microsoft.contacts import ContactCollectionCompletion
from message_ingest.catalog.models.microsoft.todo import TodoTraversalCompletion
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.catalog.stores.microsoft.contacts import ContactsStore
from message_ingest.extensions.catalog import CatalogService
from message_ingest.extensions.handoff import HandoffReleaseExtension
from message_ingest.items.microsoft.todo import TodoTraversalCompleteItem
from message_ingest.pipelines.evidence import RawEvidencePipeline
from message_ingest.pipelines.microsoft.todo import TodoPipeline
from message_ingest.spiders.microsoft.contacts.snapshot import (
    MicrosoftContactsDiscoverSpider,
)
from message_ingest.spiders.microsoft.todo.discover import MicrosoftTodoDiscoverSpider
from tests.test_contacts_handoff_facts import snapshot as seed_snapshot
from tests.test_todo_sync import _persist_full_snapshot


@pytest.fixture(params=["todo", "contacts"])
def traversal(request, tmp_path, monkeypatch):
    family = request.param
    bind_fixture_source(tmp_path / "catalog.db", "source")
    cls = (
        MicrosoftTodoDiscoverSpider
        if family == "todo"
        else MicrosoftContactsDiscoverSpider
    )
    crawler = Crawler(
        cls,
        Settings(
            {
                "MSGLOOM_CATALOG_ENABLED": True,
                "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
                "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.db'}",
            }
        ),
    )
    crawler.settings.set("MSGLOOM_SOURCE_ID", "source", priority="cmdline")
    crawler.stats = MemoryStatsCollector(crawler)
    crawler.request_fingerprinter = RequestFingerprinter(crawler)
    spider = cls.from_crawler(crawler)
    spider.run_id = "run"
    crawler.spider = spider
    service = CatalogService.from_crawler(crawler)
    if family == "todo":

        def save_todo(catalog, **kwargs):
            """Save the exact objects used by the existing store fixture."""
            return saved_mail_evidence(
                catalog,
                **kwargs,
                body=json.dumps(
                    {
                        "value": [
                            {"id": value}
                            for value in ("list-a", "task-a", "check-a", "link-a")
                        ]
                    }
                ).encode(),
            )

        monkeypatch.setattr("tests.test_todo_sync._evidence", save_todo)
        _persist_full_snapshot(
            service.catalog,
            source_id="source",
            run_id="run",
            observed_at="2026-10-01T00:00:00Z",
        )
    else:
        seed_snapshot(
            ContactsStore(service.catalog, source_id="source"), run="run", day=1
        )
        with service.catalog.Session() as session:
            ids = set(session.scalars(select(ContactCollectionCompletion.evidence_id)))
        for evidence_id in ids:
            saved_mail_evidence(
                service.catalog,
                evidence_id=evidence_id,
                source_id="source",
                run_id="run",
            )
        for evidence_id, body in (
            ("evidence-folder", {"id": "folder", "displayName": ""}),
            (
                "evidence-contact",
                {
                    "value": [
                        {"id": "contact", "displayName": "", "companyName": "original"},
                        {"id": "default-contact", "displayName": ""},
                    ]
                },
            ),
        ):
            saved_mail_evidence(
                service.catalog,
                evidence_id=evidence_id,
                source_id="source",
                run_id="run",
                body=json.dumps(body).encode(),
            )
    yield crawler, spider, service, family
    service.close()


def rows(case):
    stream = AcquisitionStream.TODO if case[3] == "todo" else AcquisitionStream.CONTACTS
    return AcquisitionHandoffStore(case[2].catalog).list_release_entries(
        "source", stream
    )


def test_complete_discovery_releases_positive_state_once(traversal, tmp_path):
    crawler, spider, service, _family = traversal
    extension = HandoffReleaseExtension.from_crawler(crawler)
    extension.spider_idle(spider)
    HandoffReleaseExtension.from_crawler(crawler).spider_idle(spider)
    if not rows(traversal):
        pytest.fail("Complete discovery did not release positive observations")
    with service.catalog.Session() as session:
        groups = session.scalars(select(AcquisitionReleaseGroup.payload)).all()
    if len(groups) != 1 or json.loads(groups[0])["release_kind"] != "resource_set":
        pytest.fail("Discovery needs one non-authoritative traversal group")
    reads = read_published(
        tmp_path / "catalog.db",
        tmp_path / "mail-fixture-evidence",
        "source",
        "todo" if _family == "todo" else "contacts",
    )
    expected = {
        (
            json.loads(row["payload"])["entry_kind"],
            json.loads(row["payload"])["resource_kind"],
            json.loads(row["payload"])["resource_identity"],
        )
        for row in rows(traversal)
    }
    if {
        (entry.entry_kind, entry.resource_kind, entry.resource_identity)
        for entry, _ in reads
    } != expected:
        pytest.fail("Traversal Reader lost typed resource/component/context entries")


def test_missing_collection_blocks_discovery(traversal):
    crawler, spider, service, family = traversal
    model = TodoTraversalCompletion if family == "todo" else ContactCollectionCompletion
    with service.catalog.writer_session() as writer:
        writer.execute(
            delete(model).where(
                model.collection_kind
                == ("linked_resources" if family == "todo" else "child_folders")
            )
        )
    extension = HandoffReleaseExtension.from_crawler(crawler)
    extension.spider_idle(spider)
    if rows(traversal):
        pytest.fail("Missing recursive collection proof allowed release")


def test_callback_failure_blocks_whole_discovery(traversal):
    crawler, spider, *_ = traversal
    extension = HandoffReleaseExtension.from_crawler(crawler)
    spider.mark_run_failed("request_failure:collection")
    extension.spider_idle(spider)
    if rows(traversal):
        pytest.fail("Failed traversal released a partial resource set")


def test_todo_discovery_emits_and_persists_empty_terminal_page(tmp_path):
    crawler = Crawler(
        MicrosoftTodoDiscoverSpider,
        Settings(
            {
                "MSGLOOM_CATALOG_ENABLED": True,
                "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.db'}",
            }
        ),
    )
    crawler.settings.set("MSGLOOM_SOURCE_ID", "source", priority="cmdline")
    crawler.stats = MemoryStatsCollector(crawler)
    crawler.request_fingerprinter = RequestFingerprinter(crawler)
    spider = MicrosoftTodoDiscoverSpider.from_crawler(crawler)
    request = spider._todo_request(
        "https://graph.microsoft.com/v1.0/me/todo/lists",
        callback=spider.parse_task_lists,
        purpose="todo-task-lists-page",
        cb_kwargs={},
    )
    response = TextResponse(
        request.url, request=request, body=b'{"value": []}', encoding="utf-8"
    )
    items = list(spider.parse_task_lists(response, purpose="todo-task-lists-page"))
    markers = [item for item in items if isinstance(item, TodoTraversalCompleteItem)]
    if len(markers) != 1:
        pytest.fail("Empty discovery did not emit durable terminal proof")
    pipeline = TodoPipeline.from_crawler(crawler)
    try:
        asyncio.run(pipeline.process_item(markers[0]))
        with pipeline.catalog.Session() as session:
            if session.scalar(select(TodoTraversalCompletion)) is None:
                pytest.fail("Discovery pipeline discarded terminal proof")
    finally:
        pipeline.close_spider()


@pytest.mark.parametrize("damage", ["source", "run", "status", "error", "missing"])
def test_terminal_proof_requires_current_completion_and_valid_evidence(
    traversal, damage
):
    crawler, spider, service, family = traversal
    model = TodoTraversalCompletion if family == "todo" else ContactCollectionCompletion
    with service.catalog.writer_session() as writer:
        completion = writer.scalars(select(model)).first()
        if completion is None:
            pytest.fail("Fixture omitted terminal completion")
        evidence = writer.get(RawHttpEvidence, completion.evidence_id)
        if evidence is None:
            pytest.fail("Fixture omitted terminal evidence")
        if damage == "status":
            evidence.response_status = 500
        elif damage == "source":
            evidence.source_id = "other-source"
        elif damage == "error":
            evidence.error_type = "transport_failure"
        elif damage == "missing":
            completion.evidence_id = "missing-evidence"
        else:
            completion.run_id = "other-run"
    HandoffReleaseExtension.from_crawler(crawler).spider_idle(spider)
    if rows(traversal):
        pytest.fail("Invalid terminal evidence allowed discovery release")


def test_cached_todo_traversal_releases_current_run_with_old_canonical_evidence(
    tmp_path,
):
    """Replay real callbacks and pipelines without changing capture ownership."""
    crawler = Crawler(
        MicrosoftTodoDiscoverSpider,
        Settings(
            {
                "MSGLOOM_CATALOG_ENABLED": True,
                "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
                "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.db'}",
                "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
            }
        ),
    )
    crawler.settings.set("MSGLOOM_SOURCE_ID", "source", priority="cmdline")
    crawler.stats = MemoryStatsCollector(crawler)
    crawler.request_fingerprinter = RequestFingerprinter(crawler)
    spider = MicrosoftTodoDiscoverSpider.from_crawler(crawler)
    crawler.spider = spider
    service = CatalogService.from_crawler(crawler)
    pipelines = (
        RawEvidencePipeline.from_crawler(crawler),
        EvidenceLinkPipeline.from_crawler(crawler),
        TodoPipeline.from_crawler(crawler),
    )

    async def traverse(run, *, cached):
        spider.run_id = run
        pending = [
            spider._todo_request(
                "https://graph.microsoft.com/v1.0/me/todo/lists",
                callback=spider.parse_task_lists,
                purpose="todo-task-lists-page",
                cb_kwargs={},
            )
        ]
        while pending:
            request = pending.pop()
            body = (
                b'{"value": [{"id": "list", "displayName": "Tasks"}]}'
                if request.callback == spider.parse_task_lists
                else b'{"value": []}'
            )
            response = TextResponse(
                request.url,
                request=request,
                body=body,
                encoding="utf-8",
                flags=["cached"] if cached else [],
            )
            for item in request.callback(response, **request.cb_kwargs):
                if isinstance(item, Request):
                    pending.append(item)
                    continue
                for pipeline in pipelines:
                    item = await pipeline.process_item(item)

    try:
        asyncio.run(traverse("capture-run", cached=False))
        asyncio.run(traverse("replay-run", cached=True))
        with service.catalog.Session() as session:
            captures = session.scalars(select(RawHttpEvidence)).all()
            completions = session.scalars(
                select(TodoTraversalCompletion).filter_by(run_id="replay-run")
            ).all()
            if len(captures) != 2 or {row.run_id for row in captures} != {
                "capture-run"
            }:
                pytest.fail("Cache replay did not reuse the original captures")
            if len(completions) != 2 or {row.evidence_id for row in completions} != {
                row.evidence_id for row in captures
            }:
                pytest.fail("Current completions lost exact canonical evidence")
        HandoffReleaseExtension.from_crawler(crawler).spider_idle(spider)
        HandoffReleaseExtension.from_crawler(crawler).spider_idle(spider)
        if not rows((crawler, spider, service, "todo")):
            pytest.fail("Valid cross-run cached traversal did not release")
        with service.catalog.Session() as session:
            groups = session.scalars(select(AcquisitionReleaseGroup.payload)).all()
        if len(groups) != 1 or json.loads(groups[0])["owner_run_id"] != "replay-run":
            pytest.fail("Replay did not publish one current logical-run group")
    finally:
        service.close()


def test_closed_signal_does_not_publish_traversal(traversal):
    crawler, spider, *_ = traversal
    HandoffReleaseExtension.from_crawler(crawler)
    crawler.signals.send_catch_log(
        signal=signals.spider_closed, spider=spider, reason="finished"
    )
    if rows(traversal):
        pytest.fail("Close reason replaced durable idle completion")
