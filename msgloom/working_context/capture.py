"""Bounded descriptor-based capture for selected local working context."""

from __future__ import annotations

import asyncio
import errno
import os
import stat
import time
from datetime import datetime
from functools import partial
from hashlib import sha256
from pathlib import PurePath
from zoneinfo import ZoneInfo

from msgloom.contracts import VersionRef
from msgloom.working_context.codec import (
    configuration_ref,
    snapshot_digest,
    validate_configuration,
)
from msgloom.working_context.models import (
    CapturedMemoryFile,
    FileCaptureState,
    MemoryFileSelection,
    StalePolicy,
    WorkingContextConfig,
    WorkingContextLimitation,
    WorkingContextSnapshot,
)

_CHUNK_SIZE = 64 * 1024


async def capture(
    config: WorkingContextConfig,
    capture_time: datetime,
) -> WorkingContextSnapshot:
    """
    Capture exactly selected files and drain accepted work on cancellation.

    One worker owns descriptor opening, bounded reads, and closure for the
    complete snapshot. Cancellation is re-raised only after that worker ends.
    """
    validated_config = validate_configuration(config)
    _validate_capture_time(validated_config, capture_time)
    task = asyncio.create_task(
        asyncio.to_thread(partial(_capture_sync, validated_config, capture_time))
    )
    result, cancelled = await _await_task_uninterrupted(task)
    if cancelled:
        raise asyncio.CancelledError
    return result


async def _await_task_uninterrupted[T](
    task: asyncio.Task[T],
) -> tuple[T, bool]:
    """Drain one owned task despite repeated cancellation."""
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
    if task.cancelled():
        raise asyncio.CancelledError
    error = task.exception()
    if error is not None:
        raise error
    return task.result(), cancelled


def _validate_capture_time(
    config: WorkingContextConfig,
    capture_time: datetime,
) -> None:
    if capture_time.tzinfo is None or capture_time.utcoffset() is None:
        raise ValueError("capture_time must be timezone-aware")
    if capture_time.tzinfo != ZoneInfo(config.time_policy.timezone):
        raise ValueError("capture_time timezone must match configured timezone policy")


def _capture_sync(
    config: WorkingContextConfig,
    capture_time: datetime,
) -> WorkingContextSnapshot:
    deadline = time.monotonic() + config.max_capture_seconds
    config_ref = configuration_ref(config)
    files: list[CapturedMemoryFile] = []
    total = 0
    for selection in config.selected_files:
        remaining = config.max_total_bytes - total
        item = _capture_one(
            config,
            config_ref,
            selection,
            capture_time,
            deadline,
            remaining,
        )
        files.append(item)
        if item.text is not None and item.byte_count is not None:
            total += item.byte_count
    provisional = WorkingContextSnapshot(
        configuration_ref=config_ref,
        capture_time=capture_time,
        timezone=config.time_policy.timezone,
        files=tuple(files),
        snapshot_sha256="0" * 64,
    )
    return WorkingContextSnapshot(
        configuration_ref=provisional.configuration_ref,
        capture_time=provisional.capture_time,
        timezone=provisional.timezone,
        files=provisional.files,
        snapshot_sha256=snapshot_digest(provisional),
    )


def _capture_one(
    config: WorkingContextConfig,
    config_ref: VersionRef,
    selection: MemoryFileSelection,
    capture_time: datetime,
    deadline: float,
    remaining_total: int,
) -> CapturedMemoryFile:
    selection_ref = VersionRef(
        "working-context-selection",
        selection.selection_id,
        config_ref.version,
    )
    if time.monotonic() >= deadline:
        return _unavailable(selection, selection_ref, FileCaptureState.TIMED_OUT)
    root, parts = _contained_parts(selection.path, config.allowed_roots)
    if root is None:
        return _unavailable(selection, selection_ref, FileCaptureState.PATH_UNSAFE)
    try:
        fd = _open_beneath(root, parts)
    except OSError as exc:
        return _open_failure(selection, selection_ref, exc)
    try:
        try:
            return _read_open_file(
                fd,
                config,
                selection,
                selection_ref,
                capture_time,
                deadline,
                remaining_total,
            )
        except OSError:
            return _unavailable(
                selection,
                selection_ref,
                FileCaptureState.UNREADABLE,
            )
    finally:
        try:
            os.close(fd)
        except OSError:
            pass


