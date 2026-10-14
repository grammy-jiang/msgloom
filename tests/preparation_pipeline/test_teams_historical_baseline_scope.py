"""Owner-approved Teams history must retain exact source-to-stream scope."""

import asyncio
from pathlib import Path

import pytest

from message_ingest.catalog.store import Catalog
from msgloom.persistence import Phase1Persistence
from msgloom.preparation_pipeline.historical_baseline import HistoricalBaselineService
from msgloom.preparation_pipeline.intake_models import IntakeScope
from msgloom.sources import ReleaseSourceReader, SavedSourceReaderConfig
from msgloom.sources.handoff_models import Stream
from tests.preparation_intake_helpers import payload, run
from tests.source_reader.test_teams_saved_source import SOURCE, _build_fixture


@pytest.mark.parametrize("stream", ["teams_chat", "teams_channel"])
def test_historical_baseline_accepts_explicit_teams_source(
    tmp_path: Path, stream: Stream
) -> None:
    """A previously captured Teams message can seed its own exact scope."""
    bootstrap = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    bootstrap.close()
    fixture = _build_fixture(tmp_path)

    async def check() -> None:
        reader = ReleaseSourceReader(
            SavedSourceReaderConfig(
                catalog_path=fixture.database,
                evidence_roots=(fixture.evidence_root,),
            )
        )
        persistence = await Phase1Persistence.open(f"sqlite:///{tmp_path / 'a2.db'}")
        try:
            scope = IntakeScope(
                catalog=await reader.catalog.catalog_identity(),
                source_id=SOURCE,
                stream=stream,
                consumer_id="teams-baseline-consumer",
            )
            source = fixture.chat_a if stream == "teams_chat" else fixture.channel_root
            baseline = HistoricalBaselineService(persistence, reader)
            result = await run(
                baseline, scope, sources=(source,), approval_id="owner-approved"
            )
            workset = await payload(persistence, result)
            if workset.baseline_sources != (source,) or workset.entries:
                pytest.fail(
                    "Exact Teams baseline changed its approval or fabricated work"
                )
            if len(workset.selection_refs) != 1:
                pytest.fail("Exact Teams baseline did not persist its selection")
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())
