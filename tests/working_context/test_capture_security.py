"""Descriptor safety, cancellation ownership, replay, and codec tests."""

from __future__ import annotations

import asyncio
import importlib
import os
import threading
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from msgloom.persistence import SemanticDataRegistry
from msgloom.working_context import (
    CaptureTimePolicy,
    FileCaptureState,
    MemoryFileSelection,
    StalePolicy,
    WorkingContextCodec,
    WorkingContextConfig,
    capture,
    configuration_ref,
    snapshot_ref,
)

capture_module = importlib.import_module("msgloom.working_context.capture")
UTC = ZoneInfo("UTC")
NOW = datetime(2026, 9, 29, 9, 0, tzinfo=UTC)


def _config(
    root: Path,
    *paths: Path,
    max_seconds: float = 2.0,
) -> WorkingContextConfig:
    return WorkingContextConfig(
        selected_files=tuple(
            MemoryFileSelection(selection_id=f"selected-{index}", path=str(path))
            for index, path in enumerate(paths)
        ),
        allowed_roots=(str(root),),
        time_policy=CaptureTimePolicy(timezone="UTC"),
        stale_policy=StalePolicy.CAPTURE,
        stale_after_seconds=3600.0,
        max_files=max(len(paths), 1),
        max_bytes_per_file=4096,
        max_total_bytes=8192,
        max_capture_seconds=max_seconds,
    )


def _set_now(path: Path) -> None:
    timestamp = NOW.timestamp()
    os.utime(path, (timestamp, timestamp))


def test_symlink_directory_and_fifo_are_rejected_without_following(
    tmp_path: Path,
) -> None:
    root = tmp_path / "allowed"
    root.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("secret", encoding="utf-8")
    link = root / "link.md"
    link.symlink_to(outside)
    directory = root / "directory"
    directory.mkdir()
    fifo = root / "pipe"
    os.mkfifo(fifo)

    snapshot = asyncio.run(capture(_config(root, link, directory, fifo), NOW))

    if snapshot.files[0].state is not FileCaptureState.PATH_UNSAFE:
        pytest.fail("Symlink selection was followed")
    if snapshot.files[1].state is not FileCaptureState.NOT_REGULAR:
        pytest.fail("Directory selection was not rejected")
    if snapshot.files[2].state is not FileCaptureState.NOT_REGULAR:
        pytest.fail("FIFO selection was not rejected")
    for item in snapshot.files:
        for limitation in item.limitations:
            if str(tmp_path) in limitation.detail:
                pytest.fail("Private absolute path leaked into limitation detail")


def test_symlink_swap_after_open_cannot_change_captured_inode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "allowed"
    root.mkdir()
    selected = root / "memory.md"
    selected.write_text("safe", encoding="utf-8")
    _set_now(selected)
    outside = tmp_path / "outside.md"
    outside.write_text("secret", encoding="utf-8")
    original_read = capture_module.os.read
    swapped = False

    def swap_then_read(fd: int, count: int) -> bytes:
        nonlocal swapped
        if not swapped:
            swapped = True
            selected.rename(root / "opened.md")
            selected.symlink_to(outside)
        return original_read(fd, count)

    monkeypatch.setattr(capture_module.os, "read", swap_then_read)
    snapshot = asyncio.run(capture(_config(root, selected), NOW))

    if snapshot.files[0].state is not FileCaptureState.CHANGED_DURING_READ:
        pytest.fail("Path swap was not surfaced as a changed capture")
    if snapshot.files[0].text is not None:
        pytest.fail("Path swap content was accepted after metadata changed")


def test_changed_during_read_discards_inconsistent_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = tmp_path / "memory.md"
    selected.write_text("before", encoding="utf-8")
    _set_now(selected)
    original_read = capture_module.os.read
    changed = False

    def change_then_read(fd: int, count: int) -> bytes:
        nonlocal changed
        if not changed:
            changed = True
            with selected.open("a", encoding="utf-8") as stream:
                stream.write("-changed")
        return original_read(fd, count)

    monkeypatch.setattr(capture_module.os, "read", change_then_read)
    snapshot = asyncio.run(capture(_config(tmp_path, selected), NOW))

    if snapshot.files[0].state is not FileCaptureState.CHANGED_DURING_READ:
        pytest.fail("Concurrent source mutation was not detected")
    if snapshot.files[0].text is not None:
        pytest.fail("Changed-during-read content was accepted")


