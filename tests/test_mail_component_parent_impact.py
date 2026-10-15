"""Mail authority impacts must remain consumable at their message parent."""

import asyncio

import pytest

from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from tests._mail_provisional import capture, prepare, promote
from tests.source_reader.release_mail_helpers import (
    RAW,
)
from tests.source_reader.release_mail_helpers import (
    mail_catalog as mail_catalog,  # noqa: PLC0414 - fixture registration
)
from tests.source_reader.release_nonmail_helpers import (
    SOURCE,
    WHEN,
    reader_api,
    save_evidence,
)


def test_delta_discovery_component_is_readable_with_exact_primary(mail_catalog):
    """A winning Delta must not publish a component that A2 must hold."""
    raw = {**RAW, "parentFolderId": "inbox"}
    save_evidence(mail_catalog, "delta-page", {"value": [raw]})
    catalog = Catalog(f"sqlite:///{mail_catalog['database']}")
    store = OutlookMailStore(catalog, source_id=SOURCE)
    try:
        validated = prepare(store, "delta-parent", when=WHEN)
        primary = capture(
            store,
            "delta-parent",
            raw,
            evidence="delta-page",
            when=WHEN,
        )
        store.set_surface(
            run_id="delta-parent",
            message_id=raw["id"],
            surface="discovery",
            status="acquired",
            observed_at=WHEN,
            evidence_id="delta-page",
            resource_version=primary.fact.source_state_key,
            observation_kind="delta",
        )
        promote(store, validated)
    finally:
        catalog.close()

    async def verify():
        reader = reader_api(mail_catalog)
        try:
            ceiling = await reader.catalog.max_release_entry_seq(SOURCE, "outlook_mail")
            page = await reader.catalog.list_release_entries(
                SOURCE, "outlook_mail", after_seq=0, through_seq=ceiling, limit=20
            )
            message_entries = [
                entry
                for entry in page.entries
                if entry.resource_identity == raw["id"]
                and entry.resource_kind in {"message", "message_surface"}
            ]
            if not message_entries:
                pytest.fail("Delta released no message impact")
            for entry in message_entries:
                released = await reader.read_entry(entry.reference)
                if released.selection is None:
                    pytest.fail(
                        "A message component was not bound to a readable parent"
                    )
            if len(message_entries) != 1:
                pytest.fail(
                    "Delta split one message and discovery into separate impacts"
                )
        finally:
            await reader.close()

    asyncio.run(verify())


def test_later_independent_same_version_primary_keeps_delta_component_readable(
    mail_catalog,
):
    """An accepted Full version can be pinned by a deferred Delta component."""
    from tests._mail_provisional import LATER

    raw = {**RAW, "parentFolderId": "inbox"}
    save_evidence(mail_catalog, "delta-page", {"value": [raw]})
    save_evidence(mail_catalog, "full-primary", raw)
    catalog = Catalog(f"sqlite:///{mail_catalog['database']}")
    store = OutlookMailStore(catalog, source_id=SOURCE)
    try:
        validated = prepare(store, "same-version", when=WHEN)
        pending = capture(store, "same-version", raw, evidence="delta-page", when=WHEN)
        store.set_surface(
            run_id="same-version",
            message_id=raw["id"],
            surface="discovery",
            status="acquired",
            observed_at=WHEN,
            evidence_id="delta-page",
            resource_version=pending.fact.source_state_key,
            observation_kind="delta",
        )
        store.record_message(
            run_id="full-independent",
            message=raw,
            kind="detail",
            evidence_id="full-primary",
            observed_at=LATER,
        )
        promote(store, validated)
    finally:
        catalog.close()

    async def verify():
        reader = reader_api(mail_catalog)
        try:
            ceiling = await reader.catalog.max_release_entry_seq(SOURCE, "outlook_mail")
            page = await reader.catalog.list_release_entries(
                SOURCE, "outlook_mail", after_seq=0, through_seq=ceiling, limit=20
            )
            message_entries = [
                entry
                for entry in page.entries
                if entry.resource_kind == "message"
                and entry.resource_identity == raw["id"]
            ]
            if len(message_entries) != 1:
                pytest.fail("Deferred component was not published as one Mail impact")
            released = await reader.read_entry(message_entries[0].reference)
            if released.selection is None or len(released.components) != 1:
                pytest.fail(
                    "Accepted same-version primary did not bind Delta component"
                )
        finally:
            await reader.close()

    asyncio.run(verify())


