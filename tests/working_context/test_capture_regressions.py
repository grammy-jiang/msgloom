"""Regressions for containment, elapsed time, and public integrity."""

from __future__ import annotations

import asyncio
import importlib
import os
import threading
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from msgloom.contracts import VersionRef
from msgloom.working_context import (
    CaptureTimePolicy,
    FileCaptureState,
    MemoryFileSelection,
    StalePolicy,
    WorkingContextCodec,
    WorkingContextConfig,
    capture,
    snapshot_digest,
)

capture_module = importlib.import_module("msgloom.working_context.capture")
UTC = ZoneInfo("UTC")
SYDNEY = ZoneInfo("Australia/Sydney")


def _config(
    root: Path,
    *paths: Path,
    timezone: str = "UTC",
    stale_after: float = 1800.0,
    stale_policy: StalePolicy = StalePolicy.CAPTURE,
) -> WorkingContextConfig:
    return WorkingContextConfig(
        selected_files=tuple(
            MemoryFileSelection(selection_id=f"selected-{index}", path=str(path))
            for index, path in enumerate(paths)
        ),
        allowed_roots=(str(root),),
        time_policy=CaptureTimePolicy(timezone=timezone),
        stale_policy=stale_policy,
        stale_after_seconds=stale_after,
        max_files=max(len(paths), 1),
        max_bytes_per_file=4096,
        max_total_bytes=8192,
        max_capture_seconds=2.0,
    )


def _set_time(path: Path, value: datetime) -> None:
    timestamp = value.timestamp()
    os.utime(path, (timestamp, timestamp))


