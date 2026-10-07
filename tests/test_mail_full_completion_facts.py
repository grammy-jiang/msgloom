"""Prove Mail target reuse, cache provenance and final release freshness."""

from __future__ import annotations

import pytest
from _full_completion_fixtures import (
    LATER,
    NOW,
    save,
    seed_target,
    set_surface,
)
from sqlalchemy import delete, select, update

from message_ingest.acquisition.handoff import (
    AcquisitionStream,
    ReleaseEntrySpec,
    ReleaseGroupSpec,
    ReleaseKind,
)
from message_ingest.acquisition.microsoft.outlook.email.full_completion import (
    verify_current_full_v1,
    verify_full_v1_target,
)
from message_ingest.catalog import Catalog
from message_ingest.catalog.models.microsoft.outlook.email import (
    AttachmentRecord,
    MessageSurface,
)
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore


@pytest.fixture
def catalog(tmp_path):
    value = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    yield value
    value.close()


def verify(catalog, *, run="run", current=True):
    return verify_full_v1_target(
        catalog,
        source_id="source",
        run_id=run,
        message_id="one",
        require_current_attempt=current,
    )


def publish(catalog, proof, run):
    """
    Exercise the real immutable ledger without adding a release extension.
    """
    ledger = AcquisitionHandoffStore(catalog)
    group = ReleaseGroupSpec(
        source_id="source",
        stream=AcquisitionStream.OUTLOOK_MAIL,
        release_kind=ReleaseKind.RESOURCE_PROFILE,
        subject_kind="message",
        subject_identity="one",
        owner_run_id=run,
        released_at=LATER,
        coverage_kind="complete",
        profile="outlook-mail-full-v1",
    )
    entry = ReleaseEntrySpec(
        resource_kind="message",
        resource_identity="one",
        facts=tuple(
            (fact.fact_id, "primary" if fact.component_kind is None else "component")
            for fact in proof.required_facts
        ),
    )
    with catalog.writer_session() as session:
        ledger.release_effective_group_in_session(session, group, [entry])
    return ledger.list_release_entries("source", AcquisitionStream.OUTLOOK_MAIL)


def test_no_work_revalidation_recovers_once_and_preserves_locators(catalog):
    seed_target(catalog, "mail")
    if verify(catalog, run="reuse").complete:
        pytest.fail("An old attempt satisfied current-attempt proof")
    proof = verify(catalog, run="reuse", current=False)
    if not proof.complete:
        pytest.fail(f"No-work proof failed: {proof}")
    if len(publish(catalog, proof, "reuse")) != 1:
        pytest.fail("Unreleased effective facts were not recovered")
    if len(publish(catalog, proof, "again")) != 1:
        pytest.fail("Unchanged facts published repetitive primary work")


def test_delayed_proof_cannot_release_after_newer_primary(catalog):
    store = seed_target(catalog, "mail")
    proof = verify(catalog)
    raw = {"id": "one", "changeKey": "v2"}
    evidence = save(catalog, "new-primary", raw, run="other", at=LATER)
    store.record_message(
        run_id="other",
        message=raw,
        kind="discovery",
        evidence_id=evidence,
        observed_at=LATER,
    )
    if publish(catalog, proof, "delayed"):
        pytest.fail("Old completion became new work after state replacement")


def test_changed_parent_cannot_reuse_old_versioned_mime(catalog):
    store = seed_target(catalog, "mail")
    raw = {"id": "one", "changeKey": "v2"}
    evidence = save(catalog, "new-primary", raw, at=LATER)
    primary = store.record_message(
        run_id="run",
        message=raw,
        kind="detail",
        evidence_id=evidence,
        observed_at=LATER,
    ).fact
    set_surface(
        store,
        "mail",
        "one",
        "detail",
        evidence,
        version=primary.source_state_key,
        at=LATER,
    )
    if verify(catalog, current=False).complete:
        pytest.fail("Older parent-bound MIME satisfied new Full target")


def test_mail_inventory_cannot_hide_failed_metadata(catalog):
    store = seed_target(catalog, "mail")
    evidence = save(
        catalog,
        "inventory",
        {
            "value": [
                {"id": "a1", "@odata.type": "#microsoft.graph.fileAttachment"},
            ]
        },
    )
    set_surface(store, "mail", "one", "attachments", evidence, version=None)
    if verify(catalog).complete:
        pytest.fail("Missing Mail metadata and child fact escaped completion")


def test_cache_logical_run_does_not_weaken_capture_run_authority(catalog):
    store = seed_target(catalog, "mail")
    store.record_message(
        run_id="cache-retry",
        message={"id": "one", "changeKey": "v1"},
        kind="detail",
        evidence_id="mail-one-run-detail",
        observed_at=NOW,
    )
    for surface in ("detail", "mime", "attachments"):
        set_surface(
            store,
            "mail",
            "one",
            surface,
            f"mail-one-run-{surface}",
            run="cache-retry",
            version=None,
        )
    proof = verify(catalog, run="cache-retry")
    if not proof.complete:
        pytest.fail(f"Logical cache retry did not bind exact existing state: {proof}")
    authority = verify_current_full_v1(
        catalog,
        source_id="source",
        run_id="cache-retry",
        message_ids=("one",),
    )
    if authority.complete:
        pytest.fail("Additional release proof weakened current-capture authority")


def test_caller_transaction_is_not_committed_by_verifier(catalog):
    seed_target(catalog, "mail")
    with catalog.writer_session() as session:
        proof = verify_full_v1_target(
            catalog,
            source_id="source",
            run_id="run",
            message_id="one",
            writer=session,
        )
        if not proof.complete or not session.in_transaction():
            pytest.fail("Verifier changed caller transaction ownership")


