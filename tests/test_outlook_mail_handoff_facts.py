"""Mail facts retain logical provenance and share provider transactions."""

import asyncio
import json

import pytest
from scrapy.utils.test import get_crawler
from sqlalchemy import select, text
from sqlalchemy.exc import DatabaseError

from message_ingest.acquisition.evidence_link import EvidenceLinkPipeline
from message_ingest.acquisition.handoff import (
    AcquisitionStream,
    FactSpec,
    ReleaseEntrySpec,
    ReleaseGroupSpec,
    ReleaseKind,
)
from message_ingest.catalog.models.handoff import AcquisitionFact
from message_ingest.catalog.models.microsoft.outlook.email import (
    MessageObservation,
    MessageRecord,
)
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.acquisition import RawHttpEvidenceItem
from message_ingest.items.microsoft.outlook.email import OutlookMailItem
from message_ingest.pipelines.evidence import RawEvidencePipeline
from message_ingest.pipelines.microsoft.outlook.email import OutlookMailPipeline

NOW = "2026-10-03T00:00:00+00:00"
LATER = "2026-10-03T01:00:00+00:00"
MESSAGE = {
    "id": "m1",
    "subject": "private body",
    "changeKey": "v1",
    "toRecipients": [{"emailAddress": {"address": "one@example.test"}}],
}


@pytest.fixture
def setup(tmp_path):
    crawler = get_crawler(
        settings_dict={
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'mail.db'}",
            "MSGLOOM_SOURCE_ID": "source",
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
            "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
        }
    )
    pipeline = OutlookMailPipeline.from_crawler(crawler)
    yield crawler, pipeline, pipeline.store
    CatalogService.from_crawler(crawler).spider_closed(None, "test-finished")


def capture(
    crawler, run="r1", evidence="e1", body=b"{}", observed=NOW, origin="network"
):
    item = RawHttpEvidenceItem(
        evidence_id=evidence,
        run_id=run,
        purpose="message-list",
        observed_at=observed,
        origin=origin,
        request_fingerprint="same-request",
        request_url="https://graph.test/messages",
        request_method="GET",
        request_headers={},
        request_body=b"",
        response_url="https://graph.test/messages",
        response_status=200,
        response_headers={},
        response_body=body,
        response_flags=[],
    )
    asyncio.run(RawEvidencePipeline.from_crawler(crawler).process_item(item))
    return item


def facts(store):
    with store.catalog.Session() as session:
        return [
            FactSpec.from_json(p)
            for p in session.scalars(select(AcquisitionFact.payload))
        ]


def message(
    store,
    run="r1",
    evidence: str | None = "e1",
    observed=NOW,
    payload=None,
    kind="discovery",
):
    return store.record_message(
        run_id=run,
        message=MESSAGE if payload is None else payload,
        kind=kind,
        evidence_id=evidence,
        observed_at=observed,
    )


def publish(store, fact, run):
    ledger = AcquisitionHandoffStore(store.catalog)
    group = ReleaseGroupSpec(
        source_id="source",
        stream=AcquisitionStream.OUTLOOK_MAIL,
        release_kind=ReleaseKind.RESOURCE_SET,
        subject_kind="mailbox",
        subject_identity="test-mailbox",
        owner_run_id=run,
        released_at=LATER,
        coverage_kind="complete",
    )
    entry = ReleaseEntrySpec(
        resource_kind=fact.resource_kind,
        resource_identity=fact.resource_identity,
        facts=((fact.fact_id, "primary"),),
    )
    with store.catalog.writer_session() as session:
        ledger.release_effective_group_in_session(session, group, [entry])
    return ledger.list_release_entries("source", AcquisitionStream.OUTLOOK_MAIL)


