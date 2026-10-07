"""Deterministic synchronization for the native Mail ordering fixture."""

import asyncio

import pytest

from message_ingest.items.microsoft.outlook.email import (
    OutlookMailDetailItem,
    OutlookMailInventoryPageItem,
    OutlookMessageSurfaceItem,
)
from message_ingest.pipelines.microsoft.outlook.email import OutlookMailPipeline


def install_pipeline_order():
    """Delay the selected detail until its component writes have completed."""
    original = OutlookMailPipeline.process_item
    ready = {}
    completed = {}
    failures = {}

    async def delayed_detail(self, item):
        key = (
            getattr(item, "run_id", None),
            getattr(item, "selection_id", None),
            getattr(item, "message_id", None),
        )
        if key[2] != "slow":
            return await original(self, item)
        event = ready.setdefault(key, asyncio.Event())
        if isinstance(item, OutlookMailDetailItem):
            # Await actual writes outside the production pipeline write lock.
            # The subprocess watchdog bounds missing items without a second
            # wall-clock deadline that can expire during ordinary startup.
            await event.wait()
            if key in failures:
                raise RuntimeError(
                    "Component write failed before detail"
                ) from failures[key]
            print("MAIL_CONTRACT_DETAIL_PIPELINE_LAST_CONFIRMED", flush=True)
            return await original(self, item)
        # This Graph fixture has exactly one terminal inventory page. Its
        # real store transaction retains the ``attachments`` capture.
        component = (
            "attachments"
            if isinstance(item, OutlookMailInventoryPageItem)
            else (item.surface if isinstance(item, OutlookMessageSurfaceItem) else None)
        )
        try:
            result = await original(self, item)
        except BaseException as error:
            if component in {"mime", "attachments"}:
                failures[key] = error
                event.set()
            raise
        if component in {"mime", "attachments"}:
            completed.setdefault(key, set()).add(component)
            if {"mime", "attachments"} <= completed[key]:
                event.set()
        return result

    OutlookMailPipeline.process_item = delayed_detail


def test_order_barrier_waits_for_exact_successful_component_completion(monkeypatch):
    """A delayed write and another selection cannot release the detail."""

    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()
        processed = []

        async def original(self, item):
            if isinstance(item, OutlookMailInventoryPageItem):
                entered.set()
                await release.wait()
            processed.append(item)
            return item

        monkeypatch.setattr(OutlookMailPipeline, "process_item", original)
        install_pipeline_order()
        owner = object.__new__(OutlookMailPipeline)
        detail = OutlookMailDetailItem("slow", {}, "", "", None, "run", "selected")

        def surface(kind, selection="selected"):
            return OutlookMessageSurfaceItem(
                "slow", kind, "available", "", None, "run", selection_id=selection
            )

        detail_task = asyncio.create_task(
            OutlookMailPipeline.process_item(owner, detail)
        )
        await asyncio.sleep(0)
        await OutlookMailPipeline.process_item(owner, surface("mime", "other"))
        inventory = OutlookMailInventoryPageItem(
            "slow",
            "selected",
            "version",
            "parent",
            "inventory",
            "page",
            None,
            1,
            (),
            "acquired",
            "profile",
            "evidence",
            "",
            "run",
        )
        attachment = asyncio.create_task(
            OutlookMailPipeline.process_item(owner, inventory)
        )
        await entered.wait()
        try:
            if detail_task.done():
                await detail_task
                pytest.fail("Detail completed before component writes")
            release.set()
            await attachment
            if detail_task.done():
                pytest.fail("Another selection released the detail")
            await OutlookMailPipeline.process_item(owner, surface("mime"))
            await detail_task
            if processed[-1] is not detail:
                pytest.fail("Detail did not finish after component writes")
        finally:
            release.set()
            await attachment
            if not detail_task.done():
                detail_task.cancel()
            await asyncio.gather(detail_task, return_exceptions=True)

    asyncio.run(scenario())


def test_failed_component_releases_detail_without_success_marker(monkeypatch, capsys):
    """Failed component writes release the waiter and preserve failure."""

    async def scenario():
        async def original(self, item):
            raise ValueError("component failed")

        monkeypatch.setattr(OutlookMailPipeline, "process_item", original)
        install_pipeline_order()
        owner = object.__new__(OutlookMailPipeline)
        detail = OutlookMailDetailItem("slow", {}, "", "", None, "run", "selected")
        pending = asyncio.create_task(OutlookMailPipeline.process_item(owner, detail))
        await asyncio.sleep(0)
        component = OutlookMessageSurfaceItem(
            "slow", "mime", "acquired", "", None, "run", selection_id="selected"
        )
        with pytest.raises(ValueError, match="component failed"):
            await OutlookMailPipeline.process_item(owner, component)
        with pytest.raises(RuntimeError, match="Component write failed"):
            await pending

    asyncio.run(scenario())
    if "PIPELINE_LAST_CONFIRMED" in capsys.readouterr().out:
        pytest.fail("Failed component produced a successful ordering witness")
