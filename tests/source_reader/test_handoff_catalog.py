"""Prove bounded read-only release admission against real local A1 ledgers."""

import asyncio
import importlib
import sqlite3
from dataclasses import replace

import pytest
from pydantic import ValidationError

from message_ingest.acquisition.handoff import (
    AcquisitionFactKind,
    AcquisitionStream,
    FactSpec,
    ReleaseEntrySpec,
    ReleaseGroupSpec,
    ReleaseKind,
    SourceVersionLocator,
    source_state_key,
)
from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from msgloom.sources import SourceReaderLimits, SourceReferenceError


def api():
    """Fail explicitly until the public feed API is implemented."""
    module = importlib.import_module("msgloom.sources")
    if not hasattr(module, "HandoffCatalog"):
        pytest.fail("Task 6 read-only HandoffCatalog API is missing")
    return module.HandoffCatalog


def publish(catalog, source="source", stream=AcquisitionStream.OUTLOOK_MAIL, count=3):
    """Publish exact fixture facts through the accepted A1 writer."""
    store = AcquisitionHandoffStore(catalog)
    group = ReleaseGroupSpec(
        source_id=source,
        stream=stream,
        release_kind=ReleaseKind.RESOURCE_SET,
        subject_kind="inventory",
        subject_identity=f"{source}-{stream}",
        owner_run_id="run",
        released_at="2026-10-03T00:00:00Z",
        coverage_kind="complete",
    )
    facts = []
    entries = []
    with catalog.writer_session() as session:
        for index in range(count):
            fact = FactSpec(
                source_id=source,
                stream=stream,
                run_id="run",
                spider_name="fixture",
                fact_kind=AcquisitionFactKind.RESOURCE_OBSERVATION,
                resource_kind="resource",
                resource_identity=str(index),
                provider_observed_at="2026-10-03T00:00:00Z",
                source_state_key=source_state_key({"version": index}),
                source_version_locator=SourceVersionLocator(
                    kind="evidence",
                    evidence_id=f"evidence-{index}",
                    resource_identity=str(index),
                ),
            )
            fact = store.stage_state_fact_in_session(session, fact)
            facts.append(fact)
            entries.append(
                ReleaseEntrySpec(
                    resource_kind="resource",
                    resource_identity=str(index),
                    facts=((fact.fact_id, "primary"),),
                )
            )
        store.release_effective_group_in_session(session, group, entries)
    return facts


@pytest.fixture
def ledger(tmp_path):
    """Create local source/stream-isolated committed releases."""
    path = tmp_path / "catalog.db"
    catalog = Catalog(f"sqlite:///{path}")
    publish(catalog)
    publish(catalog, stream=AcquisitionStream.OUTLOOK_CALENDAR, count=1)
    publish(catalog, source="other", count=1)
    yield path, catalog
    catalog.close()


def test_bounded_pages_and_isolation(ledger):
    async def check():
        reader = api()(ledger[0], SourceReaderLimits(max_list_results=2))
        try:
            identity = await reader.catalog_identity()
            if (
                identity.catalog_identity
                != AcquisitionHandoffStore(ledger[1]).catalog_identity()
                or identity.schema_version != 1
            ):
                pytest.fail("Wrong stable catalog identity")
            maximum = await reader.max_release_entry_seq("source", "outlook_mail")
            page = await reader.list_release_entries(
                "source",
                "outlook_mail",
                after_seq=0,
                through_seq=maximum,
                limit=2,
            )
            if [entry.release_entry_seq for entry in page.entries] != [1, 2]:
                pytest.fail("First page is not bounded and ordered")
            if page.catalog != identity or page.through_seq != 3 or not page.has_more:
                pytest.fail("Page lost its catalog/cutoff or continuation")
            following = await reader.list_release_entries(
                "source",
                "outlook_mail",
                after_seq=2,
                through_seq=3,
                limit=2,
            )
            if [entry.release_entry_seq for entry in following.entries] != [3]:
                pytest.fail("Pagination crossed source or stream")
            if following.has_more:
                pytest.fail("Exhausted page incorrectly advertises more entries")
            empty = await reader.list_release_entries(
                "missing",
                "outlook_mail",
                after_seq=0,
                through_seq=5,
                limit=2,
            )
            if (
                empty.entries
                or await reader.max_release_entry_seq("missing", "outlook_mail") != 0
            ):
                pytest.fail("Missing stream is not empty")
            if await reader.get_release_entry(99) is not None:
                pytest.fail("Unknown sequence returned an entry")
        finally:
            await reader.close()

    asyncio.run(check())


