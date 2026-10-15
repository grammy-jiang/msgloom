"""Mail A/B/A release must not attach old selected components to new primary applications."""

import asyncio

import pytest

from message_ingest.acquisition.handoff import AcquisitionStream
from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from message_ingest.sync.microsoft.outlook.email.checkpoints import (
    OutlookDeltaCheckpointStore,
)
from tests._mail_provisional import LATER, WHEN, prepare, promote
from tests.source_reader.release_mail_helpers import RAW
from tests.source_reader.release_mail_helpers import (
    mail_catalog as mail_catalog,  # noqa: PLC0414 - fixture registration
)
from tests.source_reader.release_nonmail_helpers import (
    SOURCE,
    reader_api,
    save_evidence,
)


@pytest.mark.parametrize("replacement_mime", [False, True])
def test_selected_mime_from_first_a_cannot_poison_later_same_run_a(
    mail_catalog, replacement_mime
):
    """A1->B->A2 must preserve only components bound to the selected A2."""
    message_a = {**RAW, "changeKey": "v1", "parentFolderId": "inbox"}
    message_b = {**message_a, "changeKey": "v2"}
    for evidence_id, body in (
        ("a-first", message_a),
        ("b-middle", message_b),
        ("a-return", message_a),
        ("old-mime", b"From: first@example.test\r\nSubject: first\r\n\r\nOld MIME"),
        ("new-mime", b"From: later@example.test\r\nSubject: later\r\n\r\nNew MIME"),
    ):
        save_evidence(mail_catalog, evidence_id, body)
    catalog = Catalog(f"sqlite:///{mail_catalog['database']}")
    store = OutlookMailStore(catalog, source_id=SOURCE)
    try:
        validated = prepare(store, "aba-selected", when=WHEN)
        first = store.record_message(
            run_id="aba-selected",
            kind="discovery",
            message=message_a,
            evidence_id="a-first",
            observed_at=WHEN,
            selection_id="first-a",
        )
        original = store.set_surface(
            run_id="aba-selected",
            message_id=message_a["id"],
            surface="mime",
            status="acquired",
            evidence_id="old-mime",
            observed_at=WHEN,
            profile_version="full-v1",
            resource_version=first.fact.source_state_key,
            selection_id="first-a",
            parent_evidence_id="a-first",
        )
        if original.fact is None:
            pytest.fail("The selected MIME was not applied to the first A")
        store.record_message(
            run_id="aba-selected",
            kind="discovery",
            message=message_b,
            evidence_id="b-middle",
            observed_at=LATER,
            selection_id="middle-b",
        )
        latest = store.record_message(
            run_id="aba-selected",
            kind="discovery",
            message=message_a,
            evidence_id="a-return",
            observed_at="2026-10-03T00:00:00+00:00",
            selection_id="later-a",
        )
        current_mime_id = original.fact.fact_id
        if replacement_mime:
            applied_mime = store.set_surface(
                run_id="aba-selected",
                message_id=message_a["id"],
                surface="mime",
                status="acquired",
                evidence_id="new-mime",
                observed_at="2026-10-03T00:00:00+00:00",
                profile_version="full-v1",
                resource_version=latest.fact.source_state_key,
                selection_id="later-a",
                parent_evidence_id="a-return",
            )
            if applied_mime.fact is None:
                pytest.fail("The selected later-A MIME was not persisted")
            current_mime_id = applied_mime.fact.fact_id
        if (
            first.fact.source_state_key != latest.fact.source_state_key
            or first.fact.fact_id == latest.fact.fact_id
        ):
            pytest.fail(
                "The ABA fixture did not create distinct equal-key applications"
            )
        ledger = AcquisitionHandoffStore(catalog)
        with catalog.Session() as session:
            current = ledger.current_effective_state(
                session, original.fact.effective_key
            )
            expected = current_mime_id
            if current is None or current["fact_id"] != expected:
                pytest.fail("The exact selected MIME is not independently current")
        applied = promote(store, validated)
        if applied["committed_folders"] != 1:
            pytest.fail("The valid ABA cursor promotion was lost")
        if (
            OutlookDeltaCheckpointStore(catalog, SOURCE).get_delta_link("inbox")
            != "cursor-aba-selected"
        ):
            pytest.fail("The valid ABA cursor was not committed")
        entries = ledger.list_release_entries(SOURCE, AcquisitionStream.OUTLOOK_MAIL)
        if not entries:
            pytest.fail("The valid final A primary produced no release")
    finally:
        catalog.close()

    async def check():
        reader = reader_api(mail_catalog)
        try:
            cutoff = await reader.catalog.max_release_entry_seq(SOURCE, "outlook_mail")
            page = await reader.catalog.list_release_entries(
                SOURCE, "outlook_mail", after_seq=0, through_seq=cutoff, limit=30
            )
            impacts = [
                entry
                for entry in page.entries
                if entry.resource_kind == "message"
                and entry.resource_identity == message_a["id"]
            ]
            if len(impacts) != 1:
                pytest.fail("ABA must leave one exact readable primary impact")
            released = await reader.read_entry(impacts[0].reference)
            if released.selection is None or len(released.components) != int(
                replacement_mime
            ):
                pytest.fail("Old first-A MIME contaminated later A application")
            if replacement_mime:
                from hashlib import sha256

                bodies = released.selection.record.alternate_bodies
                if (
                    len(bodies) != 1
                    or bodies[0].saved_bytes is None
                    or bodies[0].saved_bytes.sha256
                    != sha256(
                        b"From: later@example.test\r\nSubject: later\r\n\r\nNew MIME"
                    ).hexdigest()
                ):
                    pytest.fail("The selected later-A MIME was lost or replaced")
            facts = released.facts
            if not any(
                fact.fact_id == latest.fact.fact_id and fact.role == "primary"
                for fact in facts
            ):
                pytest.fail("Final ABA primary application was not retained")
        finally:
            await reader.close()

    asyncio.run(check())
