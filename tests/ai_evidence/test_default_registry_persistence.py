"""Replay exact AI evidence through the production persistence registries."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from msgloom.ai import AnalysisResponse, AttemptStatus, TraceEvent, TraceKind
from msgloom.ai_evidence import EvidenceSession, TerminalEvidence, TraceEvidence
from msgloom.contracts import ExecutionIdentity, ResultRef
from msgloom.persistence import Phase1Persistence
from msgloom.working_context import (
    CaptureTimePolicy,
    StalePolicy,
    WorkingContextConfig,
    capture,
    snapshot_ref,
)
from tests.prepared_contract_fixtures import (
    phase1_url,
    prepared_record,
    prepared_result,
)

from .helpers import analysis_attempt, trusted_policy


def test_default_evidence_registries_replay_real_saved_inputs(
    tmp_path: Path,
) -> None:
    """Request, trace, and terminal data remain exact after a store restart."""

    async def exercise() -> None:
        config = WorkingContextConfig(
            selected_files=(),
            allowed_roots=(str(tmp_path),),
            time_policy=CaptureTimePolicy(timezone="UTC"),
            stale_policy=StalePolicy.CAPTURE,
            stale_after_seconds=3600.0,
            max_files=1,
            max_bytes_per_file=1024,
            max_total_bytes=1024,
            max_capture_seconds=5.0,
        )
        context = await capture(config, datetime.now(ZoneInfo("UTC")))
        context_version = snapshot_ref(context)
        url = phase1_url(tmp_path / "phase1.sqlite3")
        store = await Phase1Persistence.open(url)
        record = prepared_record()
        try:
            prepared_data = store.semantic_reference(
                "prepared-data", "prepared", "1", record
            )
            prepared = prepared_result(prepared_data)
            await store.append_result_with_data(prepared, record)
            context_data = store.semantic_reference(
                "context-data", "working_context", "1", context
            )
            context_result = replace(
                prepared_result(context_data, result_id="context"),
                kind="working_context",
                source_versions=(),
                prepared_versions=(),
                working_context_version=context_version,
            )
            await store.append_result_with_data(context_result, context)
            request = replace(
                analysis_attempt(),
                input_refs=prepared.prepared_versions,
                context_ref=context_version,
            )
            session = await EvidenceSession.begin(
                store,
                ExecutionIdentity("execution-evidence-integration"),
                request,
                trusted_policy=trusted_policy(request),
                required_inputs=(
                    ResultRef(prepared.result_id, "prepared", "1"),
                    ResultRef(context_result.result_id, "working_context", "1"),
                ),
                configuration_version="configuration-evidence-v1",
                code_version="code-evidence-v1",
            )
            event = TraceEvent(
                request.attempt,
                0,
                TraceKind.ASSISTANT_TEXT,
                "synthetic-message",
                "Synthetic structured response follows.",
            )
            await session.trace_sink.write(event)
            response = AnalysisResponse(
                request.attempt,
                AttemptStatus.COMPLETE,
                {"result": "synthetic"},
                1,
            )
            terminal_ref = await session.finish(response)
            expected = (
                (session.request_ref, session.request),
                (session.trace_refs[0], TraceEvidence(session.request_ref, event)),
                (
                    terminal_ref,
                    TerminalEvidence(
                        session.request_ref, session.trace_refs, response, True
                    ),
                ),
            )
        finally:
            await store.close()

        reopened = await Phase1Persistence.open(url)
        try:
            for reference, value in expected:
                saved = await reopened.get_result(reference.result_id)
                if saved is None or saved.semantic_data_ref is None:
                    pytest.fail("default registry lost durable AI evidence")
                replay = await reopened.load_semantic_data(saved.semantic_data_ref)
                if replay != value:
                    pytest.fail("AI evidence changed through production restart")
                if saved.working_context_version != context_version:
                    pytest.fail("AI evidence lost the exact working context")
                if saved.prepared_versions != prepared.prepared_versions:
                    pytest.fail("AI evidence lost exact prepared input versions")
        finally:
            await reopened.close()

    asyncio.run(exercise())
