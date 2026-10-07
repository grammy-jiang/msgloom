"""Cancellation-safe blocking work and verified local evidence file access."""

from __future__ import annotations

import asyncio
import hashlib
import os
import stat
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from msgloom.preparation.contracts import SavedByteReference
from msgloom.sources._catalog import EvidenceRow
from msgloom.sources._safe_io import open_root
from msgloom.sources.models import (
    SourceEvidenceError,
    SourceEvidenceLimitError,
    SourceReferenceError,
)

_T = TypeVar("_T")


class BlockingGate:
    """Bound accepted thread work and retain ownership through cancellation."""

    def __init__(self, max_workers: int, max_queue: int) -> None:
        self._tasks: set[asyncio.Task[object]] = set()
        self._semaphore = asyncio.Semaphore(max_workers)
        self._max_queue = max_queue
        self._queued = 0
        self._closing = False
        self._closed = False

    async def run(self, function: Callable[..., _T], *args: object) -> _T:
        """Run one bounded blocking call and drain it after acceptance."""
        if self._closing or self._closed:
            raise SourceReferenceError("saved source reader is closing")
        if self._queued >= self._max_queue:
            raise SourceReferenceError("saved source reader blocking queue is full")
        self._queued += 1
        acquired = False
        try:
            await self._semaphore.acquire()
            acquired = True
        finally:
            self._queued -= 1
        if self._closing or self._closed:
            if acquired:
                self._semaphore.release()
            raise SourceReferenceError("saved source reader is closing")
        task = asyncio.create_task(asyncio.to_thread(function, *args))
        self._tasks.add(task)
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            await self._drain_after_cancel(task)
            raise
        finally:
            self._tasks.discard(task)
            self._semaphore.release()

    @staticmethod
    async def _drain_after_cancel(task: asyncio.Task[object]) -> None:
        current = asyncio.current_task()
        while True:
            try:
                await asyncio.shield(task)
                return
            except asyncio.CancelledError:
                if current is not None:
                    current.uncancel()
            except Exception:  # noqa: BLE001 -- consume accepted worker failure.
                return

    async def close(self) -> None:
        """Reject new work, drain accepted calls, then preserve cancellation."""
        if self._closed:
            return
        self._closing = True
        current = asyncio.current_task()
        cancelled = False
        for task in tuple(self._tasks):
            while True:
                try:
                    await asyncio.shield(task)
                    break
                except asyncio.CancelledError:
                    cancelled = True
                    if current is not None:
                        current.uncancel()
                except Exception:  # noqa: BLE001 -- consume failed worker.
                    break
        self._closed = True
        if cancelled:
            raise asyncio.CancelledError


class EvidenceFiles:
    """Verify A1 response files using pinned descriptor-relative roots."""

    def __init__(self, roots: tuple[Path, ...], max_bytes: int) -> None:
        self.max_bytes = max_bytes
        checked: list[tuple[Path, int]] = []
        try:
            for root in roots:
                absolute = Path(os.path.abspath(root))
                descriptor = open_root(absolute)
                checked.append((absolute, descriptor))
        except Exception:
            for _, descriptor in checked:
                os.close(descriptor)
            raise
        self.roots = tuple(checked)

    @staticmethod
    def reference(row: EvidenceRow) -> SavedByteReference:
        """Create a path-free byte reference from catalog integrity metadata."""
        return SavedByteReference(
            reference=f"a1-{row.body_kind}:{row.evidence_id}",
            sha256=row.response_body_sha256,
            byte_count=row.response_body_bytes,
        )

    def read(self, row: EvidenceRow) -> bytes:
        """Read one regular file through a pinned root and verify integrity."""
        if row.response_body_bytes > self.max_bytes:
            raise SourceEvidenceLimitError(
                "saved evidence exceeds configured byte limit"
            )
        path = Path(row.response_body_path)
        if not path.is_absolute():
            raise SourceEvidenceError("saved evidence path is not absolute")
        absolute = Path(os.path.abspath(path))
        for root, root_fd in self.roots:
            try:
                relative = absolute.relative_to(root)
            except ValueError:
                continue
            if not relative.parts:
                raise SourceEvidenceError("saved evidence path names a directory")
            return self._read_relative(root_fd, relative, row)
        raise SourceEvidenceError("saved evidence escapes configured roots")

    def _read_relative(
        self,
        root_fd: int,
        relative: Path,
        row: EvidenceRow,
    ) -> bytes:
        descriptor = os.dup(root_fd)
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        try:
            for part in relative.parts[:-1]:
                next_descriptor = os.open(
                    part,
                    directory_flags,
                    dir_fd=descriptor,
                )
                os.close(descriptor)
                descriptor = next_descriptor
            name = relative.parts[-1]
            before = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            if not stat.S_ISREG(before.st_mode):
                raise SourceEvidenceError("saved evidence is not a regular file")
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
            file_fd = os.open(name, flags, dir_fd=descriptor)
            try:
                opened = os.fstat(file_fd)
                if (
                    not stat.S_ISREG(opened.st_mode)
                    or opened.st_dev != before.st_dev
                    or opened.st_ino != before.st_ino
                ):
                    raise SourceEvidenceError("saved evidence changed during open")
                data = self._read_bounded(file_fd)
                after = os.fstat(file_fd)
                if (
                    after.st_dev != opened.st_dev
                    or after.st_ino != opened.st_ino
                    or after.st_size != opened.st_size
                    or after.st_mtime_ns != opened.st_mtime_ns
                ):
                    raise SourceEvidenceError("saved evidence changed during read")
            finally:
                os.close(file_fd)
        except SourceEvidenceError:
            raise
        except OSError:
            raise SourceEvidenceError("saved evidence cannot be read safely") from None
        finally:
            os.close(descriptor)
        if len(data) != row.response_body_bytes:
            raise SourceEvidenceError("saved evidence byte count changed")
        if hashlib.sha256(data).hexdigest() != row.response_body_sha256:
            raise SourceEvidenceError("saved evidence digest changed")
        return data

    def _read_bounded(self, descriptor: int) -> bytes:
        chunks: list[bytes] = []
        remaining = self.max_bytes + 1
        while remaining:
            chunk = os.read(descriptor, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) > self.max_bytes:
            raise SourceEvidenceLimitError(
                "saved evidence exceeds configured byte limit"
            )
        return data

    def close(self) -> None:
        """Release pinned root descriptors after accepted work is drained."""
        for _, descriptor in self.roots:
            os.close(descriptor)
        self.roots = ()

    @staticmethod
    def evidence_id(reference: SavedByteReference) -> str:
        """Decode an A1 body reference; the reader verifies its exact body kind."""
        prefix, separator, evidence_id = reference.reference.partition(":")
        if not separator or prefix not in {"a1-response", "a1-request"}:
            raise SourceReferenceError("saved byte reference is not an A1 body")
        if not evidence_id or ":" in evidence_id:
            raise SourceReferenceError("saved byte reference is malformed")
        return evidence_id