def test_root_ancestors_are_opened_without_following_symlinks(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside"
    allowed = outside / "allowed"
    allowed.mkdir(parents=True)
    selected = allowed / "memory.md"
    selected.write_text("outside", encoding="utf-8")
    alias = tmp_path / "alias"
    alias.symlink_to(outside, target_is_directory=True)

    snapshot = asyncio.run(
        capture(
            _config(alias / "allowed", alias / "allowed" / "memory.md"),
            datetime(
                2026,
                9,
                29,
                9,
                0,
                tzinfo=UTC,
            ),
        )
    )

    if snapshot.files[0].state is not FileCaptureState.PATH_UNSAFE:
        pytest.fail("Symlinked allowed-root ancestor was not rejected")
    if snapshot.files[0].text is not None:
        pytest.fail("Symlinked allowed-root ancestor exposed outside content")


def test_swapped_root_ancestor_cannot_redirect_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ancestor = tmp_path / "synthetic-ancestor"
    allowed = ancestor / "allowed"
    allowed.mkdir(parents=True)
    selected = allowed / "memory.md"
    selected.write_text("safe", encoding="utf-8")
    outside = tmp_path / "outside"
    outside_allowed = outside / "allowed"
    outside_allowed.mkdir(parents=True)
    (outside_allowed / "memory.md").write_text("outside", encoding="utf-8")
    when = datetime(2026, 9, 29, 9, 0, tzinfo=UTC)
    _set_time(selected, when)
    _set_time(outside_allowed / "memory.md", when)
    parked = tmp_path / "parked"
    original_open = capture_module.os.open
    swapped = False

    def swap_after_ancestor_open(
        path: str,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal swapped
        fd = original_open(path, flags, mode, dir_fd=dir_fd)
        if path == ancestor.name and not swapped:
            swapped = True
            ancestor.rename(parked)
            ancestor.symlink_to(outside, target_is_directory=True)
        return fd

    monkeypatch.setattr(capture_module.os, "open", swap_after_ancestor_open)
    snapshot = asyncio.run(capture(_config(allowed, selected), when))

    if snapshot.files[0].text != "safe":
        pytest.fail("Ancestor replacement redirected descriptor-relative capture")
    if snapshot.files[0].state is not FileCaptureState.CAPTURED:
        pytest.fail("Honest opened ancestor did not remain usable after rename")


def test_honest_root_components_capture_normally(tmp_path: Path) -> None:
    root = tmp_path / "one" / "two" / "allowed"
    root.mkdir(parents=True)
    selected = root / "memory.md"
    selected.write_text("synthetic", encoding="utf-8")
    when = datetime(2026, 9, 29, 9, 0, tzinfo=UTC)
    _set_time(selected, when)

    snapshot = asyncio.run(capture(_config(root, selected), when))

    if snapshot.files[0].text != "synthetic":
        pytest.fail("Descriptor-relative root traversal broke honest capture")


def test_elapsed_age_uses_instants_across_dst_transitions(tmp_path: Path) -> None:
    selected = tmp_path / "memory.md"
    selected.write_text("synthetic", encoding="utf-8")

    fall_modified = datetime(2026, 4, 5, 2, 30, tzinfo=SYDNEY, fold=0)
    fall_capture = datetime(2026, 4, 5, 2, 30, tzinfo=SYDNEY, fold=1)
    _set_time(selected, fall_modified)
    fall = asyncio.run(
        capture(
            _config(
                tmp_path,
                selected,
                timezone="Australia/Sydney",
                stale_after=1800.0,
                stale_policy=StalePolicy.OMIT,
            ),
            fall_capture,
        )
    )
    if fall.files[0].state is not FileCaptureState.STALE:
        pytest.fail("DST fallback elapsed hour was treated as zero age")

    spring_modified = datetime(2026, 10, 4, 1, 30, tzinfo=SYDNEY)
    spring_capture = datetime(2026, 10, 4, 3, 30, tzinfo=SYDNEY)
    _set_time(selected, spring_modified)
    spring = asyncio.run(
        capture(
            _config(
                tmp_path,
                selected,
                timezone="Australia/Sydney",
                stale_after=5400.0,
            ),
            spring_capture,
        )
    )
    if spring.files[0].state is not FileCaptureState.CAPTURED:
        pytest.fail("DST spring-forward wall jump overstated elapsed age")

    future = datetime(2026, 10, 4, 4, 0, tzinfo=SYDNEY)
    _set_time(selected, future)
    future_snapshot = asyncio.run(
        capture(
            _config(tmp_path, selected, timezone="Australia/Sydney"),
            spring_capture,
        )
    )
    if future_snapshot.files[0].state is not FileCaptureState.FUTURE_TIMESTAMP:
        pytest.fail("Future timestamp was not based on elapsed instants")


def test_read_oserror_is_typed_closed_and_does_not_stop_later_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")
    when = datetime(2026, 9, 29, 9, 0, tzinfo=UTC)
    _set_time(first, when)
    _set_time(second, when)
    original_read = capture_module.os.read
    failed_fd: int | None = None
    failed = False

    def fail_once(fd: int, count: int) -> bytes:
        nonlocal failed, failed_fd
        if not failed:
            failed = True
            failed_fd = fd
            raise OSError("SYNTHETIC_PRIVATE_MARKER")
        return original_read(fd, count)

    monkeypatch.setattr(capture_module.os, "read", fail_once)
    snapshot = asyncio.run(capture(_config(tmp_path, first, second), when))

    if snapshot.files[0].state is not FileCaptureState.UNREADABLE:
        pytest.fail("Read OSError did not become a typed unreadable outcome")
    if snapshot.files[1].text != "second":
        pytest.fail("Read OSError prevented a later selection from capturing")
    if "SYNTHETIC_PRIVATE_MARKER" in snapshot.files[0].limitations[0].detail:
        pytest.fail("Read exception text leaked into a limitation")
    if failed_fd is None:
        pytest.fail("Controlled read failure did not execute")
    with pytest.raises(OSError):
        os.fstat(failed_fd)


def test_fstat_oserror_is_typed_closed_and_later_file_continues(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")
    when = datetime(2026, 9, 29, 9, 0, tzinfo=UTC)
    _set_time(first, when)
    _set_time(second, when)
    original_fstat = capture_module.os.fstat
    failed_fd: int | None = None
    failed = False

    def fail_once(fd: int):
        nonlocal failed, failed_fd
        if not failed:
            failed = True
            failed_fd = fd
            raise OSError("SYNTHETIC_PRIVATE_MARKER")
        return original_fstat(fd)

    monkeypatch.setattr(capture_module.os, "fstat", fail_once)
    snapshot = asyncio.run(capture(_config(tmp_path, first, second), when))

    if snapshot.files[0].state is not FileCaptureState.UNREADABLE:
        pytest.fail("fstat OSError did not become a typed unreadable outcome")
    if snapshot.files[1].text != "second":
        pytest.fail("fstat OSError prevented a later selection from capturing")
    if failed_fd is None:
        pytest.fail("Controlled fstat failure did not execute")
    with pytest.raises(OSError):
        original_fstat(failed_fd)


def test_repeated_cancel_drains_read_error_and_closes_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = tmp_path / "memory.md"
    selected.write_text("synthetic", encoding="utf-8")
    when = datetime(2026, 9, 29, 9, 0, tzinfo=UTC)
    _set_time(selected, when)
    entered = threading.Event()
    release = threading.Event()
    failed_fd: int | None = None

    def blocked_failure(fd: int, _count: int) -> bytes:
        nonlocal failed_fd
        failed_fd = fd
        entered.set()
        release.wait(timeout=2)
        raise OSError("SYNTHETIC_PRIVATE_MARKER")

    monkeypatch.setattr(capture_module.os, "read", blocked_failure)

    async def exercise() -> None:
        task = asyncio.create_task(capture(_config(tmp_path, selected), when))
        if not await asyncio.to_thread(entered.wait, 1):
            pytest.fail("Controlled read barrier was not reached")
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()
        await asyncio.sleep(0)
        if task.done():
            pytest.fail("Cancellation returned before failed read was drained")
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(exercise())
    if failed_fd is None:
        pytest.fail("Controlled failed read did not own a descriptor")
    with pytest.raises(OSError):
        os.fstat(failed_fd)


def test_capture_revalidates_bypassed_config_before_filesystem(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = tmp_path / "memory.md"
    selected.write_text("synthetic", encoding="utf-8")
    when = datetime(2026, 9, 29, 9, 0, tzinfo=UTC)
    base = _config(tmp_path, selected)
    opened = False
    original_open = capture_module.os.open

    def record_open(*args: object, **kwargs: object) -> int:
        nonlocal opened
        opened = True
        return original_open(*args, **kwargs)

    monkeypatch.setattr(capture_module.os, "open", record_open)
    invalid = (
        base.model_copy(update={"max_files": 0}),
        base.model_copy(update={"stale_policy": "invalid"}),
        base.model_copy(
            update={
                "time_policy": base.time_policy.model_copy(
                    update={"timezone": "Invalid/Synthetic"}
                )
            }
        ),
        base.model_copy(
            update={
                "selected_files": (
                    base.selected_files[0].model_copy(update={"path": "relative"}),
                )
            }
        ),
    )
    for bypassed in invalid:
        with pytest.raises(
            ValueError,
            match="^working-context configuration is invalid$",
        ):
            asyncio.run(capture(bypassed, when))
    if opened:
        pytest.fail("Invalid bypassed configuration reached filesystem work")

    with pytest.raises(ValidationError):
        WorkingContextConfig(
            **{
                **base.model_dump(),
                "max_capture_seconds": float("inf"),
            }
        )
    with pytest.raises(ValidationError):
        WorkingContextConfig(
            **{
                **base.model_dump(),
                "future_tolerance_seconds": float("nan"),
            }
        )


def _rehash(snapshot):
    return snapshot.model_copy(update={"snapshot_sha256": snapshot_digest(snapshot)})


def test_codec_revalidates_snapshot_semantics_and_bounds(tmp_path: Path) -> None:
    selected = tmp_path / "memory.md"
    selected.write_text("synthetic", encoding="utf-8")
    when = datetime(2026, 9, 29, 9, 0, tzinfo=UTC)
    _set_time(selected, when)
    snapshot = asyncio.run(capture(_config(tmp_path, selected), when))
    item = snapshot.files[0]
    codec = WorkingContextCodec()

    missing_content = item.model_copy(
        update={"text": None, "sha256": None, "content_ref": None}
    )
    with pytest.raises(TypeError):
        codec.encode(_rehash(snapshot.model_copy(update={"files": (missing_content,)})))

    wrong_binding = item.model_copy(
        update={
            "selection_ref": VersionRef(
                "working-context-selection",
                item.selection_id,
                "wrong-version",
            )
        }
    )
    with pytest.raises(TypeError):
        codec.encode(_rehash(snapshot.model_copy(update={"files": (wrong_binding,)})))

    wrong_path = item.model_copy(update={"path": "relative"})
    with pytest.raises(TypeError):
        codec.encode(_rehash(snapshot.model_copy(update={"files": (wrong_path,)})))

    wrong_zone = snapshot.model_copy(update={"timezone": "Australia/Sydney"})
    with pytest.raises(TypeError):
        codec.encode(_rehash(wrong_zone))

    payload = codec.encode(snapshot)
    codec.max_bytes = len(payload) - 1
    with pytest.raises(TypeError, match="size bound"):
        codec.encode(snapshot)
    with pytest.raises(ValueError):
        codec.decode(payload)