def test_unreadable_and_elapsed_time_bound_are_visible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = tmp_path / "memory.md"
    selected.write_text("bounded", encoding="utf-8")
    _set_now(selected)
    config = _config(tmp_path, selected)

    def denied(_root: str, _parts: tuple[str, ...]) -> int:
        raise PermissionError(13, "synthetic denied")

    monkeypatch.setattr(capture_module, "_open_beneath", denied)
    unreadable = asyncio.run(capture(config, NOW))
    if unreadable.files[0].state is not FileCaptureState.UNREADABLE:
        pytest.fail("Unreadable selected file did not remain visible")
    if str(selected) in unreadable.files[0].limitations[0].detail:
        pytest.fail("Unreadable limitation leaked a private absolute path")

    monkeypatch.undo()
    original_open = capture_module._open_beneath

    def slow_open(root: str, parts: tuple[str, ...]) -> int:
        capture_module.time.sleep(0.01)
        return original_open(root, parts)

    monkeypatch.setattr(capture_module, "_open_beneath", slow_open)
    timed_out = asyncio.run(
        capture(_config(tmp_path, selected, max_seconds=0.001), NOW)
    )
    if timed_out.files[0].state is not FileCaptureState.TIMED_OUT:
        pytest.fail("Elapsed capture bound did not stop later file work")


def test_capture_drains_worker_through_repeated_cancellation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entered = threading.Event()
    release = threading.Event()
    finished = threading.Event()
    original = capture_module._capture_sync
    config = _config(tmp_path)

    def blocked(
        selected_config: WorkingContextConfig,
        selected_time: datetime,
    ):
        entered.set()
        release.wait(timeout=2)
        try:
            return original(selected_config, selected_time)
        finally:
            finished.set()

    monkeypatch.setattr(capture_module, "_capture_sync", blocked)

    async def exercise() -> None:
        task = asyncio.create_task(capture(config, NOW))
        if not await asyncio.to_thread(entered.wait, 1):
            pytest.fail("Capture worker did not enter the controlled barrier")
        responsive = False

        async def tick() -> None:
            nonlocal responsive
            await asyncio.sleep(0)
            responsive = True

        tick_task = asyncio.create_task(tick())
        await tick_task
        if not responsive:
            pytest.fail("Event loop did not remain responsive")
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()
        await asyncio.sleep(0)
        if task.done():
            pytest.fail("Cancelled capture returned before owned worker drained")
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        if not finished.is_set():
            pytest.fail("Capture returned cancellation before worker completion")

    asyncio.run(exercise())


def test_replay_hash_codec_and_validation_bypass(tmp_path: Path) -> None:
    selected = tmp_path / "memory.md"
    selected.write_text("exact text", encoding="utf-8")
    _set_now(selected)
    config = _config(tmp_path, selected)

    first = asyncio.run(capture(config, NOW))
    replay = asyncio.run(capture(config, NOW))
    later = asyncio.run(capture(config, datetime(2026, 9, 29, 9, 1, tzinfo=UTC)))

    if first != replay:
        pytest.fail("Exact replay did not produce an identical snapshot")
    if snapshot_ref(first) != snapshot_ref(replay):
        pytest.fail("Exact replay changed snapshot version")
    if first.snapshot_sha256 == later.snapshot_sha256:
        pytest.fail("Capture time did not affect the exact snapshot version")
    if first.configuration_ref != configuration_ref(config):
        pytest.fail("Snapshot lost exact configuration version")

    codec = WorkingContextCodec()
    registry = SemanticDataRegistry((codec,))
    semantic_ref = registry.reference(
        "working-context:synthetic",
        "working_context",
        "1",
        first,
    )
    encoded = registry.encode_for_reference(semantic_ref, first)
    if registry.decode(semantic_ref, encoded.payload) != first:
        pytest.fail("Codec was not compatible with SemanticDataRegistry")

    payload = codec.encode(first)
    if codec.decode(payload) != first:
        pytest.fail("Working-context codec did not round trip exactly")

    bypassed = first.model_copy(update={"capture_time": later.capture_time})
    with pytest.raises(TypeError, match="digest"):
        codec.encode(bypassed)

    corrupted = payload.replace(b"exact text", b"other text")
    with pytest.raises(ValueError):
        codec.decode(corrupted)