def test_newer_different_version_does_not_block_mail_cursor(mail_catalog):
    """An older reconciliation component cannot veto a newer Full version."""
    from message_ingest.acquisition.handoff import AcquisitionStream
    from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
    from message_ingest.sync.microsoft.outlook.email.checkpoints import (
        OutlookDeltaCheckpointStore,
    )
    from tests._mail_provisional import LATER

    old = {**RAW, "parentFolderId": "inbox"}
    newer = {**old, "changeKey": "v2", "subject": "new-version"}
    save_evidence(mail_catalog, "reconcile-old", {"value": [old]})
    save_evidence(mail_catalog, "full-new", newer)
    catalog = Catalog(f"sqlite:///{mail_catalog['database']}")
    store = OutlookMailStore(catalog, source_id=SOURCE)
    try:
        validated = prepare(store, "overlap", when=WHEN)
        original = store.record_message(
            run_id="overlap",
            message=old,
            kind="reconcile",
            evidence_id="reconcile-old",
            observed_at=WHEN,
        )
        store.set_surface(
            run_id="overlap",
            message_id=old["id"],
            surface="discovery",
            status="acquired",
            evidence_id="reconcile-old",
            observed_at=WHEN,
            resource_version=original.fact.source_state_key,
            observation_kind="reconcile",
        )
        store.record_message(
            run_id="independent-full",
            message=newer,
            kind="detail",
            evidence_id="full-new",
            observed_at=LATER,
        )
        committed = promote(store, validated)
        if committed["committed_folders"] != 1:
            pytest.fail("Different-version Full capture blocked provider cursor")
        if (
            OutlookDeltaCheckpointStore(catalog, SOURCE).get_delta_link("inbox")
            != "cursor-overlap"
        ):
            pytest.fail("Winning provider checkpoint was not promoted")
        current = store.get_message_state(message_id=old["id"])
        if current is None or current["latest_observed_at"] != LATER:
            pytest.fail("Earlier reconciliation replaced independent new message")
        entries = AcquisitionHandoffStore(catalog).list_release_entries(
            SOURCE, AcquisitionStream.OUTLOOK_MAIL
        )
        if any(
            member.resource_kind == "message_surface"
            and member.resource_identity == old["id"]
            for entry in entries
            for member in AcquisitionHandoffStore(catalog).load_release_facts(
                entry["release_entry_seq"]
            )
        ):
            pytest.fail("Obsolete component was released against a newer parent")
    finally:
        catalog.close()


