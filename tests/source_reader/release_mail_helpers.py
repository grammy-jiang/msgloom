"""Released Mail fixtures from real atomic domain writers."""

import asyncio

import pytest

from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from tests.source_reader.release_nonmail_helpers import (
    SOURCE,
    WHEN,
    publish,
    reader_api,
    save_evidence,
)

LATER = "2026-09-30T00:00:00+00:00"
MIME = b"From: old@example.test\r\nSubject: Original\r\n\r\nOld MIME body"
RAW = {
    "id": "released-mail",
    "changeKey": "v1",
    "subject": "Original",
    "body": {"contentType": "text", "content": "Old body"},
    "sender": {"emailAddress": {"address": "sender@example.test"}},
    "from": {"emailAddress": {"address": "author@example.test"}},
    "toRecipients": [{"emailAddress": {"address": "to@example.test"}}],
}


def mail_facts(saved, status="acquired", *, evidence=True, full=False, bound=False):
    """Retain exact old facts before independently advancing current rows."""
    save_evidence(saved, "mail-primary", {"value": [RAW]})
    save_evidence(saved, "mail-mime", MIME)
    catalog = Catalog(f"sqlite:///{saved['database']}")
    store = OutlookMailStore(catalog, source_id=SOURCE)
    try:
        primary = store.record_message(
            run_id="mail-old",
            message=RAW,
            kind="discovery",
            selection_id="selection-old" if bound else None,
            evidence_id="mail-primary",
            observed_at=WHEN,
        ).fact
        component = store.set_surface(
            run_id="mail-old",
            message_id=RAW["id"],
            surface="mime",
            status=status,
            selection_id="selection-old" if bound else None,
            parent_evidence_id="mail-primary" if bound else None,
            evidence_id="mail-mime" if evidence else None,
            observed_at=WHEN,
            profile_version="full-v1",
            resource_version=primary.source_state_key,
        ).fact
        facts = [primary, component]
        if full:
            attachment = {
                "id": "a1",
                "name": "old.txt",
                "size": 9,
                "contentType": "text/plain",
                "isInline": False,
            }
            save_evidence(saved, "mail-detail", {**RAW, "subject": "Detail"})
            save_evidence(saved, "mail-inventory", {"value": [attachment]})
            save_evidence(saved, "mail-raw", b"old bytes")
            for surface, eid in (
                ("detail", "mail-detail"),
                ("attachments", "mail-inventory"),
                ("attachment_raw:a1", "mail-raw"),
            ):
                facts.append(
                    store.set_surface(
                        run_id="mail-old",
                        message_id=RAW["id"],
                        surface=surface,
                        status="acquired",
                        evidence_id=eid,
                        observed_at=WHEN,
                        profile_version="full-v1",
                        resource_version=primary.source_state_key,
                    ).fact
                )
            facts.append(
                store.upsert_attachment(
                    run_id="mail-old",
                    message_id=RAW["id"],
                    attachment=attachment,
                    evidence_id="mail-inventory",
                    observed_at=WHEN,
                    resource_version=primary.source_state_key,
                    profile_version="full-v1",
                ).fact
            )
        return facts
    finally:
        catalog.close()


def release(saved, facts):
    """Publish the provided exact facts, preserving component roles."""
    return publish(saved, facts, roles=("primary",) + ("component",) * (len(facts) - 1))


def read(saved, seq, **limits):
    """Resolve the public release API and close every read boundary."""

    async def run():
        reader = reader_api(saved, **limits)
        try:
            entry = await reader.catalog.get_release_entry(seq)
            if entry is None:
                pytest.fail("Mail release missing")
            return await reader.read_entry(entry.reference)
        finally:
            await reader.close()

    return asyncio.run(run())


@pytest.fixture
def mail_catalog(tmp_path):
    """Use the production schema initializer, including immutable guards."""
    from message_ingest.catalog.models.acquisition import SourceBinding

    database = tmp_path / "mail.sqlite3"
    root = tmp_path / "evidence"
    root.mkdir()
    catalog = Catalog(f"sqlite:///{database}")
    try:
        with catalog.writer_session() as session:
            session.add(
                SourceBinding(
                    source_id=SOURCE,
                    provider="microsoft",
                    key_scheme="synthetic",
                    account_key_sha256="a" * 64,
                    binding_method="test",
                    bound_at=WHEN,
                )
            )
    finally:
        catalog.close()
    return {"database": database, "evidence_root": root}


def selected_inventory(saved, *, terminal_status="acquired"):
    """Retain two native pages and metadata in one selected inventory."""
    from message_ingest.items.microsoft.outlook.email import (
        OutlookMailInventoryPageItem,
    )
    from tests.source_reader.conftest import _evidence

    facts = mail_facts(saved, bound=True)
    catalog = Catalog(f"sqlite:///{saved['database']}")
    store = OutlookMailStore(catalog, source_id=SOURCE)
    try:
        for number in (1, 2):
            identity = f"page-{number}"
            member = {"id": f"a{number}", "name": f"page-{number}.txt"}
            url = (
                "https://graph.example.invalid/messages/released-mail/"
                f"attachments?page={number}"
            )
            status = terminal_status if number == 2 else "acquired"
            payload: dict[str, object] | bytes
            if status == "acquired":
                payload = {"value": [member]}
                if number == 1:
                    payload["@odata.nextLink"] = url.replace("page=1", "page=2")
            else:
                payload = b"provider unavailable"
            with catalog.writer_session() as session:
                row = _evidence(
                    session,
                    saved["evidence_root"],
                    identity,
                    payload,
                    purpose="attachments-list",
                    observed_at=WHEN,
                )
                row.request_url = url
            if status == "acquired":
                metadata = store.upsert_attachment(
                    run_id="mail-old",
                    message_id=RAW["id"],
                    attachment=member,
                    evidence_id=identity,
                    observed_at=WHEN,
                    resource_version=facts[0].source_state_key,
                    selection_id="selection-old",
                    parent_evidence_id="mail-primary",
                    profile_version="full-v1",
                    capture_id=f"member-{number}",
                ).fact
                if metadata is None:
                    pytest.fail("Selected metadata did not produce a retained fact")
                facts.append(metadata)
            outcome = store.record_inventory_page(
                OutlookMailInventoryPageItem(
                    message_id=RAW["id"],
                    selection_id="selection-old",
                    resource_version=facts[0].source_state_key,
                    parent_evidence_id="mail-primary",
                    inventory_id="inventory",
                    page_id=identity,
                    previous_page_id="page-1" if number == 2 else None,
                    page_number=number,
                    member_capture_ids=(f"member-{number}",)
                    if status == "acquired"
                    else (),
                    status=status,
                    profile_version="full-v1",
                    evidence_id=identity,
                    observed_at=WHEN,
                    run_id="mail-old",
                )
            )
        if outcome is None or outcome.fact is None:
            pytest.fail("Terminal page did not produce a retained inventory")
        if terminal_status != "acquired":
            # Partial pages are provenance, not released attachment members.
            facts = facts[:2]
        facts.append(outcome.fact)
        return facts
    finally:
        catalog.close()
