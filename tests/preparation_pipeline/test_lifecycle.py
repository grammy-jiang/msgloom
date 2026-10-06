"""Claim, ordering, timeout, and cancellation lifecycle tests."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest

from msgloom.contracts import (
    AttemptIdentity,
    ExecutionIdentity,
    OperationRequest,
    PhaseCapability,
    TerminalStatus,
    VersionRef,
)
from msgloom.preparation import (
    BlockRole,
    DocumentFormat,
    DocumentLocation,
    NativeRelationship,
    ParserOutput,
    ParserProvenance,
    PreparedSourceType,
    TextBlock,
)
from msgloom.preparation_pipeline import PreparationHandler
from msgloom.sources import (
    CollectedBody,
    CollectedRecord,
    CollectedSourceReader,
    ContentKind,
)
from msgloom.sources._snapshot import capture_selection

from .helpers import open_store, plan, profiles
from .timeout_support import HandlerDeadlineControl


def _fixture():
    source = VersionRef("outlook_message", "synthetic-message", "v1")
    scope = VersionRef("source_scope", "synthetic-mailbox", "v1")
    record = CollectedRecord(
        source=source,
        source_scope=scope,
        source_type=PreparedSourceType.OUTLOOK_EMAIL,
        semantic_identity="outlook:synthetic",
        observed_at=datetime(2026, 9, 29, tzinfo=UTC),
        source_time=datetime(2026, 9, 29, tzinfo=UTC),
        subject="Synthetic subject",
        sender=None,
        author=None,
        recipients=(),
        source_content_kind=ContentKind.JSON,
        source_bytes=None,
        body=CollectedBody(
            kind=ContentKind.PLAIN,
            content="Synthetic body",
            saved_bytes=None,
            location=DocumentLocation(part="graph-json"),
        ),
        alternate_bodies=(),
        attachments=(),
        relationships=(NativeRelationship(kind="source_scope", target=scope),),
        metadata=(),
        source_locations=(DocumentLocation(part="graph-json"),),
        limitations=(),
    )
    selection = capture_selection(record)

    class Reader:
        async def read_selection(self, requested):
            if requested != source:
                pytest.fail("unexpected source")
            return selection

        async def load_saved_bytes(self, _reference):
            pytest.fail("fixture has no attachment bytes")

    return source, Reader()


def _request(execution: str, source) -> OperationRequest:
    return OperationRequest(
        execution=ExecutionIdentity(execution),
        caller="test",
        capability=PhaseCapability.PREPARE,
        target_inputs=(source,),
    )


def _output(request) -> ParserOutput:
    return ParserOutput(
        provenance=ParserProvenance.from_request(request),
        blocks=(
            TextBlock(
                order=0,
                role=BlockRole.TEXT,
                text="Synthetic parsed text",
                location=DocumentLocation(part="text", block_index=0),
            ),
        ),
    )


def test_selection_write_precedes_parser_and_duplicate_claim_is_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Parser cannot start before selection durability; duplicate work blocks.
    """

    async def exercise() -> None:
        source, reader = _fixture()
        store = await open_store(tmp_path / "ordering.sqlite3")
        selected_saved = False
        entered = asyncio.Event()
        release = asyncio.Event()
        original = store.append_result_with_data

        async def tracked(result, value, **kwargs):
            nonlocal selected_saved
            await original(result, value, **kwargs)
            if result.kind == "collected_selection":
                selected_saved = True

        async def blocked_parser(request, _content):
            if not selected_saved:
                pytest.fail("parser started before captured selection was durable")
            entered.set()
            await release.wait()
            return _output(request)

        monkeypatch.setattr(store, "append_result_with_data", tracked)
        monkeypatch.setattr(
            "msgloom.preparation_pipeline.record_steps.parse_isolated",
            blocked_parser,
        )
        work_plan = plan(
            source,
            attempt=AttemptIdentity("ordering-attempt"),
            parser_profiles=profiles(DocumentFormat.TEXT, DocumentFormat.JSON),
        )
        first = PreparationHandler(
            store, cast(CollectedSourceReader, reader), work_plan
        )
        second_plan = work_plan.model_copy(
            update={"attempt": AttemptIdentity("ordering-second-attempt")}
        )
        second = PreparationHandler(
            store, cast(CollectedSourceReader, reader), second_plan
        )
        task = asyncio.create_task(first.run(_request("ordering-first", source)))
        await entered.wait()
        duplicate = await second.run(_request("ordering-second", source))
        if duplicate.status is not TerminalStatus.BLOCKED:
            pytest.fail("duplicate durable claim was not blocked")
        release.set()
        first_outcome = await task
        if first_outcome.status is not TerminalStatus.COMPLETE:
            pytest.fail("first durable owner did not complete")
        await store.close()

    asyncio.run(exercise())