@pytest.mark.parametrize(
    "kwargs",
    [
        {"limit": 0},
        {"limit": True},
        {"limit": 201},
        {"after_seq": -1},
        {"after_seq": True},
        {"through_seq": 2**63},
        {"through_seq": -1},
        {"source_id": ""},
        {"source_id": "x" * 2049},
        {"stream": "unknown"},
        {"after_seq": 3, "through_seq": 2},
    ],
)
def test_invalid_page_inputs(ledger, kwargs):
    async def check():
        reader = api()(ledger[0])
        try:
            values = {
                "source_id": "source",
                "stream": "outlook_mail",
                "after_seq": 0,
                "through_seq": 5,
                "limit": 2,
            }
            values.update(kwargs)
            with pytest.raises((ValueError, SourceReferenceError)):
                await reader.list_release_entries(**values)
        finally:
            await reader.close()

    asyncio.run(check())


def test_exact_immutable_facts_ignore_newer_effective_state(ledger):
    async def check():
        reader = api()(ledger[0])
        try:
            entry = await reader.get_release_entry(1)
            if entry is None:
                pytest.fail("Released entry missing")
            before = await reader.get_release_facts(entry)
            fact = before[0]
            if fact.resource_identity != "0" or fact.role != "primary":
                pytest.fail("Exact fact ownership lost")
            if fact.source_version_locator.evidence_id != "evidence-0":
                pytest.fail("Exact locator lost")
            with pytest.raises(ValidationError):
                fact.resource_identity = "mutated"
            with pytest.raises(ValidationError):
                entry.resource_identity = "mutated"
            store = AcquisitionHandoffStore(ledger[1])
            original = store.load_release_facts(1)[0]
            with ledger[1].writer_session() as session:
                store.stage_state_fact_in_session(
                    session,
                    replace(
                        original,
                        run_id="later",
                        source_state_key="b" * 64,
                        source_version_locator=SourceVersionLocator(
                            kind="evidence",
                            evidence_id="later",
                            resource_identity="0",
                        ),
                    ),
                )
            if await reader.get_release_facts(entry.reference) != before:
                pytest.fail("Mutable effective state changed released facts")
            if not await reader.verify_entry_anchor(1, entry.entry_digest):
                pytest.fail("Correct anchor rejected")
            if await reader.verify_entry_anchor(1, "0" * 64):
                pytest.fail("Incorrect anchor accepted")
            if await reader.verify_entry_anchor(99, entry.entry_digest):
                pytest.fail("Missing anchor accepted")
        finally:
            await reader.close()

    asyncio.run(check())


def test_restore_and_replacement_visible(ledger, tmp_path):
    async def check():
        old_path = tmp_path / "older.db"
        with sqlite3.connect(ledger[0]) as current, sqlite3.connect(old_path) as old:
            current.backup(old)
        publish(ledger[1], source="later", count=1)
        reader = api()(ledger[0])
        old_reader = api()(old_path)
        replacement_path = tmp_path / "replacement.db"
        replacement = Catalog(f"sqlite:///{replacement_path}")
        publish(replacement)
        replacement.close()
        other = api()(replacement_path)
        try:
            latest = await reader.get_release_entry(6)
            if latest is None:
                pytest.fail("Fixture newer release missing")
            if await old_reader.catalog_identity() != await reader.catalog_identity():
                pytest.fail("Backup failed to preserve identity")
            if await old_reader.verify_entry_anchor(6, latest.entry_digest):
                pytest.fail("Older restore silently accepted newer cursor")
            entry = await reader.get_release_entry(1)
            if await other.catalog_identity() == await reader.catalog_identity():
                pytest.fail("Independent catalog identity collision")
            with pytest.raises(SourceReferenceError):
                await other.get_release_facts(entry)
        finally:
            await reader.close()
            await old_reader.close()
            await other.close()

    asyncio.run(check())


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE acquisition_release_entry_facts SET role='proof' WHERE release_entry_seq=1",
        "DELETE FROM acquisition_release_entry_facts WHERE release_entry_seq=1",
        "UPDATE acquisition_release_entries SET entry_digest='bad' WHERE release_entry_seq=1",
        "UPDATE acquisition_facts SET payload='{}'",
        "UPDATE acquisition_ledger_metadata SET schema_version=999",
    ],
)
def test_corrupt_ledger_fails_closed(ledger, mutation):
    async def check():
        reader = api()(ledger[0])
        try:
            entry = await reader.get_release_entry(1)
            with sqlite3.connect(ledger[0]) as connection:
                triggers = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='trigger'"
                ).fetchall()
                for (name,) in triggers:
                    connection.execute(f'DROP TRIGGER "{name}"')
                connection.execute(mutation)
            with pytest.raises(SourceReferenceError):
                await reader.get_release_facts(entry)
        finally:
            await reader.close()

    asyncio.run(check())


