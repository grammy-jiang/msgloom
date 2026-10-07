"""R3 cancellation lifecycle regression."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from msgloom.reporting import RendererConfig, ReportBuildHandler
from tests.reporting.helpers import (
    open_store,
    plan,
    policy,
    save_triage,
    topic,
    triage_data,
)
from tests.reporting.test_handler import _config, _request


def test_repeated_cancellation_drains_render_and_retains_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Repeated cancellation drains owned rendering and preserves durable evidence."""

    async def exercise() -> None:
        from time import sleep

        import msgloom.reporting.handler as handler_module

        store = await open_store(tmp_path / "repeat-cancel.sqlite3")
        triage_ref = await save_triage(store, triage_data(topic()))
        selection = plan(triage_ref)
        original = handler_module.render_report

        def slow_render(*args: object, **kwargs: object) -> object:
            sleep(0.15)
            return original(*args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(handler_module, "render_report", slow_render)
        task = asyncio.create_task(
            ReportBuildHandler(
                policy=policy(),
                selection_plan=selection,
                persistence=store,
                renderer_config=RendererConfig(
                    max_part_bytes=100_000, max_total_bytes=300_000, max_parts=8
                ),
                config=_config("repeat-cancel-report"),
            ).run(_request(selection, "repeat-cancel-execution"))
        )
        for _ in range(100):
            if await store.get_result("selection-repeat-cancel-report") is not None:
                break
            await asyncio.sleep(0.005)
        task.cancel()
        await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        if await store.get_result("selection-repeat-cancel-report") is None:
            pytest.fail("repeated cancellation lost frozen selection evidence")
        if await store.get_result("repeat-cancel-report") is not None:
            pytest.fail("cancelled rendering published a final report")
        await store.close()

    asyncio.run(exercise())
