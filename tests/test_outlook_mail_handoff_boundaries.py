"""Additional Mail freshness, byte verification, and transaction checks."""

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError
from test_outlook_mail_handoff_facts import (
    LATER,
    MESSAGE,
    NOW,
    capture,
    facts,
    message,
    setup,
)

from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.models.microsoft.outlook.email import MessageRecord

__all__ = ["setup"]


def test_unbacked_changed_primary_still_advances_without_fabricated_locator(setup):
    _, _, store = setup
    payload = {k: v for k, v in MESSAGE.items() if k != "changeKey"}
    first = message(store, evidence=None, payload=payload)
    changed = message(store, "r2", None, LATER, {**payload, "subject": "new"})
    if changed.storage_relation != "advanced":
        pytest.fail("Missing evidence identity hid a real primary change")
    if first.fact.source_state_key == changed.fact.source_state_key:
        pytest.fail("Changed retained primary projection reused its state key")
    if changed.fact.source_version_locator is not None:
        pytest.fail("Unbacked state fabricated an exact evidence locator")


def test_corrupt_saved_bytes_never_create_acquired_surface(setup):
    crawler, _, store = setup
    capture(crawler, body=b"saved MIME")
    with store.catalog.Session() as session:
        row = session.get(RawHttpEvidence, "e1")
        if row is None:
            pytest.fail("Missing local evidence fixture")
        path = Path(row.response_body_path)
    path.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="digest or size mismatch"):
        store.set_surface(
            run_id="r1",
            message_id="m1",
            surface="mime",
            status="acquired",
            evidence_id="e1",
            observed_at=NOW,
        )
    if store.get_surfaces(message_id="m1") or facts(store):
        pytest.fail("Corrupt content created state or a successful fact")


def test_preledger_equivalent_message_does_not_create_future_only_work(setup):
    crawler, _, store = setup
    import json

    capture(crawler, body=json.dumps({"value": [MESSAGE]}).encode())
    with store.catalog.writer_session() as session:
        session.add(
            MessageRecord(
                source_id="source",
                message_id="m1",
                subject=MESSAGE["subject"],
                latest_observed_at=NOW,
                latest_evidence_id="e1",
                is_removed=False,
            )
        )
    result = message(store, "r2")
    if result.storage_relation != "current_equivalent":
        pytest.fail("Pre-ledger equivalent state fabricated an advancement")
    with store.catalog.Session() as session:
        if session.execute(
            text("SELECT count(*) FROM acquisition_effective_states")
        ).scalar():
            pytest.fail("Pre-ledger history entered the new effective-state feed")


@pytest.mark.parametrize("family", ["attachment", "folder", "surface"])
def test_component_writes_expose_advanced_equivalent_and_stale(setup, family):
    crawler, _, store = setup
    capture(crawler)
    capture(crawler, "r2", "e2", observed=LATER)

    def write(run, evidence, observed):
        args = {"run_id": run, "evidence_id": evidence, "observed_at": observed}
        if family == "attachment":
            return store.upsert_attachment(
                message_id="m1", attachment={"id": "a1", "name": "same"}, **args
            )
        if family == "folder":
            return store.upsert_folder(
                folder={"id": "f1", "displayName": "same"}, **args
            )
        return store.set_surface(
            message_id="m1", surface="mime", status="acquired", **args
        )

    first = write("r1", "e1", NOW)
    equivalent = write("r2", "e2", LATER)
    stale = write("r3", "e1", NOW)
    if [r.storage_relation for r in (first, equivalent, stale)] != [
        "advanced",
        "current_equivalent",
        "stale",
    ]:
        pytest.fail("Provider freshness and state equivalence were conflated")


