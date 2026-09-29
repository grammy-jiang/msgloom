"""Check default report composition and owned codec cancellation."""

import asyncio
from pathlib import Path
from threading import Event

import pytest

from msgloom.contracts import TerminalStatus
from msgloom.persistence import Phase1Persistence, StaleClaimError
from msgloom.reporting import SavedReport

from .helpers import plan, save_triage, topic, triage_data
from .test_handler import _handler, _request


def test_default_registry_reloads_selection_and_report(tmp_path: Path) -> None:
    """Production registry composition preserves both durable report products."""

    async def exercise() -> None:
        url = f"sqlite:///{tmp_path / 'default-report.db'}"
        store = await Phase1Persistence.open(url)
        try:
            triage_ref = await save_triage(store, triage_data(topic()))
            selection = plan(triage_ref)
            outcome = await _handler(store, selection).run(_request(selection))
            if outcome.status is not TerminalStatus.COMPLETE:
                pytest.fail("Default composition did not build a complete report")
            values = {}
            for identity in ("selection-report-result", "report-result"):
                result = await store.get_result(identity)
                if result is None or result.semantic_data_ref is None:
                    pytest.fail("Default report product lacks semantic evidence")
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
                if result != expected or result is None:
                    pytest.fail("Restart changed a default report result")
                if result.semantic_data_ref is None:
                    pytest.fail("Restart lost the report semantic reference")
                actual = await reopened.load_semantic_data(result.semantic_data_ref)
                if actual != value:
                    pytest.fail("Restart changed saved report output")
            if not isinstance(values["report-result"][1], SavedReport):
                pytest.fail("Default report codec returned the wrong product")
        finally:
            await reopened.close()

    asyncio.run(exercise())


@pytest.mark.parametrize("kind", ("report_selection", "report"))
def test_owned_codec_drains_and_stale_cleanup_preserves_cancellation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """A blocked codec permits cancellation and cannot outlive handler cleanup."""

    async def exercise() -> None:
        store = await Phase1Persistence.open(f"sqlite:///{tmp_path / 'cancel.db'}")
        triage_ref = await save_triage(store, triage_data(topic()))
        selection = plan(triage_ref)
        original = store.semantic_reference
        entered = asyncio.Event()
        release = Event()
        finished = Event()
        loop = asyncio.get_running_loop()

        def blocked_reference(identity, result_kind, schema, value):
            if result_kind == kind and not finished.is_set():
                loop.call_soon_threadsafe(entered.set)
                if not release.wait(timeout=2.0):
                    raise RuntimeError("Codec blocked the caller event loop")
                finished.set()
            return original(identity, result_kind, schema, value)

        async def stale_finish(*args, **kwargs):
            raise StaleClaimError("Synthetic replacement owner")

        monkeypatch.setattr(store, "semantic_reference", blocked_reference)
        monkeypatch.setattr(store, "finish_claim", stale_finish)
        task = asyncio.create_task(_handler(store, selection).run(_request(selection)))
        try:
            await asyncio.wait_for(entered.wait(), timeout=5.0)
            task.cancel()
            await asyncio.sleep(0)
            task.cancel()
            await asyncio.sleep(0)
            if task.done():
                pytest.fail("Handler returned before its codec finished")
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            if not finished.is_set():
                pytest.fail("Owned codec was not drained")
            if await store.get_result("report-result") is not None:
                pytest.fail("Cancelled codec published a final report")
        finally:
            release.set()
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            await store.close()

    asyncio.run(exercise())
