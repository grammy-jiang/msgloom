"""Check default delivery composition across restart and import order."""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

import pytest

from msgloom.contracts import ExternalEffectState, TerminalStatus
from msgloom.persistence import Phase1Persistence
from tests.delivery.helpers import (
    RecordingTransport,
    build_report,
    submission_handler,
    submission_plan,
    submission_request,
)

ROOT = Path(__file__).resolve().parents[2]


def test_default_registry_reloads_submission_evidence(tmp_path: Path) -> None:
    """Production registries save and reload exact attempt and receipt data."""

    async def exercise() -> None:
        url = f"sqlite:///{tmp_path / 'default-delivery.db'}"
        store = await Phase1Persistence.open(url)
        values: dict[str, tuple[object, object]] = {}
        try:
            report_ref, report = await build_report(store)
            plan = submission_plan(report_ref, report)
            outcome = await submission_handler(store, plan, RecordingTransport()).run(
                submission_request(plan)
            )
            if (
                outcome.status is not TerminalStatus.COMPLETE
                or outcome.external_effect is not ExternalEffectState.ACCEPTED
            ):
                pytest.fail(f"default delivery composition failed: {outcome}")
            for part in plan.parts:
                for identity in (part.attempt_result_id, part.receipt_result_id):
                    result = await store.get_result(identity)
                    if result is None or result.semantic_data_ref is None:
                        pytest.fail("default delivery result lacks semantic data")
                    values[identity] = (
                        result,
                        await store.load_semantic_data(result.semantic_data_ref),
                    )
        finally:
            await store.close()
        reopened = await Phase1Persistence.open(url)
        try:
            for identity, (expected, value) in values.items():
                result = await reopened.get_result(identity)
                if result is None or result != expected:
                    pytest.fail("restart changed a saved delivery result")
                if result.semantic_data_ref is None:
                    pytest.fail("restart lost a delivery semantic reference")
                actual = await reopened.load_semantic_data(result.semantic_data_ref)
                if actual != value:
                    pytest.fail("restart changed saved delivery evidence")
        finally:
            await reopened.close()

    asyncio.run(exercise())


@pytest.mark.parametrize("module", ["msgloom.persistence", "msgloom.delivery"])
def test_fresh_interpreter_imports_without_cycle(module: str) -> None:
    """Default codec registration does not create an import cycle."""
    result = subprocess.run(
        [sys.executable, "-c", f"import {module}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(f"fresh import of {module} failed: {result.stderr[-500:]}")
