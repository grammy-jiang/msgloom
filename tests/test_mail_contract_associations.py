"""Regressions for immutable Mail outcomes and exact parent association."""

import json

import pytest
from test_outlook_mail_handoff_facts import (
    LATER,
    NOW,
    capture,
    message,
)
from test_outlook_mail_handoff_facts import (
    setup as setup,  # noqa: PLC0414 - pytest fixture registration
)

from message_ingest.acquisition.handoff import (
    AcquisitionStream,
    ReleaseEntrySpec,
    ReleaseGroupSpec,
    ReleaseKind,
)
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore


@pytest.mark.parametrize(
    "status",
    [
        "acquired",
        "unsupported",
        "not_applicable",
        "omitted_size_limit",
        "unauthorized",
        "unavailable",
    ],
)
def test_surface_outcome_is_readable_and_canonical(setup, status):
    """Retain bounded local outcomes independently of mutable projections."""
    crawler, _, store = setup
    capture(crawler)
    first = store.set_surface(
        run_id="r1",
        message_id="m1",
        surface="mime",
        status=status,
        evidence_id="e1",
        observed_at=NOW,
        profile_version="outlook-mail-full-v1",
        resource_version="parent-1",
    ).fact
    store.set_surface(
        run_id="r2",
        message_id="m1",
        surface="mime",
        status="unavailable",
        evidence_id="e1",
        observed_at=LATER,
        profile_version="outlook-mail-full-v1",
        resource_version="parent-2",
    )
    expected = json.dumps(
        {"status": status, "profile_version": "outlook-mail-full-v1"},
        sort_keys=True,
        separators=(",", ":"),
    )
    if first.transition_reason != expected:
        pytest.fail("Immutable fact lost canonical status/profile metadata")


@pytest.mark.parametrize("family", ["surface", "attachment"])
def test_identical_component_only_equivalent_under_same_parent(setup, family):
    """Same content under another primary must retain another locator."""
    crawler, _, store = setup
    capture(crawler)

    def write(run, parent):
        kwargs = {
            "run_id": run,
            "message_id": "m1",
            "evidence_id": "e1",
            "observed_at": LATER,
            "resource_version": parent,
        }
        if family == "surface":
            return store.set_surface(
                surface="mime",
                status="acquired",
                profile_version="outlook-mail-full-v1",
                **kwargs,
            ).fact
        return store.upsert_attachment(
            attachment={"id": "a", "name": "same"},
            **kwargs,
        ).fact

    first = write("r1", "parent-1")
    same = write("r2", "parent-1")
    changed = write("r3", "parent-2")
    if same.storage_relation != "current_equivalent":
        pytest.fail("Same-parent equivalent replay created new work")
    if changed.storage_relation != "advanced":
        pytest.fail("New parent was incorrectly equivalent to old association")
    if changed.source_state_key == first.source_state_key:
        pytest.fail("Exact parent missing from component semantic key")
    if changed.source_version_locator.resource_version != "parent-2":
        pytest.fail("Component locator lost explicit parent")


def test_same_parent_failed_run_recovers_once(setup):
    """Frozen ledger recovers an unchanged component once across retries."""
    crawler, _, store = setup
    capture(crawler)
    parent = message(store).fact
    ledger = AcquisitionHandoffStore(store.catalog)
    for n in range(3):
        run = f"run-{n}"
        component = store.set_surface(
            run_id=run,
            message_id="m1",
            surface="mime",
            status="acquired",
            evidence_id="e1",
            observed_at=LATER,
            profile_version="outlook-mail-full-v1",
            resource_version=parent.source_state_key,
        ).fact
        if n == 0:
            continue
        group = ReleaseGroupSpec(
            source_id="source",
            stream=AcquisitionStream.OUTLOOK_MAIL,
            release_kind=ReleaseKind.RESOURCE_PROFILE,
            subject_kind="message",
            subject_identity="m1",
            owner_run_id=run,
            released_at=LATER,
            coverage_kind="complete",
            profile="outlook-mail-full-v1",
        )
        entry = ReleaseEntrySpec(
            resource_kind="message",
            resource_identity="m1",
            facts=((parent.fact_id, "primary"), (component.fact_id, "component")),
        )
        with store.catalog.writer_session() as session:
            ledger.release_effective_group_in_session(session, group, [entry])
    if len(ledger.list_release_entries("source", AcquisitionStream.OUTLOOK_MAIL)) != 1:
        pytest.fail("Failed-run recovery lost work or repeated released state")


