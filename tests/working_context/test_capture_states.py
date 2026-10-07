"""Working-context configuration, state, and bound tests."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from msgloom.working_context import (
    CaptureTimePolicy,
    FileCaptureState,
    MemoryFileSelection,
    StalePolicy,
    WorkingContextConfig,
    capture,
)

UTC = ZoneInfo("UTC")
NOW = datetime(2026, 9, 29, 9, 0, tzinfo=UTC)


def _config(
    root: Path,
    *paths: Path,
    stale_policy: StalePolicy = StalePolicy.CAPTURE,
    stale_after: float = 3600,
    per_file: int = 1024,
    total: int = 4096,
) -> WorkingContextConfig:
    return WorkingContextConfig(
        selected_files=tuple(
            MemoryFileSelection(selection_id=f"memory-{index}", path=str(path))
            for index, path in enumerate(paths)
        ),
        allowed_roots=(str(root),),
        time_policy=CaptureTimePolicy(timezone="UTC"),
        stale_policy=stale_policy,
        stale_after_seconds=stale_after,
        max_files=max(len(paths), 1),
        max_bytes_per_file=per_file,
        max_total_bytes=total,
        max_capture_seconds=2.0,
    )


def _set_time(path: Path, value: datetime) -> None:
    timestamp = value.timestamp()
    os.utime(path, (timestamp, timestamp))


def test_exact_allowlist_distinguishes_no_selection_empty_and_missing(
    tmp_path: Path,
) -> None:
    empty = tmp_path / "empty.md"
    empty.write_bytes(b"")
    _set_time(empty, NOW)

    none_snapshot = asyncio.run(capture(_config(tmp_path), NOW))
    snapshot = asyncio.run(
        capture(_config(tmp_path, empty, tmp_path / "missing.md"), NOW)
    )

    if none_snapshot.files != ():
        pytest.fail("No selection unexpectedly discovered local files")
    if snapshot.files[0].state is not FileCaptureState.EMPTY:
        pytest.fail("Selected empty file did not retain an empty state")
    if snapshot.files[0].text != "":
        pytest.fail("Selected empty file did not retain exact empty content")
    if snapshot.files[1].state is not FileCaptureState.MISSING:
        pytest.fail("Missing selected file did not remain visible")
    if snapshot.files[1].text is not None:
        pytest.fail("Missing selected file unexpectedly had content")


def test_stale_and_future_states_follow_explicit_capture_time(tmp_path: Path) -> None:
    stale = tmp_path / "stale.md"
    future = tmp_path / "future.md"
    stale.write_text("old", encoding="utf-8")
    future.write_text("future", encoding="utf-8")
    _set_time(stale, NOW - timedelta(hours=2))
    _set_time(future, NOW + timedelta(minutes=5))

    included = asyncio.run(
        capture(_config(tmp_path, stale, future, stale_after=60), NOW)
    )
    omitted = asyncio.run(
        capture(
            _config(
                tmp_path,
                stale,
                stale_policy=StalePolicy.OMIT,
                stale_after=60,
            ),
            NOW,
        )
    )

    if included.files[0].state is not FileCaptureState.STALE:
        pytest.fail("Stale file state was not retained")
    if included.files[0].text != "old":
        pytest.fail("Capture stale policy did not retain stale text")
    if included.files[1].state is not FileCaptureState.FUTURE_TIMESTAMP:
        pytest.fail("Future timestamp was not made visible")
    if omitted.files[0].text is not None:
        pytest.fail("Omit stale policy exposed stale content")


def test_utf8_encoding_and_actual_read_limits_are_enforced(tmp_path: Path) -> None:
    utf8 = tmp_path / "utf8.md"
    too_large = tmp_path / "large.md"
    malformed = tmp_path / "bad.md"
    utf8.write_text("预算 ✓", encoding="utf-8")
    too_large.write_bytes(b"abcd")
    malformed.write_bytes(b"\xff\xfe")
    for path in (utf8, too_large, malformed):
        _set_time(path, NOW)

    snapshot = asyncio.run(
        capture(
            _config(
                tmp_path,
                utf8,
                too_large,
                malformed,
                per_file=16,
                total=32,
            ),
            NOW,
        )
    )

    if snapshot.files[0].text != "预算 ✓":
        pytest.fail("Exact UTF-8 content was not captured")
    if snapshot.files[1].state is not FileCaptureState.CAPTURED:
        pytest.fail("File inside byte bound was not captured")
    if snapshot.files[2].state is not FileCaptureState.MALFORMED_ENCODING:
        pytest.fail("Malformed UTF-8 did not remain a visible state")

    limited = asyncio.run(
        capture(_config(tmp_path, too_large, per_file=3, total=3), NOW)
    )
    if limited.files[0].state is not FileCaptureState.LIMIT_EXCEEDED:
        pytest.fail("Actual read bound did not reject oversized content")
    if limited.files[0].text is not None:
        pytest.fail("Oversized content leaked through the capture result")


def test_total_byte_budget_applies_across_selected_files(tmp_path: Path) -> None:
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    first.write_bytes(b"abc")
    second.write_bytes(b"d")
    for path in (first, second):
        _set_time(path, NOW)

    snapshot = asyncio.run(
        capture(_config(tmp_path, first, second, per_file=3, total=3), NOW)
    )
    if snapshot.files[0].text != "abc":
        pytest.fail("First selected content did not consume the shared budget")
    if snapshot.files[1].state is not FileCaptureState.LIMIT_EXCEEDED:
        pytest.fail("Shared total byte budget was not enforced")


def test_config_rejects_traversal_duplicates_and_timezone_mismatch(
    tmp_path: Path,
) -> None:
    selected = tmp_path / "memory.md"
    with pytest.raises(ValidationError, match="traversal"):
        MemoryFileSelection(selection_id="bad", path=str(tmp_path / ".." / "x"))
    other = tmp_path / "other.md"
    with pytest.raises(ValidationError, match="max_files"):
        WorkingContextConfig(
            selected_files=(
                MemoryFileSelection(selection_id="a", path=str(selected)),
                MemoryFileSelection(selection_id="b", path=str(other)),
            ),
            allowed_roots=(str(tmp_path),),
            time_policy=CaptureTimePolicy(timezone="UTC"),
            stale_policy=StalePolicy.CAPTURE,
            stale_after_seconds=1.0,
            max_files=1,
            max_bytes_per_file=10,
            max_total_bytes=20,
            max_capture_seconds=1.0,
        )
    with pytest.raises(ValidationError, match="unique"):
        WorkingContextConfig(
            selected_files=(
                MemoryFileSelection(selection_id="a", path=str(selected)),
                MemoryFileSelection(selection_id="b", path=str(selected)),
            ),
            allowed_roots=(str(tmp_path),),
            time_policy=CaptureTimePolicy(timezone="UTC"),
            stale_policy=StalePolicy.CAPTURE,
            stale_after_seconds=1.0,
            max_files=2,
            max_bytes_per_file=10,
            max_total_bytes=20,
            max_capture_seconds=1.0,
        )
    config = _config(tmp_path, selected)
    with pytest.raises(ValueError, match="timezone"):
        asyncio.run(capture(config, NOW.astimezone(ZoneInfo("Australia/Sydney"))))