@pytest.mark.parametrize("released_first", [False, True])
def test_cache_replay_keeps_current_run_and_adopts_exact_unreleased_fact(
    setup,
    released_first,
):
    crawler, pipeline, store = setup
    body = json.dumps({"value": [MESSAGE]}).encode()
    capture(crawler, body=body)
    first = message(store)
    if not hasattr(first, "storage_relation"):
        pytest.fail("record_message needs a structured persistence outcome")
    if first.storage_relation != "advanced" or not first.observation_created:
        pytest.fail("First message did not advance")
    original = first.fact
    if released_first:
        publish(store, original, "r1")
    cached = capture(crawler, "r2", "e2", body, LATER, "http_cache")
    if cached.evidence_id != "e1":
        pytest.fail("Local HTTP-cache fixture did not resolve canonical evidence")
    item = OutlookMailItem.from_graph(
        MESSAGE,
        source_response_url="https://graph.test/messages",
        observed_at=LATER,
        observation_kind="discovery",
        evidence_id="e2",
        run_id="r2",
    )
    asyncio.run(EvidenceLinkPipeline.from_crawler(crawler).process_item(item))
    asyncio.run(pipeline.process_item(item))
    current = next(
        f
        for f in facts(store)
        if f.run_id == "r2" and f.fact_kind == "resource_observation"
    )
    if (current.evidence_id, current.source_state_key, current.storage_relation) != (
        "e1",
        original.source_state_key,
        "current_equivalent",
    ):
        pytest.fail("Replay lost exact state or current logical-run provenance")
    entries = publish(store, current, "r2")
    if len(entries) != 1:
        pytest.fail("Equivalent retry lost work or duplicated published work")
    released = AcquisitionHandoffStore(store.catalog).load_release_facts(
        entries[0]["release_entry_seq"]
    )
    if released != [original]:
        pytest.fail("Recovery did not adopt the exact original advanced fact")
    with store.catalog.Session() as session:
        if len(session.scalars(select(MessageObservation)).all()) != 1:
            pytest.fail("Canonical evidence replay duplicated observations")


def test_changed_primary_version_blocks_delayed_release(setup):
    crawler, _, store = setup
    capture(crawler)
    first = message(store)
    if not hasattr(first, "fact"):
        pytest.fail("Missing atomic primary fact")
    changed = {**MESSAGE, "changeKey": "v2", "toRecipients": []}
    capture(crawler, "r2", "e2", observed=LATER)
    second = message(store, "r2", "e2", LATER, changed)
    if first.fact.source_state_key == second.fact.source_state_key:
        pytest.fail("New changeKey reused an older primary semantic version")
    if publish(store, first.fact, "r1"):
        pytest.fail("Delayed older run published superseded primary state")
    stale = message(store, "r3")
    if stale.storage_relation != "stale":
        pytest.fail("Older provider observation was not classified stale")
    if len(publish(store, second.fact, "r2")) != 1:
        pytest.fail("Current primary state was not eligible")
    with store.catalog.Session() as session:
        if "private body" in " ".join(session.scalars(select(AcquisitionFact.payload))):
            pytest.fail("Ledger copied provider body content")


def test_detail_has_independent_component_and_preserves_primary_key(setup):
    crawler, _, store = setup
    capture(crawler)
    first = message(store)
    if not hasattr(first, "fact"):
        pytest.fail("Missing structured result")
    capture(crawler, "r2", "e2", observed=LATER)
    detail = message(
        store,
        "r2",
        "e2",
        LATER,
        {**MESSAGE, "body": {"content": "full private text"}},
        "detail",
    )
    if first.fact.source_state_key != detail.fact.source_state_key:
        pytest.fail("Full-only fields fabricated a new primary semantic version")


