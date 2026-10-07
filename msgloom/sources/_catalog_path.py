"""Pinned read-only SQLite catalog path handling."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from urllib.parse import quote

from msgloom.sources.models import SourceReferenceError


class CatalogPath:
    """Pin catalog ancestors and reject final-file replacement."""

    def __init__(self, path: Path) -> None:
        absolute = Path(os.path.abspath(path))
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        descriptor = os.open("/", flags)
        try:
            for part in absolute.parent.parts[1:]:
                next_descriptor = os.open(part, flags, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = next_descriptor
            metadata = os.stat(
                absolute.name,
                dir_fd=descriptor,
                follow_symlinks=False,
            )
            if not stat.S_ISREG(metadata.st_mode):
                raise SourceReferenceError("catalog is not a regular file")
            file_fd = os.open(
                absolute.name,
                os.O_RDONLY | os.O_NOFOLLOW,
                dir_fd=descriptor,
            )
            try:
                opened = os.fstat(file_fd)
            finally:
                os.close(file_fd)
            if opened.st_dev != metadata.st_dev or opened.st_ino != metadata.st_ino:
                raise SourceReferenceError("catalog changed during validation")
        except (OSError, SourceReferenceError):
            os.close(descriptor)
            raise SourceReferenceError("catalog is unavailable or unsafe") from None
        self._parent_fd = descriptor
        self._name = absolute.name
        self._device = metadata.st_dev
        self._inode = metadata.st_ino

    def uri(self) -> str:
        """Return a read-only URI rooted at the pinned directory descriptor."""
        self.verify()
        path = f"/dev/fd/{self._parent_fd}/{self._name}"
        return f"file:{quote(path, safe='/')}?mode=ro"

    def verify(self) -> None:
        """Verify the catalog name still denotes the pinned regular inode."""
        try:
            metadata = os.stat(
                self._name,
                dir_fd=self._parent_fd,
                follow_symlinks=False,
            )
        except OSError:
            raise SourceReferenceError("catalog is unavailable or unsafe") from None
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_dev != self._device
            or metadata.st_ino != self._inode
        ):
            raise SourceReferenceError("catalog changed after reader construction")

    def close(self) -> None:
        """Release the pinned catalog parent descriptor."""
        if self._parent_fd >= 0:
            os.close(self._parent_fd)
            self._parent_fd = -1
