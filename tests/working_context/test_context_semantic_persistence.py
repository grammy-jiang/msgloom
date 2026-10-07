"""Verify context capture remains exact across the production data boundary."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

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
from msgloom.working_context import (
    CaptureTimePolicy,
    FileCaptureState,
    MemoryFileSelection,
    StalePolicy,
    WorkingContextConfig,
    WorkingContextSnapshot,
    capture,
    snapshot_ref,
)
from tests.prepared_contract_fixtures import phase1_url, prepared_result


def test_empty_and_missing_context_survive_saved_dependency_restart(
    tmp_path: Path,
) -> None:
    """A dependent claim must see the saved capture, including unavailable data."""
    empty = tmp_path / "selected-empty.txt"
    empty.write_text("", encoding="utf-8")
    missing = tmp_path / "selected-missing.txt"
    config = WorkingContextConfig(
        selected_files=(
            MemoryFileSelection(selection_id="empty", path=str(empty)),
            MemoryFileSelection(selection_id="missing", path=str(missing)),
        ),
        allowed_roots=(str(tmp_path),),
        time_policy=CaptureTimePolicy(timezone="UTC"),
        stale_policy=StalePolicy.CAPTURE,
        stale_after_seconds=3600.0,
        max_files=2,
        max_bytes_per_file=1024,
        max_total_bytes=2048,
        max_capture_seconds=5.0,
    )

    async def exercise() -> None:
        snapshot = await capture(config, datetime.now(ZoneInfo("UTC")))
        context_version = snapshot_ref(snapshot)
        url = phase1_url(tmp_path / "phase1.sqlite3")
        store = await Phase1Persistence.open(url)
        try:
            data_ref = store.semantic_reference(
                "data-context", "working_context", "1", snapshot
            )
            result = replace(
                prepared_result(data_ref, result_id="result-context"),
                kind="working_context",
                source_versions=(),
                prepared_versions=(),
                configuration_version=snapshot.configuration_ref.version,
                rule_version=None,
                working_context_version=context_version,
            )
            await store.append_result_with_data(result, snapshot)
        finally:
            await store.close()

        reopened = await Phase1Persistence.open(url)
        try:
            result = await reopened.get_result("result-context")
            if result is None or result.semantic_data_ref is None:
                pytest.fail("saved context result or semantic reference is missing")
            actual = await reopened.load_semantic_data(result.semantic_data_ref)
            if not isinstance(actual, WorkingContextSnapshot):
                pytest.fail("saved context did not decode to its closed schema")
            if actual != snapshot or snapshot_ref(actual) != context_version:
                pytest.fail("saved context changed its exact data or version")
            if actual.files[0].state is not FileCaptureState.EMPTY:
                pytest.fail("selected empty file lost its distinct capture state")
            if actual.files[1].state is not FileCaptureState.MISSING:
                pytest.fail("missing selection lost its explicit unavailable state")
            if actual.files[0].text != "" or actual.files[1].text is not None:
                pytest.fail("empty content and unavailable content were conflated")
            token = await reopened.acquire_claim(
                "triage:context-restart",
                ClaimKind.TRIAGE,
                ExecutionIdentity("execution-context-consumer"),
                AttemptIdentity("attempt-context-consumer"),
                required_inputs=(ResultRef("result-context", "working_context", "1"),),
            )
            await reopened.finish_claim(
                token, TerminalStatus.COMPLETE, ExternalEffectState.NONE
            )
        finally:
            await reopened.close()

    asyncio.run(exercise())
