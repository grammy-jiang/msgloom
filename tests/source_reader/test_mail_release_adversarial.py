"""Mail release boundaries reject foreign evidence and mutable lookup."""

import sqlite3
from dataclasses import replace

import pytest

from message_ingest.catalog import Catalog
from message_ingest.catalog.models.acquisition import SourceBinding
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from msgloom.sources import SourceEvidenceError, SourceReferenceError
from msgloom.sources._catalog import ReadOnlyCatalog
from msgloom.sources.models import SourceEvidenceLimitError
from msgloom.sources.reader import SavedSourceReader
from tests.source_reader.conftest import _evidence
from tests.source_reader.release_mail_helpers import (
    MIME,
    RAW,
    mail_facts,
    read,
    release,
    selected_inventory,
)
from tests.source_reader.release_mail_helpers import (
    mail_catalog as mail_catalog,  # noqa: PLC0414 - pytest fixture registration
)
from tests.source_reader.release_nonmail_helpers import SOURCE, WHEN, save_evidence


def test_mail_evidence_from_another_source_fails_closed(mail_catalog):
    primary, component = mail_facts(mail_catalog)
    catalog = Catalog(f"sqlite:///{mail_catalog['database']}")
    try:
        with catalog.writer_session() as session:
            session.add(
                SourceBinding(
                    source_id="foreign",
                    provider="microsoft",
                    key_scheme="synthetic",
                    account_key_sha256="b" * 64,
                    binding_method="test",
                    bound_at=WHEN,
                )
            )
            row = _evidence(
                session,
                mail_catalog["evidence_root"],
                "foreign-mime",
                MIME,
                purpose="message-mime",
                observed_at=WHEN,
            )
            row.source_id = "foreign"
    finally:
        catalog.close()
    component = replace(
        component,
        evidence_id="foreign-mime",
        source_state_key="a" * 64,
        source_version_locator=replace(
            component.source_version_locator,
            evidence_id="foreign-mime",
        ),
    )
    seq = release(mail_catalog, [primary, component])
    with pytest.raises(SourceEvidenceError, match="another source"):
        read(mail_catalog, seq)


def test_mail_forged_observation_id_fails_closed(mail_catalog):
    primary, _ = mail_facts(mail_catalog)
    primary = replace(
        primary,
        source_state_key="b" * 64,
        source_version_locator=replace(
            primary.source_version_locator,
            kind="observation",
            observation_id="forged-observation",
        ),
    )
    seq = release(mail_catalog, [primary])
    with pytest.raises(SourceReferenceError, match="association"):
        read(mail_catalog, seq)


def test_mail_scheduled_read_avoids_version_lists_and_current_rows(
    mail_catalog,
    monkeypatch,
):
    seq = release(mail_catalog, selected_inventory(mail_catalog))
    original = ReadOnlyCatalog._connect
    forbidden = {
        "messages",
        "message_surfaces",
        "attachments",
        "message_presence",
        "mail_folder_presence",
        "acquisition_effective_states",
    }
    attempted = []

    def authorize(action, table, _column, _database, _trigger):
        if action == sqlite3.SQLITE_READ and table in forbidden:
            attempted.append(table)
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    def connect(self):
        connection = original(self)
        connection.set_authorizer(authorize)
        return connection

    def no_versions(*_args, **_kwargs):
        pytest.fail("Scheduled Mail read called list_versions")

    monkeypatch.setattr(ReadOnlyCatalog, "_connect", connect)
    monkeypatch.setattr(ReadOnlyCatalog, "list_versions", no_versions)
    monkeypatch.setattr(SavedSourceReader, "list_versions", no_versions)
    result = read(mail_catalog, seq)
    if attempted or len(result.selection.record.attachments) != 2:
        pytest.fail("Scheduled reconstruction used current projection rows")


def test_mail_snapshot_metadata_budget_fails_closed(mail_catalog):
    seq = release(mail_catalog, mail_facts(mail_catalog, full=True))
    with pytest.raises(SourceReferenceError, match="metadata.*byte bound"):
        read(mail_catalog, seq, max_snapshot_bytes=1)


def test_mail_snapshot_evidence_budget_fails_closed(mail_catalog):
    primary, _ = mail_facts(mail_catalog)
    save_evidence(mail_catalog, "large-mime", b"Subject: Large\r\n\r\n" + b"x" * 16384)
    catalog = Catalog(f"sqlite:///{mail_catalog['database']}")
    try:
        component = (
            OutlookMailStore(catalog, source_id=SOURCE)
            .set_surface(
                run_id="large",
                message_id=RAW["id"],
                surface="mime",
                status="acquired",
                evidence_id="large-mime",
                observed_at=WHEN,
                profile_version="full-v1",
                resource_version=primary.source_state_key,
            )
            .fact
        )
    finally:
        catalog.close()
    seq = release(mail_catalog, [primary, component])
    with pytest.raises(SourceEvidenceLimitError, match="byte budget"):
        read(mail_catalog, seq, max_snapshot_bytes=8192)


def test_mail_snapshot_serialized_budget_fails_closed(mail_catalog):
    seq = release(mail_catalog, mail_facts(mail_catalog, full=True))
    with pytest.raises(SourceReferenceError, match="snapshot|selections"):
        read(mail_catalog, seq, max_snapshot_bytes=8192)


def test_selected_mail_aba_and_current_equivalent_primary_remain_exact(mail_catalog):
    first = mail_facts(mail_catalog, bound=True)
    releases = [(release(mail_catalog, first), MIME)]
    primaries = [first[0]]
    relations = []
    for number, version in enumerate(("v2", "v1", "v1"), 1):
        raw = {**RAW, "changeKey": version}
        eid = f"primary-{number}"
        mime_id = f"mime-{number}"
        mime = f"Subject: Application {number}\r\n\r\nBody {number}".encode()
        save_evidence(mail_catalog, eid, raw)
        save_evidence(mail_catalog, mime_id, mime)
        catalog = Catalog(f"sqlite:///{mail_catalog['database']}")
        try:
            store = OutlookMailStore(catalog, source_id=SOURCE)
            when = f"2026-09-30T0{number}:00:00+00:00"
            outcome = store.record_message(
                run_id=eid,
                message=raw,
                kind="discovery",
                evidence_id=eid,
                observed_at=when,
                selection_id=eid,
            )
            primary = outcome.fact
            relations.append(str(outcome.storage_relation))
            component = store.set_surface(
                run_id=eid,
                message_id=RAW["id"],
                surface="mime",
                status="acquired",
                selection_id=eid,
                parent_evidence_id=eid,
                evidence_id=mime_id,
                observed_at=when,
                profile_version="full-v1",
                resource_version=primary.source_state_key,
            ).fact
        finally:
            catalog.close()
        primaries.append(primary)
        releases.append((release(mail_catalog, [primary, component]), mime))
    if primaries[0].source_state_key != primaries[2].source_state_key:
        pytest.fail("ABA fixture did not restore the original semantic state")
    if primaries[0].fact_id == primaries[2].fact_id:
        pytest.fail("ABA fixture did not retain distinct applications")
    if relations[-1] != "current_equivalent":
        pytest.fail("Fixture did not exercise a current-equivalent primary")
    for seq, expected in releases:
        result = read(mail_catalog, seq)
        saved = result.selection.record.alternate_bodies[0].saved_bytes
        import hashlib

        if saved.sha256 != hashlib.sha256(expected).hexdigest():
            pytest.fail("A different same-state primary replaced exact MIME bytes")