def test_repeated_cancellation_drains_claim_and_restart_can_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cancellation drains accepted work and releases the owned claim."""

    async def exercise() -> None:
        source, reader = _fixture()
        store = await open_store(tmp_path / "cancel.sqlite3")
        entered = asyncio.Event()
        parser_cancelled = asyncio.Event()

        async def waiting_parser(_request, _content):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                parser_cancelled.set()

        monkeypatch.setattr(
            "msgloom.preparation_pipeline.record_steps.parse_isolated",
            waiting_parser,
        )
        work_plan = plan(
            source,
            attempt=AttemptIdentity("cancel-attempt"),
            parser_profiles=profiles(DocumentFormat.TEXT, DocumentFormat.JSON),
        )
        handler = PreparationHandler(
            store, cast(CollectedSourceReader, reader), work_plan
        )
        task = asyncio.create_task(handler.run(_request("cancel-first", source)))
        await entered.wait()
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        if not parser_cancelled.is_set():
            pytest.fail("accepted parser work did not observe cancellation")

        async def fast_parser(request, _content):
            return _output(request)

        monkeypatch.setattr(
            "msgloom.preparation_pipeline.record_steps.parse_isolated",
            fast_parser,
        )
        restarted = await handler.run(_request("cancel-restart", source))
        if restarted.status is not TerminalStatus.COMPLETE:
            pytest.fail("finished cancelled claim prevented restart")
        await store.close()

    asyncio.run(exercise())


def test_execution_timeout_retains_partial_results_without_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Timeout keeps evidence writes but cannot publish prepared success."""

    async def exercise() -> None:
        source, reader = _fixture()
        store = await open_store(tmp_path / "timeout.sqlite3")
        entered = asyncio.Event()
        parser_cancelled = asyncio.Event()

        async def waiting_parser(_request, _content):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                parser_cancelled.set()

        monkeypatch.setattr(
            "msgloom.preparation_pipeline.record_steps.parse_isolated",
            waiting_parser,
        )
        work_plan = plan(
            source,
            attempt=AttemptIdentity("timeout-attempt"),
            parser_profiles=profiles(DocumentFormat.TEXT, DocumentFormat.JSON),
            timeout=0.05,
        )
        handler = PreparationHandler(
            store, cast(CollectedSourceReader, reader), work_plan
        )
        control = HandlerDeadlineControl(entered)
        # Arm the same real asyncio deadline at parser entry so this test owns
        # parser cancellation, not variable SQLite/thread startup latency.
        with control.installed():
            outcome = await asyncio.wait_for(
                handler.run(_request("timeout-execution", source)),
                timeout=3.0,
            )
        if outcome.status is not TerminalStatus.INCOMPLETE:
            pytest.fail("execution timeout did not report incomplete operation")
        kinds = {ref.kind for ref in outcome.result_refs}
        if "collected_selection" not in kinds or "derived_bytes" not in kinds:
            pytest.fail("timeout discarded already durable evidence")
        if "prepared" in kinds:
            pytest.fail("timeout published prepared success after parser deadline")
        if not entered.is_set() or not parser_cancelled.is_set():
            pytest.fail("execution timeout did not cancel the active parser")
        if control.arm_count != 1 or control.active_watchers:
            pytest.fail("parser deadline control did not arm and clean up exactly once")
        await store.close()

    asyncio.run(exercise())


