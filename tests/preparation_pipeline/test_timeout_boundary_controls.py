"""Adversarial controls for preparation execution-timeout boundaries."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import cast

import pytest

from msgloom.contracts import AttemptIdentity, TerminalStatus
from msgloom.preparation import DocumentFormat
from msgloom.preparation_pipeline import PreparationHandler
from msgloom.sources import CollectedSourceReader

from .helpers import open_store, plan, profiles
from .test_lifecycle import _fixture, _request
from .timeout_support import HandlerDeadlineControl


def test_parser_armed_timeout_cancels_active_parser_after_slow_setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Parser-bound timeout remains deterministic after slow durable setup."""

    async def exercise() -> None:
        source, reader = _fixture()
        store = await open_store(tmp_path / "parser-armed.sqlite3")
        entered = asyncio.Event()
        cancelled = asyncio.Event()
        original = store.append_result_with_data

        async def delayed_after_durable(result, value, **kwargs):
            await original(result, value, **kwargs)
            if result.kind == "derived_bytes":
                # The result is already durable here. Delay only the return to
                # model scheduler/persistence variance before parser entry.
                await asyncio.sleep(0.2)

        async def waiting_parser(_request, _content):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        monkeypatch.setattr(store, "append_result_with_data", delayed_after_durable)
        monkeypatch.setattr(
            "msgloom.preparation_pipeline.record_steps.parse_isolated",
            waiting_parser,
        )
        control = HandlerDeadlineControl(entered)
        handler = PreparationHandler(
            store,
            cast(CollectedSourceReader, reader),
            plan(
                source,
                attempt=AttemptIdentity("parser-armed-attempt"),
                parser_profiles=profiles(DocumentFormat.TEXT, DocumentFormat.JSON),
                timeout=0.05,
            ),
        )
        with control.installed():
            outcome = await asyncio.wait_for(
                handler.run(_request("parser-armed-execution", source)),
                timeout=3.0,
            )
        if outcome.status is not TerminalStatus.INCOMPLETE:
            pytest.fail("active parser timeout did not report incomplete operation")
        if not entered.is_set() or not cancelled.is_set():
            pytest.fail("execution deadline did not cancel an active parser")
        kinds = {ref.kind for ref in outcome.result_refs}
        if not {"collected_selection", "derived_bytes"} <= kinds:
            pytest.fail("parser timeout discarded durable setup evidence")
        if "prepared" in kinds:
            pytest.fail("parser timeout published prepared success")
        if not any(item.code == "preparation-timeout" for item in outcome.limitations):
            pytest.fail("active execution deadline did not propagate timeout")
        if control.arm_count != 1 or control.active_watchers:
            pytest.fail("parser deadline did not arm and clean up exactly once")
        await store.close()

    asyncio.run(exercise())


