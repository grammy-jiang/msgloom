"""Exact pending Mail state survives competing writes and saved-source reads."""

import json

import pytest
from sqlalchemy import select

from message_ingest.acquisition.handoff import AcquisitionStream
from message_ingest.catalog import Catalog
from message_ingest.catalog.models.microsoft.outlook.email import MessageRecord
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from tests._mail_provisional import LATER, WHEN, capture, prepare, promote
from tests.source_reader.authority_release_helpers import read_entries
from tests.source_reader.release_mail_helpers import (
    mail_catalog as mail_catalog,  # noqa: PLC0414 - fixture registration
)
from tests.source_reader.release_nonmail_helpers import SOURCE, save_evidence


def current(store):
    with store.catalog.Session() as session:
        row = session.scalar(
            select(MessageRecord).filter_by(source_id=store.source_id, message_id="m")
        )
        return (
            None
            if row is None
            else (
                row.subject,
                row.is_read,
                row.has_attachments,
                row.internet_message_id,
                row.latest_evidence_id,
            )
        )


def test_older_inventory_capture_keeps_its_original_run_sighting(tmp_path):
    """Independent newer metadata cannot erase another run's inventory."""
    from message_ingest.catalog.models.microsoft.outlook.email import MailFolderRecord

    catalog = Catalog(f"sqlite:///{tmp_path / 'mail.db'}")
    store = OutlookMailStore(catalog, source_id=SOURCE)
    try:
        store.upsert_folder(
            folder={"id": "inbox", "displayName": "newer"},
            run_id="other",
            evidence_id=None,
            observed_at=LATER,
        )
        validated = prepare(store, "winner", when=WHEN)
        capture(store, "winner", {"id": "m", "changeKey": "v2"})
        promote(store, validated)
        with catalog.Session() as session:
            folder = session.scalar(
                select(MailFolderRecord).filter_by(source_id=SOURCE, folder_id="inbox")
            )
            if folder is None or folder.display_name != "newer":
                pytest.fail("Older run changed independent accepted metadata")
    finally:
        catalog.close()


def test_membership_removal_does_not_replace_run_local_primary(tmp_path):
    """A removal and a primary have separate effective keys in one scope."""
    catalog = Catalog(f"sqlite:///{tmp_path / 'mail.db'}")
    store = OutlookMailStore(catalog, source_id=SOURCE)
    try:
        validated = prepare(store, "winner")
        capture(store, "winner", {"id": "m", "subject": "kept", "changeKey": "v1"})
        removal = {
            "run_id": "winner",
            "message_id": "m",
            "folder_id": "inbox",
            "removed_reason": "changed",
            "evidence_id": None,
            "observed_at": WHEN,
        }
        store.record_folder_removal(**removal)
        store.record_folder_removal(**removal)
        capture(store, "winner", {"id": "m", "changeKey": "v2"})
        promote(store, validated)
        store.record_folder_removal(**removal)
        state = current(store)
        if state is None or state[0] != "kept":
            pytest.fail("Membership removal replaced the primary projection")
    finally:
        catalog.close()


def test_pinned_partial_projection_preserves_null_and_false(tmp_path):
    catalog = Catalog(f"sqlite:///{tmp_path / 'mail.db'}")
    store = OutlookMailStore(catalog, source_id=SOURCE)
    try:
        store.record_message(
            run_id="seed",
            kind="discovery",
            observed_at=WHEN,
            evidence_id=None,
            message={
                "id": "m",
                "subject": "accepted",
                "internetMessageId": "original",
                "isRead": True,
                "hasAttachments": True,
                "changeKey": "seed",
            },
        )
        decision = prepare(store, "winner")
        winner = capture(
            store,
            "winner",
            {
                "id": "m",
                "changeKey": "winner",
                "subject": None,
                "isRead": False,
                "hasAttachments": False,
            },
        )
        capture(
            store,
            "loser",
            {
                "id": "m",
                "changeKey": "loser",
                "internetMessageId": "wrong",
                "subject": "wrong",
            },
            when=LATER,
        )
        if current(store) != ("accepted", True, True, "original", None):
            pytest.fail("Pending input changed an accepted projection")
        promote(store, decision)
        if current(store) != (None, False, False, "original", None):
            pytest.fail("Projection lost null/false or inherited speculative fields")
        ledger = AcquisitionHandoffStore(catalog)
        with catalog.Session() as session:
            effective = ledger.current_effective_state(
                session, winner.fact.effective_key
            )
        if effective is None or effective["fact_id"] != winner.fact.fact_id:
            pytest.fail("Exact winning primary was not effective")
    finally:
        catalog.close()


