"""
Inspect immutable publication through SQLite and the bounded public reader.
"""

import asyncio
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from time import monotonic, sleep

import pytest

from message_ingest.catalog import Catalog
from msgloom.sources import HandoffCatalog, SourceReaderLimits
from msgloom.sources.handoff_models import Stream

LEDGER_TABLES = (
    "acquisition_release_groups",
    "acquisition_release_entries",
    "acquisition_release_entry_facts",
)
AUTHORITY_TABLES = {
    "todo": (
        "todo_snapshot_state",
        "todo_task_list_presence",
        "todo_task_presence",
        "todo_checklist_item_presence",
        "todo_linked_resource_presence",
    ),
    "contacts": (
        "contacts_snapshot_state",
        "contact_promotion_generations",
        "contact_delta_checkpoints",
        "contact_presence",
        "contact_folder_presence",
    ),
    "outlook_calendar": (
        "calendar_delta_checkpoints",
        "calendar_delta_event_states",
    ),
    "onedrive": ("onedrive_delta_checkpoints",),
}


def rows(root: Path, table: str):
    """Read a known test table without opening a writer or altering the DB."""
    with closing(
        sqlite3.connect((root / "catalog.sqlite3").as_uri() + "?mode=ro", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        return [dict(row) for row in db.execute(f'SELECT * FROM "{table}"')]


def authority(root: Path, stream: str):
    """Freeze committed authority and publication, excluding staged residue."""
    return {
        table: rows(root, table)
        for table in (*AUTHORITY_TABLES[stream], *LEDGER_TABLES)
    }


def reject_entries(root: Path):
    """
    Inject an actual SQLite insert failure after establishing prior state.
    """
    with closing(sqlite3.connect(root / "catalog.sqlite3")) as db, db:
        db.execute(
            "CREATE TRIGGER qualification_reject BEFORE INSERT ON "
            "acquisition_release_entries BEGIN SELECT "
            "RAISE(ABORT, 'qualification release fault'); END"
        )


def restore_entries(root: Path):
    """Remove only the trigger owned by this fixture."""
    with closing(sqlite3.connect(root / "catalog.sqlite3")) as db, db:
        db.execute("DROP TRIGGER qualification_reject")


def initialize(root: Path):
    """Initialize the normal catalog schema for a profile-only crawl."""
    catalog = Catalog(f"sqlite:///{root / 'catalog.sqlite3'}")
    catalog.close()


def groups(root: Path):
    """Return full immutable group identities alongside canonical metadata."""
    return [
        {**json.loads(row["payload"]), "id": row["release_group_id"]}
        for row in rows(root, "acquisition_release_groups")
    ]


def staged(root: Path):
    """
    Return staged facts, keeping IDs for exact comparison to reader output.
    """
    return [
        {**json.loads(row["payload"]), "fact_id": row["fact_id"]}
        for row in rows(root, "acquisition_facts")
    ]


def wait_staged(root: Path):
    """
    Await the actual pipeline write while a later HTTP request is held.

    Download progress does not imply completion of concurrent item writes.
    The fixture barrier remains closed while this bounded read-only probe
    waits for a durable observation; it cannot promote authority itself.
    """
    deadline = monotonic() + 5
    while monotonic() < deadline:
        if facts := staged(root):
            return facts
        sleep(0.01)
    pytest.fail("Held crawl did not persist its observation within five seconds")


def feed(root: Path, source: str, stream: Stream, *, limit: int = 7):
    """
    Page a fixed cutoff and check membership, scope, anchors and evidence.
    """

    async def read():
        """Load the fixed stream cut through awaited public reader methods."""
        reader = HandoffCatalog(
            root / "catalog.sqlite3", SourceReaderLimits(max_list_results=limit)
        )
        result = []
        try:
            maximum = await reader.max_release_entry_seq(source, stream)
            after = 0
            while after < maximum:
                page = await reader.list_release_entries(
                    source,
                    stream,
                    after_seq=after,
                    through_seq=maximum,
                    limit=limit,
                )
                if not page.entries or len(page.entries) > limit:
                    pytest.fail("Bounded feed omitted or overfilled a page")
                for entry in page.entries:
                    facts = await reader.get_release_facts(entry)
                    if (entry.source_id, entry.stream) != (source, stream):
                        pytest.fail("Reader crossed the source/stream boundary")
                    if (
                        entry.group.source_id != source
                        or entry.group.stream != stream
                        or entry.group.release_kind != "authority_scope"
                        or entry.group.coverage_kind != "complete"
                    ):
                        pytest.fail("Entry lost its authority group contract")
                    if tuple((f.fact_id, f.role) for f in facts) != entry.facts:
                        pytest.fail("Fact identity/role ordering changed in reader")
                    if any(
                        (f.source_id, f.stream) != (source, stream)
                        or not f.source_state_key
                        for f in facts
                    ):
                        pytest.fail("Released fact lost identity or semantic key")
                    if not await reader.verify_entry_anchor(
                        entry.release_entry_seq, entry.entry_digest
                    ):
                        pytest.fail("Reader rejected the immutable entry anchor")
                    if await reader.get_release_entry(entry.release_entry_seq) != entry:
                        pytest.fail("Exact lookup disagreed with paged entry")
                    result.append((entry, facts))
                next_after = page.entries[-1].release_entry_seq
                if next_after <= after or next_after > maximum:
                    pytest.fail("Reader did not advance within its frozen cutoff")
                if page.has_more != (next_after < maximum):
                    pytest.fail("Reader continuation flag lost committed entries")
                after = next_after
            if len({e.release_entry_seq for e, _ in result}) != len(result):
                pytest.fail("Bounded pages duplicated a release")
        finally:
            await reader.close()
        metadata = "\n".join(
            row["payload"]
            for table in ("acquisition_facts", *LEDGER_TABLES[:2])
            for row in rows(root, table)
        )
        if any(
            value in metadata
            for value in (
                "http://127.0.0.1",
                "provider-private-title",
                "opaque-terminal",
                "@microsoft.graph.downloadUrl",
                "companyName",
                "jobTitle",
            )
        ):
            pytest.fail("Provider bodies or transport URLs leaked into handoff")
        evidence = {r["evidence_id"] for r in rows(root, "raw_http_evidence")}
        for _, facts in result:
            for fact in facts:
                if fact.evidence_id is not None and fact.evidence_id not in evidence:
                    pytest.fail("Published fact lacks durable HTTP evidence")
                if (
                    fact.role in {"primary", "component", "context"}
                    and fact.source_version_locator is None
                ):
                    pytest.fail("Readable fact lacks its immutable locator")
        return result

    return asyncio.run(read())


def successful(result):
    """Reject both command failure and hidden crawler errors."""
    if result.returncode or "ERROR" in result.stderr:
        pytest.fail(result.stderr)


def no_churn(before, after):
    """Compare immutable entries and exact facts, including IDs and digests."""
    if before != after:
        pytest.fail("Unchanged authority round generated downstream churn")
