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
