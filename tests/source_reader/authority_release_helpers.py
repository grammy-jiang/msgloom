"""Read actual Mail authority entries through the public Reader boundary."""

import asyncio
import json

import pytest

from message_ingest.acquisition.handoff import AcquisitionStream
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from tests.source_reader.release_nonmail_helpers import SOURCE, reader_api

OLD = "2026-09-28T00:00:00+00:00"
CURRENT = "2026-09-29T00:00:00+00:00"
LATER = "2026-09-30T00:00:00+00:00"
FOLDER = {"id": "inbox", "displayName": "Original inbox"}
MESSAGE = {
    "id": "present",
    "parentFolderId": "inbox",
    "changeKey": "v1",
    "subject": "Original subject",
    "body": {"contentType": "text", "content": "Original body"},
}


def entries(catalog):
    """Return only entries published by real authority commit operations."""
    return AcquisitionHandoffStore(catalog).list_release_entries(
        SOURCE, AcquisitionStream.OUTLOOK_MAIL, after_seq=0, limit=100
    )


def read_entries(saved, rows):
    """Resolve recorded anchors and load each pinned evidence byte sequence."""

    async def read():
        reader = reader_api(saved)
        try:
            results = []
            for row in rows:
                entry = await reader.catalog.get_release_entry(row["release_entry_seq"])
                if entry is None:
                    pytest.fail("Committed authority entry is missing")
                result = await reader.read_entry(entry.reference)
                references = [item.record.source_bytes for item in result.contexts]
                if result.selection is not None:
                    references.append(result.selection.record.source_bytes)
                references.extend(item.evidence for item in result.transitions)
                payloads = []
                for reference in references:
                    if reference is None:
                        pytest.fail("Authority entry lost its saved evidence")
                    payloads.append(await reader.load_saved_bytes(reference))
                results.append((entry, result, tuple(payloads)))
            return results
        finally:
            await reader.close()

    return asyncio.run(read())


def page_bytes(value):
    """Match the authentic local evidence helper's JSON byte encoding."""
    return json.dumps(value, separators=(",", ":")).encode()


def only(reads, kind, identity):
    """Select one exact impact and fail on absent or duplicate entries."""
    found = [
        item
        for item in reads
        if item[0].entry_kind == kind and item[0].resource_identity == identity
    ]
    if len(found) != 1:
        pytest.fail(f"Expected one {kind} entry for {identity}: {len(found)}")
    return found[0]
