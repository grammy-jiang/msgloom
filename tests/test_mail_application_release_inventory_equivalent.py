"""An equivalent selected Mail inventory must retain its new exact page chain."""

import asyncio

import pytest

from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from message_ingest.items.microsoft.outlook.email import OutlookMailInventoryPageItem
from tests._mail_provisional import WHEN, prepare, promote
from tests.source_reader.conftest import _evidence
from tests.source_reader.release_mail_helpers import RAW
from tests.source_reader.release_mail_helpers import (
    mail_catalog as mail_catalog,  # noqa: PLC0414 - fixture registration
)
from tests.source_reader.release_nonmail_helpers import (
    SOURCE,
    reader_api,
    save_evidence,
)
from tests.test_mail_inventory_bindings import PROFILE


def test_equivalent_inventory_alias_uses_current_selected_page_not_old_page(
    mail_catalog,
):
    """Semantic-empty inventories can have different canonical HTTP bytes."""
    raw_a = {**RAW, "parentFolderId": "inbox", "changeKey": "v1"}
    raw_b = {**raw_a, "changeKey": "v2"}
    for evidence_id, raw in (
        ("primary-a-one", raw_a),
        ("primary-b", raw_b),
        ("primary-a-two", raw_a),
    ):
        save_evidence(mail_catalog, evidence_id, raw)
    catalog = Catalog(f"sqlite:///{mail_catalog['database']}")
    store = OutlookMailStore(catalog, source_id=SOURCE)
    run = "inventory-aba"
    try:
        validated = prepare(store, run, when=WHEN)
        first = store.record_message(
            run_id=run,
            message=raw_a,
            kind="discovery",
            evidence_id="primary-a-one",
            observed_at=WHEN,
            selection_id="a-one",
        ).fact

        def inventory(selection, parent, primary_evidence, page_id, payload, when):
            with catalog.writer_session() as session:
                capture = _evidence(
                    session,
                    mail_catalog["evidence_root"],
                    page_id,
                    payload,
                    purpose="attachments-list",
                    observed_at=when,
                )
                capture.request_url = (
                    f"https://graph.example.invalid/messages/{raw_a['id']}/attachments"
                )
            item = OutlookMailInventoryPageItem(
                message_id=raw_a["id"],
                selection_id=selection,
                resource_version=parent.source_state_key,
                parent_evidence_id=primary_evidence,
                inventory_id=page_id,
                page_id=page_id,
                previous_page_id=None,
                page_number=1,
                member_capture_ids=(),
                status="acquired",
                profile_version=PROFILE,
                evidence_id=page_id,
                observed_at=when,
                run_id=run,
            )
            result = store.record_inventory_page(item)
            if result is None or result.fact is None:
                pytest.fail("Inventory fixture did not create an applied component")
            return result.fact

        original = inventory(
            "a-one",
            first,
            "primary-a-one",
            "inventory-old",
            {"value": [], "@odata.context": "https://example.invalid/old"},
            WHEN,
        )
        store.record_message(
            run_id=run,
            message=raw_b,
            kind="discovery",
            evidence_id="primary-b",
            observed_at="2026-10-02T00:00:00+00:00",
            selection_id="middle",
        )
        latest = store.record_message(
            run_id=run,
            message=raw_a,
            kind="discovery",
            evidence_id="primary-a-two",
            observed_at="2026-10-03T00:00:00+00:00",
            selection_id="a-two",
        ).fact
        new = inventory(
            "a-two",
            latest,
            "primary-a-two",
            "inventory-new",
            {"@odata.context": "https://example.invalid/new", "value": []},
            "2026-10-03T00:00:00+00:00",
        )
        if (
            new.storage_relation != "current_equivalent"
            or new.revalidated_fact_id != original.fact_id
        ):
            pytest.fail("ABA inventory did not revalidate an exact semantic manifest")
        promoted = promote(store, validated)
        if promoted["committed_folders"] != 1:
            pytest.fail("Valid ABA inventory did not promote its provider cursor")
    finally:
        catalog.close()

    async def inspect():
        reader = reader_api(mail_catalog)
        try:
            cutoff = await reader.catalog.max_release_entry_seq(SOURCE, "outlook_mail")
            page = await reader.catalog.list_release_entries(
                SOURCE, "outlook_mail", after_seq=0, through_seq=cutoff, limit=20
            )
            matches = [
                entry
                for entry in page.entries
                if entry.resource_kind == "message"
                and entry.resource_identity == raw_a["id"]
            ]
            if len(matches) != 1:
                pytest.fail("ABA inventory lost its single selected message impact")
            result = await reader.read_entry(matches[0].reference)
            components = [
                fact
                for fact in result.facts
                if fact.component_kind == "attachments" and fact.role == "component"
            ]
            if len(components) != 1 or result.selection is None:
                pytest.fail("Equivalent inventory lost its exact selected application")
        finally:
            await reader.close()

    asyncio.run(inspect())
