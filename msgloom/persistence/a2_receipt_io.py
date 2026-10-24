"""
Small file helpers of the receipt store (C0-14a), PROVISIONAL.

Writes are all-or-nothing. A file is written in full under a private
temporary name, checked for its exact size, flushed with ``fsync`` and
published with ``os.link``, which fails if the final name exists. The
containing directory is then flushed with ``fsync`` so the new name
survives a crash.

Platform guard: Windows cannot open a directory for ``fsync``. There
:func:`fsync_directory` does nothing, and durability of a new name is not
guaranteed. On POSIX every directory ``fsync`` error is surfaced. Errors
use the fixed reason codes of :mod:`msgloom.persistence.a2_receipt_errors`.
"""

from __future__ import annotations

import os
import secrets
import stat
import sys
from contextlib import suppress
from pathlib import Path

from msgloom.persistence.a2_receipt_errors import (
    A2ReceiptBoundError,
    A2ReceiptError,
)


def fsync_directory(path: Path) -> None:
    """Flush a directory entry to disk. Raise ``OSError`` on failure."""
    if sys.platform == "win32":  # pragma: no cover - platform guard
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    fd = os.open(path, flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def read_bounded(path: Path, limit: int) -> bytes | None:
    """
    Return the content of a regular file of at most ``limit`` bytes.

    Return ``None`` if the file is absent. Never follow a final symlink.
    Never block on a FIFO or other special file: it raises ``read-failed``.
    Read until end of file or ``limit + 1`` bytes, because one ``os.read``
    may return fewer bytes than asked.
    """
    # O_NONBLOCK: opening a FIFO must not wait. S_ISREG then rejects it.
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(path, flags)
    except FileNotFoundError:
        return None
    except OSError:
        raise A2ReceiptError("read-failed") from None
    chunks: list[bytes] = []
    total = 0
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise A2ReceiptError("read-failed")
        while total <= limit:
            chunk = os.read(fd, limit + 1 - total)
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
    except OSError:
        raise A2ReceiptError("read-failed") from None
    finally:
        os.close(fd)
    if total > limit:
        raise A2ReceiptBoundError("stored-too-large")
    return b"".join(chunks)


def _write_all(fd: int, data: bytes) -> None:
    """Write every byte of ``data`` or raise ``OSError``."""
    view = memoryview(data)
    written = 0
    while written < len(data):
        count = os.write(fd, view[written:])
        if count <= 0 or count > len(data) - written:
            raise OSError("write made no valid progress")
        written += count
    if os.fstat(fd).st_size != len(data):
        raise OSError("stored size differs from the data size")


def create_once(directory: Path, name: str, data: bytes) -> bool:
    """
    Publish ``data`` as ``name`` unless it exists; return whether it was new.

    A failure before the link leaves no final file. The temporary file is
    removed on every exit path. A directory ``fsync`` failure after the
    link raises ``write-failed``. The complete file stays. A retry that finds
    the name already linked flushes the directory again before it reports
    a replay. The caller must do the same on a replay path that returns
    before this function runs (``append_claim`` does).
    """
    temp = directory / f".tmp-{secrets.token_hex(8)}"
    try:
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            _write_all(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)
        try:
            os.link(temp, directory / name)
        except FileExistsError:
            fsync_directory(directory)
            return False
        fsync_directory(directory)
        return True
    except OSError:
        raise A2ReceiptError("write-failed") from None
    finally:
        with suppress(OSError):
            temp.unlink()
