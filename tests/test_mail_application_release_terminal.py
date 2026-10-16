"""Equivalent Mail terminal outcomes must not depend on error-body identity."""

import asyncio

import pytest

from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
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


def test_selected_equivalent_terminal_errors_keep_new_application(mail_catalog):
    """Two 503-like bodies can represent one terminal limitation, not one capture."""
    a = {**RAW, "changeKey": "v1", "parentFolderId": "inbox"}
    b = {**a, "changeKey": "v2"}
    for evidence, payload in (
        ("first-primary", a),
        ("middle-primary", b),
        ("last-primary", a),
        ("first-error", b'{"error":{"code":"unavailable","message":"first"}}'),
        ("last-error", b'{"error":{"code":"unavailable","message":"second"}}'),
    ):
        save_evidence(mail_catalog, evidence, payload)
    catalog = Catalog(f"sqlite:///{mail_catalog['database']}")
    store = OutlookMailStore(catalog, source_id=SOURCE)
    try:
        validated = prepare(store, "terminal-alias", when=WHEN)
        first = store.record_message(
            run_id="terminal-alias",
            kind="discovery",
            message=a,
            evidence_id="first-primary",
            observed_at=WHEN,
            selection_id="first",
        ).fact
        original = store.set_surface(
            run_id="terminal-alias",
            message_id=a["id"],
            surface="mime",
            status="unavailable",
            evidence_id="first-error",
            observed_at=WHEN,
            resource_version=first.source_state_key,
            selection_id="first",
            parent_evidence_id="first-primary",
            profile_version="full-v1",
        )
        if original.fact is None:
            pytest.fail("First selected terminal surface missing")
        store.record_message(
            run_id="terminal-alias",
            kind="discovery",
            message=b,
            evidence_id="middle-primary",
            observed_at=LATER,
            selection_id="middle",
        )
        latest = store.record_message(
            run_id="terminal-alias",
            kind="discovery",
            message=a,
            evidence_id="last-primary",
            observed_at="2026-10-03T00:00:00+00:00",
            selection_id="last",
        ).fact
        current = store.set_surface(
            run_id="terminal-alias",
            message_id=a["id"],
            surface="mime",
            status="unavailable",
            evidence_id="last-error",
            observed_at="2026-10-03T00:00:00+00:00",
            resource_version=latest.source_state_key,
            selection_id="last",
            parent_evidence_id="last-primary",
            profile_version="full-v1",
        )
        if (
            current.fact is None
            or current.fact.storage_relation != "current_equivalent"
            or current.fact.revalidated_fact_id != original.fact.fact_id
        ):
            pytest.fail(
                "Different terminal HTTP bytes were not semantically equivalent"
            )
        outcome = promote(store, validated)
        if outcome["committed_folders"] != 1:
            pytest.fail("Equivalent terminal surface vetoed the valid Delta cursor")
    finally:
        catalog.close()

    async def verify():
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
                and entry.resource_identity == a["id"]
            ]
            if len(matches) != 1:
                pytest.fail("Selected terminal capture lost its message impact")
            released = await reader.read_entry(matches[0].reference)
            components = [
                fact
                for fact in released.facts
                if fact.role == "component" and fact.component_kind == "mime"
            ]
            if len(components) != 1 or released.selection is None:
                pytest.fail("Valid equivalent terminal application was dropped")
        finally:
            await reader.close()

    asyncio.run(verify())