def test_no_credentials_or_provider_table_access(ledger, monkeypatch):
    original = sqlite3.connect
    reads = set()
    writes = []

    def connect(*args, **kwargs):
        connection = original(*args, **kwargs)
        connection.set_trace_callback(writes.append)

        def authorize(action, table, column, database, trigger):
            if action == sqlite3.SQLITE_READ:
                reads.add(table)
                if not table.startswith("acquisition_"):
                    return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK

        connection.set_authorizer(authorize)
        return connection

    async def check():
        reader = api()(ledger[0])
        try:
            await reader.catalog_identity()
            await reader.max_release_entry_seq("source", "outlook_mail")
            page = await reader.list_release_entries(
                "source",
                "outlook_mail",
                after_seq=0,
                through_seq=5,
                limit=3,
            )
            await reader.get_release_facts(page.entries[0])
            await reader.verify_entry_anchor(1, page.entries[0].entry_digest)
        finally:
            await reader.close()

    monkeypatch.setattr(sqlite3, "connect", connect)
    asyncio.run(check())
    if reads - {
        "acquisition_ledger_metadata",
        "acquisition_release_groups",
        "acquisition_release_entries",
        "acquisition_release_entry_facts",
        "acquisition_facts",
    }:
        pytest.fail("Read escaped immutable ledger tables")
    if any(
        sql.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        for sql in writes
    ):
        pytest.fail("Reader attempted an A1 mutation")


def test_unsafe_paths_and_close(ledger, tmp_path):
    reader_type = api()
    link = tmp_path / "link.db"
    link.symlink_to(ledger[0])
    with pytest.raises(SourceReferenceError):
        reader_type(link)

    async def check():
        reader = reader_type(ledger[0])
        await reader.close()
        await reader.close()
        with pytest.raises(SourceReferenceError):
            await reader.catalog_identity()

    asyncio.run(check())


def test_fact_budget_is_not_silent_truncation(ledger):
    async def check():
        reader = api()(ledger[0], SourceReaderLimits(max_snapshot_bytes=64))
        try:
            with pytest.raises(SourceReferenceError):
                entry = await reader.get_release_entry(1)
                await reader.get_release_facts(entry)
        finally:
            await reader.close()

    asyncio.run(check())


def test_encoded_catalog_path_and_inode_replacement(ledger, tmp_path):
    async def check():
        copied = tmp_path / "catalog ?#.db"
        with sqlite3.connect(ledger[0]) as source, sqlite3.connect(copied) as target:
            source.backup(target)
        reader = api()(copied)
        try:
            identity = await reader.catalog_identity()
            if (
                identity.catalog_identity
                != AcquisitionHandoffStore(ledger[1]).catalog_identity()
            ):
                pytest.fail("URI special characters changed catalog selection")
            copied.rename(tmp_path / "original.db")
            with sqlite3.connect(copied):
                pass
            with pytest.raises(SourceReferenceError):
                await reader.catalog_identity()
        finally:
            await reader.close()

    asyncio.run(check())


def test_multi_member_order_and_row_bound(tmp_path):
    path = tmp_path / "members.db"
    catalog = Catalog(f"sqlite:///{path}")
    store = AcquisitionHandoffStore(catalog)
    try:
        originals = publish(catalog)
        with catalog.writer_session() as session:
            facts = tuple(
                store.stage_state_fact_in_session(
                    session,
                    replace(
                        fact,
                        run_id="new",
                        source_state_key="c" * 64,
                    ),
                )
                for fact in originals
            )
            group = ReleaseGroupSpec(
                source_id="source",
                stream=AcquisitionStream.OUTLOOK_MAIL,
                release_kind=ReleaseKind.RESOURCE_PROFILE,
                subject_kind="resource",
                subject_identity="0",
                owner_run_id="new",
                released_at="2026-10-03T01:00:00Z",
                coverage_kind="complete",
            )
            store.release_effective_group_in_session(
                session,
                group,
                (
                    ReleaseEntrySpec(
                        resource_kind="resource",
                        resource_identity="0",
                        facts=tuple(
                            (fact.fact_id, "proof" if index else "primary")
                            for index, fact in enumerate(facts)
                        ),
                    ),
                ),
            )

        async def check():
            reader = api()(path)
            bounded = api()(path, SourceReaderLimits(max_query_rows=2))
            try:
                entry = await reader.get_release_entry(4)
                loaded = await reader.get_release_facts(entry)
                if tuple(f.fact_id for f in loaded) != tuple(f.fact_id for f in facts):
                    pytest.fail("Ordered exact members were changed")
                if tuple(f.role for f in loaded) != ("primary", "proof", "proof"):
                    pytest.fail("Member roles were changed")
                with pytest.raises(SourceReferenceError):
                    await bounded.get_release_entry(4)
            finally:
                await reader.close()
                await bounded.close()

        asyncio.run(check())
    finally:
        catalog.close()
