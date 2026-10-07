"""Check real publisher references at the public exact Reader boundary."""

import asyncio
import json
import sqlite3
from pathlib import Path
from urllib.parse import unquote

import pytest

from message_ingest.catalog import Catalog
from message_ingest.catalog.models.acquisition import SourceBinding
from msgloom.sources.models import SavedSourceReaderConfig
from msgloom.sources.release_reader import ReleaseSourceReader


def bind_fixture_source(database, source_id):
    """Bind the local account because these crawls disable remote identity."""
    catalog = Catalog(f"sqlite:///{database}")
    try:
        with catalog.writer_session() as writer:
            writer.add(
                SourceBinding(
                    source_id=source_id,
                    provider="microsoft_graph",
                    key_scheme="fixture-v1",
                    account_key_sha256="1" * 64,
                    binding_method="test",
                    bound_at="2026-10-01T00:00:00Z",
                )
            )
    finally:
        catalog.close()


def read_published(database, evidence_root, source_id, stream):
    """Read every committed fixture entry and check its exact saved membership.

    The publisher owns the expected ledger facts. These checks bind the Reader
    result to those facts and independently load each returned byte reference.
    Callers check the provider-specific entry identities and completion state.
    """
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT release_entry_seq, payload FROM acquisition_release_entries "
            "WHERE source_id = ? AND stream = ? ORDER BY release_entry_seq",
            (source_id, stream),
        ).fetchall()
        evidence = dict(
            connection.execute(
                "SELECT evidence_id, response_body_path FROM raw_http_evidence"
            )
        )

    async def read():
        reader = ReleaseSourceReader(
            SavedSourceReaderConfig(
                catalog_path=database, evidence_roots=(evidence_root,)
            )
        )
        try:
            results = []
            for sequence, raw in rows:
                payload = json.loads(raw)
                entry = await reader.catalog.get_release_entry(sequence)
                if entry is None:
                    pytest.fail("Publisher entry disappeared at Reader boundary")
                result = await reader.read_entry(entry.reference)
                if (
                    result.reference != entry.reference
                    or [[fact.fact_id, fact.role] for fact in result.facts]
                    != payload["facts"]
                ):
                    pytest.fail("Reader changed exact entry reference or facts")
                if any(
                    (fact.source_id, fact.stream) != (source_id, stream)
                    for fact in result.facts
                ):
                    pytest.fail("Reader changed source or stream ownership")
                if result.transitions or entry.group.authority_revision:
                    pytest.fail("Discovery/Full/content acquired authority")
                if entry.entry_kind == "context" and (
                    result.selection is not None or len(result.contexts) != 1
                ):
                    pytest.fail("Context entry became primary work")
                if entry.entry_kind == "resource" and result.selection is None:
                    pytest.fail("Resource entry lost its primary selection")
                selections = (
                    *result.contexts,
                    *result.components,
                    *((result.selection,) if result.selection else ()),
                )
                expected_owners = {
                    (
                        fact.source_id,
                        fact.stream,
                        fact.resource_kind,
                        fact.resource_identity,
                    )
                    for fact in result.facts
                    if fact.role != "proof"
                }
                # Content-only OneDrive entries reconstruct the declared
                # item parent from the capture's separate metadata evidence.
                if entry.entry_kind == "component" and stream == "onedrive":
                    expected_owners.add(
                        (
                            source_id,
                            stream,
                            entry.resource_kind,
                            entry.resource_identity,
                        )
                    )
                for selection in selections:
                    owner = tuple(
                        unquote(part)
                        for part in selection.source.identity.split("/")[:4]
                    )
                    if owner not in expected_owners:
                        pytest.fail("Reader changed material resource ownership")
                    reference = selection.record.source_bytes
                    if reference is None:
                        continue  # Terminal surfaces can be evidence-free.
                    evidence_id = reference.reference.removeprefix("a1-response:")
                    if evidence_id not in evidence or (
                        await reader.load_saved_bytes(reference)
                        != Path(evidence[evidence_id]).read_bytes()
                    ):
                        pytest.fail("Reader changed exact saved evidence bytes")
                results.append((entry, result))
            return results
        finally:
            await reader.close()

    return asyncio.run(read())