def test_parser_deadline_control_cleans_up_on_failure_before_parser(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pre-parser failure propagates while deadline control cleans up."""

    async def exercise() -> None:
        source, reader = _fixture()
        store = await open_store(tmp_path / "preparser-failure.sqlite3")
        entered = asyncio.Event()
        original = store.append_result_with_data

        async def failing_derived_write(result, value, **kwargs):
            if result.kind == "derived_bytes":
                raise RuntimeError("synthetic pre-parser write failure")
            await original(result, value, **kwargs)

        async def unexpected_parser(_request, _content):
            entered.set()
            pytest.fail("parser entered after injected pre-parser failure")

        monkeypatch.setattr(store, "append_result_with_data", failing_derived_write)
        monkeypatch.setattr(
            "msgloom.preparation_pipeline.record_steps.parse_isolated",
            unexpected_parser,
        )
        control = HandlerDeadlineControl(entered)
        handler = PreparationHandler(
            store,
            cast(CollectedSourceReader, reader),
            plan(
                source,
                attempt=AttemptIdentity("preparser-failure-attempt"),
                parser_profiles=profiles(DocumentFormat.TEXT, DocumentFormat.JSON),
                timeout=0.05,
            ),
        )
        with control.installed():
            outcome = await asyncio.wait_for(
                handler.run(_request("preparser-failure-execution", source)),
                timeout=3.0,
            )
        if outcome.status is not TerminalStatus.FAILED:
            pytest.fail("pre-parser write failure did not fail the operation")
        if entered.is_set():
            pytest.fail("parser entered despite failed durable setup")
        if not any(item.code == "preparation-failed" for item in outcome.failures):
            pytest.fail("pre-parser failure did not propagate through handler outcome")
        if control.arm_count != 0 or control.active_watchers:
            pytest.fail("pre-parser failure left an armed or live deadline watcher")
        await store.close()

    asyncio.run(exercise())


def test_real_execution_timeout_can_expire_before_parser_after_durable_setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Injected timeout expires after durable evidence before parsing."""

    async def exercise() -> None:
        source, reader = _fixture()
        store = await open_store(tmp_path / "preparser-timeout.sqlite3")
        durable = asyncio.Event()
        entered = asyncio.Event()
        post_durable_cancelled = asyncio.Event()
        original = store.append_result_with_data

        async def block_after_durable(result, value, **kwargs):
            await original(result, value, **kwargs)
            if result.kind == "derived_bytes":
                durable.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    post_durable_cancelled.set()

        async def unexpected_parser(_request, _content):
            entered.set()
            pytest.fail("parser entered after the pre-parser deadline")

        monkeypatch.setattr(store, "append_result_with_data", block_after_durable)
        monkeypatch.setattr(
            "msgloom.preparation_pipeline.record_steps.parse_isolated",
            unexpected_parser,
        )
        handler = PreparationHandler(
            store,
            cast(CollectedSourceReader, reader),
            plan(
                source,
                attempt=AttemptIdentity("preparser-timeout-attempt"),
                parser_profiles=profiles(DocumentFormat.TEXT, DocumentFormat.JSON),
                timeout=0.05,
            ),
        )
        control = HandlerDeadlineControl(durable)
        with control.installed():
            outcome = await asyncio.wait_for(
                handler.run(_request("preparser-timeout-execution", source)),
                timeout=3.0,
            )
        if outcome.status is not TerminalStatus.INCOMPLETE:
            pytest.fail("pre-parser execution timeout was not incomplete")
        kinds = {ref.kind for ref in outcome.result_refs}
        if not {"collected_selection", "derived_bytes"} <= kinds:
            pytest.fail("pre-parser timeout discarded durable evidence")
        if "prepared" in kinds or entered.is_set():
            pytest.fail("pre-parser timeout crossed the parser/success boundary")
        if not durable.is_set() or not post_durable_cancelled.is_set():
            pytest.fail("deadline did not propagate from the durable boundary")
        if not any(item.code == "preparation-timeout" for item in outcome.limitations):
            pytest.fail("pre-parser timeout limitation is missing")
        if control.arm_count != 1 or control.active_watchers:
            pytest.fail("durable-boundary deadline did not arm and clean up once")
        await store.close()

    asyncio.run(exercise())


def test_parser_deadline_control_restores_after_external_cancellation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """External cancellation restores the handler-local timeout dependency."""

    async def exercise() -> None:
        source, reader = _fixture()
        store = await open_store(tmp_path / "external-cancel.sqlite3")
        started = asyncio.Event()
        entered = asyncio.Event()
        original_read = reader.read_selection

        async def blocked_read(requested):
            started.set()
            await asyncio.Event().wait()
            return await original_read(requested)

        monkeypatch.setattr(reader, "read_selection", blocked_read)
        control = HandlerDeadlineControl(entered)
        handler = PreparationHandler(
            store,
            cast(CollectedSourceReader, reader),
            plan(
                source,
                attempt=AttemptIdentity("external-cancel-attempt"),
                parser_profiles=profiles(DocumentFormat.TEXT, DocumentFormat.JSON),
                timeout=1.0,
            ),
        )
        with control.installed():
            task = asyncio.create_task(
                handler.run(_request("external-cancel-execution", source))
            )
            await asyncio.wait_for(started.wait(), timeout=1.0)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(task, timeout=3.0)
        if entered.is_set() or control.arm_count != 0 or control.active_watchers:
            pytest.fail("external cancellation leaked parser deadline state")
        await store.close()

    asyncio.run(exercise())
