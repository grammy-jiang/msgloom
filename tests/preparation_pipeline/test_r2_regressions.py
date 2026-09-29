"""R2 regressions for strict admission, lineage identity, and claim fencing."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ExecutionIdentity,
    ExternalEffectState,
    TerminalStatus,
)
from msgloom.preparation import DocumentFormat, ParserConfig, PreparedRecord
from msgloom.preparation_pipeline import PreparationHandler, PreparationMode
from msgloom.sources import CollectedSelection, CollectedSourceReader

from .helpers import open_store, plan, profiles
from .test_lifecycle import _fixture, _output, _request


def test_copied_plan_is_revalidated_before_reader_or_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Forged copied bounds and nested parser config fail before external work."""

    async def exercise() -> None:
        source, reader = _fixture()
        store = await open_store(tmp_path / "strict-plan.sqlite3")
        reads = 0

        original_read = reader.read_selection

        async def counted_read(reference):
            nonlocal reads
            reads += 1
            return await original_read(reference)

        monkeypatch.setattr(reader, "read_selection", counted_read)
        base = plan(
            source,
            attempt=AttemptIdentity("strict-attempt"),
            parser_profiles=profiles(DocumentFormat.TEXT, DocumentFormat.JSON),
        )
        zero = base.model_copy(update={"max_records": 0})
        outcome = await PreparationHandler(
            store, cast(CollectedSourceReader, reader), zero
        ).run(_request("strict-zero", source))
        if outcome.status is not TerminalStatus.BLOCKED or outcome.result_refs:
            pytest.fail("copied invalid bound crossed the public boundary")

        bad_config = ParserConfig("valid")
        object.__setattr__(bad_config, "profile", "")
        forged_profile = base.parser_profiles[0].model_copy(
            update={"config": bad_config}
        )
        nested = base.model_copy(
            update={"parser_profiles": (forged_profile, *base.parser_profiles[1:])}
        )
        outcome = await PreparationHandler(
            store, cast(CollectedSourceReader, reader), nested
        ).run(_request("strict-nested", source))
        if outcome.status is not TerminalStatus.BLOCKED or outcome.result_refs:
            pytest.fail("forged nested parser config crossed the public boundary")
        if reads:
            pytest.fail("invalid trusted plans reached the source reader")
        await store.close()

    asyncio.run(exercise())


def test_parser_profile_changes_identity_and_prepared_lineage_survives_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Changed parser semantics create new refs while old durable refs remain."""

    async def exercise() -> None:
        source, reader = _fixture()
        path = tmp_path / "lineage.sqlite3"
        store = await open_store(path)

        async def parser(request, _content):
            return _output(request)

        monkeypatch.setattr(
            "msgloom.preparation_pipeline.record_steps.parse_isolated", parser
        )
        base = plan(
            source,
            attempt=AttemptIdentity("lineage-attempt"),
            parser_profiles=profiles(DocumentFormat.TEXT, DocumentFormat.JSON),
        )
        first = await PreparationHandler(
            store, cast(CollectedSourceReader, reader), base
        ).run(_request("lineage-execution", source))
        first_prepared_ref = next(
            ref for ref in first.result_refs if ref.kind == "prepared"
        )
        first_result = await store.get_result(first_prepared_ref.result_id)
        if first_result is None:
            pytest.fail("first prepared result was not durable")
        if first_result.semantic_data_ref is None:
            pytest.fail("first prepared result omitted semantic data")
        first_value = await store.load_semantic_data(first_result.semantic_data_ref)
        if not isinstance(first_value, PreparedRecord):
            pytest.fail("first prepared semantic data has wrong type")
        if first_result.prepared_versions[0].kind != "prepared":
            pytest.fail("prepared lineage still points at original source")
        if not any(ref.kind == "derived_bytes" for ref in first_result.input_refs):
            pytest.fail("prepared lineage omitted derived parser input")

        changed_profiles = tuple(
            item.model_copy(
                update={
                    "config": replace(item.config, profile=item.config.profile + "-r2")
                }
            )
            for item in base.parser_profiles
        )
        changed = base.model_copy(update={"parser_profiles": changed_profiles})
        second = await PreparationHandler(
            store, cast(CollectedSourceReader, reader), changed
        ).run(_request("lineage-execution", source))
        second_ref = next(ref for ref in second.result_refs if ref.kind == "prepared")
        if second_ref == first_prepared_ref:
            pytest.fail("changed parser profile reused prepared result identity")
        second_result = await store.get_result(second_ref.result_id)
        if second_result is None or second_result.semantic_data_ref is None:
            pytest.fail("second prepared result omitted semantic data")
        second_value = await store.load_semantic_data(second_result.semantic_data_ref)
        if not isinstance(second_value, PreparedRecord):
            pytest.fail("second prepared semantic data has wrong type")
        if (
            first_value.parsed_contents[0].reference
            == second_value.parsed_contents[0].reference
        ):
            pytest.fail("changed parser profile reused parsed semantic identity")
        await store.close()

        reopened = await open_store(path)
        old = await reopened.get_result(first_prepared_ref.result_id)
        if old is None:
            pytest.fail("restart lost historical prepared result")
        if old.semantic_data_ref is None:
            pytest.fail("historical prepared result omitted semantic data")
        await reopened.load_semantic_data(old.semantic_data_ref)
        await reopened.close()

    asyncio.run(exercise())


def test_reclaimed_claim_fences_late_parser_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A parser completing after lease replacement cannot publish semantics."""

    async def exercise() -> None:
        source, reader = _fixture()
        path = tmp_path / "stale.sqlite3"
        first_store = await open_store(path)
        second_store = await open_store(path)
        cancelled = asyncio.Event()
        release = asyncio.Event()

        async def stubborn_parser(request, _content):
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.set()
                await release.wait()
                return _output(request)

        monkeypatch.setattr(
            "msgloom.preparation_pipeline.record_steps.parse_isolated",
            stubborn_parser,
        )
        work = plan(
            source,
            attempt=AttemptIdentity("stale-first"),
            parser_profiles=profiles(DocumentFormat.TEXT, DocumentFormat.JSON),
            timeout=0.5,
        ).model_copy(update={"claim_lease_seconds": 1.6})
        handler = PreparationHandler(
            first_store, cast(CollectedSourceReader, reader), work
        )
        task = asyncio.create_task(handler.run(_request("stale-execution", source)))
        await asyncio.wait_for(cancelled.wait(), timeout=1.0)
        await asyncio.sleep(1.7)

        replacement = await second_store.acquire_claim(
            handler._claim_key(),
            ClaimKind.PREPARE,
            ExecutionIdentity("replacement-execution"),
            AttemptIdentity("replacement-attempt"),
            lease_seconds=2.0,
        )
        release.set()
        outcome = await asyncio.wait_for(task, timeout=2.0)
        if outcome.status is TerminalStatus.COMPLETE:
            pytest.fail("reclaimed stale owner reported complete")
        if not any(
            item.code == "preparation-claim-lost" for item in outcome.limitations
        ):
            pytest.fail("stale owner did not report lost claim ownership")
        if any(ref.kind == "prepared" for ref in outcome.result_refs):
            pytest.fail("stale owner published prepared semantics after reclaim")
        await second_store.finish_claim(
            replacement, TerminalStatus.CANCELLED, ExternalEffectState.NONE
        )
        await first_store.close()
        await second_store.close()

    asyncio.run(exercise())


