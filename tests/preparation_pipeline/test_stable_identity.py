"""Stable A2 semantic identity and execution-scoped lineage regressions."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from msgloom.contracts import AttemptIdentity, ResultRef, StageResult, VersionRef
from msgloom.preparation import DocumentFormat, PreparedRecord
from msgloom.preparation_pipeline import (
    DerivedByteArtifact,
    PreparationHandler,
    PreparationMode,
)
from msgloom.sources import CollectedSelection, CollectedSourceReader
from msgloom.sources._snapshot import capture_selection

from .helpers import open_store, plan, profiles
from .test_lifecycle import _fixture, _output, _request


async def _saved(store, ref: ResultRef) -> StageResult:
    value = await store.get_result(ref.result_id)
    if value is None:
        pytest.fail(f"missing durable {ref.kind} result")
    return value


async def _semantic_signatures(store, refs: tuple[ResultRef, ...]):
    signatures: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {}
    parsed: tuple[str, ...] = ()
    for kind in ("prepared", "filter_result", "group_result"):
        values = []
        for ref in refs:
            if ref.kind != kind:
                continue
            saved = await _saved(store, ref)
            if saved.semantic_data_ref is None:
                pytest.fail(f"{kind} result omitted semantic data")
            values.append(
                (
                    saved.semantic_data_ref.sha256,
                    tuple(item.version for item in saved.prepared_versions),
                )
            )
            if kind == "prepared":
                record = await store.load_semantic_data(saved.semantic_data_ref)
                if not isinstance(record, PreparedRecord):
                    pytest.fail("prepared semantic data has the wrong type")
                parsed = tuple(
                    item.reference.version for item in record.parsed_contents
                )
        signatures[kind] = tuple(values)
    return signatures, parsed


async def _check_derived_lineage(store, prepared_ref: ResultRef) -> None:
    prepared = await _saved(store, prepared_ref)
    if prepared.semantic_data_ref is None:
        pytest.fail("prepared result omitted semantic data")
    selection_refs = tuple(
        ref for ref in prepared.input_refs if ref.kind == "collected_selection"
    )
    derived_refs = tuple(
        ref for ref in prepared.input_refs if ref.kind == "derived_bytes"
    )
    if len(selection_refs) != 1 or not derived_refs:
        pytest.fail("prepared result lost exact selection or derived-byte lineage")

    record = await store.load_semantic_data(prepared.semantic_data_ref)
    if not isinstance(record, PreparedRecord):
        pytest.fail("prepared semantic data has the wrong type")
    artifacts: dict[str, DerivedByteArtifact] = {}
    for ref in derived_refs:
        saved = await _saved(store, ref)
        if saved.input_refs != selection_refs or saved.semantic_data_ref is None:
            pytest.fail("derived bytes do not point to the exact captured selection")
        artifact = await store.load_semantic_data(saved.semantic_data_ref)
        if not isinstance(artifact, DerivedByteArtifact):
            pytest.fail("derived semantic data has the wrong type")
        artifacts[artifact.stable_reference()] = artifact

    for parsed in record.parsed_contents:
        source = parsed.output.provenance.source
        artifact = artifacts.get(source.reference)
        if artifact is None:
            pytest.fail("parsed provenance cannot resolve through durable lineage")
        if source.sha256 != artifact.sha256 or source.byte_count != artifact.byte_count:
            pytest.fail("parsed provenance mismatches the exact derived bytes")
        if artifact.bytes() != artifact.text.encode("utf-8"):
            pytest.fail("derived-byte replay changed the exact saved bytes")


def test_semantic_identity_is_stable_while_durable_results_remain_per_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Equivalent executions retain semantics but append distinct durable results."""

    async def exercise() -> None:
        source, reader = _fixture()
        store = await open_store(tmp_path / "stable.sqlite3")

        async def parser(request, _content):
            return _output(request)

        monkeypatch.setattr(
            "msgloom.preparation_pipeline.record_steps.parse_isolated", parser
        )
        runs = []
        for suffix in ("first", "second"):
            work = plan(
                source,
                attempt=AttemptIdentity(f"stable-{suffix}"),
                parser_profiles=profiles(DocumentFormat.TEXT, DocumentFormat.JSON),
            )
            outcome = await PreparationHandler(
                store, cast(CollectedSourceReader, reader), work
            ).run(_request(f"stable-{suffix}", source))
            signatures, parsed = await _semantic_signatures(store, outcome.result_refs)
            runs.append((outcome, signatures, parsed))

        if runs[0][1:] != runs[1][1:]:
            pytest.fail("equivalent executions changed A2 semantic versions")
        first_ids = {ref.result_id for ref in runs[0][0].result_refs}
        second_ids = {ref.result_id for ref in runs[1][0].result_refs}
        if first_ids & second_ids:
            pytest.fail("equivalent executions reused durable result identities")

        first_prepared = next(
            ref for ref in runs[0][0].result_refs if ref.kind == "prepared"
        )
        second_prepared = next(
            ref for ref in runs[1][0].result_refs if ref.kind == "prepared"
        )
        await _check_derived_lineage(store, first_prepared)
        await _check_derived_lineage(store, second_prepared)
        await store.close()

    asyncio.run(exercise())


