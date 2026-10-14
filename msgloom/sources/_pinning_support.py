"""Runtime preflight for descriptor-pinned, symlink-safe A1 evidence readers.

A path-based fallback would lose the no-follow and inode-replacement contract.
Windows requires a separately qualified native-handle implementation; the
POSIX reader must reject it *before* opening any unpinned user-selected path.
"""

from __future__ import annotations

import os
import sys


def supports_pinned_posix_reader() -> bool:
    """Check the exact operations used by CatalogPath and EvidenceFiles."""
    return bool(
        os.name == "posix"
        and sys.platform != "win32"
        and all(
            hasattr(os, name)
            for name in (
                "O_DIRECTORY",
                "O_NOFOLLOW",
                "O_NONBLOCK",
                "supports_dir_fd",
                "supports_follow_symlinks",
            )
        )
        and os.open in os.supports_dir_fd
        and os.stat in os.supports_dir_fd
        and os.stat in os.supports_follow_symlinks
        and os.path.isdir("/dev/fd")
    )


__all__ = ["supports_pinned_posix_reader"]