def test_replay_budget_rejects_before_semantic_load_and_profile_replay_changes_ref(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Replay metadata bounds precede loads; changed profiles retain new identity."""

    async def exercise() -> None:
        source, reader = _fixture()
        store = await open_store(tmp_path / "replay-bound.sqlite3")

        async def parser(request, _content):
            return _output(request)

        monkeypatch.setattr(
            "msgloom.preparation_pipeline.record_steps.parse_isolated", parser
        )
        base = plan(
            source,
            attempt=AttemptIdentity("replay-base"),
            parser_profiles=profiles(DocumentFormat.TEXT, DocumentFormat.JSON),
        )
        first = await PreparationHandler(
            store, cast(CollectedSourceReader, reader), base
        ).run(_request("replay-base-execution", source))
        selection_ref = next(
            ref for ref in first.result_refs if ref.kind == "collected_selection"
        )
        selection_result = await store.get_result(selection_ref.result_id)
        if selection_result is None or selection_result.semantic_data_ref is None:
            pytest.fail("captured selection omitted semantic data")
        selection = await store.load_semantic_data(selection_result.semantic_data_ref)
        if not isinstance(selection, CollectedSelection):
            pytest.fail("captured selection semantic type is invalid")

        replay = plan(
            source,
            attempt=AttemptIdentity("replay-bounded"),
            mode=PreparationMode.REPLAY,
            replay_result=selection_ref,
            replay_selection=selection.selection,
            parser_profiles=base.parser_profiles,
        ).model_copy(update={"max_total_selected_bytes": 1})
        loads = 0
        original_load = store.load_semantic_data

        async def counted_load(reference):
            nonlocal loads
            loads += 1
            return await original_load(reference)

        monkeypatch.setattr(store, "load_semantic_data", counted_load)
        bounded = await PreparationHandler(
            store, cast(CollectedSourceReader, reader), replay
        ).run(_request("replay-bounded-execution", source))
        if bounded.status is not TerminalStatus.BLOCKED or loads != 0:
            pytest.fail("replay aggregate budget was checked after semantic loading")
        monkeypatch.setattr(store, "load_semantic_data", original_load)

        changed_profiles = tuple(
            item.model_copy(
                update={
                    "config": replace(item.config, profile=item.config.profile + "-r")
                }
            )
            for item in base.parser_profiles
        )
        changed = plan(
            source,
            attempt=AttemptIdentity("replay-changed"),
            mode=PreparationMode.REPLAY,
            replay_result=selection_ref,
            replay_selection=selection.selection,
            parser_profiles=changed_profiles,
        )
        replayed = await PreparationHandler(
            store, cast(CollectedSourceReader, reader), changed
        ).run(_request("replay-changed-execution", source))
        first_ref = next(ref for ref in first.result_refs if ref.kind == "prepared")
        replayed_ref = next(
            ref for ref in replayed.result_refs if ref.kind == "prepared"
        )
        first_result = await store.get_result(first_ref.result_id)
        replayed_result = await store.get_result(replayed_ref.result_id)
        if (
            first_result is None
            or replayed_result is None
            or first_result.semantic_data_ref is None
            or replayed_result.semantic_data_ref is None
        ):
            pytest.fail("prepared replay result is missing")
        first_value = await store.load_semantic_data(first_result.semantic_data_ref)
        replayed_value = await store.load_semantic_data(
            replayed_result.semantic_data_ref
        )
        if not isinstance(first_value, PreparedRecord) or not isinstance(
            replayed_value, PreparedRecord
        ):
            pytest.fail("prepared replay semantic type is invalid")
        if (
            first_value.parsed_contents[0].reference
            == replayed_value.parsed_contents[0].reference
        ):
            pytest.fail("changed-profile replay reused parsed identity")
        await store.close()

    asyncio.run(exercise())