def _read_open_file(
    fd: int,
    config: WorkingContextConfig,
    selection: MemoryFileSelection,
    selection_ref: VersionRef,
    capture_time: datetime,
    deadline: float,
    remaining_total: int,
) -> CapturedMemoryFile:
    before = os.fstat(fd)
    if not stat.S_ISREG(before.st_mode):
        return _unavailable(selection, selection_ref, FileCaptureState.NOT_REGULAR)
    modified = datetime.fromtimestamp(before.st_mtime, tz=capture_time.tzinfo)
    age = capture_time.timestamp() - before.st_mtime
    stale = age > config.stale_after_seconds
    future = age < -config.future_tolerance_seconds
    if stale and config.stale_policy is StalePolicy.OMIT:
        return _metadata_only(
            selection,
            selection_ref,
            FileCaptureState.STALE,
            modified,
            before.st_size,
        )
    allowed = min(config.max_bytes_per_file, max(remaining_total, 0))
    if allowed < 1 and before.st_size:
        return _metadata_only(
            selection,
            selection_ref,
            FileCaptureState.LIMIT_EXCEEDED,
            modified,
            before.st_size,
        )
    payload = _bounded_read(fd, allowed, deadline)
    after = os.fstat(fd)
    if _changed(before, after):
        return _metadata_only(
            selection,
            selection_ref,
            FileCaptureState.CHANGED_DURING_READ,
            modified,
            after.st_size,
        )
    if payload is None:
        return _metadata_only(
            selection,
            selection_ref,
            FileCaptureState.TIMED_OUT,
            modified,
            after.st_size,
        )
    if len(payload) > allowed:
        return _metadata_only(
            selection,
            selection_ref,
            FileCaptureState.LIMIT_EXCEEDED,
            modified,
            after.st_size,
        )
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return _metadata_only(
            selection,
            selection_ref,
            FileCaptureState.MALFORMED_ENCODING,
            modified,
            len(payload),
        )
    digest = sha256(payload).hexdigest()
    state = FileCaptureState.EMPTY if not payload else FileCaptureState.CAPTURED
    if stale:
        state = FileCaptureState.STALE
    elif future:
        state = FileCaptureState.FUTURE_TIMESTAMP
    return CapturedMemoryFile(
        selection_id=selection.selection_id,
        path=selection.path,
        selection_ref=selection_ref,
        state=state,
        modified_at=modified,
        byte_count=len(payload),
        sha256=digest,
        content_ref=VersionRef(
            "working-context-content",
            selection.selection_id,
            digest,
        ),
        text=text,
    )


def _contained_parts(
    path: str,
    roots: tuple[str, ...],
) -> tuple[str | None, tuple[str, ...]]:
    normalized = os.path.normpath(path)
    candidates: list[tuple[int, str, tuple[str, ...]]] = []
    for root in roots:
        normalized_root = os.path.normpath(root)
        try:
            if os.path.commonpath((normalized, normalized_root)) != normalized_root:
                continue
        except ValueError:
            continue
        relative = os.path.relpath(normalized, normalized_root)
        parts = () if relative == "." else PurePath(relative).parts
        if any(part in {"", ".", ".."} for part in parts):
            continue
        candidates.append((len(normalized_root), normalized_root, parts))
    if not candidates:
        return None, ()
    _length, root, parts = max(candidates, key=lambda item: item[0])
    return root, parts


def _open_beneath(root: str, parts: tuple[str, ...]) -> int:
    """Open from the filesystem anchor without following any component."""
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    current = os.open("/", directory_flags)
    try:
        root_parts = tuple(
            part
            for part in PurePath(os.path.normpath(root)).parts
            if part not in {"/", ""}
        )
        for part in root_parts:
            child = os.open(part, directory_flags, dir_fd=current)
            os.close(current)
            current = child
        if not parts:
            return os.dup(current)
        for part in parts[:-1]:
            child = os.open(part, directory_flags, dir_fd=current)
            os.close(current)
            current = child
        return os.open(
            parts[-1],
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=current,
        )
    finally:
        os.close(current)


def _bounded_read(fd: int, allowed: int, deadline: float) -> bytes | None:
    chunks: list[bytes] = []
    remaining = allowed + 1
    while remaining > 0:
        if time.monotonic() >= deadline:
            return None
        chunk = os.read(fd, min(_CHUNK_SIZE, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _changed(before: os.stat_result, after: os.stat_result) -> bool:
    return (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )


def _open_failure(
    selection: MemoryFileSelection,
    selection_ref: VersionRef,
    exc: OSError,
) -> CapturedMemoryFile:
    if exc.errno == errno.ENOENT:
        state = FileCaptureState.MISSING
    elif exc.errno in {errno.EACCES, errno.EPERM}:
        state = FileCaptureState.UNREADABLE
    elif exc.errno in {errno.ELOOP, errno.ENOTDIR}:
        state = FileCaptureState.PATH_UNSAFE
    else:
        state = FileCaptureState.UNREADABLE
    return _unavailable(selection, selection_ref, state)


def _metadata_only(
    selection: MemoryFileSelection,
    selection_ref: VersionRef,
    state: FileCaptureState,
    modified_at: datetime,
    byte_count: int,
) -> CapturedMemoryFile:
    return CapturedMemoryFile(
        selection_id=selection.selection_id,
        path=selection.path,
        selection_ref=selection_ref,
        state=state,
        modified_at=modified_at,
        byte_count=byte_count,
        limitations=(_limitation(state),),
    )


def _unavailable(
    selection: MemoryFileSelection,
    selection_ref: VersionRef,
    state: FileCaptureState,
) -> CapturedMemoryFile:
    return CapturedMemoryFile(
        selection_id=selection.selection_id,
        path=selection.path,
        selection_ref=selection_ref,
        state=state,
        limitations=(_limitation(state),),
    )


def _limitation(state: FileCaptureState) -> WorkingContextLimitation:
    details = {
        FileCaptureState.MISSING: "selected file was not present",
        FileCaptureState.STALE: "selected file was stale under configured policy",
        FileCaptureState.UNREADABLE: "selected file could not be read",
        FileCaptureState.CHANGED_DURING_READ: "selected file changed during capture",
        FileCaptureState.MALFORMED_ENCODING: "selected file was not valid UTF-8",
        FileCaptureState.LIMIT_EXCEEDED: "selected file exceeded capture byte bounds",
        FileCaptureState.PATH_UNSAFE: "selected path failed containment checks",
        FileCaptureState.NOT_REGULAR: "selected path was not a regular file",
        FileCaptureState.TIMED_OUT: "capture time bound expired",
    }
    return WorkingContextLimitation(
        code=state.value,
        detail=details.get(state, "selected content is unavailable"),
    )
