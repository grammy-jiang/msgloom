"""Verify saved triage inputs retain exact parts across a durable restart."""

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
from msgloom.triage_input import (
    TriageInputSnapshot,
    build_triage_input,
    saved_part_payloads,
)
from msgloom.working_context import (
    CaptureTimePolicy,
    StalePolicy,
    WorkingContextConfig,
    capture,
    snapshot_ref,
)
from tests.prepared_contract_fixtures import phase1_url, prepared_result
from tests.triage_input.helpers import config, record, selection


def test_saved_input_parts_and_dependencies_survive_restart(tmp_path: Path) -> None:
    """Reload exact parts only after all selected semantic inputs are durable."""

    async def exercise() -> None:
        context = await capture(
            WorkingContextConfig(
                selected_files=(),
                allowed_roots=(str(tmp_path),),
                time_policy=CaptureTimePolicy(timezone="UTC"),
                stale_policy=StalePolicy.CAPTURE,
                stale_after_seconds=3600.0,
                max_files=1,
                max_bytes_per_file=1024,
                max_total_bytes=1024,
                max_capture_seconds=5.0,
            ),
            datetime(2026, 1, 1, tzinfo=ZoneInfo("UTC")),
        )
        chosen = selection((record("saved-synthetic-input"),)).model_copy(
            update={"working_context_ref": snapshot_ref(context)}
        )
        snapshot = build_triage_input(chosen, config())
        original_parts = saved_part_payloads(snapshot)
        if not snapshot.complete or not original_parts:
            pytest.fail("synthetic input did not produce complete saved parts")
        url = phase1_url(tmp_path / "phase1.sqlite3")
        store = await Phase1Persistence.open(url)
        dependencies: list[ResultRef] = []
        try:
            for kind, bindings, field in (
                ("prepared", chosen.prepared, "record"),
                ("filter_result", chosen.filters, "result"),
                ("group_result", chosen.groups, "result"),
                ("triage_rules", (chosen.rules,), "evaluation"),
            ):
                for binding in bindings:
                    value = getattr(binding, field)
                    result = replace(
                        prepared_result(
                            binding.data_ref,
                            result_id=binding.result_ref.result_id,
                        ),
                        kind=kind,
                        input_refs=tuple(dependencies),
                        source_versions=tuple(
                            item.record.source for item in chosen.prepared
                        ),
                    )
                    await store.append_result_with_data(result, value)
                    dependencies.append(binding.result_ref)
            context_data = store.semantic_reference(
                "context-data", "working_context", "1", context
            )
            context_result = replace(
                prepared_result(context_data, result_id="context-result"),
                kind="working_context",
                source_versions=(),
                working_context_version=snapshot_ref(context),
            )
            await store.append_result_with_data(context_result, context)
            dependencies.append(ResultRef("context-result", "working_context", "1"))
            data_ref = store.semantic_reference(
                "triage-input-data", "triage_input", "1", snapshot
            )
            result = replace(
                prepared_result(data_ref, result_id="triage-input-result"),
                kind="triage_input",
                input_refs=tuple(dependencies),
                working_context_version=snapshot_ref(context),
                prompt_version=chosen.versions.prompt.version,
            )
            await store.append_result_with_data(result, snapshot)
        finally:
            await store.close()

        reopened = await Phase1Persistence.open(url)
        try:
            result = await reopened.get_result("triage-input-result")
            if result is None or result.semantic_data_ref is None:
                pytest.fail("saved triage input reference is missing")
            saved = await reopened.load_semantic_data(result.semantic_data_ref)
            if not isinstance(saved, TriageInputSnapshot) or saved != snapshot:
                pytest.fail("closed saved snapshot changed across restart")
            if saved_part_payloads(saved) != original_parts:
                pytest.fail("saved input part bytes or references changed on restart")
            if result.input_refs != tuple(dependencies):
                pytest.fail("saved triage input lost exact dependency references")
            token = await reopened.acquire_claim(
                "triage:saved-input",
                ClaimKind.TRIAGE,
                ExecutionIdentity("input-consumer"),
                AttemptIdentity("input-consumer-attempt"),
                required_inputs=(ResultRef(result.result_id, "triage_input", "1"),),
            )
            await reopened.finish_claim(
                token, TerminalStatus.COMPLETE, ExternalEffectState.NONE
            )
        finally:
            await reopened.close()

    asyncio.run(exercise())
