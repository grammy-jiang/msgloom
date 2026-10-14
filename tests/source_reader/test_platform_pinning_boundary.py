"""A2 evidence safety must fail closed on platforms without pinned handles."""

import sys
from pathlib import Path

import pytest

from msgloom.sources._catalog_path import CatalogPath
from msgloom.sources._pinning_support import supports_pinned_posix_reader
from msgloom.sources._safe_io import open_root
from msgloom.sources.models import SourceEvidenceError, SourceReferenceError


def test_reader_platform_preflight_is_explicit_and_never_uses_unsafe_fallback(
    monkeypatch, tmp_path: Path
) -> None:
    """A Windows-like runtime cannot silently use non-pinned local paths."""
    with monkeypatch.context() as patch:
        patch.setattr(sys, "platform", "win32")
        if supports_pinned_posix_reader():
            pytest.fail("Windows cannot satisfy POSIX descriptor-pinning contract")
        with pytest.raises(SourceReferenceError, match="POSIX descriptor pinning"):
            CatalogPath(tmp_path / "unopened.db")
        with pytest.raises(SourceEvidenceError, match="POSIX descriptor pinning"):
            open_root(tmp_path)
    if sys.platform.startswith("linux") and not supports_pinned_posix_reader():
        pytest.fail("The qualified Linux runner lost its safe descriptor boundary")


def test_reader_requires_qualified_native_file_handles(tmp_path: Path) -> None:
    """Never attempt unverified catalog traversal on a non-POSIX platform."""
    if supports_pinned_posix_reader():
        file = tmp_path / "catalog.db"
        file.write_bytes(b"not-a-valid-db-but-a-regular-file")
        pinned = CatalogPath(file)
        try:
            if "mode=ro" not in pinned.uri():
                pytest.fail("Safe POSIX read URI lost its immutable pinned parent")
        finally:
            pinned.close()
    else:
        with pytest.raises(SourceReferenceError, match="POSIX descriptor pinning"):
            CatalogPath(tmp_path / "catalog.db")