@pytest.mark.parametrize("family", ["surface", "attachment"])
def test_delayed_component_cannot_replace_newer_parent(setup, family):
    """A newer component response time cannot refresh an obsolete parent."""
    crawler, _, store = setup
    capture(crawler)
    old = message(store).fact
    from test_outlook_mail_handoff_facts import MESSAGE

    new = message(store, "r2", "e1", LATER, {**MESSAGE, "changeKey": "v2"}).fact
    kwargs = {
        "run_id": "old-run",
        "message_id": "m1",
        "evidence_id": "e1",
        "observed_at": "2026-10-03T02:00:00+00:00",
        "resource_version": old.source_state_key,
        "primary_observed_at": NOW,
    }
    if family == "surface":
        outcome = store.set_surface(surface="mime", status="acquired", **kwargs)
        current = store.get_surfaces(message_id="m1")
    else:
        outcome = store.upsert_attachment(attachment={"id": "a"}, **kwargs)
        current = store.get_attachments(message_id="m1")
    if outcome.storage_relation != "stale" or current:
        pytest.fail("Superseded parent advanced component projection")
    if old.source_state_key == new.source_state_key:
        pytest.fail("Fixture did not advance the primary")


@pytest.mark.parametrize(
    "reason",
    [
        None,
        "",
        "{}",
        '{"status":"invented","profile_version":null}',
        '{"status":"acquired","profile_version":null,"payload":"forbidden"}',
        '{"status":"acquired", "profile_version":null}',
    ],
)
def test_legacy_unknown_or_noncanonical_metadata_fails_closed(reason):
    """Readers cannot infer missing historical acquisition decisions."""
    from message_ingest.catalog.stores.microsoft.outlook._email_handoff import (
        decode_surface_reason,
    )

    with pytest.raises(ValueError):
        decode_surface_reason(reason)


def test_unbound_complete_rows_still_require_acquisition(setup):
    """Mutable terminal surfaces cannot permanently suppress valid work."""
    crawler, _, store = setup
    capture(crawler)
    for surface in ("detail", "mime", "attachments"):
        store.set_surface(
            run_id="unbound",
            message_id="m1",
            surface=surface,
            status="acquired",
            evidence_id="e1",
            observed_at=NOW,
            profile_version="outlook-mail-full-v1",
        )
    message(store)
    if store.full_binding_complete(message_id="m1"):
        pytest.fail("Legacy unbound surfaces falsely counted as complete")
    state = store.full_binding_state(message_id="m1")
    if state["surfaces"]:
        pytest.fail("Planner exposed unbound projections as exact Full state")