def test_folder_tombstone_failure_preserves_presence_and_cursors(setup):
    crawler, _, store = setup
    from message_ingest.sync.microsoft.outlook.email.checkpoints import (
        OutlookDeltaCheckpointStore,
    )

    capture(crawler)
    store.upsert_folder(
        run_id="r1", folder={"id": "f1"}, evidence_id="e1", observed_at=NOW
    )
    checkpoints = OutlookDeltaCheckpointStore(store.catalog, "source")
    checkpoints.write_candidate(
        run_id="r1",
        folder_id="f1",
        delta_link="https://graph.test/opaque",
        observed_at=NOW,
    )
    checkpoints.commit("r1")
    before = len(facts(store))
    with store.catalog.writer_session() as session:
        session.execute(
            text(
                "CREATE TRIGGER reject_tombstone BEFORE INSERT ON acquisition_facts "
                "WHEN json_extract(NEW.payload, '$.fact_kind') = 'scoped_state_transition' "
                "BEGIN SELECT RAISE(ABORT, 'second fact failure'); END"
            )
        )
    with pytest.raises(DatabaseError, match="second fact failure"):
        store.mark_folder_removed(
            run_id="r2",
            folder_id="f1",
            reason="deleted",
            evidence_id="e1",
            observed_at=LATER,
        )
    if store.folder_presence(folder_id="f1") is not True:
        pytest.fail("Partial tombstone survived failure of its transition fact")
    if checkpoints.get_delta_links() != {"f1": "https://graph.test/opaque"}:
        pytest.fail("Tombstone rollback lost the existing message cursor")
    if len(facts(store)) != before:
        pytest.fail("Partial folder control fact survived transaction rollback")


def test_older_folder_tombstone_does_not_discard_newer_cursor(setup):
    crawler, _, store = setup
    from message_ingest.sync.microsoft.outlook.email.checkpoints import (
        OutlookDeltaCheckpointStore,
    )

    capture(crawler)
    store.upsert_folder(
        run_id="r2", folder={"id": "f1"}, evidence_id="e1", observed_at=LATER
    )
    checkpoints = OutlookDeltaCheckpointStore(store.catalog, "source")
    checkpoints.write_candidate(
        run_id="r2",
        folder_id="f1",
        delta_link="https://graph.test/newer",
        observed_at=LATER,
    )
    checkpoints.commit("r2")
    result = store.mark_folder_removed(
        run_id="r1", folder_id="f1", reason="deleted", evidence_id="e1", observed_at=NOW
    )
    if result.storage_relation != "stale":
        pytest.fail("Delayed tombstone did not report stale")
    if not store.folder_presence(folder_id="f1") or not checkpoints.get_delta_links():
        pytest.fail("Older tombstone erased newer folder state")


def test_resource_version_change_advances_terminal_surface_with_same_evidence(setup):
    crawler, _, store = setup
    capture(crawler)
    first = store.set_surface(
        run_id="r1",
        message_id="m1",
        surface="mime",
        status="unavailable",
        evidence_id="e1",
        observed_at=NOW,
        profile_version="full-v1",
        resource_version="v1",
    )
    second = store.set_surface(
        run_id="r2",
        message_id="m1",
        surface="mime",
        status="unavailable",
        evidence_id="e1",
        observed_at=LATER,
        profile_version="full-v1",
        resource_version="v2",
    )
    if second.storage_relation != "advanced":
        pytest.fail("Terminal resource-version change was suppressed by same evidence")
    if second.fact.source_state_key == first.fact.source_state_key:
        pytest.fail("Terminal resource-version was absent from semantic state")


def test_mime_key_does_not_depend_on_detail_callback_order(setup):
    crawler, _, store = setup
    capture(crawler, body=b"same MIME")
    first = store.set_surface(
        run_id="r1",
        message_id="m1",
        surface="mime",
        status="acquired",
        evidence_id="e1",
        observed_at=NOW,
    )
    message(store, "r2", "e1", LATER)
    second = store.set_surface(
        run_id="r2",
        message_id="m1",
        surface="mime",
        status="acquired",
        evidence_id="e1",
        observed_at=LATER,
    )
    if first.fact.source_state_key != second.fact.source_state_key:
        pytest.fail("MIME semantic key depends on callback scheduling")
    if second.storage_relation != "current_equivalent":
        pytest.fail("Identical MIME bytes created repetitive work")


