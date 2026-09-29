"""Precise saved-evidence resource error typing."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from msgloom.sources import SourceEvidenceLimitError
from msgloom.sources._catalog import EvidenceRow
from msgloom.sources._io import EvidenceFiles


def test_evidence_file_byte_ceiling_has_distinct_error_type(
    tmp_path: Path,
) -> None:
    """Keep configured byte ceilings distinct from unavailable evidence."""
    root = tmp_path / "evidence"
    root.mkdir()
    content = b"synthetic-limit"
    path = root / "evidence.bin"
    path.write_bytes(content)
    row = EvidenceRow(
        "synthetic-limit",
        "synthetic-source",
        "2026-09-29T00:00:00+00:00",
        "test",
        hashlib.sha256(content).hexdigest(),
        str(path),
        len(content),
    )
    files = EvidenceFiles((root,), len(content) - 1)
    try:
        with pytest.raises(SourceEvidenceLimitError):
            files.read(row)
    finally:
        files.close()
