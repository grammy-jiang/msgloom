"""A malformed or bounded release cannot permanently block later A2 admission."""

import asyncio
from pathlib import Path

import pytest

from msgloom.persistence import Phase1Persistence
from msgloom.preparation_pipeline.intake import PreparationIntakeService
from msgloom.preparation_pipeline.intake_models import IntakeScope
from msgloom.sources import (
    ReleaseSourceReader,
    SavedSourceReaderConfig,
    SourceReaderLimits,
)
from tests.preparation_intake_helpers import large_transition_group, payload, run
from tests.source_reader.conftest import saved_catalog as saved_catalog  # noqa: PLC0414
from tests.source_reader.release_nonmail_helpers import SOURCE


@pytest.mark.parametrize(
    "limits",
    [
        SourceReaderLimits(max_query_rows=1, max_list_results=1),
        SourceReaderLimits(max_snapshot_bytes=64, max_list_results=1),
    ],
    ids=["two-fact-member-over-budget", "release-metadata-over-budget"],
)
def test_bad_first_entry_is_held_and_later_entry_can_progress(
    saved_catalog, tmp_path: Path, limits: SourceReaderLimits
) -> None:
    """Admit durable bounded held anchors, not an eternal page-read exception."""
    large_transition_group(saved_catalog, entry_count=2)

    async def check() -> None:
        reader = ReleaseSourceReader(
            SavedSourceReaderConfig(
                catalog_path=saved_catalog["database"],
                evidence_roots=(saved_catalog["evidence_root"],),
                limits=limits,
            )
        )
        persistence = await Phase1Persistence.open(f"sqlite:///{tmp_path / 'a2.db'}")
        try:
            scope = IntakeScope(
                catalog=await reader.catalog.catalog_identity(),
                source_id=SOURCE,
                stream="contacts",
                consumer_id="bounded-reader-consumer",
            )
            service = PreparationIntakeService(persistence, reader)
            seen = []
            for index in range(2):
                result = await run(service, scope, identity=f"bounded-{index}", limit=1)
                workset = await payload(persistence, result)
                if workset.selections or workset.transitions or len(workset.held) != 1:
                    pytest.fail("Oversized metadata/entry was not isolated as held")
                if workset.held[0].reason not in {
                    "query_limit",
                    "byte_limit",
                    "materialization_failed",
                }:
                    pytest.fail("Reader returned an unsupported held disposition")
                if len(workset.entries) != 1:
                    pytest.fail("Reader exceeded its bounded single-entry window")
                seen.append(workset.entries[0].release_entry_seq)
            if len(set(seen)) != 2:
                pytest.fail("Bounded metadata lost a later entry")
            if await run(service, scope, identity="drained", limit=1) is not None:
                pytest.fail("The held entry prevented bounded cursor progress")
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())


def test_anchor_enumeration_charges_aggregate_metadata_before_next_row(
    saved_catalog, tmp_path: Path
) -> None:
    """A strict 64-byte materialization budget cannot load a 1000-entry anchor page."""
    large_transition_group(saved_catalog, entry_count=3)

    async def check() -> None:
        reader = ReleaseSourceReader(
            SavedSourceReaderConfig(
                catalog_path=saved_catalog["database"],
                evidence_roots=(saved_catalog["evidence_root"],),
                limits=SourceReaderLimits(max_snapshot_bytes=64, max_list_results=1000),
            )
        )
        try:
            ceiling = await reader.catalog.max_release_entry_seq(SOURCE, "contacts")
            after = 0
            seen = []
            for _ in range(3):
                refs = await reader.catalog.list_release_entry_refs(
                    SOURCE, "contacts", after_seq=after, through_seq=ceiling, limit=1000
                )
                if len(refs) != 1:
                    pytest.fail("Anchor enumeration ignored aggregate byte budget")
                seen.append(refs[0].release_entry_seq)
                after = refs[0].release_entry_seq
            if len(set(seen)) != 3 or (
                await reader.catalog.list_release_entry_refs(
                    SOURCE, "contacts", after_seq=after, through_seq=ceiling, limit=1000
                )
            ):
                pytest.fail(
                    "Budgeted anchor paging skipped or repeated entry identities"
                )
        finally:
            await reader.close()

    asyncio.run(check())