@pytest.mark.parametrize(
    "operation",
    [
        "message",
        "surface",
        "attachment",
        "folder",
        "folder_removed",
        "membership",
    ],
)
def test_fact_insert_failure_rolls_back_provider_state(setup, operation):
    crawler, _, store = setup
    capture(crawler)
    with store.catalog.writer_session() as session:
        session.execute(
            text(
                "CREATE TRIGGER reject_mail_fact BEFORE INSERT ON acquisition_facts "
                "BEGIN SELECT RAISE(ABORT, 'injected fact failure'); END"
            )
        )
    with pytest.raises(DatabaseError, match="injected fact failure"):
        if operation == "message":
            message(store)
        elif operation == "surface":
            store.set_surface(
                run_id="r1",
                message_id="m1",
                surface="mime",
                status="acquired",
                evidence_id="e1",
                observed_at=NOW,
            )
        elif operation == "attachment":
            store.upsert_attachment(
                run_id="r1",
                message_id="m1",
                attachment={"id": "a1"},
                evidence_id="e1",
                observed_at=NOW,
            )
        elif operation == "folder":
            store.upsert_folder(
                run_id="r1", folder={"id": "f1"}, evidence_id="e1", observed_at=NOW
            )
        elif operation == "folder_removed":
            store.mark_folder_removed(
                run_id="r1",
                folder_id="f1",
                reason="deleted",
                evidence_id="e1",
                observed_at=NOW,
            )
        else:
            store.record_folder_removal(
                run_id="r1",
                message_id="m1",
                folder_id="f1",
                removed_reason="deleted",
                evidence_id="e1",
                observed_at=NOW,
            )
    with store.catalog.Session() as session:
        for table in (
            "messages",
            "message_observations",
            "message_surfaces",
            "attachments",
            "mail_folders",
            "mail_folder_presence",
            "message_presence",
            "acquisition_facts",
            "acquisition_effective_states",
        ):
            if session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one():
                pytest.fail(f"Fact failure left provider state in {table}")


def test_surface_content_digest_and_terminal_semantics(setup):
    crawler, _, store = setup
    capture(crawler, body=b"mime bytes")
    first = store.set_surface(
        run_id="r1",
        message_id="m1",
        surface="mime",
        status="acquired",
        evidence_id="e1",
        observed_at=NOW,
        profile_version="full-v1",
    )
    capture(crawler, "r2", "e2", b"mime bytes", LATER)
    second = store.set_surface(
        run_id="r2",
        message_id="m1",
        surface="mime",
        status="acquired",
        evidence_id="e2",
        observed_at=LATER,
        profile_version="full-v1",
    )
    if second.storage_relation != "current_equivalent":
        pytest.fail("Identical saved bytes fabricated new component work")
    if first.fact.source_state_key != second.fact.source_state_key:
        pytest.fail("Component key included evidence/run identity")
    for run, evidence, observed in [("r1", "e1", NOW), ("r2", "e2", LATER)]:
        result = store.set_surface(
            run_id=run,
            message_id="m1",
            surface="attachment_raw:a1",
            status="unsupported",
            evidence_id=evidence,
            observed_at=observed,
            profile_version="full-v1",
            resource_version="v1",
        )
    if result.storage_relation != "current_equivalent":
        pytest.fail("Terminal limitation identity included attempt evidence")


def test_folder_removals_are_scoped_and_authority_pending(setup):
    crawler, _, store = setup
    capture(crawler)
    message(store)
    store.record_folder_removal(
        run_id="r1",
        message_id="m1",
        folder_id="f1",
        removed_reason="deleted",
        evidence_id="e1",
        observed_at=NOW,
    )
    result = store.mark_folder_removed(
        run_id="r1", folder_id="f1", reason="deleted", evidence_id="e1", observed_at=NOW
    )
    staged = facts(store)
    transitions = [f for f in staged if f.fact_kind == "scoped_state_transition"]
    if len(transitions) != 2:
        pytest.fail("Missing folder and membership transition facts")
    if any(
        f.scope_identity != "f1" or f.storage_relation != "authority_staged"
        for f in transitions
    ):
        pytest.fail("Folder tombstone lost scope or authority gate")
    if not hasattr(result, "storage_relation"):
        pytest.fail("Folder removal did not expose persistence outcome")
    with store.catalog.Session() as session:
        row = session.scalar(select(MessageRecord))
        if row is None or row.is_removed:
            pytest.fail("Folder removal became global message deletion")
    ledger = AcquisitionHandoffStore(store.catalog)
    if ledger.list_release_entries("source", AcquisitionStream.OUTLOOK_MAIL):
        pytest.fail("Provider staging prematurely published a release")