def test_parse_failure_is_visible_and_downstream_partial_results_survive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Opaque parser failure becomes a limitation, not fabricated empty success.
    """

    async def exercise() -> None:
        source, reader = _fixture()
        store = await open_store(tmp_path / "parse-failure.sqlite3")

        async def failing_parser(_request, _content):
            raise RuntimeError("synthetic private parser detail")

        monkeypatch.setattr(
            "msgloom.preparation_pipeline.record_steps.parse_isolated",
            failing_parser,
        )
        handler = PreparationHandler(
            store,
            cast(CollectedSourceReader, reader),
            plan(
                source,
                attempt=AttemptIdentity("parse-failure-attempt"),
                parser_profiles=profiles(DocumentFormat.TEXT, DocumentFormat.JSON),
            ),
        )
        outcome = await handler.run(_request("parse-failure-execution", source))
        if outcome.status is not TerminalStatus.INCOMPLETE:
            pytest.fail("parse failure was not reported as incomplete")
        if not any(item.code == "content-parse-failed" for item in outcome.limitations):
            pytest.fail("parse failure limitation is missing")
        kinds = {ref.kind for ref in outcome.result_refs}
        if not {"prepared", "filter_result", "group_result"} <= kinds:
            pytest.fail("partial prepared/filter/group results were not retained")
        if any(
            "synthetic private parser detail" in item.detail
            for item in outcome.limitations
        ):
            pytest.fail("private parser exception leaked into public limitation")
        await store.close()

    asyncio.run(exercise())


def test_failed_write_finishes_claim_and_restart_is_independent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    A failed prepared write leaves evidence durable and releases safe claim.
    """

    async def exercise() -> None:
        source, reader = _fixture()
        store = await open_store(tmp_path / "write-failure.sqlite3")

        async def fast_parser(request, _content):
            return _output(request)

        monkeypatch.setattr(
            "msgloom.preparation_pipeline.record_steps.parse_isolated",
            fast_parser,
        )
        original = store.append_result_with_data
        failed_once = False

        async def failing_write(result, value, **kwargs):
            nonlocal failed_once
            if result.kind == "prepared" and not failed_once:
                failed_once = True
                raise RuntimeError("synthetic storage failure")
            await original(result, value, **kwargs)

        monkeypatch.setattr(store, "append_result_with_data", failing_write)
        handler = PreparationHandler(
            store,
            cast(CollectedSourceReader, reader),
            plan(
                source,
                attempt=AttemptIdentity("write-failure-attempt"),
                parser_profiles=profiles(DocumentFormat.TEXT, DocumentFormat.JSON),
            ),
        )
        failed = await handler.run(_request("write-failure-first", source))
        if failed.status is not TerminalStatus.FAILED:
            pytest.fail("failed durable write did not fail the operation")
        kinds = {ref.kind for ref in failed.result_refs}
        if "collected_selection" not in kinds or "derived_bytes" not in kinds:
            pytest.fail("failed write discarded earlier durable evidence")
        if "prepared" in kinds:
            pytest.fail("failed prepared write was reported as durable")

        monkeypatch.setattr(store, "append_result_with_data", original)
        restarted = await handler.run(_request("write-failure-restart", source))
        if restarted.status is not TerminalStatus.COMPLETE:
            pytest.fail("failed write left durable claim stuck")
        if any(
            old.result_id == new.result_id
            for old in failed.result_refs
            for new in restarted.result_refs
        ):
            pytest.fail("restart reused result identity from failed execution")
        await store.close()

    asyncio.run(exercise())
