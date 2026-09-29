"""End-to-end A2 production over the real synthetic A1 catalog."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import cast

import pytest

from msgloom.application.app import Application
from msgloom.contracts import (
    AttemptIdentity,
    ExecutionIdentity,
    OperationRequest,
    PhaseCapability,
    ResultRef,
    TerminalStatus,
    TrustedAdmission,
)
from msgloom.preparation import DocumentFormat, PreparedRecord, PreparedSourceType
from msgloom.preparation.filtering import FilterResult
from msgloom.preparation.grouping import GroupResult
from msgloom.preparation_pipeline import (
    DerivedByteArtifact,
    PreparationHandler,
    PreparationMode,
)
from msgloom.sources import (
    CollectedSelection,
    CollectedSourceReader,
    SavedSourceReader,
    SavedSourceReaderConfig,
)

from .helpers import open_store, plan, profiles


def _request(execution: str, source) -> OperationRequest:
    return OperationRequest(
        execution=ExecutionIdentity(execution),
        caller="synthetic-cli",
        capability=PhaseCapability.PREPARE,
        target_inputs=(source,),
        authority_ref="synthetic-authority",
    )


def test_real_catalog_persists_evidence_before_prepared_semantics_and_replays(
    saved_catalog: dict[str, object],
    tmp_path: Path,
) -> None:
    """Captured A1 selection survives projection-independent replay."""

    async def exercise() -> None:
        reader = SavedSourceReader(
            SavedSourceReaderConfig(
                catalog_path=cast(Path, saved_catalog["database"]),
                evidence_roots=(cast(Path, saved_catalog["evidence_root"]),),
            )
        )
        store = await open_store(tmp_path / "phase1.sqlite3")
        try:
            versions = await reader.list_versions(
                PreparedSourceType.OUTLOOK_EMAIL,
                source_id=cast(str, saved_catalog["source_id"]),
                limit=10,
            )
            source = next(item for item in versions if item.version == "obs-current")
            live_plan = plan(
                source,
                attempt=AttemptIdentity("attempt-live"),
                parser_profiles=profiles(
                    DocumentFormat.HTML,
                    DocumentFormat.TEXT,
                    DocumentFormat.JSON,
                    DocumentFormat.MIME,
                ),
            )
            handler = PreparationHandler(store, reader, live_plan)
            app = Application(
                store,
                trusted_admissions=(
                    TrustedAdmission(
                        "synthetic-cli",
                        "synthetic-authority",
                        frozenset({PhaseCapability.PREPARE}),
                    ),
                ),
                prepare_factory=lambda: handler,
            )
            outcome = await app.run(_request("execution-live", source))
            if outcome.status is not TerminalStatus.INCOMPLETE:
                pytest.fail(f"source limitation was not retained: {outcome}")
            if not any(
                item.code == "captured-current-component-selection"
                for item in outcome.limitations
            ):
                pytest.fail("source-reader association limitation was dropped")

            by_kind = {}
            for ref in outcome.result_refs:
                by_kind.setdefault(ref.kind, []).append(ref)
            for required in (
                "collected_selection",
                "derived_bytes",
                "prepared",
                "filter_result",
                "group_result",
            ):
                if required not in by_kind:
                    pytest.fail(f"missing durable {required} result")

            selection_ref = by_kind["collected_selection"][0]
            selection_result = await store.get_result(selection_ref.result_id)
            if selection_result is None or selection_result.semantic_data_ref is None:
                pytest.fail("captured selection was not durably saved")
            selection = await store.load_semantic_data(
                selection_result.semantic_data_ref
            )
            if not isinstance(selection, CollectedSelection):
                pytest.fail("captured selection decoded to the wrong type")

            body_artifact = None
            for ref in by_kind["derived_bytes"]:
                result = await store.get_result(ref.result_id)
                if result is None or result.semantic_data_ref is None:
                    pytest.fail("derived-byte result is missing data")
                value = await store.load_semantic_data(result.semantic_data_ref)
                if isinstance(
                    value, DerivedByteArtifact
                ) and value.component.startswith("body:"):
                    body_artifact = value
                    if result.input_refs != (selection_ref,):
                        pytest.fail("derived bytes were not bound to saved selection")
            if body_artifact is None or body_artifact.text != "<p>Current body</p>":
                pytest.fail("HTML body was not captured as exact derived bytes")
            if (
                selection.record.body is None
                or selection.record.body.saved_bytes is None
            ):
                pytest.fail("fixture body did not retain its Graph envelope")
            if body_artifact.sha256 == selection.record.body.saved_bytes.sha256:
                pytest.fail("derived body incorrectly reused Graph envelope digest")

            prepared_ref = by_kind["prepared"][0]
            prepared_result = await store.get_result(prepared_ref.result_id)
            if prepared_result is None or prepared_result.semantic_data_ref is None:
                pytest.fail("prepared result is missing semantic data")
            prepared = await store.load_semantic_data(prepared_result.semantic_data_ref)
            if not isinstance(prepared, PreparedRecord):
                pytest.fail("prepared result decoded to the wrong type")
            if prepared.body != "Current body":
                pytest.fail("parsed HTML did not retain readable body text")
            if not any(
                '"semantic_identity"' in getattr(block, "text", "")
                and '"metadata"' in getattr(block, "text", "")
                for item in prepared.parsed_contents
                for block in item.output.blocks
            ):
                pytest.fail("collected contextual metadata was not retained")

            filter_ref = by_kind["filter_result"][0]
            filter_result = await store.get_result(filter_ref.result_id)
            if filter_result is None or filter_result.semantic_data_ref is None:
                pytest.fail("filter result is missing")
            filter_value = await store.load_semantic_data(
                filter_result.semantic_data_ref
            )
            if not isinstance(filter_value, FilterResult):
                pytest.fail("filter result decoded to wrong type")
            if filter_result.input_refs != (prepared_ref,):
                pytest.fail("filter result was not ordered after prepared result")

            group_ref = by_kind["group_result"][0]
            group_result = await store.get_result(group_ref.result_id)
            if group_result is None or group_result.semantic_data_ref is None:
                pytest.fail("group result is missing")
            group_value = await store.load_semantic_data(group_result.semantic_data_ref)
            if not isinstance(group_value, GroupResult):
                pytest.fail("group result decoded to wrong type")
            if prepared_ref not in group_result.input_refs or filter_ref not in (
                group_result.input_refs
            ):
                pytest.fail("group result did not bind durable prepared/filter inputs")

            replay_result_ref = ResultRef(
                selection_result.result_id,
                selection_result.kind,
                selection_result.schema_version,
            )
        finally:
            await store.close()

        reopened = await open_store(tmp_path / "phase1.sqlite3")

        class ReplayOnlyReader:
            async def read_selection(self, _source):
                pytest.fail("replay consulted current A1 projections")

            async def load_saved_bytes(self, reference):
                return await reader.load_saved_bytes(reference)

        try:
            replay_plan = plan(
                source,
                attempt=AttemptIdentity("attempt-replay"),
                mode=PreparationMode.REPLAY,
                replay_result=replay_result_ref,
                replay_selection=selection.selection,
                parser_profiles=profiles(
                    DocumentFormat.HTML,
                    DocumentFormat.TEXT,
                    DocumentFormat.JSON,
                    DocumentFormat.MIME,
                ),
            )
            replay = PreparationHandler(
                reopened, cast(CollectedSourceReader, ReplayOnlyReader()), replay_plan
            )
            replay_outcome = await replay.run(_request("execution-replay", source))
            if replay_outcome.status is not TerminalStatus.INCOMPLETE:
                pytest.fail(f"replay lost source limitation: {replay_outcome}")
            if any(
                ref.result_id == old.result_id
                for ref in replay_outcome.result_refs
                for old in outcome.result_refs
                if ref.kind != "collected_selection"
            ):
                pytest.fail("replay reused a derived historical result identity")
        finally:
            await reopened.close()
            await reader.close()

    asyncio.run(exercise())