def test_real_reader_uses_winning_original_page_after_late_loser(mail_catalog):
    saved = mail_catalog
    message = {
        "id": "m",
        "changeKey": "v2",
        "subject": "winner",
        "body": {"contentType": "text", "content": "winning body"},
    }
    page = {"value": [{"id": "unrelated", "subject": "not selected"}, message]}
    save_evidence(saved, "winner-page", page)
    losing = {**message, "changeKey": "v1", "subject": "loser"}
    save_evidence(saved, "loser-page", {"value": [losing]})
    catalog = Catalog(f"sqlite:///{saved['database']}")
    store = OutlookMailStore(catalog, source_id=SOURCE)
    try:
        decision = prepare(store, "winner")
        accepted = capture(store, "winner", message, evidence="winner-page")
        capture(store, "loser", losing, evidence="loser-page", when=LATER)
        promote(store, decision)
        capture(
            store,
            "loser",
            losing,
            evidence="loser-page",
            when="2026-10-03T00:00:00+00:00",
        )
        ledger = AcquisitionHandoffStore(catalog)
        rows = [
            row
            for row in ledger.list_release_entries(
                SOURCE, AcquisitionStream.OUTLOOK_MAIL, limit=100
            )
            if json.loads(row["payload"])["entry_kind"] == "resource"
        ]
        facts = [
            fact
            for row in rows
            for fact in ledger.load_release_facts(row["release_entry_seq"])
        ]
        if len(facts) != 1 or facts[0].fact_id != accepted.fact.fact_id:
            pytest.fail("Release substituted a competing primary capture")
        locator = facts[0].source_version_locator
        if (
            locator is None
            or locator.evidence_id != "winner-page"
            or locator.resource_version != "v2"
            or facts[0].run_id != "winner"
        ):
            pytest.fail("Original capture provenance changed")
        reads = read_entries(saved, rows)
        result = reads[0][1]
        if result.selection is None or reads[0][2] != (
            json.dumps(page, separators=(",", ":")).encode(),
        ):
            pytest.fail("Real reader did not reconstruct the exact winning evidence")
        state = current(store)
        if state is None or state[0] != "winner":
            pytest.fail("Late losing evidence changed current primary")
    finally:
        catalog.close()


@pytest.mark.parametrize(
    "problem", ["missing", "source", "corrupt", "resource", "version"]
)
def test_pending_primary_rejects_unverifiable_evidence(mail_catalog, problem):
    saved = mail_catalog
    message = {"id": "m", "changeKey": "v2", "subject": "winner"}
    save_evidence(saved, "page", {"value": [message]})
    catalog = Catalog(f"sqlite:///{saved['database']}")
    store = OutlookMailStore(catalog, source_id=SOURCE)
    try:
        evidence = "page"
        if problem == "missing":
            evidence = "missing"
        elif problem == "source":
            store = OutlookMailStore(catalog, source_id="wrong-source")
        elif problem == "corrupt":
            from pathlib import Path

            from message_ingest.catalog.models.acquisition import RawHttpEvidence

            with catalog.Session() as session:
                row = session.get(RawHttpEvidence, evidence)
                if row is None:
                    pytest.fail("Fixture evidence is missing")
                Path(row.response_body_path).write_bytes(b"corrupt")
        else:
            message = {
                **message,
                "id" if problem == "resource" else "changeKey": "wrong",
            }
        with pytest.raises(ValueError):
            capture(store, "winner", message, evidence=evidence)
        if current(store) is not None:
            pytest.fail("Rejected evidence changed mutable state")
    finally:
        catalog.close()