def test_meaning_bearing_changes_update_affected_semantic_versions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bytes, parser config, plan config, and code versions affect identity."""

    async def exercise() -> None:
        source, reader = _fixture()
        store = await open_store(tmp_path / "changes.sqlite3")

        async def parser(request, _content):
            return _output(request)

        monkeypatch.setattr(
            "msgloom.preparation_pipeline.record_steps.parse_isolated", parser
        )
        base = plan(
            source,
            attempt=AttemptIdentity("base"),
            parser_profiles=profiles(DocumentFormat.TEXT, DocumentFormat.JSON),
        )

        async def run(
            work,
            execution: str,
            selected: VersionRef = source,
            source_reader: object = reader,
        ):
            outcome = await PreparationHandler(
                store, cast(CollectedSourceReader, source_reader), work
            ).run(_request(execution, selected))
            return await _semantic_signatures(store, outcome.result_refs)

        baseline = await run(base, "base")
        changed_profiles = tuple(
            item.model_copy(
                update={
                    "config": replace(
                        item.config, profile=item.config.profile + "-changed"
                    )
                }
            )
            for item in base.parser_profiles
        )
        parser_changed = base.model_copy(
            update={
                "attempt": AttemptIdentity("parser-changed"),
                "parser_profiles": changed_profiles,
            }
        )
        config_changed = base.model_copy(
            update={
                "attempt": AttemptIdentity("config-changed"),
                "configuration_version": "prepare-config-v2",
            }
        )
        code_changed = base.model_copy(
            update={
                "attempt": AttemptIdentity("code-changed"),
                "code_version": "test-build-v2",
            }
        )
        for label, work in (
            ("parser", parser_changed),
            ("configuration", config_changed),
            ("code", code_changed),
        ):
            changed = await run(work, f"{label}-changed")
            if changed == baseline:
                pytest.fail(f"{label} change did not affect A2 semantic versions")

        selection = await reader.read_selection(source)
        changed_source = VersionRef(source.kind, source.identity, "v2")
        if selection.record.body is None:
            pytest.fail("synthetic fixture unexpectedly omitted its body")
        changed_body = selection.record.body.model_copy(
            update={"content": "Synthetic body changed"}
        )
        changed_record = selection.record.model_copy(
            update={"source": changed_source, "body": changed_body}
        )
        changed_selection = capture_selection(changed_record)

        class ChangedReader:
            async def read_selection(self, requested):
                if requested != changed_source:
                    pytest.fail("changed-byte run requested the wrong source")
                return changed_selection

            async def load_saved_bytes(self, _reference):
                pytest.fail("changed-byte fixture has no external saved bytes")

        bytes_plan = plan(
            changed_source,
            attempt=AttemptIdentity("bytes-changed"),
            parser_profiles=base.parser_profiles,
        )
        bytes_changed = await run(
            bytes_plan,
            "bytes-changed",
            selected=changed_source,
            source_reader=cast(CollectedSourceReader, ChangedReader()),
        )
        if bytes_changed == baseline:
            pytest.fail("changed selected bytes did not affect A2 semantic versions")
        await store.close()

    asyncio.run(exercise())


def test_replay_keeps_semantics_and_rebinds_exact_durable_lineage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Replay preserves semantic identity while binding new results to saved input."""

    async def exercise() -> None:
        source, reader = _fixture()
        store = await open_store(tmp_path / "replay.sqlite3")

        async def parser(request, _content):
            return _output(request)

        monkeypatch.setattr(
            "msgloom.preparation_pipeline.record_steps.parse_isolated", parser
        )
        live_plan = plan(
            source,
            attempt=AttemptIdentity("live"),
            parser_profiles=profiles(DocumentFormat.TEXT, DocumentFormat.JSON),
        )
        live = await PreparationHandler(
            store, cast(CollectedSourceReader, reader), live_plan
        ).run(_request("live", source))
        live_signatures = await _semantic_signatures(store, live.result_refs)
        selection_ref = next(
            ref for ref in live.result_refs if ref.kind == "collected_selection"
        )
        selection_saved = await _saved(store, selection_ref)
        if selection_saved.semantic_data_ref is None:
            pytest.fail("live selection omitted semantic data")
        selection = await store.load_semantic_data(selection_saved.semantic_data_ref)
        if not isinstance(selection, CollectedSelection):
            pytest.fail("live selection semantic data has the wrong type")

        class ReplayReader:
            async def read_selection(self, _requested):
                pytest.fail("replay consulted mutable source projections")

            async def load_saved_bytes(self, _reference):
                pytest.fail("replay fixture has no external saved bytes")

        replay_plan = plan(
            source,
            attempt=AttemptIdentity("replay"),
            mode=PreparationMode.REPLAY,
            replay_result=selection_ref,
            replay_selection=selection.selection,
            parser_profiles=live_plan.parser_profiles,
        )
        replay = await PreparationHandler(
            store, cast(CollectedSourceReader, ReplayReader()), replay_plan
        ).run(_request("replay", source))
        replay_signatures = await _semantic_signatures(store, replay.result_refs)
        if replay_signatures != live_signatures:
            pytest.fail("exact replay changed A2 semantic versions")
        prepared_ref = next(ref for ref in replay.result_refs if ref.kind == "prepared")
        await _check_derived_lineage(store, prepared_ref)
        prepared = await _saved(store, prepared_ref)
        if selection_ref not in prepared.input_refs:
            pytest.fail("replay prepared result lost the exact saved selection ref")
        await store.close()

    asyncio.run(exercise())