@pytest.mark.parametrize(
    ("accepted_version", "component_expected"),
    [("v1", True), ("v2", False)],
)
def test_terminal_component_without_locator_cannot_bridge_new_full_version(
    mail_catalog, accepted_version, component_expected
):
    """A terminal status has no evidence locator, but still pins its parent."""
    from message_ingest.acquisition.handoff import AcquisitionStream
    from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
    from message_ingest.sync.microsoft.outlook.email.checkpoints import (
        OutlookDeltaCheckpointStore,
    )
    from tests._mail_provisional import LATER

    old = {**RAW, "parentFolderId": "inbox"}
    new = {**old, "changeKey": accepted_version, "subject": "accepted-Full"}
    save_evidence(mail_catalog, "old-reconcile", {"value": [old]})
    save_evidence(mail_catalog, "accepted-full", new)
    catalog = Catalog(f"sqlite:///{mail_catalog['database']}")
    store = OutlookMailStore(catalog, source_id=SOURCE)
    try:
        validated = prepare(store, "terminal-overlap", when=WHEN)
        original = store.record_message(
            run_id="terminal-overlap",
            message=old,
            kind="reconcile",
            evidence_id="old-reconcile",
            observed_at=WHEN,
        )
        store.set_surface(
            run_id="terminal-overlap",
            message_id=old["id"],
            surface="mime",
            status="unsupported",
            evidence_id=None,
            observed_at=WHEN,
            profile_version="full-v1",
            resource_version=original.fact.source_state_key,
            observation_kind="reconcile",
        )
        store.record_message(
            run_id="later-full",
            message=new,
            kind="detail",
            evidence_id="accepted-full",
            observed_at=LATER,
        )
        outcome = promote(store, validated)
        if outcome["committed_folders"] != 1:
            pytest.fail("Terminal component overlap blocked legitimate cursor CAS")
        if (
            OutlookDeltaCheckpointStore(catalog, SOURCE).get_delta_link("inbox")
            != "cursor-terminal-overlap"
        ):
            pytest.fail("Terminal component overlap lost the winning cursor")
        ledger = AcquisitionHandoffStore(catalog)
        entries = ledger.list_release_entries(SOURCE, AcquisitionStream.OUTLOOK_MAIL)
        components = [
            member
            for entry in entries
            for member in ledger.load_release_facts(entry["release_entry_seq"])
            if member.resource_identity == old["id"] and member.component_kind == "mime"
        ]
        if bool(components) is not component_expected:
            pytest.fail("An obsolete or valid terminal component was mispublished")
    finally:
        catalog.close()


def test_preledger_equivalent_primary_cannot_block_valid_cursor(mail_catalog):
    """A pre-ledger historical message may have no accepted effective pointer."""
    from message_ingest.acquisition.handoff import AcquisitionStream
    from message_ingest.catalog.models.microsoft.outlook.email import MessageRecord
    from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
    from message_ingest.sync.microsoft.outlook.email.checkpoints import (
        OutlookDeltaCheckpointStore,
    )
    from tests._mail_provisional import LATER

    raw = {**RAW, "parentFolderId": "inbox"}
    save_evidence(mail_catalog, "historic-primary", {"value": [raw]})
    save_evidence(mail_catalog, "reconcile-retry", {"value": [raw]})
    catalog = Catalog(f"sqlite:///{mail_catalog['database']}")
    store = OutlookMailStore(catalog, source_id=SOURCE)
    try:
        with catalog.writer_session() as session:
            session.add(
                MessageRecord(
                    source_id=SOURCE,
                    message_id=raw["id"],
                    subject=raw["subject"],
                    latest_evidence_id="historic-primary",
                    latest_observed_at=WHEN,
                    is_removed=False,
                )
            )
        validated = prepare(store, "preledger-reconcile", when=WHEN)
        equivalent = store.record_message(
            run_id="preledger-reconcile",
            kind="reconcile",
            message=raw,
            evidence_id="reconcile-retry",
            observed_at=LATER,
        )
        store.set_surface(
            run_id="preledger-reconcile",
            message_id=raw["id"],
            surface="discovery",
            status="acquired",
            evidence_id="reconcile-retry",
            observed_at=LATER,
            resource_version=equivalent.fact.source_state_key,
            observation_kind="reconcile",
        )
        with catalog.Session() as session:
            if (
                AcquisitionHandoffStore(catalog).current_effective_state(
                    session, equivalent.fact.effective_key
                )
                is not None
            ):
                pytest.fail("Fixture unexpectedly acquired a post-ledger primary")
        promote(store, validated)
        if (
            OutlookDeltaCheckpointStore(catalog, SOURCE).get_delta_link("inbox")
            != "cursor-preledger-reconcile"
        ):
            pytest.fail("Equivalent pre-ledger message blocked valid provider cursor")
        released = AcquisitionHandoffStore(catalog).list_release_entries(
            SOURCE, AcquisitionStream.OUTLOOK_MAIL
        )
        if any(
            fact.resource_identity == raw["id"]
            for entry in released
            for fact in AcquisitionHandoffStore(catalog).load_release_facts(
                entry["release_entry_seq"]
            )
        ):
            pytest.fail("Unreleased historical primary produced fabricated new work")
    finally:
        catalog.close()
