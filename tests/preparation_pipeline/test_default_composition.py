"""Check registered A2 production composition and per-content rejection."""

import asyncio
from pathlib import Path
from typing import cast

import pytest

from msgloom.contracts import AttemptIdentity, TerminalStatus
from msgloom.persistence import Phase1Persistence
from msgloom.preparation import DocumentFormat, PreparedRecord
from msgloom.preparation_pipeline import PreparationHandler
from msgloom.sources import CollectedSourceReader

from .helpers import plan, profiles
from .test_lifecycle import _fixture, _output, _request


def test_default_registry_retains_exact_produced_chain_after_restart(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        source, reader = _fixture()
        url = f"sqlite:///{tmp_path / 'default.sqlite3'}"
        store = await Phase1Persistence.open(url)
        work = plan(
            source,
            attempt=AttemptIdentity("default-prepare"),
            parser_profiles=profiles(DocumentFormat.TEXT, DocumentFormat.JSON),
        )
        try:
            outcome = await PreparationHandler(
                store, cast(CollectedSourceReader, reader), work
            ).run(_request("default-execution", source))
            values = {}
            for ref in outcome.result_refs:
                result = await store.get_result(ref.result_id)
                if result is None or result.semantic_data_ref is None:
                    pytest.fail("Produced A2 result has no durable semantic data")
                values[ref] = (
                    result,
                    await store.load_semantic_data(result.semantic_data_ref),
                )
            kinds = {ref.kind for ref in values}
            if kinds != {
                "collected_selection",
                "derived_bytes",
                "prepared",
                "filter_result",
                "group_result",
            }:
                pytest.fail("Default registry did not produce the full A2 chain")
        finally:
            await store.close()
        reopened = await Phase1Persistence.open(url)
        try:
            for ref, (expected, value) in values.items():
                saved = await reopened.get_result(ref.result_id)
                if saved != expected or saved is None:
                    pytest.fail("Restart changed an exact A2 result")
                if saved.semantic_data_ref is None:
                    pytest.fail("Restart lost semantic lineage")
                if await reopened.load_semantic_data(saved.semantic_data_ref) != value:
                    pytest.fail("Restart changed the saved A2 semantic product")
        finally:
            await reopened.close()

    asyncio.run(exercise())


def test_rejected_content_retains_record_and_other_parser_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def exercise() -> None:
        source, reader = _fixture()
        store = await Phase1Persistence.open(f"sqlite:///{tmp_path / 'partial.db'}")

        async def parse(request, _content):
            if request.detected_format is DocumentFormat.TEXT:
                raise ValueError("synthetic invalid source representation")
            return _output(request)

        monkeypatch.setattr(
            "msgloom.preparation_pipeline.record_steps.parse_isolated", parse
        )
        work = plan(
            source,
            attempt=AttemptIdentity("partial-prepare"),
            parser_profiles=profiles(DocumentFormat.TEXT, DocumentFormat.JSON),
        )
        try:
            outcome = await PreparationHandler(
                store, cast(CollectedSourceReader, reader), work
            ).run(_request("partial-execution", source))
            if outcome.status is not TerminalStatus.INCOMPLETE:
                pytest.fail("Content rejection discarded the whole prepared record")
            ref = next(ref for ref in outcome.result_refs if ref.kind == "prepared")
            saved = await store.get_result(ref.result_id)
            if saved is None or saved.semantic_data_ref is None:
                pytest.fail("Partial prepared record was not durable")
            value = await store.load_semantic_data(saved.semantic_data_ref)
            if not isinstance(value, PreparedRecord) or not value.parsed_contents:
                pytest.fail("Unrelated metadata parsing was lost")
            if not any(x.code == "content-parse-failed" for x in value.limitations):
                pytest.fail("Content rejection lacks an explicit limitation")
        finally:
            await store.close()

    asyncio.run(exercise())
