"""Mail release reads retain immutable outcomes after current state changes."""

import pytest
from sqlalchemy import text

from message_ingest.catalog import Catalog
from tests.source_reader.release_mail_helpers import mail_facts, read, release


@pytest.mark.parametrize(
    "status,evidence",
    [
        (status, evidence)
        for status in (
            "acquired",
            "unsupported",
            "not_applicable",
            "omitted_size_limit",
            "unauthorized",
            "unavailable",
        )
        for evidence in (True, False)
        if status != "acquired" or evidence
    ],
)
def test_mail_old_outcome_ignores_current_projection(mail_catalog, status, evidence):
    facts = mail_facts(mail_catalog, status, evidence=evidence)
    seq = release(mail_catalog, facts)
    catalog = Catalog(f"sqlite:///{mail_catalog['database']}")
    try:
        with catalog.writer_session() as session:
            session.execute(
                text(
                    "UPDATE message_surfaces SET status='unavailable', "
                    "profile_version='later-profile'"
                )
            )
    finally:
        catalog.close()
    result = read(mail_catalog, seq)
    if result.selection is None or result.selection.record.subject != "Original":
        pytest.fail("Exact Mail primary was not reconstructed")
    metadata = {m.name: m.value for m in result.components[0].record.metadata}
    if (metadata["status"], metadata["profile_version"]) != (status, "full-v1"):
        pytest.fail("Mutable status/profile replaced immutable released outcome")
    record = result.selection.record
    if record.sender.identity != "sender@example.test":
        pytest.fail("Mail sender mapping lost")
    if record.author.identity != "author@example.test" or len(record.recipients) != 1:
        pytest.fail("Mail author or recipient mapping lost")
    if status == "acquired":
        if not record.alternate_bodies or record.alternate_bodies[0].kind != "mime":
            pytest.fail("MIME bytes were not retained as an alternate body")
    elif not record.limitations:
        pytest.fail("Terminal Mail outcome lost its explicit limitation")


from tests.source_reader.release_mail_helpers import (
    mail_catalog as mail_catalog,  # noqa: PLC0414 - pytest fixture registration
)


@pytest.mark.parametrize("scope", ["mail_folder", "mailbox"])
def test_mail_scoped_transition_never_invents_deleted_payload(mail_catalog, scope):
    from dataclasses import replace

    from message_ingest.acquisition.handoff import AcquisitionFactKind
    from tests.source_reader.release_nonmail_helpers import fact, publish

    item = fact(
        "outlook_mail",
        "message",
        "released-mail",
        "mail-primary",
        scope_kind=scope,
        scope_identity="folder-f" if scope == "mail_folder" else "synthetic-source",
    )
    item = replace(
        item,
        fact_kind=AcquisitionFactKind.SCOPED_STATE_TRANSITION,
        source_version_locator=None,
        evidence_id=None,
        transition_reason="folder_membership_removed"
        if scope == "mail_folder"
        else "not_in_complete_reconciliation",
    )
    result = read(
        mail_catalog,
        publish(mail_catalog, [item], authority=True, entry_kind="transition"),
    )
    if result.selection is not None or len(result.transitions) != 1:
        pytest.fail("Scoped Mail transition invented a source payload")
    if result.transitions[0].scope_kind != scope:
        pytest.fail("Mail transition scope widened")


def test_mail_supporting_context_and_old_bytes_survive_later_version(mail_catalog):
    import asyncio

    from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
    from tests.source_reader.release_mail_helpers import LATER, MIME, RAW
    from tests.source_reader.release_nonmail_helpers import (
        SOURCE,
        reader_api,
        save_evidence,
    )

    seq = release(mail_catalog, mail_facts(mail_catalog, full=True))
    before = read(mail_catalog, seq)
    later = {**RAW, "changeKey": "v2", "subject": "Future"}
    save_evidence(mail_catalog, "later", later)
    catalog = Catalog(f"sqlite:///{mail_catalog['database']}")
    try:
        store = OutlookMailStore(catalog, source_id=SOURCE)
        store.record_message(
            run_id="later",
            message=later,
            kind="discovery",
            evidence_id="later",
            observed_at=LATER,
        )
    finally:
        catalog.close()

    async def check():
        reader = reader_api(mail_catalog)
        try:
            entry = await reader.catalog.get_release_entry(seq)
            current = await reader.read_entry(entry.reference)
            context = await reader.read_supporting_context(entry.reference)
            if (
                current != before
                or context.primary
                or context.selection != before.selection
            ):
                pytest.fail("Later Mail state changed exact release/context")
            body = current.selection.record.alternate_bodies[0]
            if await reader.load_saved_bytes(body.saved_bytes) != MIME:
                pytest.fail("Released MIME bytes changed")
        finally:
            await reader.close()

    asyncio.run(check())
