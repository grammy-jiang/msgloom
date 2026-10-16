"""Terminal Mail inventories must not release partial page members."""

import asyncio

import pytest

from message_ingest.acquisition.handoff import AcquisitionStream
from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from tests._mail_provisional import prepare, promote
from tests.source_reader.release_mail_helpers import RAW, selected_inventory
from tests.source_reader.release_mail_helpers import (
    mail_catalog as mail_catalog,  # noqa: PLC0414
)
from tests.source_reader.release_nonmail_helpers import SOURCE, reader_api


@pytest.mark.parametrize(
    "terminal_status", ["acquired", "unavailable", "unauthorized", "omitted_size_limit"]
)
def test_terminal_inventory_does_not_publish_partial_metadata(
    mail_catalog, terminal_status
):
    """Only a fully acquired inventory can publish selected metadata members."""
    selected_inventory(mail_catalog, terminal_status=terminal_status)
    catalog = Catalog(f"sqlite:///{mail_catalog['database']}")
    store = OutlookMailStore(catalog, source_id=SOURCE)
    try:
        run = prepare(store, "mail-old")
        result = promote(store, run)
        if result["committed_folders"] != 1:
            pytest.fail("Valid provider cursor was not committed")
        ledger = AcquisitionHandoffStore(catalog)
        entries = ledger.list_release_entries(SOURCE, AcquisitionStream.OUTLOOK_MAIL)
        members = [
            item
            for entry in entries
            for item in ledger.load_release_facts(entry["release_entry_seq"])
            if item.parent_resource_identity == RAW["id"]
        ]
        metadata = [f for f in members if f.component_kind == "attachment_metadata"]
        if len(metadata) != (2 if terminal_status == "acquired" else 0):
            pytest.fail("Inventory published incomplete or lost acquired metadata")
    finally:
        catalog.close()

    async def verify():
        reader = reader_api(mail_catalog)
        try:
            cutoff = await reader.catalog.max_release_entry_seq(SOURCE, "outlook_mail")
            page = await reader.catalog.list_release_entries(
                SOURCE, "outlook_mail", after_seq=0, through_seq=cutoff, limit=40
            )
            for entry in page.entries:
                if (
                    entry.resource_kind == "message"
                    and entry.resource_identity == RAW["id"]
                ):
                    await reader.read_entry(entry.reference)
        finally:
            await reader.close()

    asyncio.run(verify())
