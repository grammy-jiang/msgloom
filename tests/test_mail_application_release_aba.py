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


@pytest.mark.parametrize(
    ("replacement_mime", "tamper_stage"),
    [
        ("none", False),
        ("changed", False),
        ("equivalent", False),
        ("equivalent_shared", False),
        ("equivalent_shared", True),
    ],
)
def test_selected_mime_from_first_a_cannot_poison_later_same_run_a(
    mail_catalog, replacement_mime, tamper_stage
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
        ("equiv-mime", b"From: first@example.test\r\nSubject: first\r\n\r\nOld MIME"),
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
        staged_component_id = None
        if replacement_mime != "none":
            applied_mime = store.set_surface(
                run_id="aba-selected",
                message_id=message_a["id"],
                surface="mime",
                status="acquired",
                evidence_id=(
                    "old-mime"
                    if replacement_mime == "equivalent_shared"
                    else "equiv-mime"
                    if replacement_mime == "equivalent"
                    else "new-mime"
                ),
                observed_at="2026-10-03T00:00:00+00:00",
                profile_version="full-v1",
                resource_version=latest.fact.source_state_key,
                selection_id="later-a",
                parent_evidence_id="a-return",
            )
            if applied_mime.fact is None:
                pytest.fail("The selected later-A MIME was not persisted")
            staged_component_id = applied_mime.fact.fact_id
            if replacement_mime.startswith("equivalent") and (
                applied_mime.fact.storage_relation != "current_equivalent"
                or applied_mime.fact.revalidated_fact_id != original.fact.fact_id
            ):
                pytest.fail("Selected same-byte MIME did not revalidate C1 through C2")
            current_mime_id = (
                original.fact.fact_id
                if replacement_mime.startswith("equivalent")
                else applied_mime.fact.fact_id
            )
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

    if tamper_stage:
        if staged_component_id is None:
            pytest.fail("Tamper case did not retain a staged C2 fact")
        # Model a corrupted immutable C2 application after the release is
        # sealed; C2 is not a release member, so Reader must validate the
        # staged revalidation named by the additive alias.
        import sqlite3

        with sqlite3.connect(mail_catalog["database"]) as db:
            for (name,) in db.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger' "
                "AND tbl_name='acquisition_facts'"
            ):
                db.execute(f'DROP TRIGGER "{name}"')
            db.execute(
                "DELETE FROM acquisition_facts WHERE fact_id=?",
                (staged_component_id,),
            )

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
            if tamper_stage:
                from msgloom.sources.models import SourceReferenceError

                with pytest.raises(
                    SourceReferenceError,
                    match="Mail component lacks exact primary application",
                ):
                    await reader.read_entry(impacts[0].reference)
                return
            released = await reader.read_entry(impacts[0].reference)
            if released.selection is None or len(released.components) != (
                replacement_mime != "none"
            ):
                pytest.fail("Old first-A MIME contaminated later A application")
            if replacement_mime != "none":
                from hashlib import sha256

                expected_bytes = (
                    b"From: first@example.test\r\nSubject: first\r\n\r\nOld MIME"
                    if replacement_mime.startswith("equivalent")
                    else b"From: later@example.test\r\nSubject: later\r\n\r\nNew MIME"
                )
                bodies = released.selection.record.alternate_bodies
                if (
                    len(bodies) != 1
                    or bodies[0].saved_bytes is None
                    or bodies[0].saved_bytes.sha256
                    != sha256(expected_bytes).hexdigest()
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
