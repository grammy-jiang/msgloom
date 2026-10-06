"""Qualify Contacts discovery release through the public Scrapy command."""

import json

import pytest
from handoff_release_reader_helpers import bind_fixture_source, read_published
from sqlalchemy import select

from message_ingest.acquisition.handoff import AcquisitionStream
from message_ingest.catalog import Catalog
from message_ingest.catalog.models.handoff import AcquisitionReleaseGroup
from message_ingest.catalog.models.microsoft.contacts import ContactsSnapshotState
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from tests.test_contacts_crawl import (
    FOLDER_CHILD,
    FOLDER_OTHER,
    FOLDER_PARENT,
)
from tests.test_contacts_crawl import _run as run_contacts
from tests.test_contacts_crawl import (
    contacts_server as contacts_server,  # noqa: PLC0414
)


def test_public_contacts_discover_releases_complete_additive_traversal(
    tmp_path, contacts_server
) -> None:
    """Publish exact positive facts once after the native idle boundary."""
    database = tmp_path / "catalog.sqlite3"
    bind_fixture_source(database, "contacts-fixture")
    origin, _state, requests = contacts_server

    result = run_contacts(
        tmp_path,
        origin,
        "microsoft",
        "contacts",
        "discover",
        "--page-size",
        "2",
    )
    if result.returncode or "ERROR" in result.stderr:
        pytest.fail(result.stderr)

    catalog = Catalog(f"sqlite:///{database}")
    try:
        handoff = AcquisitionHandoffStore(catalog)
        rows = handoff.list_release_entries(
            "contacts-fixture", AcquisitionStream.CONTACTS
        )
        with catalog.Session() as session:
            groups = [
                json.loads(payload)
                for payload in session.scalars(
                    select(AcquisitionReleaseGroup.payload)
                ).all()
            ]
            if session.get(ContactsSnapshotState, "contacts-fixture") is not None:
                pytest.fail("Additive discovery acquired snapshot authority")

        if len(groups) != 1:
            pytest.fail("Public Contacts discovery did not release one group")
        group = groups[0]
        expected_group = {
            "source_id": "contacts-fixture",
            "stream": "contacts",
            "release_kind": "resource_set",
            "subject_kind": "contacts_discovery",
            "subject_identity": "source",
            "coverage_kind": "complete",
            "authority_revision": None,
        }
        if any(group.get(key) != value for key, value in expected_group.items()):
            pytest.fail("Contacts discovery released incorrect group semantics")

        expected_entries = {
            ("context", "contact_folder", FOLDER_PARENT),
            ("context", "contact_folder", FOLDER_CHILD),
            ("context", "contact_folder", FOLDER_OTHER),
            ("resource", "contact", "default-one"),
            ("resource", "contact", "default-two"),
            ("resource", "contact", "parent-contact"),
            ("resource", "contact", "child-one"),
            ("resource", "contact", "child-two"),
        }
        payloads = [json.loads(row["payload"]) for row in rows]
        actual_entries = {
            (
                payload["entry_kind"],
                payload["resource_kind"],
                payload["resource_identity"],
            )
            for payload in payloads
        }
        if actual_entries != expected_entries:
            pytest.fail("Contacts discovery lost or changed positive impacts")
        if {row["release_group_id"] for row in rows} != {group["release_group_id"]}:
            pytest.fail("Contacts entries did not share one atomic group")

        for row, payload in zip(rows, payloads, strict=True):
            facts = handoff.load_release_facts(row["release_entry_seq"])
            if len(facts) != 1 or len(payload["facts"]) != 1:
                pytest.fail("Contacts impact did not retain its exact fact")
            fact = facts[0]
            if (
                fact.fact_id != payload["facts"][0][0]
                or fact.source_id != "contacts-fixture"
                or fact.stream != AcquisitionStream.CONTACTS
                or fact.run_id != group["owner_run_id"]
                or fact.source_state_key is None
                or len(fact.source_state_key) != 64
            ):
                pytest.fail("Contacts release changed fact or source-state ownership")
    finally:
        catalog.close()

    reads = read_published(database, tmp_path / "raw", "contacts-fixture", "contacts")
    if len(reads) != len(expected_entries):
        pytest.fail("Contacts Reader lost a released impact")
    if not any("/opaque/child-contacts?cursor=opaque-c" in path for path in requests):
        pytest.fail("Public discovery did not complete recursive pagination")
