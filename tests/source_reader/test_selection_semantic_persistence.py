"""Keep the exact collected selection across the production data boundary."""

from __future__ import annotations

import asyncio
import sqlite3
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ExecutionIdentity,
    ExternalEffectState,
    ResultRef,
    TerminalStatus,
)
from msgloom.persistence import Phase1Persistence
from msgloom.preparation.records import PreparedSourceType
from msgloom.sources import (
    CollectedSelection,
    CollectedSelectionCodec,
    SavedSourceReader,
    SavedSourceReaderConfig,
)
from tests.prepared_contract_fixtures import phase1_url, prepared_result


def test_selection_replays_after_restart_and_source_projection_change(
    saved_catalog: dict[str, object], tmp_path: Path
) -> None:
    """A preparation claim consumes saved selection bytes and exact lineage."""

    async def exercise() -> None:
        reader = SavedSourceReader(
            SavedSourceReaderConfig(
                catalog_path=cast(Path, saved_catalog["database"]),
                evidence_roots=(cast(Path, saved_catalog["evidence_root"]),),
            )
        )
        try:
            sources = await reader.list_versions(
                PreparedSourceType.OUTLOOK_EMAIL,
                source_id=cast(str, saved_catalog["source_id"]),
                limit=10,
            )
            source = next(ref for ref in sources if ref.version == "obs-current")
            selection = await reader.read_selection(source)
        finally:
            await reader.close()
        codec = CollectedSelectionCodec()
        payload = codec.encode(selection)
        url = phase1_url(tmp_path / "phase1.sqlite3")
        store = await Phase1Persistence.open(url)
        try:
            data_ref = store.semantic_reference(
                "data-selection", "collected_selection", "1", selection
            )
            result = replace(
                prepared_result(data_ref, result_id="result-selection"),
                kind="collected_selection",
                source_versions=(selection.source, selection.selection),
                prepared_versions=(),
                rule_version=None,
            )
            await store.append_result_with_data(result, selection)
        finally:
            await store.close()

        connection = sqlite3.connect(cast(Path, saved_catalog["database"]))
        try:
            with connection:
                connection.execute(
                    "UPDATE message_surfaces SET status = 'failed' "
                    "WHERE surface LIKE 'attachment_raw:%'"
                )
        finally:
            connection.close()

        reopened = await Phase1Persistence.open(url)
        try:
            saved = await reopened.get_result("result-selection")
            if saved is None or saved.semantic_data_ref is None:
                pytest.fail("saved selection result or payload is missing")
            replay = await reopened.load_semantic_data(saved.semantic_data_ref)
            if not isinstance(replay, CollectedSelection):
                pytest.fail("saved selection did not decode to its closed type")
            if replay != selection or codec.encode(replay) != payload:
                pytest.fail("saved selection changed after source projection mutation")
            if saved.source_versions != (selection.source, selection.selection):
                pytest.fail("saved selection lost primary or composite lineage")
            token = await reopened.acquire_claim(
                "prepare:selection-restart",
                ClaimKind.PREPARE,
                ExecutionIdentity("execution-selection-consumer"),
                AttemptIdentity("attempt-selection-consumer"),
                required_inputs=(
                    ResultRef("result-selection", "collected_selection", "1"),
                ),
            )
            await reopened.finish_claim(
                token, TerminalStatus.COMPLETE, ExternalEffectState.NONE
            )
        finally:
            await reopened.close()

    asyncio.run(exercise())