@pytest.mark.parametrize("family", ["surface", "attachment"])
def test_bound_association_fact_failure_rolls_back_projection(setup, family):
    """A new exact association cannot survive failure of its atomic fact."""
    from sqlalchemy import text
    from sqlalchemy.exc import DatabaseError

    crawler, _, store = setup
    capture(crawler, body=b"original")

    def write(run, evidence, parent):
        kwargs = {
            "run_id": run,
            "message_id": "m1",
            "evidence_id": evidence,
            "observed_at": LATER,
            "resource_version": parent,
        }
        if family == "surface":
            return store.set_surface(surface="mime", status="acquired", **kwargs)
        return store.upsert_attachment(
            attachment={"id": "a1", "name": parent},
            **kwargs,
        )

    original = write("r1", "e1", "parent-1").fact
    capture(crawler, "r2", "e2", body=b"replacement", observed=LATER)
    with store.catalog.writer_session() as session:
        session.execute(
            text(
                "CREATE TRIGGER reject_bound_fact BEFORE INSERT ON acquisition_facts "
                "BEGIN SELECT RAISE(ABORT, 'bound fact failure'); END"
            )
        )
    with pytest.raises(DatabaseError, match="bound fact failure"):
        write("r2", "e2", "parent-2")
    with store.catalog.Session() as session:
        current = AcquisitionHandoffStore(store.catalog).current_effective_state(
            session,
            original.effective_key,
        )
        if current is None or current["fact_id"] != original.fact_id:
            pytest.fail("Failed association advanced effective state")
    if family == "surface":
        evidence = store.get_surfaces(message_id="m1")["mime"]["evidence_id"]
    else:
        evidence = store.get_attachments(message_id="m1")[0]["latest_evidence_id"]
    if evidence != "e1":
        pytest.fail("Failed association advanced its domain projection")


@pytest.mark.parametrize(
    "surface,status",
    [
        ("mime", "acquired"),
        ("attachments", "acquired"),
        ("attachment_raw:a", "acquired"),
        ("item_attachment_detail:a", "acquired"),
        ("attachment_raw:a", "omitted_size_limit"),
        ("attachment_raw:a", "unsupported"),
        ("mime", "unavailable"),
        ("attachment_metadata", "acquired"),
    ],
)
def test_each_component_pipeline_can_finish_before_primary(setup, surface, status):
    """Explicit pins work for every Full item before primary persistence."""
    import asyncio

    from sqlalchemy import select
    from test_mail_inventory_bindings import make_page
    from test_outlook_mail_handoff_facts import MESSAGE, facts

    from message_ingest.catalog.models.microsoft.outlook._email_bindings import (
        MailComponentCapture,
    )
    from message_ingest.catalog.stores.microsoft.outlook._email_handoff import (
        primary_projection,
        semantic_digest,
    )
    from message_ingest.items.microsoft.outlook.email import (
        OutlookAttachmentItem,
        OutlookMailDetailItem,
        OutlookMessageSurfaceItem,
    )

    crawler, pipeline, store = setup
    pin = semantic_digest(primary_projection(MESSAGE))
    capture(crawler, "r1", "detail-selected", body=json.dumps(MESSAGE).encode())
    capture(crawler, "r1", "e1", body=b"bytes")
    common = {
        "run_id": "r1",
        "message_id": "m1",
        "observed_at": NOW,
        "evidence_id": "e1",
        "resource_version": pin,
        "primary_observed_at": NOW,
        "selection_id": "selected",
        "parent_evidence_id": "detail-selected",
    }
    if surface == "attachment_metadata":
        item = OutlookAttachmentItem(
            attachment_id="a",
            attachment_type="file",
            raw={"id": "a"},
            source_response_url="https://graph.test/fixture",
            **common,
        )
    elif surface == "attachments":
        item = make_page(store, pin, [], 1, when=NOW)
    else:
        item = OutlookMessageSurfaceItem(
            surface=surface,
            status=status,
            **common,
        )
    asyncio.run(pipeline.process_item(item))
    if facts(store):
        pytest.fail("Pending component fabricated an effective ledger fact")
    with store.catalog.Session() as session:
        saved = session.scalars(select(MailComponentCapture)).all()
        if len(saved) != 1 or saved[0].parent_key != pin:
            pytest.fail("Early component lost durable exact selected-parent pin")
    asyncio.run(
        pipeline.process_item(
            OutlookMailDetailItem(
                message_id="m1",
                raw=MESSAGE,
                source_response_url="https://graph.test/fixture",
                observed_at=NOW,
                evidence_id="detail-selected",
                run_id="r1",
                selection_id="selected",
            )
        )
    )
    component = next(f for f in facts(store) if f.component_kind == surface)
    if (
        component.source_version_locator is None
        or component.source_version_locator.resource_version != pin
    ):
        pytest.fail("Primary commit did not atomically apply the selected capture")
