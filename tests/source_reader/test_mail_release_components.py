"""Exact detail, inventory, metadata and raw Mail reconstruction."""

import pytest

from tests.source_reader.release_mail_helpers import mail_facts, read, release


def test_mail_components_reconstruct_only_named_inventory(mail_catalog):
    seq = release(mail_catalog, mail_facts(mail_catalog, full=True))
    result = read(mail_catalog, seq)
    if result.selection is None:
        pytest.fail("Mail primary missing")
    record = result.selection.record
    if record.subject != "Detail" or len(record.attachments) != 1:
        pytest.fail("Exact detail or inventory was not applied")
    attachment = record.attachments[0]
    if attachment.name != "old.txt" or attachment.saved_bytes is None:
        pytest.fail("Released attachment metadata/raw association lost")
    if attachment.saved_bytes.byte_count != 9:
        pytest.fail("Exact attachment bytes were not retained")


from tests.source_reader.release_mail_helpers import (
    mail_catalog as mail_catalog,  # noqa: PLC0414 - pytest fixture registration
)


@pytest.mark.parametrize("status", ["acquired", "unsupported"])
def test_selected_mail_capture_keeps_exact_primary_application(mail_catalog, status):
    facts = mail_facts(mail_catalog, status, bound=True)
    result = read(mail_catalog, release(mail_catalog, facts))
    if result.selection is None or len(result.components) != 1:
        pytest.fail("Exact selected Mail capture was not reconstructed")


def test_terminal_mail_detail_preserves_primary_fields(mail_catalog):
    from message_ingest.catalog import Catalog
    from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
    from tests.source_reader.release_nonmail_helpers import SOURCE, WHEN

    facts = mail_facts(mail_catalog)
    catalog = Catalog(f"sqlite:///{mail_catalog['database']}")
    try:
        detail = (
            OutlookMailStore(catalog, source_id=SOURCE)
            .set_surface(
                run_id="mail-old",
                message_id="released-mail",
                surface="detail",
                status="unsupported",
                evidence_id=None,
                observed_at=WHEN,
                profile_version="full-v1",
                resource_version=facts[0].source_state_key,
            )
            .fact
        )
    finally:
        catalog.close()
    result = read(mail_catalog, release(mail_catalog, [*facts, detail]))
    if result.selection.record.subject != "Original":
        pytest.fail("Terminal detail erased the released primary subject")


@pytest.mark.parametrize("component_kind", ["attachment_metadata", "attachment_raw:a1"])
def test_mail_attachment_from_another_primary_version_is_rejected(
    mail_catalog,
    component_kind,
):
    """Matching attachment IDs cannot bridge distinct parent versions."""
    from dataclasses import replace

    from msgloom.sources import SourceReferenceError

    facts = mail_facts(mail_catalog, full=True)
    mixed = []
    for fact in facts:
        if fact.component_kind == component_kind:
            fact = replace(
                fact,
                source_state_key="c" * 64,
                source_version_locator=replace(
                    fact.source_version_locator,
                    resource_version="another-parent",
                ),
            )
        mixed.append(fact)
    seq = release(mail_catalog, mixed)
    with pytest.raises(SourceReferenceError, match="version mismatch"):
        read(mail_catalog, seq)


def test_selected_empty_inventory_needs_no_metadata_facts(mail_catalog):
    """An acquired empty inventory is complete without attachment facts."""
    from message_ingest.catalog import Catalog
    from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
    from message_ingest.items.microsoft.outlook.email import (
        OutlookMailInventoryPageItem,
    )
    from tests.source_reader.conftest import _evidence
    from tests.source_reader.release_mail_helpers import RAW
    from tests.source_reader.release_nonmail_helpers import SOURCE, WHEN

    facts = mail_facts(mail_catalog, bound=True)
    catalog = Catalog(f"sqlite:///{mail_catalog['database']}")
    try:
        with catalog.writer_session() as session:
            row = _evidence(
                session,
                mail_catalog["evidence_root"],
                "empty-inventory",
                {"value": []},
                purpose="attachments-list",
                observed_at=WHEN,
            )
            row.request_url = (
                "https://graph.example.invalid/messages/released-mail/attachments"
            )
        outcome = OutlookMailStore(catalog, source_id=SOURCE).record_inventory_page(
            OutlookMailInventoryPageItem(
                message_id=RAW["id"],
                selection_id="selection-old",
                resource_version=facts[0].source_state_key,
                parent_evidence_id="mail-primary",
                inventory_id="empty-inventory",
                page_id="empty-page",
                previous_page_id=None,
                page_number=1,
                member_capture_ids=(),
                status="acquired",
                profile_version="full-v1",
                evidence_id="empty-inventory",
                observed_at=WHEN,
                run_id="mail-old",
            )
        )
    finally:
        catalog.close()
    if outcome is None or outcome.fact is None:
        pytest.fail("Empty selected inventory did not produce its terminal fact")
    inventory = outcome.fact
    result = read(mail_catalog, release(mail_catalog, [*facts, inventory]))
    if result.selection is None or result.selection.record.attachments:
        pytest.fail("Empty inventory reconstruction lost primary or added attachments")
    if result.selection.record.limitations:
        pytest.fail("Acquired empty inventory was treated as incomplete")
    if len(result.components) != 2:
        pytest.fail("Empty inventory or retained MIME component was omitted")
