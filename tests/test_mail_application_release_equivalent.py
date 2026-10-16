"""Equivalent Mail primary reapplication must release newly selected components."""

import asyncio
import hashlib

import pytest

from message_ingest.acquisition.handoff import (
    AcquisitionStream,
    ReleaseEntrySpec,
    ReleaseGroupSpec,
    ReleaseKind,
    StorageRelation,
)
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

MIME = b"From: equivalent@example.test\r\nSubject: current\r\n\r\nSelected new MIME"


@pytest.mark.parametrize("seed_released", [False, True])
def test_new_mime_for_equivalent_primary_releases_with_effective_application(
    mail_catalog, seed_released
):
    """Q revalidates P, but its new selected MIME must be readable with P."""
    raw = {**RAW, "parentFolderId": "inbox"}
    save_evidence(mail_catalog, "seed-primary", {"value": [raw]})
    save_evidence(mail_catalog, "equivalent-primary", {"value": [raw]})
    save_evidence(mail_catalog, "equivalent-mime", MIME)
    catalog = Catalog(f"sqlite:///{mail_catalog['database']}")
    store = OutlookMailStore(catalog, source_id=SOURCE)
    try:
        primary = store.record_message(
            run_id="seed",
            message=raw,
            kind="discovery",
            evidence_id="seed-primary",
            observed_at=WHEN,
        ).fact
        if seed_released:
            with catalog.writer_session() as session:
                AcquisitionHandoffStore(catalog).release_effective_group_in_session(
                    session,
                    ReleaseGroupSpec(
                        source_id=SOURCE,
                        stream=AcquisitionStream.OUTLOOK_MAIL,
                        release_kind=ReleaseKind.RESOURCE_SET,
                        subject_kind="test_seed",
                        subject_identity=raw["id"],
                        owner_run_id="seed",
                        released_at=WHEN,
                        coverage_kind="complete",
                    ),
                    [
                        ReleaseEntrySpec(
                            resource_kind="message",
                            resource_identity=raw["id"],
                            facts=((primary.fact_id, "primary"),),
                        ),
                    ],
                )
        validated = prepare(store, "equivalent", when=LATER)
        outcome = store.record_message(
            run_id="equivalent",
            message=raw,
            kind="reconcile",
            evidence_id="equivalent-primary",
            observed_at=LATER,
            selection_id="equivalent-selected",
        )
        if (
            outcome.fact.storage_relation != StorageRelation.CURRENT_EQUIVALENT
            or outcome.fact.revalidated_fact_id != primary.fact_id
        ):
            pytest.fail("Fixture did not retain exact equivalent primary reapplication")
        selected = store.set_surface(
            run_id="equivalent",
            message_id=raw["id"],
            surface="mime",
            status="acquired",
            evidence_id="equivalent-mime",
            observed_at=LATER,
            profile_version="full-v1",
            resource_version=primary.source_state_key,
            selection_id="equivalent-selected",
            parent_evidence_id="equivalent-primary",
        )
        if selected.fact is None:
            pytest.fail("New MIME was not applied to the effective primary")
        committed = promote(store, validated)
        if committed["committed_folders"] != 1:
            pytest.fail("Equivalent primary prevented the winning cursor")
        if (
            OutlookDeltaCheckpointStore(catalog, SOURCE).get_delta_link("inbox")
            != "cursor-equivalent"
        ):
            pytest.fail("Equivalent primary changed the winner's cursor")
    finally:
        catalog.close()

    async def check():
        reader = reader_api(mail_catalog)
        try:
            ceiling = await reader.catalog.max_release_entry_seq(SOURCE, "outlook_mail")
            page = await reader.catalog.list_release_entries(
                SOURCE, "outlook_mail", after_seq=0, through_seq=ceiling, limit=30
            )
            messages = [
                entry
                for entry in page.entries
                if entry.resource_kind == "message"
                and entry.resource_identity == raw["id"]
            ]
            if len(messages) != (2 if seed_released else 1):
                pytest.fail("Equivalent selected MIME produced no new message impact")
            latest = await reader.read_entry(messages[-1].reference)
            if latest.selection is None or len(latest.components) != 1:
                pytest.fail("Equivalent primary lost the new readable MIME component")
            saved = latest.selection.record.alternate_bodies
            if (
                len(saved) != 1
                or saved[0].saved_bytes is None
                or saved[0].saved_bytes.sha256 != hashlib.sha256(MIME).hexdigest()
            ):
                pytest.fail("Equivalent application did not release the selected bytes")
            if not any(
                fact.fact_id == primary.fact_id and fact.role == "primary"
                for fact in latest.facts
            ):
                pytest.fail("Equivalent release did not preserve effective primary P")
        finally:
            await reader.close()

    asyncio.run(check())
