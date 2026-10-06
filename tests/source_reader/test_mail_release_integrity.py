"""Malformed or cross-parent Mail releases fail closed."""

from dataclasses import replace

import pytest

from msgloom.sources import SourceReferenceError
from tests.source_reader.release_mail_helpers import mail_facts, read, release


@pytest.mark.parametrize(
    "reason",
    [
        None,
        "{}",
        "x" * 257,
        '{"status":"invented","profile_version":null}',
        '{"status":"unsupported", "profile_version":null}',
    ],
)
def test_mail_rejects_noncanonical_outcome(mail_catalog, reason):
    primary, component = mail_facts(mail_catalog, "unsupported")
    component = replace(component, transition_reason=reason, source_state_key="a" * 64)
    component = replace(component, source_state_key="a" * 64)
    with pytest.raises(SourceReferenceError):
        read(mail_catalog, release(mail_catalog, [primary, component]))


@pytest.mark.parametrize("corruption", ["version", "evidence", "identity"])
def test_mail_rejects_mixed_component_ownership(mail_catalog, corruption):
    primary, component = mail_facts(mail_catalog)
    locator = component.source_version_locator
    if corruption == "version":
        component = replace(
            component,
            source_version_locator=replace(locator, resource_version="another-version"),
        )
    elif corruption == "evidence":
        component = replace(component, evidence_id="ev-mime")
    else:
        component = replace(
            component,
            source_version_locator=replace(locator, resource_identity="another"),
        )
    component = replace(component, source_state_key="a" * 64)
    with pytest.raises(SourceReferenceError):
        read(mail_catalog, release(mail_catalog, [primary, component]))


from tests.source_reader.release_mail_helpers import (
    mail_catalog as mail_catalog,  # noqa: PLC0414 - pytest fixture registration
)


def test_mail_missing_acquired_evidence_fails_closed(mail_catalog):
    primary, component = mail_facts(mail_catalog)
    component = replace(
        component,
        evidence_id=None,
        source_version_locator=None,
        source_state_key="a" * 64,
    )
    with pytest.raises(SourceReferenceError):
        read(mail_catalog, release(mail_catalog, [primary, component]))


def test_mail_corrupt_mime_bytes_fail_digest_verification(mail_catalog):
    import hashlib

    from msgloom.sources import SourceEvidenceError
    from tests.source_reader.release_mail_helpers import MIME

    facts = mail_facts(mail_catalog)
    seq = release(mail_catalog, facts)
    path = mail_catalog["evidence_root"] / (hashlib.sha256(MIME).hexdigest() + ".bin")
    path.write_bytes(b"corrupt")
    with pytest.raises(SourceEvidenceError):
        read(mail_catalog, seq)


def test_mail_attachment_without_inventory_fails_closed(mail_catalog):
    facts = mail_facts(mail_catalog, full=True)
    facts = [fact for fact in facts if fact.component_kind != "attachments"]
    with pytest.raises(SourceReferenceError, match="inventory"):
        read(mail_catalog, release(mail_catalog, facts))


def test_saved_catalog_initializes_production_immutable_guards(saved_catalog):
    """Seeded reader fixtures remain valid for the production writer."""
    from message_ingest.catalog import Catalog

    catalog = Catalog(f"sqlite:///{saved_catalog['database']}")
    catalog.close()


@pytest.mark.parametrize("missing", [("a1",), ("a1", "a2")])
def test_selected_inventory_requires_every_metadata_fact(mail_catalog, missing):
    """Omitting all members must fail just like omitting one member."""
    from tests.source_reader.release_mail_helpers import selected_inventory

    facts = selected_inventory(mail_catalog)
    facts = [
        fact
        for fact in facts
        if not (
            fact.component_kind == "attachment_metadata"
            and fact.resource_identity in missing
        )
    ]
    with pytest.raises(SourceReferenceError, match="inventory membership"):
        read(mail_catalog, release(mail_catalog, facts))


@pytest.mark.parametrize("kind", ["discovery", "delta"])
@pytest.mark.parametrize("has_change_key", [True, False])
@pytest.mark.parametrize("tampered", [False, True])
def test_primary_only_mail_validates_exact_state(
    mail_catalog, kind, has_change_key, tampered
):
    """Component absence cannot bypass provider or fallback primary state."""
    from message_ingest.catalog import Catalog
    from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
    from tests.source_reader.release_mail_helpers import RAW
    from tests.source_reader.release_nonmail_helpers import SOURCE, WHEN, save_evidence

    raw = dict(RAW)
    if not has_change_key:
        raw.pop("changeKey")
    save_evidence(mail_catalog, "primary-only", {"value": [raw]})
    catalog = Catalog(f"sqlite:///{mail_catalog['database']}")
    try:
        primary = (
            OutlookMailStore(catalog, source_id=SOURCE)
            .record_message(
                run_id="primary-only",
                message=raw,
                kind=kind,
                evidence_id="primary-only",
                observed_at=WHEN,
            )
            .fact
        )
    finally:
        catalog.close()
    if tampered:
        primary = replace(primary, source_state_key="f" * 64)
        with pytest.raises(SourceReferenceError, match="primary state mismatch"):
            read(mail_catalog, release(mail_catalog, [primary]))
        return
    result = read(mail_catalog, release(mail_catalog, [primary]))
    if result.selection is None or result.selection.record.subject != "Original":
        pytest.fail("Valid primary-only Mail did not preserve its saved fields")
    if result.components:
        pytest.fail("Primary-only Mail gained unrelated components")
