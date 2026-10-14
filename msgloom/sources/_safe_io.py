"""Descriptor-relative containment helpers."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from msgloom.sources._pinning_support import supports_pinned_posix_reader
from msgloom.sources.models import SourceEvidenceError


def open_root(path: Path) -> int:
    """Open every root component without following symbolic links."""
    if not supports_pinned_posix_reader():
        raise SourceEvidenceError(
            "secure evidence roots require POSIX descriptor pinning; "
            "Windows native-handle support is not qualified"
        )
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open("/", flags)
    try:
        for part in Path(os.path.abspath(path)).parts[1:]:
            next_descriptor = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise SourceEvidenceError("configured evidence root is not a directory")
        return descriptor
    except (OSError, SourceEvidenceError):
        os.close(descriptor)
        raise SourceEvidenceError("configured evidence root is unsafe") from None