@pytest.mark.parametrize(
    "status",
    [
        "unsupported",
        "unauthorized",
        "unavailable",
        "omitted_size_limit",
        "not_applicable",
    ],
)
def test_mail_terminal_limitations_are_profile_gated(catalog, status):
    store = seed_target(catalog, "mail")
    # Existing run's primary binding is obtained by the provider store.
    store.set_surface(
        run_id="run",
        message_id="one",
        surface="mime",
        status=status,
        evidence_id="mail-one-run-mime",
        observed_at=NOW,
        profile_version="outlook-mail-full-v1",
    )
    result = verify(catalog)
    if not result.complete or result.limitation_codes != (status,):
        pytest.fail("Terminal Mail limitation did not bind profile proof")
    # A failed detail request cannot create a terminal Mail surface fact.
    with catalog.writer_session() as session:
        session.execute(
            delete(MessageSurface).where(
                MessageSurface.source_id == "source",
                MessageSurface.message_id == "one",
                MessageSurface.surface == "detail",
            )
        )
    result = verify(catalog)
    if result.complete or result.terminal_with_limitations:
        pytest.fail("Failed Mail profile masqueraded as terminal limitations")


def test_unknown_mail_target_can_finish_with_only_terminal_limitations(catalog):
    """Unavailable explicit IDs still have a terminal Full-v1 profile."""
    from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore

    store = OutlookMailStore(catalog, source_id="source")
    for name in ("detail", "mime", "attachments"):
        evidence = save(catalog, f"missing-{name}", {"error": "not found"})
        set_surface(
            store, "mail", "one", name, evidence, version=None, status="unavailable"
        )
    result = verify(catalog)
    if (
        not result.complete
        or not result.terminal_with_limitations
        or len(result.required_facts) != 3
    ):
        pytest.fail(f"Profile-complete unavailable target was rejected: {result}")


@pytest.mark.parametrize("corrupt", ["surface", "metadata"])
def test_selected_mail_capture_proves_current_inventory_and_children(tmp_path, corrupt):
    """Native selection facts must complete without legacy digest fallback."""
    from test_mail_enrichment_planner import _message, _pin, _store, _surface
    from test_mail_inventory_bindings import seed_inventory

    catalog, store = _store(tmp_path)
    try:
        _message(store, "one")
        for surface in ("detail", "mime", "attachments"):
            _surface(store, "one", surface)
        seed_inventory(
            store,
            "one",
            "selection-one",
            _pin(store, "one"),
            "primary-one",
            [{"id": "a", "@odata.type": "#microsoft.graph.fileAttachment"}],
        )

        def proof():
            return verify_full_v1_target(
                catalog,
                source_id="source-1",
                run_id="fixture-run",
                message_id="one",
            )

        if proof().complete:
            pytest.fail("Selected inventory ignored missing child bytes")
        _surface(store, "one", "attachment_raw:a")
        result = proof()
        if not result.complete or len(result.required_facts) != 6:
            pytest.fail(f"Selected Mail capture did not bind exact facts: {result}")
        with catalog.writer_session() as session:
            if corrupt == "surface":
                session.execute(
                    update(MessageSurface)
                    .where(
                        MessageSurface.source_id == "source-1",
                        MessageSurface.message_id == "one",
                        MessageSurface.surface == "mime",
                    )
                    .values(status="unavailable")
                )
            else:
                session.execute(
                    update(AttachmentRecord)
                    .where(
                        AttachmentRecord.source_id == "source-1",
                        AttachmentRecord.message_id == "one",
                    )
                    .values(attachment_type="#microsoft.graph.referenceAttachment")
                )
        if proof().complete:
            pytest.fail("Mutable projection disagreed with selected immutable fact")
    finally:
        catalog.close()


@pytest.mark.parametrize("corrupt", [False, True])
def test_selected_mail_connection_preserves_caller_transaction(tmp_path, corrupt):
    """Selected proof reads pending writes and leaves their rollback to caller."""
    from test_mail_enrichment_planner import _message, _pin, _store, _surface
    from test_mail_inventory_bindings import seed_inventory

    catalog, store = _store(tmp_path)
    try:
        _message(store, "one")
        for surface in ("detail", "mime", "attachments"):
            _surface(store, "one", surface)
        seed_inventory(
            store,
            "one",
            "selection-one",
            _pin(store, "one"),
            "primary-one",
            [{"id": "a", "@odata.type": "#microsoft.graph.fileAttachment"}],
        )
        _surface(store, "one", "attachment_raw:a")
        table = MessageSurface.metadata.tables[MessageSurface.__tablename__]
        mime = (
            (table.c.source_id == "source-1")
            & (table.c.message_id == "one")
            & (table.c.surface == "mime")
        )
        with catalog.engine.connect() as connection:
            transaction = connection.begin()
            connection.execute(
                update(table)
                .where(mime)
                .values(
                    observed_at=LATER,
                    status="unavailable" if corrupt else "acquired",
                )
            )
            result = verify_full_v1_target(
                catalog,
                source_id="source-1",
                run_id="fixture-run",
                message_id="one",
                writer=connection,
            )
            if result.complete == corrupt:
                pytest.fail(f"Proof did not read caller's selected state: {result}")
            if connection.closed or not transaction.is_active:
                pytest.fail("Selected proof closed or ended caller transaction")
            if connection.scalar(select(table.c.observed_at).where(mime)) != LATER:
                pytest.fail("Selected proof rolled back caller's pending write")
            transaction.rollback()
        with catalog.engine.connect() as connection:
            row = connection.execute(
                select(table.c.observed_at, table.c.status).where(mime)
            ).one()
            if row.observed_at == LATER or row.status != "acquired":
                pytest.fail("Selected proof committed caller's pending write")
    finally:
        catalog.close()
