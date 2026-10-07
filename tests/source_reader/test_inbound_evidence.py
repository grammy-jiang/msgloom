"""Verify saved inbound request evidence without inventing response bytes."""

import asyncio
import hashlib
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from msgloom.sources import SavedSourceReader, SavedSourceReaderConfig
from msgloom.sources._catalog import ReadOnlyCatalog
from msgloom.sources._io import EvidenceFiles
from msgloom.sources.models import (
    SourceEvidenceError,
    SourceReaderLimits,
    SourceReferenceError,
)


@pytest.mark.parametrize(
    ("origin", "method"), (("inbound-webhook", "POST"), ("local-gap", "LOCAL"))
)
def test_inbound_evidence_uses_request_bytes_and_rejects_tampering(
    saved_catalog: dict[str, object],
    origin: str,
    method: str,
) -> None:
    """Origin selects the body; public byte loading verifies the same capture."""
    database = Path(str(saved_catalog["database"]))
    root = Path(str(saved_catalog["evidence_root"]))
    incoming = root / "notification-request.bin"
    body = b'{"value":[{"changeType":"deleted"}]}'
    incoming.write_bytes(body)
    empty = root / "notification-empty-response.bin"
    empty.write_bytes(b"")
    with sqlite3.connect(database) as connection:
        evidence_id = connection.execute(
            "SELECT evidence_id FROM raw_http_evidence LIMIT 1"
        ).fetchone()[0]
        connection.execute(
            "UPDATE raw_http_evidence SET origin=?, request_method=?, "
            "request_body_path=?, request_body_sha256=?, request_body_bytes=?, "
            "response_url=NULL, response_status=NULL, response_body_path=?, "
            "response_body_sha256=?, response_body_bytes=0 WHERE evidence_id=?",
            (
                origin,
                method,
                str(incoming),
                hashlib.sha256(body).hexdigest(),
                len(body),
                str(empty),
                hashlib.sha256(b"").hexdigest(),
                evidence_id,
            ),
        )
    catalog = ReadOnlyCatalog(database, SourceReaderLimits())
    files = EvidenceFiles((root,), 1024)
    try:
        row = catalog.evidence(evidence_id)
        if files.read(row) != body:
            pytest.fail("Inbound evidence returned fabricated response bytes")
        reference = files.reference(row)
        if reference.reference != f"a1-request:{evidence_id}":
            pytest.fail("Inbound request was mislabeled as response evidence")
    finally:
        files.close()
        catalog.close()

    async def exercise() -> None:
        reader = SavedSourceReader(
            SavedSourceReaderConfig(catalog_path=database, evidence_roots=(root,))
        )
        try:
            if await reader.load_saved_bytes(reference) != body:
                pytest.fail("Public inbound byte loading changed original bytes")
            wrong_kind = replace(reference, reference=f"a1-response:{evidence_id}")
            with pytest.raises(SourceEvidenceError):
                await reader.load_saved_bytes(wrong_kind)
            incoming.write_bytes(b"altered notification")
            with pytest.raises(SourceEvidenceError):
                await reader.load_saved_bytes(reference)
        finally:
            await reader.close()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    ("origin", "method", "response_url", "response_status"),
    (
        ("inbound-webhook", "GET", None, None),
        ("inbound-webhook", "POST", "https://example.test/", None),
        ("inbound-webhook", "POST", None, 200),
        ("local-gap", "POST", None, None),
        ("local-gap", "LOCAL", "https://example.test/", None),
        ("local-gap", "LOCAL", None, 200),
    ),
)
def test_inbound_evidence_rejects_invalid_http_shape(
    saved_catalog: dict[str, object],
    origin: str,
    method: str,
    response_url: str | None,
    response_status: int | None,
) -> None:
    """An inbound capture cannot substitute a GET or a received response."""
    database = Path(str(saved_catalog["database"]))
    with sqlite3.connect(database) as connection:
        evidence_id = connection.execute(
            "SELECT evidence_id FROM raw_http_evidence LIMIT 1"
        ).fetchone()[0]
        connection.execute(
            "UPDATE raw_http_evidence SET origin=?, "
            "request_method=?, response_url=?, response_status=? "
            "WHERE evidence_id=?",
            (origin, method, response_url, response_status, evidence_id),
        )
    catalog = ReadOnlyCatalog(database, SourceReaderLimits())
    try:
        with pytest.raises(SourceReferenceError, match="invalid HTTP shape"):
            catalog.evidence(evidence_id)
    finally:
        catalog.close()