def test_surface_fact_can_publish_its_parent_message_impact(setup):
    crawler, _, store = setup
    from message_ingest.acquisition.handoff import (
        AcquisitionStream,
        ReleaseEntrySpec,
        ReleaseGroupSpec,
        ReleaseKind,
    )
    from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore

    capture(crawler)
    outcome = store.set_surface(
        run_id="r1",
        message_id="m1",
        surface="mime",
        status="acquired",
        evidence_id="e1",
        observed_at=NOW,
    )
    group = ReleaseGroupSpec(
        source_id="source",
        stream=AcquisitionStream.OUTLOOK_MAIL,
        release_kind=ReleaseKind.RESOURCE_PROFILE,
        subject_kind="message",
        subject_identity="m1",
        owner_run_id="r1",
        released_at=LATER,
        coverage_kind="complete",
        profile="full-v1",
    )
    entry = ReleaseEntrySpec(
        resource_kind="message",
        resource_identity="m1",
        facts=((outcome.fact.fact_id, "component"),),
    )
    ledger = AcquisitionHandoffStore(store.catalog)
    with store.catalog.writer_session() as session:
        ledger.release_effective_group_in_session(session, group, [entry])
    if len(ledger.list_release_entries("source", AcquisitionStream.OUTLOOK_MAIL)) != 1:
        pytest.fail("Component could not release a semantic parent impact")


def test_expanded_attachment_detail_does_not_reversion_metadata(setup):
    crawler, _, store = setup
    capture(crawler)
    metadata = {
        "id": "a1",
        "@odata.type": "#microsoft.graph.itemAttachment",
        "name": "attached.eml",
        "size": 100,
    }
    first = store.upsert_attachment(
        run_id="r1",
        message_id="m1",
        attachment=metadata,
        evidence_id="e1",
        observed_at=NOW,
    )
    capture(crawler, "r2", "e2", observed=LATER)
    second = store.upsert_attachment(
        run_id="r2",
        message_id="m1",
        attachment={**metadata, "item": {"body": {"content": "expanded detail"}}},
        evidence_id="e2",
        observed_at=LATER,
    )
    if second.storage_relation != "current_equivalent":
        pytest.fail("Expanded item data fabricated a metadata component version")
    if first.fact.source_state_key != second.fact.source_state_key:
        pytest.fail("Attachment metadata was conflated with its detail surface")


def test_same_change_key_revalidates_primary_across_different_representations(setup):
    crawler, _, store = setup
    capture(crawler)
    first = message(store)
    capture(crawler, "r2", "e2", observed=LATER)
    richer = {
        **MESSAGE,
        "toRecipients": [],
        "body": {"content": "independent full component"},
        "internetMessageHeaders": [{"name": "x-local", "value": "fixture"}],
    }
    second = message(store, "r2", "e2", LATER, richer, "detail")
    if second.fact.source_state_key != first.fact.source_state_key:
        pytest.fail("Same provider changeKey fabricated a primary version")
    if second.storage_relation != "current_equivalent":
        pytest.fail("Same provider version did not revalidate primary state")


@pytest.mark.parametrize("missing_version", [None, ""])
def test_missing_change_key_uses_bounded_semantic_fallback(setup, missing_version):
    crawler, _, store = setup
    capture(crawler)
    fallback = {k: v for k, v in MESSAGE.items() if k != "changeKey"}
    first = message(store, payload=fallback)
    capture(crawler, "r2", "e2", observed=LATER)
    transport_and_detail = {
        **fallback,
        "changeKey": missing_version,
        "run_id": "different-attempt",
        "evidence_id": "different-capture",
        "@odata.context": "https://graph.test/context",
        "@microsoft.graph.downloadUrl": "https://graph.test/opaque",
        "access_token": "local-fixture",
        "webLink": "https://graph.test/navigation",
        "body": {"content": "separate detail"},
    }
    second = message(store, "r2", "e2", LATER, transport_and_detail)
    if second.fact.source_state_key != first.fact.source_state_key:
        pytest.fail("Fallback included transport or enrichment-only fields")
    if second.storage_relation != "current_equivalent":
        pytest.fail("Equivalent fallback fabricated primary work")
    changed = message(store, "r3", "e2", LATER, {**fallback, "toRecipients": []})
    if changed.fact.source_state_key == first.fact.source_state_key:
        pytest.fail("Fallback omitted retained primary recipient semantics")
    if changed.storage_relation != "advanced":
        pytest.fail("Changed fallback did not advance primary state")
